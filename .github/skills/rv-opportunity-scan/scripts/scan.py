#!/usr/bin/env python3
"""Curve scanner: every 2-leg curve and 3-leg fly on a par-curve tenor set -> standard RV metric table, ranked.

Input  : canonical `curve_par` (date, snap, curve_id, start, tenor, par_rate_pct), spot starts only (start = 0D).
Output : one row per structure with the metric set the rv-opportunity-scan skill defines (all bp):
         level_bp, z_63/z_252/z_756, z (= z at --z-ref), pctile, halflife_days, df_t, carry_bp (3m carry+roll of the
         receive-type position), vol_bp, carry_vol, carry_vol_ann, er_bp, er_vol, pca_resid_bp, pca_z, hit_frac, side, legs_trade, j, scan_flags, passed.

Conventions
  curve A-B level = y(long) - y(short);  fly level = 2*y(belly) - y(front) - y(back)   (rates in bp).
  Risk (DV01) weights of the receive-type position: curve (+1 long, -1 short); fly (+2 belly, -1, -1). So
  level = sum(rho_i * y_i) and the position P&L over a horizon = -(change in level) + carry_bp.
  side = +1 "receive-type": P&L rises when the level FALLS (receive long/belly, pay short/wings). Default side = sign(z):
  fade the deviation. carry_bp is always the carry+roll of the side=+1 position; side*carry_bp is what the trade earns.
  legs_trade = the trade to execute: leg:notional with + = receive fixed, - = pay fixed (already multiplied by side).
  z > 0 = level high vs its own trailing window = receive-type cheap.
  z = (level - mean)/std over the trailing L observations INCLUDING today, ddof=1. Nothing is forward-filled.
Carry+roll (approximation, screening only): receiver leg in rate-equivalent bp
  cr_i = (y_i - r) * h / A_i  +  (y_i - y(T_i - h)),  A_i = (1-(1+y)^-T)/y annuity proxy, r = shortest curve tenor
  (<= 1Y, else financing carry is omitted and `cr_basis` says roll_only), y(T-h) linear interpolation on tenor.
CLI    : python scan.py --curve-par curve_par.csv --curve-id USD-SOFR [--snap eod_ny] [--out ranked.csv]
         python scan.py --demo            (synthetic data worked run)      python -I scan.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import math
import re
import sys

import numpy as np
import pandas as pd

LN2 = math.log(2.0)
DF_CRIT = -2.86      # 5% Dickey-Fuller critical value, regression with constant, large n


def tenor_years(t: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([DWMY])", t.strip().upper())
    if not m:
        raise ValueError(f"bad tenor {t!r}")
    return float(m.group(1)) * {"D": 1 / 365, "W": 7 / 365, "M": 1 / 12, "Y": 1.0}[m.group(2)]


def annuity(y_pct: float, T: float) -> float:
    y = y_pct / 100.0
    return T if abs(y) < 1e-9 else (1 - (1 + y) ** -T) / y


def last_z(x: np.ndarray, L: int) -> float:
    """z of the last value vs the trailing L observations (inclusive), ddof=1."""
    w = x[-L:]
    if len(w) < L or np.isnan(w).any():
        return np.nan
    s = w.std(ddof=1)
    return (w[-1] - w.mean()) / s if s > 1e-12 else np.nan


def halflife(x: np.ndarray) -> float:
    """AR(1) half-life in observations: x_t = a + phi x_{t-1}; hl = ln2 / -ln(phi) for 0 < phi < 1, else NaN."""
    x = x[~np.isnan(x)]
    if len(x) < 30:
        return np.nan
    a, b = x[:-1], x[1:]
    va = ((a - a.mean()) ** 2).sum()
    if va < 1e-12:
        return np.nan
    phi = ((a - a.mean()) * (b - b.mean())).sum() / va
    return LN2 / -math.log(phi) if 0 < phi < 1 else np.nan


def df_tstat(x: np.ndarray) -> float:
    """Dickey-Fuller t of (phi - 1) in x_t = a + phi x_{t-1} + e (OLS with constant). H0: unit root (no reversion).
    t > DF_CRIT (-2.86) = cannot reject a random walk: the half-life is then not evidence of reversion."""
    x = x[~np.isnan(x)]
    if len(x) < 30:
        return np.nan
    a, b = x[:-1] - x[:-1].mean(), x[1:] - x[1:].mean()
    va = (a ** 2).sum()
    if va < 1e-12:
        return np.nan
    phi = (a * b).sum() / va
    se = math.sqrt(((b - phi * a) ** 2).sum() / (len(a) - 2) / va)
    return (phi - 1.0) / se if se > 1e-12 else np.nan


def hit_frac(level: np.ndarray, h: int, side: int, cr: float) -> float:
    """Share of h-day windows in which the side position made money: -side*(L[t+h]-L[t]) + side*cr > 0.
    Windows overlap, so the effective sample is about len/h. Constant carry (today's) is assumed."""
    if len(level) <= h:
        return np.nan
    pnl = -side * (level[h:] - level[:-h]) + side * cr
    return float((pnl > 0).mean())


def ou_er(x_minus_mu: float, hl: float, h: int, side: int, cr: float) -> float:
    """Expected h-day gain (bp) of the side position: OU reversion of the gap + carry+roll.
    gain = side*(x-mu)*(1 - exp(-k h)) + side*cr, k = ln2/hl per observation. No half-life -> no reversion credit."""
    rev = 0.0 if np.isnan(hl) else side * x_minus_mu * (1 - math.exp(-LN2 / hl * h))
    return rev + side * cr


def pca_resid(X: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """Residual (actual - rank-k reconstruction) of the demeaned level panel, bp. Positive = tenor high vs fit.
    In-sample (the fit sees today): fine for screening, not for a back-test."""
    A = X.to_numpy(float)
    A0 = A - A.mean(axis=0)
    _, _, vt = np.linalg.svd(A0, full_matrices=False)
    V = vt[:k].T
    return pd.DataFrame(A0 - A0 @ V @ V.T, index=X.index, columns=X.columns)


def structures(tenors: list[str], kind: str = "both"):
    """Yield (structure_name, kind, legs, rho). Curves: every pair; flies: every triple, belly strictly between."""
    ty = {t: tenor_years(t) for t in tenors}
    ts = sorted(tenors, key=ty.get)
    if kind in ("both", "curves"):
        for s, l in itertools.combinations(ts, 2):
            yield f"{s}{l}", "curve", (s, l), (-1.0, 1.0)
    if kind in ("both", "flies"):
        for f, b, k in itertools.combinations(ts, 3):
            yield f"{f}{b}{k}", "fly", (f, b, k), (-1.0, 2.0, -1.0)


def wide_curve(par: pd.DataFrame, curve_id: str, snap: str | None) -> pd.DataFrame:
    d = par[(par["curve_id"] == curve_id) & (par["start"].astype(str).str.upper() == "0D")]
    if snap is None:
        snaps = d["snap"].unique()
        if len(snaps) > 1:
            raise SystemExit(f"several snaps {list(snaps)}: pass --snap (one snap time per run)")
    else:
        d = d[d["snap"] == snap]
    if d.empty:
        raise SystemExit("no rows for that curve_id/snap with start=0D")
    w = d.pivot_table(index="date", columns="tenor", values="par_rate_pct", aggfunc="last") * 100.0
    w.index = pd.to_datetime(w.index)
    return w.sort_index()


def scan(wide: pd.DataFrame, tenors: list[str], h_days: int = 63, lookbacks=(63, 252, 756), z_ref: int = 252,
         pct_window: int = 756, hl_window: int = 756, vol_window: int = 252, hit_window: int = 756,
         pca_k: int = 3, pca_window: int = 756, kind: str = "both", ccy: str = "XXX", curve_id: str = "CURVE",
         min_obs: int = 100, max_hl: float = 90.0, min_abs_z: float = 1.5, hl_cap: float = 180.0,
         cost_bp: float = 0.5, cost_mult: float = 2.0) -> pd.DataFrame:
    """wide: date x tenor panel of par rates in bp (NaN = missing). Returns the ranked metric table."""
    h_y = h_days / 252.0
    full = wide[tenors].dropna()
    if len(full) < min_obs:
        raise SystemExit(f"only {len(full)} complete dates for tenors {tenors}; need {min_obs}")
    last = wide.dropna(subset=tenors).index[-1]
    cur = wide.loc[last].dropna()                          # whole curve, used for interpolation
    cur = cur[sorted(cur.index, key=tenor_years)]          # tenor order (pivot sorts columns alphabetically)
    ty_all = np.array([tenor_years(t) for t in cur.index])
    y_all = cur.to_numpy(float)
    r = y_all[0] if ty_all[0] <= 1.0 else np.nan           # short-rate proxy = shortest tenor
    cr_i = {}
    for t in tenors:
        T, y = tenor_years(t), cur[t]
        roll = y - np.interp(T - h_y, ty_all, y_all)
        carry = (y - r) * h_y / annuity(y / 100, T) if not np.isnan(r) else 0.0
        cr_i[t] = carry + roll
    basis = "carry+roll" if not np.isnan(r) else "roll_only"
    resid = pca_resid(full.iloc[-pca_window:], pca_k) if len(tenors) >= pca_k + 2 else None
    rows = []
    for name, knd, legs, rho in structures(tenors, kind):
        L = (full[list(legs)] * np.array(rho)).sum(axis=1).to_numpy()
        n = len(L)
        zs = {f"z_{lb}": last_z(L, lb) for lb in lookbacks}
        z = last_z(L, z_ref)
        side = int(np.sign(z)) if not np.isnan(z) else 0
        cr = float(sum(rw * cr_i[t] for rw, t in zip(rho, legs)))
        dl = np.diff(L[-(vol_window + 1):])
        vol = float(dl.std(ddof=1) * math.sqrt(h_days)) if len(dl) > 10 else np.nan
        cv = side * cr / vol if vol and vol > 0 and side else np.nan
        pw = L[-pct_window:]
        if resid is not None:
            rs = (resid[list(legs)] * np.array(rho)).sum(axis=1).to_numpy()
            pr, pz = float(rs[-1]), float(rs[-1] / rs.std(ddof=1)) if rs.std(ddof=1) > 1e-9 else np.nan
        else:
            pr = pz = np.nan
        hl = halflife(L[-hl_window - 1:-1])        # speed fitted on history BEFORE today: a fresh jump must not set its own reversion speed
        dft = df_tstat(L[-hl_window - 1:-1])
        A = {t: annuity(cur[t] / 100, tenor_years(t)) for t in legs}
        if knd == "curve":
            nots = {legs[1]: 1.0, legs[0]: -A[legs[1]] / A[legs[0]]}
        else:
            nots = {legs[1]: 2.0, legs[0]: -A[legs[1]] / A[legs[0]], legs[2]: -A[legs[1]] / A[legs[2]]}
        er = ou_er(L[-1] - L[-z_ref:].mean(), hl, h_days, side, cr) if side else np.nan
        fl = []
        if side and er < cost_mult * cost_bp:
            fl.append("cost_fail")
        if np.isnan(hl) or hl > hl_cap:
            fl.append("no_reversion")
        elif not dft < DF_CRIT:            # also true when dft is NaN
            fl.append("unit_root")
        if side and side * cr < 0:
            fl.append("carry_against")
        if not np.isnan(pz) and side and np.sign(pz) != side:
            fl.append("z_disagree")
        if abs(z) > 4:
            fl.append("z>4")
        if n < max(lookbacks):
            fl.append("thin_history")
        if full.index[-1] < wide.index.max():
            fl.append("stale")
        ok = (not np.isnan(z)) and abs(z) >= min_abs_z and 'cost_fail' not in fl and (not np.isnan(hl)) and hl <= max_hl and n >= min_obs
        rows.append(dict(
            package_id=f"{curve_id}:{name}:{knd}", structure=name, kind=knd, ccy=ccy, level_bp=L[-1], **zs, z=z,
            pca_resid_bp=pr, pca_z=pz, pctile=float((pw <= L[-1]).mean()), halflife_days=hl, df_t=dft, carry_bp=cr, vol_bp=vol,
            carry_vol=cv, carry_vol_ann=cv / math.sqrt(h_y) if cv == cv else np.nan,
            er_bp=er, er_vol=er / vol if vol and vol > 0 else np.nan, hit_frac=hit_frac(L[-hit_window:], h_days, side, cr) if side else np.nan, side=side,
            legs_trade="|".join(f"{t}:{nots[t] * (side or 1):+.2f}" for t in legs), n_obs=n, cr_basis=basis,
            scan_flags=" ".join(fl), passed=ok))
    d = pd.DataFrame(rows)
    d["j"] = d["carry_vol_ann"].fillna(0) + d["z"].abs().fillna(0)      # provisional J-style key, composite scoring is the real rank
    d = d.sort_values(["passed", "j"], ascending=[False, False]).reset_index(drop=True)
    d.insert(0, "rank", np.arange(1, len(d) + 1))
    d.attrs.update(asof=str(last.date()), horizon_days=h_days, z_ref=z_ref)
    return d


def synth_curves(n=1000, seed=7, tenors=("3M", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"), plant=None, base=3.0):
    """Synthetic par curve in bp: random-walk level/slope + mean-reverting curvature + OU noise per tenor.
    plant = {tenor: bp} added to the LAST date only (a planted dislocation with known size)."""
    rng = np.random.default_rng(seed)
    ty = np.array([tenor_years(t) for t in tenors])
    ld = np.log1p(ty)
    lvl = np.cumsum(rng.normal(0, 4.0, n))
    slope = np.cumsum(rng.normal(0, 1.5, n))
    cur = np.zeros(n)
    for i in range(1, n):
        cur[i] = 0.97 * cur[i - 1] + rng.normal(0, 1.5)
    idio = np.zeros((n, len(ty)))
    for i in range(1, n):
        idio[i] = 0.965 * idio[i - 1] + rng.normal(0, 0.45, len(ty))   # half-life ~19 days
    y = base * 100 + 35 * ld[None, :] * 1.0 + lvl[:, None] * 0.3 + slope[:, None] * (ld[None, :] - ld.mean()) \
        + cur[:, None] * (ld[None, :] - ld.mean()) ** 2 + idio
    y[:, 0] = y[:, 0].clip(min=50)
    if plant:
        for t, b in plant.items():
            y[-1, tenors.index(t)] += b
    idx = pd.bdate_range(end="2026-11-10", periods=n)
    return pd.DataFrame(y, index=idx, columns=list(tenors))


def to_par_long(w: pd.DataFrame, curve_id="USD-SOFR", snap="eod_ny") -> pd.DataFrame:
    d = (w / 100.0).stack().rename("par_rate_pct").reset_index()
    d.columns = ["date", "tenor", "par_rate_pct"]
    d.insert(1, "snap", snap)
    d.insert(2, "curve_id", curve_id)
    d.insert(3, "start", "0D")
    d["source"] = "synthetic"
    return d


def lfilter_ar(e: np.ndarray, phi: float) -> np.ndarray:
    x = np.zeros(len(e))
    for i in range(1, len(e)):
        x[i] = phi * x[i - 1] + e[i]
    return x


def _selftest() -> int:
    bad = []

    def chk(name, got, want, tol=1e-6):
        ok = (got == want) if isinstance(want, (str, bool)) else abs(got - want) <= tol * max(1.0, abs(want))
        print(("ok   " if ok else "FAIL ") + f"{name}: got {got!r} want {want!r}")
        if not ok:
            bad.append(name)

    # 1. linear curve y = 3% + 0.1%/yr (flat 3M at 3.025): levels and carry+roll by hand
    tn = ["3M", "2Y", "5Y", "10Y"]
    lin = pd.DataFrame({t: [300 + 10 * tenor_years(t)] * 120 for t in tn},
                       index=pd.bdate_range("2026-01-01", periods=120))
    lin = lin + np.random.default_rng(0).normal(0, 1e-6, lin.shape)          # tiny noise so std > 0
    d = scan(lin, tn, min_obs=100, min_abs_z=0, max_hl=1e9, lookbacks=(63,), z_ref=63, pca_k=3).set_index("structure")
    chk("curve 2Y10Y level = 80bp", d.loc["2Y10Y", "level_bp"], 80.0, 1e-3)
    chk("fly 2Y5Y10Y level = 2*350-320-400", d.loc["2Y5Y10Y", "level_bp"], -20.0, 1e-3)
    # receiver 10Y: carry (400-302.5)*0.25/A(4%,10y)=3.0046..., roll 400-397.5=2.5 -> cr
    A10 = (1 - 1.04 ** -10) / 0.04
    c10 = (400 - 302.5) * 0.25 / A10 + 2.5
    A2 = (1 - 1.032 ** -2) / 0.032
    c2 = (320 - 302.5) * 0.25 / A2 + 2.5
    sh = scan(lin[["10Y", "2Y", "3M", "5Y"]], tn, min_obs=100, min_abs_z=0, max_hl=1e9, lookbacks=(63,), z_ref=63).set_index("structure")
    chk("column order does not matter (shuffled columns)", sh.loc["2Y10Y", "carry_bp"], d.loc["2Y10Y", "carry_bp"], 1e-9)
    chk("cr 2s10s = cr10 - cr2 (hand)", d.loc["2Y10Y", "carry_bp"], c10 - c2, 1e-5)
    sd = int(d.loc["2Y10Y", "side"]) or 1
    chk("legs_trade: side x (pay 2Y at A10/A2, receive 10Y)", d.loc["2Y10Y", "legs_trade"], f"2Y:{-A10 / A2 * sd:+.2f}|10Y:{sd:+.2f}")
    # flat curve: zero carry and roll
    flat = pd.DataFrame({t: [400.0] * 120 for t in tn}, index=lin.index) + np.random.default_rng(1).normal(0, 1e-6, lin.shape)
    f = scan(flat, tn, min_obs=100, min_abs_z=0, max_hl=1e9, lookbacks=(63,), z_ref=63)
    chk("flat curve carry+roll = 0", float(f["carry_bp"].abs().max()), 0.0, 1e-2)
    # 1b. kinked curve: roll differs by leg, so a sign error in roll or carry shows (linear curve: roll cancels in spreads)
    kk = {"3M": 300.0, "2Y": 340.0, "5Y": 400.0, "10Y": 425.0}
    kp = pd.DataFrame({t: [v] * 120 for t, v in kk.items()}, index=lin.index) + np.random.default_rng(2).normal(0, 1e-6, lin.shape)
    kd = scan(kp, list(kk), min_obs=100, min_abs_z=0, max_hl=1e9, lookbacks=(63,), z_ref=63).set_index("structure")
    ann = lambda y, T: (1 - (1 + y / 1e4) ** -T) / (y / 1e4)
    roll = {"2Y": 300 + 40 * 1.5 / 1.75 - 340, "5Y": 340 + 60 * 2.75 / 3 - 400, "10Y": 400 + 25 * 4.75 / 5 - 425}   # y(T-h) - y(T), by hand
    cr = {t: (kk[t] - 300) * 0.25 / ann(kk[t], T) - roll[t] for t, T in (("2Y", 2), ("5Y", 5), ("10Y", 10))}
    chk("kinked curve: roll of 5Y = 5.0bp (hand)", -roll["5Y"], 5.0, 1e-9)
    chk("kinked curve 2Y5Y10Y fly carry+roll (hand)", kd.loc["2Y5Y10Y", "carry_bp"], -cr["2Y"] + 2 * cr["5Y"] - cr["10Y"], 1e-5)
    # 2. z by hand: 1..252 window, last = 252 -> (252-126.5)/std ; std^2 = n(n+1)/12
    x = np.arange(1.0, 253.0)
    chk("last_z consecutive ints", last_z(x, 252), (252 - 126.5) / math.sqrt(252 * 253 / 12.0), 1e-9)
    # 3. half-life: deterministic AR(1) phi=0.95 (no noise) -> exact; noisy sim recovers
    ar = 0.95 ** np.arange(300) * 10
    chk("half-life exact AR(1)", halflife(ar), LN2 / -math.log(0.95), 1e-9)
    rng = np.random.default_rng(3)
    s = np.zeros(6000)
    for i in range(1, len(s)):
        s[i] = 0.97 * s[i - 1] + rng.normal()
    hl = halflife(s)
    chk("half-life simulated phi=0.97 within 15%", abs(hl / (LN2 / -math.log(0.97)) - 1) < 0.15, True)
    # Dickey-Fuller: a half-life alone does not prove reversion. 200 random walks (n=756) should reject at ~5%, AR(1) 0.95 almost always
    rg2 = np.random.default_rng(8)
    rw_rej = np.mean([df_tstat(np.cumsum(rg2.normal(size=756))) < DF_CRIT for _ in range(200)])
    ar_rej = np.mean([df_tstat(lfilter_ar(rg2.normal(size=756), 0.95)) < DF_CRIT for _ in range(200)])
    chk("DF test: random-walk rejection rate < 12% (nominal 5%)", bool(rw_rej < 0.12), True)
    chk("DF test: AR(1) phi=0.95 rejection rate > 80%", bool(ar_rej > 0.80), True)
    # 3b. OU expected gain: gap 10bp, half-life = horizon -> half the gap closes (5.0) + carry 1.5
    chk("ou_er half-life = horizon: 10*(1-0.5)+1.5", ou_er(10.0, 63.0, 63, 1, 1.5), 6.5, 1e-9)
    chk("ou_er pay-side mirror", ou_er(-10.0, 63.0, 63, -1, -1.5), 6.5, 1e-9)
    chk("ou_er no half-life -> carry only", ou_er(10.0, float("nan"), 63, 1, 1.5), 1.5, 1e-9)
    # 4. hit fraction: level falls 1bp/day -> receive-type always wins; rising -> loses unless carry > rise*h
    chk("hit_frac falling level, side +1", hit_frac(100 - np.arange(200.0), 10, 1, 0.0), 1.0)
    chk("hit_frac rising level, side +1", hit_frac(100 + np.arange(200.0), 10, 1, 0.0), 0.0)
    chk("hit_frac rising, carry 11 > 10 rise", hit_frac(100 + np.arange(200.0), 10, 1, 11.0), 1.0)
    # 5. PCA residual of a planted bump equals (I-P) b with the TRUE projector
    tenors = ["2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]
    rg = np.random.default_rng(11)
    Q, _ = np.linalg.qr(rg.normal(size=(8, 3)))
    F = np.cumsum(rg.normal(size=(800, 3)) * np.array([6.0, 2.5, 1.0]), axis=0)
    Y = 400 + F @ Q.T + rg.normal(0, 0.02, (800, 8))
    b = np.zeros(8)
    b[4] = 20.0
    Y[-1] += b
    pan = pd.DataFrame(Y, index=pd.bdate_range("2023-01-02", periods=800), columns=tenors)
    P = Q @ Q.T
    want = float(np.dot([-1, 2, -1], ((np.eye(8) - P) @ b)[[3, 4, 5]]))
    r = scan(pan, tenors, lookbacks=(252,), z_ref=252, pct_window=800, hl_window=800, pca_window=800, min_obs=100)
    got = float(r.set_index("structure").loc["7Y10Y15Y", "pca_resid_bp"])
    chk(f"PCA fly resid ~ (I-P)b projection ({want:.2f})", abs(got / want - 1) < 0.1, True)
    # 6. end-to-end synthetic: planted +12bp on 7Y at the last date -> 7Y-belly fly is top by |z| with side +1
    w = synth_curves(plant={"7Y": 12.0})
    tt = ["2Y", "3Y", "5Y", "7Y", "10Y"]
    res = scan(wide_curve(to_par_long(w), "USD-SOFR", None), tt)
    top = res.assign(az=res["z"].abs()).sort_values("az", ascending=False).iloc[0]
    chk("planted 7Y bump: top |z| structure has 7Y as belly or long leg", "7Y" in top["structure"], True)
    chk("planted bump -> receive-type (side +1) on the 3Y7Y10Y fly", int(res.set_index("structure").loc["3Y7Y10Y", "side"]), 1)
    chk("row count 5 tenors: 10 curves + 10 flies", len(res), 20)
    wc = wide_curve(to_par_long(w), "USD-SOFR", None)
    hi = scan(wc, tt, cost_bp=1000.0)
    chk("cost hurdle 2000bp: nothing passes, all flagged cost_fail", int(hi["passed"].sum()) == 0 and bool(hi["scan_flags"].str.contains("cost_fail").all()), True)
    chk("cost 0.5bp: planted dislocation passes", int(res["passed"].sum()) > 0, True)
    # 7. row-level definitions on a mixed-side table (7Y10Y has side -1 and negative carry)
    ss = res[res["side"] != 0]
    chk("both sides present", set(ss["side"]) == {-1, 1}, True)
    chk("carry_vol = side*carry/vol on every row", bool(np.allclose(ss["carry_vol"], ss["side"] * ss["carry_bp"] / ss["vol_bp"])), True)
    chk("carry_vol_ann = 2 x carry_vol at h=63 (x sqrt(4))", bool(np.allclose(ss["carry_vol_ann"], 2 * ss["carry_vol"])), True)
    rv = ss[ss["halflife_days"].notna()]
    chk("reversion credit er - side*carry >= 0 when side = sign(z)", bool(((rv["er_bp"] - rv["side"] * rv["carry_bp"]) >= -1e-9).all()), True)
    s25 = wc["5Y"] - wc["2Y"]
    chk("vol_bp = std(daily change, 252d) x sqrt(63)", res.set_index("structure").loc["2Y5Y", "vol_bp"], float(np.diff(s25.to_numpy()[-253:]).std(ddof=1) * math.sqrt(63)), 1e-9)
    print("SELFTEST", "FAILED: " + ", ".join(bad) if bad else "PASSED")
    return 1 if bad else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--curve-par")
    p.add_argument("--curve-id")
    p.add_argument("--snap")
    p.add_argument("--tenors", default="2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y")
    p.add_argument("--kind", default="both", choices=["both", "curves", "flies"])
    p.add_argument("--h-days", type=int, default=63, help="horizon in trading days (63 = 3m)")
    p.add_argument("--z-ref", type=int, default=252)
    p.add_argument("--min-abs-z", type=float, default=1.5)
    p.add_argument("--max-hl", type=float, default=90.0)
    p.add_argument("--cost-bp", type=float, default=0.5, help="round-trip cost of a structure in bp of level; hurdle = 2x")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--out")
    p.add_argument("--passed-only", action="store_true", help="write only rows that passed the filters to --out")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if a.demo:
        w = synth_curves(plant={"7Y": 12.0})
        par, cid = to_par_long(w), "USD-SOFR"
        a.tenors = "2Y,3Y,5Y,7Y,10Y"
    else:
        if not (a.curve_par and a.curve_id):
            p.error("--curve-par and --curve-id are required (or --demo / --selftest)")
        par = pd.read_parquet(a.curve_par) if a.curve_par.endswith(".parquet") else pd.read_csv(a.curve_par)
        cid = a.curve_id
    w = wide_curve(par, cid, a.snap)
    tn = [t.strip().upper() for t in a.tenors.split(",")]
    miss = [t for t in tn if t not in w.columns]
    if miss:
        raise SystemExit(f"tenors missing from the curve: {miss}")
    d = scan(w, tn, h_days=a.h_days, z_ref=a.z_ref, kind=a.kind, ccy=cid.split("-")[0], curve_id=cid,
             min_abs_z=a.min_abs_z, max_hl=a.max_hl, cost_bp=a.cost_bp)
    if a.out:
        (d[d["passed"]] if a.passed_only else d).to_csv(a.out, index=False)
    print(f"# asof {d.attrs['asof']}  horizon {a.h_days}d  z_ref {a.z_ref}d  curve {cid}  structures {len(d)}  passed {int(d['passed'].sum())}")
    show = ["rank", "structure", "level_bp", "z_63", "z", "z_756", "pca_z", "pctile", "halflife_days", "df_t", "carry_bp", "vol_bp",
            "carry_vol", "er_bp", "hit_frac", "side", "scan_flags", "passed"]
    print(d[show].head(a.top).to_string(index=False, float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
