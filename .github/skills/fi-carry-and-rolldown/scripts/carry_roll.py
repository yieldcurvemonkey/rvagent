"""Carry, roll-down and carry/vol for swaps, bonds (repo financed) and bond-futures basis.

Sign convention everywhere: receiver / long duration / long bond is POSITIVE. Rates in percent in, bp out.
Scenario: curve UNCHANGED (frozen) over the horizon. carry = F(h, T-h) - S(T); roll = S(T) - S(T-h);
total = carry + roll = F(h, T-h) - S(T-h). Forward-starting swaps have zero carry; roll ages the START.

Simplified single-curve model (annual or semi-annual fixed leg, accrual 1/m, no calendars or day counts).
Use it for screening and for known-answer checks. For trading numbers use the dated curve (curve_zero) from
fi-curve-construction and the conventions in swap_conventions.

CLI:  python carry_roll.py --par curve_par.csv --curve USD-SOFR --date 2026-11-10 --h 0.25 \
          --tenors 2,5,10,30 --structures 2s10s,2s5s10s
      python carry_roll.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.optimize import brentq


# ----------------------------------------------------------------------------- curve
class Curve:
    """Par curve (percent, indexed by tenor in years) -> bootstrapped discount factors on a 1/freq grid."""

    def __init__(self, par_pct: pd.Series, freq: int = 1, interp: str = "pchip"):
        s = par_pct.dropna().sort_index()
        if len(s) < 2:
            raise ValueError("need at least two par points")
        self.freq, self.a = int(freq), 1.0 / int(freq)
        self.max_t = float(s.index[-1])
        x, y = s.index.to_numpy(float), s.to_numpy(float)
        if interp == "cubic" and len(s) >= 4:
            f = CubicSpline(x, y, bc_type="natural")
        elif interp == "linear" or (interp == "cubic" and len(s) < 4):
            f = lambda t: np.interp(t, x, y)  # noqa: E731
        else:  # pchip: shape preserving, no spurious humps between knots (fake roll)
            f = PchipInterpolator(x, y, extrapolate=False)
        grid = np.arange(1, int(round(self.max_t * self.freq)) + 1) * self.a
        par = np.asarray(f(np.clip(grid, x[0], x[-1])), float) / 100.0
        dfs, ann = [], 0.0
        for k, S in enumerate(par):
            df = (1.0 - S * self.a * ann) / (1.0 + S * self.a)
            dfs.append(df)
            ann += df
        self._t = np.concatenate([[0.0], grid])
        self._lndf = np.log(np.concatenate([[1.0], dfs]))

    def df(self, t: float) -> float:
        if t < -1e-12 or t > self.max_t + 1e-9:
            raise ValueError(f"time {t} outside curve (0..{self.max_t})")
        return float(np.exp(np.interp(t, self._t, self._lndf)))

    def _sched(self, start: float, tenor: float):
        """Payment times (backward from the end, so any stub is at the front) and accruals."""
        end, times, t = start + tenor, [], start + tenor
        while t > start + 1e-9:
            times.append(t)
            t -= self.a
        times = times[::-1]
        prev = [start] + times[:-1]
        return times, [b - a for a, b in zip(prev, times)]

    def annuity(self, start: float, tenor: float) -> float:
        """sum accrual*DF per unit notional; DV01 per 1 notional = annuity * 1e-4."""
        times, acc = self._sched(start, tenor)
        return sum(a * self.df(t) for t, a in zip(times, acc))

    def par(self, start: float, tenor: float) -> float:
        """Par swap rate in percent for a swap starting `start` years forward, length `tenor` years."""
        return 100.0 * (self.df(start) - self.df(start + tenor)) / self.annuity(start, tenor)


# ----------------------------------------------------------------------------- swaps
def carry_roll(curve: Curve, start: float, tenor: float, h: float) -> dict:
    """Receiver-positive carry / roll / total in bp for one swap leg over horizon h (years), curve frozen.

    start == 0 : carry = F(h, T-h) - S(T); roll = S(T) - S(T-h).
    start  > 0 : carry = 0 (no float fixing known); roll = S(start, T) - S(start-h, T) (start aged, end moves
                 with it). If h > start the aged swap is spot-starting with the remaining tail and the first
                 fixing becomes known; that carry is NOT counted, so prefer h <= start for forward starters.
    """
    if tenor - h <= 1e-9 and start == 0:
        raise ValueError("horizon must be shorter than the swap tenor")
    if start == 0:
        S, S_aged, F = curve.par(0, tenor), curve.par(0, tenor - h), curve.par(h, tenor - h)
        carry, roll = F - S, S - S_aged
    else:
        new_start = max(start - h, 0.0)
        new_len = start + tenor - h - new_start
        carry, roll = 0.0, curve.par(start, tenor) - curve.par(new_start, new_len)
    return {"carry_bp": 100 * carry, "roll_bp": 100 * roll, "total_bp": 100 * (carry + roll)}


def structure_carry_roll(curve: Curve, legs: dict, h: float) -> dict:
    """legs: {(start, tenor): weight}. Weights are DV01 weights (receive = +), so bp add without scaling.
    2s10s steepener (long the 10y-2y spread) = receive 2y, pay 10y = {(0,2): +1, (0,10): -1};
    fly 2s5s10s receive belly = {(0,2): -1, (0,5): +2, (0,10): -1} (= SHORT the fly level 2*5y-2y-10y)."""
    out = {"carry_bp": 0.0, "roll_bp": 0.0, "total_bp": 0.0}
    for (s, t), w in legs.items():
        r = carry_roll(curve, s, t, h)
        for k in out:
            out[k] += w * r[k]
    return out


def carry_from_fixing(swap_pct: float, fixing_pct: float, df_h: float, accrual: float, fwd_annuity: float) -> float:
    """Running carry in bp from the fixing shortcut: DF(h)*(S - fix)*accrual / annuity(fwd swap).
    Valid ONLY for a horizon equal to the first fixing period (equals F(h,T-h) - S(T) then)."""
    return 100.0 * df_h * (swap_pct - fixing_pct) * accrual / fwd_annuity


def zero_carry_roll(z_pct: dict, T: int, h: int = 1) -> dict:
    """Annual-compounding zero curve {year: zero %}: Ilmanen rolling-yield split. Receiver/long positive."""
    f = (((1 + z_pct[T] / 100) ** T / (1 + z_pct[h] / 100) ** h) ** (1 / (T - h)) - 1) * 100
    return {"fwd_pct": f, "carry": f - z_pct[T], "roll": z_pct[T] - z_pct[T - h], "total": f - z_pct[T - h]}


# ----------------------------------------------------------------------------- bonds
def bond_carry_price(clean: float, accrued: float, coupon_pct: float, freq: int, repo_pct: float,
                     d1: float, dcoup1: float, d2: float = 0.0, dcoup2: float | None = None, basis: float = 360.0) -> dict:
    """Carry per 100 face (price units): coupon income - financing at TERM repo (Burghardt, App. B).
    d1 = days settle -> delivery (or -> coupon date if d2 > 0); dcoup1 = days in that coupon period;
    d2 = days from the intervening coupon to delivery, dcoup2 = days in the next coupon period."""
    c = coupon_pct / freq
    r = repo_pct / 100.0
    if d2 > 0:
        inc = c * (d1 / dcoup1 + d2 / dcoup2)
        fin = (clean + accrued) * r * d1 / basis + clean * r * d2 / basis
    else:
        inc = c * d1 / dcoup1
        fin = (clean + accrued) * r * d1 / basis
    return {"coupon_income": inc, "financing": fin, "carry": inc - fin}


def forward_clean_price(clean: float, accrued0: float, repo_pct: float, days: float, accrued_fwd: float,
                        coupons: tuple = (), basis: float = 360.0) -> dict:
    """Forward price by repo carry. coupons = ((amount, days_from_coupon_date_to_forward_date), ...).
    full_fwd = (P + AI)(1 + r d/basis) - sum c (1 + r dd/basis); flat_fwd = full_fwd - AI_fwd. 'Forward drop' = P - flat_fwd."""
    r = repo_pct / 100.0
    full = (clean + accrued0) * (1 + r * days / basis) - sum(c * (1 + r * dd / basis) for c, dd in coupons)
    flat = full - accrued_fwd
    return {"full_fwd": full, "flat_fwd": flat, "drop": clean - flat}


def bond_dirty_from_yield(y_pct: float, coupon_pct: float, f: float, n: int, m: int = 2) -> float:
    """Street-convention dirty price. f = fraction of a coupon period to the next coupon (0<f<=1), n = coupons left."""
    y, c = y_pct / 100.0 / m, coupon_pct / m
    k = np.arange(n)
    return float(np.sum(c / (1 + y) ** (f + k)) + 100.0 / (1 + y) ** (f + n - 1))


def bond_yield_from_dirty(dirty: float, coupon_pct: float, f: float, n: int, m: int = 2) -> float:
    return brentq(lambda y: bond_dirty_from_yield(y, coupon_pct, f, n, m) - dirty, -20.0, 100.0, xtol=1e-12)


def bond_carry_yield(clean: float, coupon_pct: float, f: float, n: int, m: int, repo_pct: float, h: float) -> dict:
    """Yield-space carry of a long bond over horizon h years at term repo (simple, h*repo accrual):
    carry_bp = y_fwd - y_spot (positive when yield > repo). Coupons paid inside the horizon are carried at repo.
    ponytail: repo accrual uses h directly (no ACT/360 vs 365 split); fine to ~1% of carry."""
    c = coupon_pct / m
    ai = c * (1 - f)
    p0 = clean + ai
    y0 = bond_yield_from_dirty(p0, coupon_pct, f, n, m)
    r, dt = repo_pct / 100.0, h * m
    paid = [k for k in range(n) if f + k <= dt + 1e-12]
    fwd = p0 * (1 + r * h) - sum(c * (1 + r * (h - (f + k) / m)) for k in paid)
    n2, f2 = n - len(paid), f + len(paid) - dt
    if n2 <= 0:
        raise ValueError("bond matures inside the horizon")
    y1 = bond_yield_from_dirty(fwd, coupon_pct, f2, n2, m)
    return {"y_spot_pct": y0, "y_fwd_pct": y1, "fwd_dirty": fwd, "carry_bp": 100 * (y1 - y0)}


def simple_carry_approx_bp(y_pct: float, repo_pct: float, fwd_mod_dur: float, h: float) -> float:
    """(y - repo) * h / forward modified duration, in yield bp. Use YIELD, never the coupon."""
    return 100.0 * (y_pct - repo_pct) * h / fwd_mod_dur


def basis_carry(clean: float, fwd_clean: float, cf: float, fut_px: float) -> dict:
    """Gross basis = P - CF*F; net basis = forward P - CF*F; carry to delivery = gross - net."""
    g, n = clean - cf * fut_px, fwd_clean - cf * fut_px
    return {"gross": g, "net": n, "carry": g - n}


# ----------------------------------------------------------------------------- carry / vol
def realised_vol_bp(level_bp: pd.Series, window: int = 63) -> float:
    """Latest rolling std (bp/day) of 1-day changes of the structure level. 63d ~ 3m: matches a 3m horizon."""
    return float(level_bp.diff().rolling(window).std().iloc[-1])


def carry_vol(total_bp: float, vol_daily_bp: float, h: float, days: int = 252) -> dict:
    """Horizon-matched ex-ante Sharpe. sigma_h = vol_daily*sqrt(days*h).
    horizon_sharpe = total/sigma_h is ALSO the breakeven as a fraction of a 1-sigma move over the horizon.
    NaN (short history) or non-positive vol returns NaN rather than inf."""
    if not (vol_daily_bp > 0):
        return {"sigma_h_bp": np.nan, "horizon_sharpe": np.nan, "annual_sharpe": np.nan}
    sig_h = vol_daily_bp * np.sqrt(days * h)
    hs = total_bp / sig_h
    return {"sigma_h_bp": sig_h, "horizon_sharpe": hs, "annual_sharpe": hs / np.sqrt(h)}


def carry_over_R(sharpe: float, R: float) -> float:
    """Directionality-penalised carry score: Sharpe / (1 + |R|), R = corr/rank-corr of changes with the outright."""
    return sharpe / (1.0 + abs(R))


def months_to_breakeven(mispricing_bp: float, carry_bp_per_month: float) -> float:
    """Negative-carry trade: months until carry bleed equals the mispricing. inf if carry >= 0."""
    return np.inf if carry_bp_per_month >= 0 else mispricing_bp / -carry_bp_per_month


# ----------------------------------------------------------------------------- CLI
def _years(tok: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([YMW]?)", tok.strip().upper())
    if not m:
        raise ValueError(f"bad tenor {tok}")
    v, u = float(m.group(1)), m.group(2) or "Y"
    return v * {"Y": 1.0, "M": 1 / 12, "W": 1 / 52}[u]


def _parse_structure(s: str) -> dict:
    nums = [int(x) for x in re.findall(r"\d+", s)]
    # receiver-positive weights. 2 legs: steepener = long (longer - shorter) = receive short end, pay long end.
    # 3 legs: long the fly level (2*belly - wings) = PAY the belly, receive the wings. Negate for "receive the belly".
    if len(nums) == 2:
        return {(0, nums[0]): 1.0, (0, nums[1]): -1.0}
    if len(nums) == 3:
        return {(0, nums[0]): 1.0, (0, nums[1]): -2.0, (0, nums[2]): 1.0}
    raise ValueError(f"structure {s}: use 2s10s or 2s5s10s")


def _load(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--par", help="curve_par table (csv/parquet): date, snap, curve_id, start, tenor, par_rate_pct")
    ap.add_argument("--curve", help="curve_id, e.g. USD-SOFR")
    ap.add_argument("--date", help="as-of date YYYY-MM-DD (default: latest)")
    ap.add_argument("--snap", help="snap (default: the only/first one present)")
    ap.add_argument("--h", type=float, default=0.25, help="horizon in years (default 0.25 = 3m)")
    ap.add_argument("--tenors", default="2,5,10,30", help="outright spot tenors in years")
    ap.add_argument("--structures", default="2s10s,2s5s10s")
    ap.add_argument("--freq", type=int, default=1, help="fixed-leg payments per year in the simplified curve")
    ap.add_argument("--vol-window", type=int, default=63)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.par and a.curve):
        ap.error("--par and --curve are required (or use --selftest)")
    df = _load(a.par)
    df = df[(df.curve_id == a.curve) & (df.start == "0D")].copy()
    if a.snap:
        df = df[df.snap == a.snap]
    else:
        df = df[df.snap == df.snap.iloc[0]]
    df["date"] = pd.to_datetime(df["date"])
    df["T"] = df["tenor"].map(_years)
    wide = df.pivot_table(index="date", columns="T", values="par_rate_pct").sort_index()
    d = pd.Timestamp(a.date) if a.date else wide.index[-1]
    curve = Curve(wide.loc[d].dropna(), freq=a.freq)
    rows = []
    items = [(f"{t}Y", {(0, float(t)): 1.0}) for t in a.tenors.split(",")]
    items += [(s, _parse_structure(s)) for s in a.structures.split(",") if s]
    for name, legs in items:
        r = structure_carry_roll(curve, {(s0, float(t)): w for (s0, t), w in legs.items()}, a.h)
        # level of the structure in bp (sign irrelevant for vol); use history up to the as-of date only (no look-ahead)
        lvl = sum(w * wide[float(t)] for (_, t), w in legs.items()) * 100
        v = realised_vol_bp(lvl.loc[:d].dropna(), a.vol_window)
        cv = carry_vol(r["total_bp"], v, a.h)
        rows.append({"structure": name, "carry_bp": r["carry_bp"], "roll_bp": r["roll_bp"], "total_bp": r["total_bp"],
                     "vol_bp_day": v, "horizon_sharpe": cv["horizon_sharpe"], "annual_sharpe": cv["annual_sharpe"]})
    print(f"curve={a.curve} date={d.date()} horizon={a.h}y sign: receiver/long positive; curve unchanged")
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    return 0


# ----------------------------------------------------------------------------- selftest
def selftest() -> int:
    bad = []

    def chk(name, got, want, tol=1e-6):
        ok = abs(got - want) <= tol
        print(("ok   " if ok else "FAIL ") + f"{name}: got {got:.6f} want {want:.6f}")
        if not ok:
            bad.append(name)

    # 1. Ilmanen zero curve s1=6, s2=7 (annual comp): forward 1y1y 8.0094, carry 1.0094, roll 1.00
    f = (1.07 ** 2 / 1.06 - 1) * 100
    z = zero_carry_roll({1: 6.0, 2: 7.0}, 2, 1)
    chk("zero fwd", z["fwd_pct"], f)
    chk("zero carry", z["carry"], f - 7.0)
    chk("zero roll", z["roll"], 1.0)
    chk("zero total", z["total"], f - 6.0)

    # 2. Swap curve built from the same zero curve: closed-form par rates, hand-derived expectations
    df1, df2 = 1 / 1.06, 1 / 1.07 ** 2
    S1, S2 = 6.0, 100 * (1 - df2) / (df1 + df2)
    cv = Curve(pd.Series({1.0: S1, 2.0: S2}))
    F11 = (df1 / df2 - 1) * 100            # 1y1y par rate (single annual period)
    r = carry_roll(cv, 0, 2, 1.0)
    chk("swap carry", r["carry_bp"], 100 * (F11 - S2), 1e-4)
    chk("swap roll", r["roll_bp"], 100 * (S2 - S1), 1e-4)
    chk("swap total", r["total_bp"], 100 * (F11 - S1), 1e-4)
    rf = carry_roll(cv, 1, 1, 1.0)         # 1y1y receiver ages to spot 1y: zero carry, roll = F11 - S1
    chk("fwd-start carry", rf["carry_bp"], 0.0)
    chk("fwd-start roll", rf["roll_bp"], 100 * (F11 - S1), 1e-4)

    # 3. Fixing shortcut equals forward-minus-spot when horizon = fixing period (identity (S2-S1)DF1 = (F-S2)DF2)
    chk("fixing identity", carry_from_fixing(S2, S1, df1, 1.0, df2), r["carry_bp"], 1e-4)

    # 4. Nordea Carry & Roll, 14 Jun 2013: 5y 1.023, 6m Euribor 0.319, P(0,6m) .9995, dv01 4.45 -> 7.9bp; roll 9.5bp
    chk("nordea carry bp", carry_from_fixing(1.023, 0.319, 0.9995, 0.5, 4.45), 7.9, 0.05)
    chk("nordea roll bp", 100 * (1.023 - 0.928), 9.5, 1e-9)

    # 5. flat par curve: all carry/roll zero, spot and forward starting, several horizons
    flat = Curve(pd.Series({1.0: 3.0, 5.0: 3.0, 10.0: 3.0}))
    for h in (0.25, 0.5, 1.0):
        chk(f"flat spot h={h}", carry_roll(flat, 0, 10, h)["total_bp"], 0.0, 1e-6)
        chk(f"flat fwd h={h}", carry_roll(flat, 5, 5, h)["total_bp"], 0.0, 1e-6)

    # 5b. semi-annual bootstrap round-trips its own par rates (guards the DF recursion when freq != 1)
    c2 = Curve(pd.Series({1.0: 3.0, 5.0: 4.0, 10.0: 4.5}), freq=2, interp="linear")
    chk("semi-annual par round trip 5y", c2.par(0, 5), 4.0, 1e-9)
    chk("semi-annual par round trip 10y", c2.par(0, 10), 4.5, 1e-9)

    # 6. structure = weighted sum of legs
    st = structure_carry_roll(cv, {(0, 1): -1.0, (0, 2): 1.0}, 0.5)
    manual = carry_roll(cv, 0, 2, 0.5)["total_bp"] - carry_roll(cv, 0, 1, 0.5)["total_bp"]
    chk("structure additivity", st["total_bp"], manual, 1e-9)
    # sign convention: steepener = receive short end, pay long end; fly parse = pay belly (long fly level)
    chk("steepener sign", structure_carry_roll(cv, _parse_structure("1s2s"), 0.5)["total_bp"],
        carry_roll(cv, 0, 1, 0.5)["total_bp"] - carry_roll(cv, 0, 2, 0.5)["total_bp"], 1e-9)
    if _parse_structure("2s5s10s") != {(0, 2): 1.0, (0, 5): -2.0, (0, 10): 1.0}:
        bad.append("fly parse")
    if not np.isnan(carry_vol(2.0, float("nan"), 0.25)["horizon_sharpe"]):
        bad.append("nan vol guard")

    # 7. Burghardt bond carry: 7-1/4% 8/15/22, full price 120.8764, repo 4.54%, 84 of 181 days
    b = bond_carry_price(120.8764, 0.0, 7.25, 2, 4.54, 84, 181)
    chk("burghardt income", b["coupon_income"], 1.68232, 5e-6)
    chk("burghardt financing", b["financing"], 1.280484, 5e-6)
    chk("burghardt carry", b["carry"], 0.401836, 5e-6)

    # 8. Tuckman forward: 2.875s 5/15/28, spot 110.77344 + AI 0.01562, repo 0.015%, 136d, AI_fwd 1.07813
    fw = forward_clean_price(110.77344, 0.01562, 0.015, 136, 1.07813)
    chk("tuckman full fwd", fw["full_fwd"], 110.79534, 2e-5)
    chk("tuckman flat fwd", fw["flat_fwd"], 109.71721, 2e-5)
    bc = basis_carry(110.77344, fw["flat_fwd"], 0.8338, 131.546875)
    chk("TYU1 gross basis", bc["gross"], 1.0896, 5e-4)
    chk("TYU1 net basis", bc["net"], 0.0334, 5e-4)
    chk("TYU1 carry (33.8 ticks)", bc["carry"], 33.8 / 32, 5e-4)
    fw2 = forward_clean_price(95.50781, 0.28280, 0.015, 136, 0.14063, coupons=((0.5625, 46),))
    chk("tuckman coupon full fwd", fw2["full_fwd"], 95.23353, 5e-5)

    # 9. yield-space carry: par bond, repo == coupon, one coupon period -> forward price par, zero carry
    z0 = bond_carry_yield(100.0, 4.0, 1.0, 10, 2, 4.0, 0.5)
    chk("par bond fwd dirty", z0["fwd_dirty"], 100.0, 1e-9)
    chk("par bond carry", z0["carry_bp"], 0.0, 1e-6)
    z1 = bond_carry_yield(100.0, 4.0, 1.0, 10, 2, 3.0, 0.5)   # repo 100bp below yield: forward price 99.5
    chk("pos carry fwd dirty", z1["fwd_dirty"], 99.5, 1e-9)
    if not z1["carry_bp"] > 0:
        bad.append("positive carry sign")
    z2 = bond_carry_yield(100.0, 4.0, 1.0, 10, 2, 5.0, 0.5)   # negative carry bond
    if not z2["carry_bp"] < 0:
        bad.append("negative carry sign")
    chk("ytm round trip", bond_yield_from_dirty(bond_dirty_from_yield(3.37, 4.0, 0.6, 9), 4.0, 0.6, 9), 3.37, 1e-9)

    # 10. carry/vol: total 2bp, 1bp/day, 3m -> sigma_h = sqrt(63), Sharpe 2/sqrt(63), annual x2
    c = carry_vol(2.0, 1.0, 0.25)
    chk("carry/vol horizon", c["horizon_sharpe"], 2 / np.sqrt(63), 1e-9)
    chk("carry/vol annual", c["annual_sharpe"], 4 / np.sqrt(63), 1e-9)
    chk("carry/R", carry_over_R(1.2, -0.5), 0.8, 1e-12)
    chk("months to BE", months_to_breakeven(14.0, -2.5 / 3), 14.0 / (2.5 / 3), 1e-9)

    print("SELFTEST " + ("FAILED: " + ", ".join(bad) if bad else "PASSED"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
