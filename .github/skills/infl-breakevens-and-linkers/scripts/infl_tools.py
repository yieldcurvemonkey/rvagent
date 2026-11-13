#!/usr/bin/env python3
"""Linker / inflation-swap arithmetic: reference index, index ratio, breakevens, ZC forwards, ZCIS legs,
real-yield carry, seasonal factors, seasonally adjusted price, linker z-spread.

Conventions (all stated, none hidden):
  * rates and yields in percent unless a name ends in _bp; carry and spreads returned in bp.
  * lag / interpolation are ARGUMENTS (US 3m interpolated; EUR swaps 3m not interpolated; UK swaps 2m not
    interpolated; AUD bonds 6m). There is no default market.
  * yields use a street-convention solver (periodic compounding, ACT/ACT within the coupon period). Good for
    relative carry; for settlement cash flows use the issuer's published formulae.
CLI:  python infl_tools.py {refindex|fwdinfl|carry} ...   |   python -I infl_tools.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import brentq

# ---------------------------------------------------------------- index mechanics


def ref_index(actual: pd.Series, d, lag: int, interp: bool = True) -> float:
    """Reference index for date d. `actual` = published NSA index indexed by the 1st of the month it measures.
    interp: RV = A[m-lag] + (day-1)/days_in_month * (A[m-lag+1] - A[m-lag]); else RV = A[m-lag]."""
    d = pd.Timestamp(d)
    m = pd.Timestamp(d.year, d.month, 1) - pd.DateOffset(months=lag)
    need = [m] + ([m + pd.DateOffset(months=1)] if interp else [])
    miss = [x.strftime("%Y-%m") for x in need if x not in actual.index or pd.isna(actual.loc[x])]
    if miss:  # a reference value is known only once the later month is published: never extrapolate silently
        raise KeyError(f"reference index for {d.date()} needs unpublished/missing month(s) {miss}")
    a0 = float(actual.loc[m])
    if not interp:
        return a0
    a1 = float(actual.loc[m + pd.DateOffset(months=1)])
    return a0 + (d.day - 1) / d.days_in_month * (a1 - a0)


def index_ratio(ref: float, base: float, floor: bool = False, dp: int | None = None) -> float:
    """IR = ref/base. floor=True applies the deflation floor (redemption-type use only). dp: truncate to 6dp then
    round to dp (OATei practice: reference value and IR are truncated at 6dp, rounded at 5dp)."""
    ir = ref / base
    if floor:
        ir = max(ir, 1.0)
    if dp is not None:
        ir = round(math.floor(ir * 1e6 + 1e-9) / 1e6, dp)
    return ir


def breakeven(nominal_pct: float, real_pct: float) -> dict:
    """Fisher (market convention: simple difference) and FX-points (1y horizon) breakevens, in percent."""
    return {"fisher": nominal_pct - real_pct,
            "fx": 100 * ((1 + nominal_pct / 100) / (1 + real_pct / 100) - 1)}


def fwd_zc(r_a: float, t_a: float, r_b: float, t_b: float) -> float:
    """Forward ZC inflation rate (pct, annualised) between t_a and t_b from ZC swap rates (pct). 5y5y = (5,10)."""
    if t_b <= t_a:
        raise ValueError("need t_b > t_a")
    return 100 * (((1 + r_b / 100) ** t_b / (1 + r_a / 100) ** t_a) ** (1 / (t_b - t_a)) - 1)


def zcis_legs(notional: float, k_pct: float, i0: float, iT: float, years: float) -> dict:
    """Zero-coupon inflation swap, seen from the INFLATION RECEIVER (long inflation). net > 0 = long wins."""
    fixed = notional * ((1 + k_pct / 100) ** years - 1)
    infl = notional * (iT / i0 - 1)
    return {"pay_fixed": fixed, "receive_inflation": infl, "net_long": infl - fixed}


# ---------------------------------------------------------------- real-yield maths


def _coupon_dates(mat, freq: int):
    """Coupon dates working back from maturity, returned ascending (long enough to bracket any settle)."""
    step = 12 // freq
    out, k = [], 0
    while k < 400:
        out.append((pd.Timestamp(mat) - pd.DateOffset(months=step * k)).normalize())
        k += 1
    return sorted(out)


def _bracket(settle, mat, freq):
    cds = _coupon_dates(mat, freq)
    s = pd.Timestamp(settle)
    prev = max(c for c in cds if c <= s)
    nxt = min(c for c in cds if c > s)
    return cds, prev, nxt


def accrued(settle, mat, cpn_pct: float, freq: int = 2) -> float:
    """Real accrued per 100 (ACT/ACT within period; ex-dividend ignored)."""
    _, p, n = _bracket(settle, mat, freq)
    return cpn_pct / freq * (pd.Timestamp(settle) - p).days / (n - p).days


def real_clean(y_pct: float, settle, mat, cpn_pct: float, freq: int = 2) -> float:
    cds, p, n = _bracket(settle, mat, freq)
    w = (n - pd.Timestamp(settle)).days / (n - p).days
    pay = [c for c in cds if n <= c <= pd.Timestamp(mat)]
    y = y_pct / 100 / freq
    pv = sum((cpn_pct / freq + (100.0 if c == pd.Timestamp(mat) else 0.0)) / (1 + y) ** (w + k) for k, c in enumerate(pay))
    return pv - cpn_pct / freq * (1 - w)


def real_yield(clean: float, settle, mat, cpn_pct: float, freq: int = 2) -> float:
    return brentq(lambda y: real_clean(y, settle, mat, cpn_pct, freq) - clean, -20, 50, xtol=1e-12)


def linker_carry(clean, cpn_pct, settle, mat, ir_settle, ir_fwd, repo_pct, fwd_date,
                 freq: int = 2, basis: int = 360, ir_at=None) -> dict:
    """Real-yield carry over [settle, fwd_date] (BofA procedure).
    carry_bp = forward real yield - spot real yield = the break-even yield rise for a LONG funded at repo.
    POSITIVE = good for the long (it can lose carry_bp of real-yield before the position loses money).
    Higher repo, or a lower index accrual in ir_fwd, LOWERS carry_bp. Repo compounds simply (ACT/basis).
    ir_at(date)->IR values interim coupons (defaults to ir_fwd)."""
    s, f = pd.Timestamp(settle), pd.Timestamp(fwd_date)
    dirty_cash = (clean + accrued(s, mat, cpn_pct, freq)) * ir_settle
    fwd_cash = dirty_cash * (1 + repo_pct / 100 * (f - s).days / basis)
    cds = _coupon_dates(mat, freq)
    for c in cds:
        if s < c <= f:  # coupon received: cash value rolled at repo to the horizon, taken off the forward value
            irc = ir_at(c) if ir_at else ir_fwd
            fwd_cash -= cpn_pct / freq * irc * (1 + repo_pct / 100 * (f - c).days / basis)
    fwd_dirty_real = fwd_cash / ir_fwd
    fwd_clean = fwd_dirty_real - accrued(f, mat, cpn_pct, freq)
    y0 = real_yield(clean, s, mat, cpn_pct, freq)
    y1 = real_yield(fwd_clean, f, mat, cpn_pct, freq)
    return {"dirty_cash": dirty_cash, "fwd_cash": fwd_cash, "fwd_real_clean": fwd_clean,
            "spot_ry_pct": y0, "fwd_ry_pct": y1, "carry_bp": (y1 - y0) * 100}


# ---------------------------------------------------------------- seasonality and spreads


def seasonal_factors(nsa: pd.Series) -> pd.Series:
    """Additive % seasonal deviation by calendar month (index 1..12), ratio-to-centred-2x12-MA on log(NSA).
    Matches infl_seasonals.seasonal_pct (sums to ~0). Needs >= 3 full years of contiguous monthly data (all 12 factors)."""
    if len(nsa) < 36 or not nsa.index.equals(pd.date_range(nsa.index[0], periods=len(nsa), freq="MS")) or nsa.isna().any():
        raise ValueError("need >= 36 contiguous month-start observations without NaN")
    s = np.log(nsa.astype(float))
    ma = s.rolling(12, center=True).mean().rolling(2).mean().shift(-1)  # centred 2x12 MA
    dev = (s - ma).dropna()
    f = dev.groupby(dev.index.month).mean()
    if len(f) < 12:
        raise ValueError("fewer than 12 calendar months after trimming the moving-average ends: use a longer history")
    return 100 * (f - f.mean())


def sa_price(price: float, seas_value_pct: float, seas_maturity_pct: float) -> float:
    """SAP = P * Sv/Sm with multiplicative factors S = 1 + pct/100 (value-date vs maturity reference month)."""
    return price * (1 + seas_value_pct / 100) / (1 + seas_maturity_pct / 100)


def z_spread(dirty_cash: float, times: np.ndarray, cashflows: np.ndarray, df_fn) -> float:
    """Parallel continuously-compounded spread z (bp) such that sum(cf*df(t)*exp(-z t)) = dirty_cash.
    cashflows are PROJECTED NOMINAL cash (index-ratio applied). Positive z = bond cheap to the curve."""
    t, cf = np.asarray(times, float), np.asarray(cashflows, float)
    dfs = np.array([df_fn(x) for x in t])
    z = brentq(lambda z: float(np.sum(cf * dfs * np.exp(-z * t))) - dirty_cash, -0.5, 0.5, xtol=1e-14)
    return z * 1e4


# ---------------------------------------------------------------- selftest


def _close(a, b, tol, what):
    if not abs(a - b) <= tol:
        raise AssertionError(f"{what}: got {a!r}, expected {b!r} (tol {tol})")


def selftest() -> None:
    # reference index: US 22 Jul 2025, 3m lag interpolated (BofA primer): Apr 320.795, May 321.44339 -> 321.23423
    us = pd.Series({pd.Timestamp("2025-04-01"): 320.795, pd.Timestamp("2025-05-01"): 321.44339})
    _close(ref_index(us, "2025-07-22", 3, True), 321.23423, 2e-5, "US ref CPI")
    _close(ref_index(us, "2025-07-22", 3, False), 320.795, 1e-9, "no-interp ref")
    # unit-test case from a textbook index-lag example: 16 Jan 2022, lag 3 -> 101 + 15/31
    uk = pd.Series({pd.Timestamp("2021-10-01"): 101.0, pd.Timestamp("2021-11-01"): 102.0})
    _close(ref_index(uk, "2022-01-16", 3, True), 101.4839, 5e-5, "daily interpolation")
    # OATei 1.85% 2027, value 22 Jul 25: RV 128.10581, IR 1.36681, cash EUR1m principal and accrued
    eu = pd.Series({pd.Timestamp("2025-04-01"): 128.16, pd.Timestamp("2025-05-01"): 128.08})
    rv = math.floor(ref_index(eu, "2025-07-22", 3, True) * 1e6 + 1e-9) / 1e6
    rv = round(rv, 5)
    _close(rv, 128.10581, 1e-9, "OATei RV")
    ir = index_ratio(rv, 93.72591, dp=5)
    _close(ir, 1.36681, 1e-9, "OATei IR")
    _close(1.03141 * ir * 1e6, 1_409_741.50, 0.01, "OATei principal")
    _close(0.0185 * 362 / 365 * ir * 1e6, 25_078.15, 0.01, "OATei accrued")
    _close(index_ratio(0.97, 1.0, floor=True), 1.0, 0, "floor")
    # breakevens
    b = breakeven(4.0, 1.0)
    _close(b["fisher"], 3.0, 1e-12, "fisher")
    _close(b["fx"], 100 * (1.04 / 1.01 - 1), 1e-12, "fx")
    # forwards: flat 2% curve -> 2% forward; and 5y5y identity
    _close(fwd_zc(2, 5, 2, 10), 2.0, 1e-9, "flat fwd")
    _close(fwd_zc(2.0, 5, 2.05, 10), 100 * ((1.0205) ** 2 / 1.02 - 1), 1e-9, "5y5y identity")
    # ZCIS legs (BofA term sheets): EUR 5y 1.8438% HICPxT 128.16 -> 148.57 on 100m; US 5y 2.7040% 321.24887 -> 372.41548
    e = zcis_legs(100e6, 1.8438, 128.16, 148.57, 5)
    _close(e["pay_fixed"], 9_565_286, 1.0, "EUR fixed leg")
    _close(e["receive_inflation"] / 15_925_406, 1.0, 1e-6, "EUR inflation leg")
    u = zcis_legs(100e6, 2.7040, 321.24887, 372.41548, 5)
    _close(u["pay_fixed"] / 14_271_201, 1.0, 1e-6, "US fixed leg")
    _close(u["receive_inflation"] / 15_927_409, 1.0, 1e-6, "US inflation leg")
    # real yield: par bond at a coupon date prices at 100; price/yield round trip; accrued mid-period
    _close(real_clean(0.125, date(2026, 4, 15), date(2027, 4, 15), 0.125), 100.0, 1e-9, "par at coupon date")
    p = real_clean(1.3, date(2025, 7, 3), date(2027, 4, 15), 0.125)
    _close(real_yield(p, date(2025, 7, 3), date(2027, 4, 15), 0.125), 1.3, 1e-8, "price-yield round trip")
    _close(accrued(date(2025, 7, 3), date(2027, 4, 15), 0.125), 0.125 / 2 * 79 / 183, 1e-12, "accrued 79/183")
    # carry identity (zero-coupon linker, 90 days, ACT/360): P_f = P_0 (1 + r t)/(1 + i t), t = 0.25
    t, r_, i_ = 0.25, 0.04, 0.03
    c = linker_carry(95.0, 0.0, date(2025, 7, 1), date(2027, 4, 15), 1.10, 1.10 * (1 + i_ * t), r_ * 100,
                     date(2025, 9, 29), freq=2)
    _close(c["fwd_real_clean"], 95.0 * (1 + r_ * t) / (1 + i_ * t), 1e-9, "carry identity")
    # real_clean mid-period, known answer: yield == coupon gives dirty = 100*(1+y/2)^elapsed, clean = dirty - accrued
    el = 90 / 181  # settle 15 Apr 2025 inside the 15 Jan - 15 Jul period (181 days)
    _close(real_clean(4.0, date(2025, 4, 15), date(2030, 1, 15), 4.0), 100 * 1.02 ** el - 2.0 * el, 1e-9, "mid-period clean")
    _close(accrued(date(2025, 4, 15), date(2030, 1, 15), 4.0), 2.0 * el, 1e-12, "accrued 90/181")
    # coupon inside the carry window (constant IR 1.0): fwd clean = dirty0*(1+r*273/360) - c*(1+r*92/360) - accrued_fwd
    c2 = linker_carry(100.0, 4.0, date(2025, 1, 15), date(2030, 1, 15), 1.0, 1.0, 5.0, date(2025, 10, 15))
    _close(c2["fwd_real_clean"], 100 * (1 + 0.05 * 273 / 360) - 2.0 * (1 + 0.05 * 92 / 360) - 2.0 * 92 / 184, 1e-9, "carry with coupon")
    # BofA TIPS pipeline arithmetic from printed numbers (not the printed repo step, which does not tie)
    d0 = (97.85938 + 0.125 / 2 * 79 / 183) * 1.13891
    _close(d0, 111.4834, 5e-4, "TIPS dirty cash")
    _close(112.71173 / (324.34323 / 282.34640) - 0.125 / 2 * 171 / 183, 98.05911, 1e-4, "TIPS fwd clean")
    # carry sign: higher repo -> higher forward real clean price on a fixed index path -> LOWER fwd real yield
    lo = linker_carry(97.86, 0.125, date(2025, 7, 3), date(2027, 4, 15), 1.13891, 1.14874, 2.0, date(2025, 10, 3))
    hi = linker_carry(97.86, 0.125, date(2025, 7, 3), date(2027, 4, 15), 1.13891, 1.14874, 6.0, date(2025, 10, 3))
    if not hi["carry_bp"] < lo["carry_bp"]:
        raise AssertionError("carry sign: higher repo must LOWER carry_bp (fwd real yield) at fixed index path")
    # seasonal recovery: 3% trend, known log-seasonal pattern
    pat = np.array([-.6, -.4, .1, .3, .4, .3, -.1, -.2, .2, .1, .0, -.1]) - np.mean([-.6, -.4, .1, .3, .4, .3, -.1, -.2, .2, .1, .0, -.1])
    idx = pd.date_range("2010-01-01", periods=12 * 10, freq="MS")
    nsa = pd.Series(100 * np.exp(0.03 * np.arange(len(idx)) / 12 + pat[idx.month - 1] / 100), index=idx)
    est = seasonal_factors(nsa)
    for m in range(1, 13):
        _close(est[m], pat[m - 1], 0.02, f"seasonal month {m}")
    _close(sa_price(100, 0.5, -0.5), 100 * 1.005 / 0.995, 1e-12, "SAP")
    # z-spread round trip; positive when dirty < PV at z=0
    times = np.array([0.5, 1.0, 1.5, 2.0])
    cfs = np.array([1.2, 1.2, 1.2, 101.2])
    df = lambda x: math.exp(-0.04 * x)  # noqa: E731
    pv_true = float(np.sum(cfs * np.array([df(x) * math.exp(-0.00312 * x) for x in times])))
    _close(z_spread(pv_true, times, cfs, df), 31.2, 1e-6, "z-spread roundtrip")
    if not z_spread(pv_true - 1.0, times, cfs, df) > 31.2:
        raise AssertionError("cheaper bond must have larger z")
    # edge cases: missing month, short history and NaN must raise, never extrapolate
    for bad in (lambda: ref_index(us, "2025-08-22", 3, True), lambda: seasonal_factors(nsa.iloc[:30]),
                lambda: seasonal_factors(nsa.where(nsa.index != nsa.index[50]))):
        try:
            bad()
        except (KeyError, ValueError):
            continue
        raise AssertionError("edge case did not raise")
    print("selftest OK")


# ---------------------------------------------------------------- CLI over canonical tables


def _read(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def _cmd_refindex(a):
    f = _read(a.fixings)
    f = f[f.index_id == a.index_id].copy()
    f["pub_ts_utc"] = pd.to_datetime(f["pub_ts_utc"], utc=True)
    if a.asof:
        f = f[f.pub_ts_utc <= pd.Timestamp(a.asof, tz="UTC")]
    f = f.sort_values("pub_ts_utc").groupby("ref_month").first() if a.first_release else \
        f.sort_values("pub_ts_utc").groupby("ref_month").last()
    s = pd.Series(f["index_level"].values, index=pd.to_datetime(f.index + "-01"))
    ref = ref_index(s, a.date, a.lag, a.interp)
    print(f"{a.index_id} reference index {a.date} (lag {a.lag}m, interp={a.interp}): {ref:.5f}")
    if a.base:
        print(f"index ratio vs base {a.base}: {index_ratio(ref, a.base):.6f}")


def _cmd_fwdinfl(a):
    sw = _read(a.swaps)
    sw = sw[(sw.index_id == a.index_id) & (pd.to_datetime(sw.date) == pd.Timestamp(a.date)) & (sw.start == "0D")
            & sw.tenor.str.endswith("Y")]
    if a.snap:
        sw = sw[sw.snap == a.snap]
    sw = sw.assign(t=sw.tenor.str.rstrip("Y").astype(float)).sort_values("t")
    r = dict(zip(sw.t, sw.zc_rate_pct))
    print("tenor  zc_pct  fwd_from_prev_pct")
    prev = None
    for t, z in r.items():
        print(f"{t:>5g}  {z:6.3f}  {'' if prev is None else f'{fwd_zc(r[prev], prev, z, t):6.3f}'}")
        prev = t
    if 5.0 in r and 10.0 in r:
        print(f"5y5y = {fwd_zc(r[5.0], 5, r[10.0], 10):.3f}% (seasonality/carry NOT removed)")


def _cmd_carry(a):
    out = linker_carry(a.clean, a.coupon, a.settle, a.maturity, a.ir_settle, a.ir_fwd, a.repo, a.fwd_date,
                       freq=a.freq, basis=a.basis)
    for k, v in out.items():
        print(f"{k}: {v:.5f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("refindex", help="reference index from an infl_fixings table")
    p.add_argument("--fixings", required=True)
    p.add_argument("--index-id", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--lag", type=int, required=True)
    p.add_argument("--interp", action=argparse.BooleanOptionalAction, required=True)
    p.add_argument("--asof", help="ISO date: ignore vintages published later (point-in-time)")
    p.add_argument("--first-release", action="store_true", help="use first published value (default: latest <= asof)")
    p.add_argument("--base", type=float)
    p.set_defaults(fn=_cmd_refindex)
    p = sub.add_parser("fwdinfl", help="forward ZC inflation from an infl_swaps table")
    p.add_argument("--swaps", required=True)
    p.add_argument("--index-id", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--snap")
    p.set_defaults(fn=_cmd_fwdinfl)
    p = sub.add_parser("carry", help="real-yield carry of one linker (explicit inputs)")
    for n, ty in [("clean", float), ("coupon", float), ("ir-settle", float), ("ir-fwd", float), ("repo", float)]:
        p.add_argument("--" + n, type=ty, required=True)
    for n in ("settle", "maturity", "fwd-date"):
        p.add_argument("--" + n, required=True)
    p.add_argument("--freq", type=int, default=2)
    p.add_argument("--basis", type=int, default=360)
    p.set_defaults(fn=_cmd_carry)
    a = ap.parse_args(argv)
    if a.selftest:
        try:
            selftest()
        except AssertionError as e:
            print("SELFTEST FAILED:", e)
            return 1
        return 0
    if not a.cmd:
        ap.print_help()
        return 2
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
