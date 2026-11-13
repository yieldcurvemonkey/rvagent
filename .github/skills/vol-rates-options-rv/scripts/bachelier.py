#!/usr/bin/env python
"""Normal-vol (Bachelier) toolkit for swaption / futures-option RV.

Units: F, K in bp (or any one consistent unit), sigma in bp per sqrt(year), T in years.
Price is in the same unit as F (bp of rate); money = price * annuity (PV01 per bp * notional).

Functions: bachelier_price, greeks, implied_vol, straddle_breakeven_bp, daily_breakeven_bp,
normal_from_black, black_from_normal, realized_vol_bp, forward_vol, fwd_swap_vol, walk_vol,
rate_pcs, grid_residuals (macro-vol / surface-PCA rich-cheap residuals with z-scores).

CLI:
  python bachelier.py price --F 100 --K 100 --vol 100 --T 1 [--side payer|receiver|straddle]
  python bachelier.py iv --price 39.89 --F 100 --K 100 --T 1 --side payer
  python bachelier.py ratio --csv rates.csv --nvol 95 [--windows 21,63]   # csv: date,rate_pct
  python bachelier.py grid --vol-csv vol_surface.csv [--curve-csv curve_par.csv] [--mode pca|macro]
  python bachelier.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

SQRT2PI = math.sqrt(2 * math.pi)


# ---------------------------------------------------------------- pricing
def bachelier_price(F, K, sigma, T, side="payer", annuity=1.0):
    """Normal-model option price. side: payer|receiver|straddle. Same unit as F."""
    if side == "straddle":
        return bachelier_price(F, K, sigma, T, "payer", annuity) + bachelier_price(F, K, sigma, T, "receiver", annuity)
    w = 1.0 if side == "payer" else -1.0
    s = sigma * math.sqrt(T)
    if s <= 0:
        return annuity * max(w * (F - K), 0.0)
    d = w * (F - K) / s
    return annuity * (w * (F - K) * norm.cdf(d) + s * norm.pdf(d))


def greeks(F, K, sigma, T, side="payer"):
    """Per-unit greeks (annuity = 1). delta: d price/dF; gamma: d2 price/dF2; vega: d price/d sigma (per 1 bp vol);
    theta: d price/dt per YEAR of time passing (undiscounted, = -0.5 sigma^2 gamma). Straddle = payer + receiver."""
    if side == "straddle":
        p, r = greeks(F, K, sigma, T, "payer"), greeks(F, K, sigma, T, "receiver")
        return {k: p[k] + r[k] for k in p}
    s = sigma * math.sqrt(T)
    d = (F - K) / s
    delta = norm.cdf(d) if side == "payer" else norm.cdf(d) - 1.0
    gamma = norm.pdf(d) / s
    return {"delta": delta, "gamma": gamma, "vega": math.sqrt(T) * norm.pdf(d), "theta": -0.5 * sigma ** 2 * gamma}


def implied_vol(price, F, K, T, side="payer", annuity=1.0, hi=5000.0):
    """Invert bachelier_price for sigma (bp/sqrt(yr)). Raises if price is below intrinsic or not bracketed."""
    p = price / annuity
    w = 1.0 if side == "payer" else -1.0
    if side != "straddle" and p < max(w * (F - K), 0.0) - 1e-12:
        raise ValueError("price below intrinsic value")
    f = lambda v: bachelier_price(F, K, v, T, side) - p
    if f(hi) < 0:
        raise ValueError("price too high for vol <= hi")
    return brentq(f, 1e-9, hi, xtol=1e-10)


def straddle_breakeven_bp(sigma, T):
    """ATMF straddle premium in bp = move needed at expiry for an UNHEDGED straddle to break even."""
    return 2.0 * sigma * math.sqrt(T / (2 * math.pi))


def daily_breakeven_bp(sigma, days=252):
    """MEAN ABSOLUTE daily move (bp) consistent with break-even for an ATM option, assuming normal moves:
    sqrt(2/pi) * sigma / sqrt(days). The RMS daily move at which hedged gamma P&L offsets theta is sigma/sqrt(days)
    (the 1-sd daily move); do not mix the two."""
    return math.sqrt(2 / math.pi) * sigma / math.sqrt(days)


def normal_from_black(F, sigma_ln, T):
    """Exact ATM normal vol (same units as F) that reprices an ATM Black vol (sigma_ln as a fraction, 0.20 = 20%)."""
    v = sigma_ln * math.sqrt(T)
    return F * (2 * norm.cdf(v / 2) - 1) * SQRT2PI / math.sqrt(T)


def black_from_normal(F, sigma_n, T):
    """Inverse of normal_from_black: ATM lognormal vol (fraction)."""
    return brentq(lambda s: normal_from_black(F, s, T) - sigma_n, 1e-9, 50.0)


# ---------------------------------------------------------------- realised vol
def realized_vol_bp(rate_pct, window=21, days=252):
    """Rolling realised normal vol in bp/yr from a series of rates in PERCENT (close-to-close, zero-mean, i.e.
    sqrt(mean(d^2)); no demeaning so a drift counts as realised movement, which is what a hedger pays)."""
    d = rate_pct.astype(float).diff() * 100.0
    return np.sqrt((d ** 2).rolling(window).mean() * days)


# ---------------------------------------------------------------- forward vol
def forward_vol(sig_long, T_long, sig_short, T_short):
    """Variance additivity for the SAME underlying rate: forward vol between T_short and T_long.
    sqrt((T_long*sig_long^2 - T_short*sig_short^2)/(T_long - T_short)). Raises on negative variance."""
    v = (T_long * sig_long ** 2 - T_short * sig_short ** 2) / (T_long - T_short)
    if v < 0:
        raise ValueError("negative forward variance: term structure inconsistent with additivity")
    return math.sqrt(v)


def fwd_swap_vol(sig_a, sig_b, L, rho):
    """Vol of a forward swap (e.g. 1y5y5y) from same-expiry par vols: sig_a = vol of the shorter tail (1y5y),
    sig_b = longer tail (1y10y), L = annuity(1y10y)/annuity(1y5y5y) (> 1), rho = corr of the two par rates' changes.
    sqrt(((1-L) a)^2 + 2 (1-L) L rho a b + (L b)^2)."""
    return math.sqrt(((1 - L) * sig_a) ** 2 + 2 * (1 - L) * L * rho * sig_a * sig_b + (L * sig_b) ** 2)


def midcurve_vol(sig_13, sig_12, dv01_13, dv01_12, dv01_23, rho):
    """Midcurve (expiry T1, swap T2-T3) vol as a DV01-weighted spread option:
    sqrt((D13 s13)^2 + (D12 s12)^2 - 2 rho D13 s13 D12 s12) / D23, s13/s12 = vols of the T1->T3 and T1->T2 swaps."""
    a, b = dv01_13 * sig_13, dv01_12 * sig_12
    return math.sqrt(a * a + b * b - 2 * rho * a * b) / dv01_23


def walk_vol(vols, weights):
    """Time-weighted 'walk' vol: sqrt(sum w_i vol_i^2 / sum w_i) over the vols delivered while an option rolls down."""
    v, w = np.asarray(vols, float), np.asarray(weights, float)
    return float(np.sqrt((w * v ** 2).sum() / w.sum()))


# ---------------------------------------------------------------- surface rich/cheap
def rate_pcs(curve_wide, n=3):
    """First n principal-component SCORES of a dates x tenors table of swap rates (levels, demeaned)."""
    X = curve_wide.dropna().astype(float)
    Xc = X - X.mean()
    u, s, _ = np.linalg.svd(Xc.values, full_matrices=False)
    return pd.DataFrame(u[:, :n] * s[:n], index=X.index, columns=[f"pc{i + 1}" for i in range(n)])


def grid_residuals(vol_wide, n_pc=3, exog=None, window=None):
    """Rich/cheap residuals of the latest row of a dates x grid-points table of ATM normal vols (bp).

    exog=None  -> surface PCA: keep n_pc PCs of the demeaned grid, residual = actual - reconstruction (RELATIVE value only).
    exog=DataFrame (same index, e.g. rate_pcs of the swap curve) -> macro-vol: each point regressed on [1, exog];
    residual = actual - fit (a LEVEL view, valid only inside a regime-consistent sample).
    window: use only the last `window` rows for the fit and for the z-score (default: all).
    Returns DataFrame[resid_bp, z] indexed by grid point; resid > 0 = rich, < 0 = cheap."""
    X = vol_wide.dropna().astype(float)
    if exog is not None:
        X = X.loc[X.index.intersection(exog.dropna().index)]
    if window:
        X = X.iloc[-window:]
    if len(X) < max(60, 5 * (n_pc + 1)):
        raise ValueError(f"only {len(X)} usable rows: need >= 60 (>= 2y of daily data advised) for a residual z-score")
    if exog is None:
        mu = X.mean()
        u, s, vt = np.linalg.svd((X - mu).values, full_matrices=False)
        fit = (u[:, :n_pc] * s[:n_pc]) @ vt[:n_pc] + mu.values
        res = X.values - fit
    else:
        E = np.column_stack([np.ones(len(X)), exog.loc[X.index].values])
        beta, *_ = np.linalg.lstsq(E, X.values, rcond=None)
        res = X.values - E @ beta
    res = pd.DataFrame(res, index=X.index, columns=X.columns)
    z = (res.iloc[-1] - res.mean()) / res.std(ddof=1)
    return pd.DataFrame({"resid_bp": res.iloc[-1], "z": z})


# ---------------------------------------------------------------- selftest
def _selftest():
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info else ""))
        ok &= bool(cond)

    # 1. ATM price closed form: sigma sqrt(T/2pi); sigma=100, T=1 -> 39.8942
    p = bachelier_price(0, 0, 100, 1, "payer")
    check("ATM payer = sigma*sqrt(T/2pi)", abs(p - 100 / SQRT2PI) < 1e-9, f"{p:.4f}")
    # 2. put-call parity: payer - receiver = F - K
    F, K, s, T = 120.0, 100.0, 85.0, 2.5
    par = bachelier_price(F, K, s, T, "payer") - bachelier_price(F, K, s, T, "receiver")
    check("payer - receiver = F - K", abs(par - (F - K)) < 1e-9, f"{par:.6f}")
    # 3. implied vol round trip (OTM, ITM, receiver)
    for side, KK in (("payer", 140.0), ("receiver", 140.0), ("payer", 90.0)):
        pr = bachelier_price(F, KK, s, T, side)
        check(f"IV round trip {side} K={KK}", abs(implied_vol(pr, F, KK, T, side) - s) < 1e-6)
    # 4. Darbyshire Ex 20.4: 2% 1Y10Y ATM straddle priced at 25bp -> normal vol 31.33
    v = implied_vol(25.0, 200.0, 200.0, 1.0, "straddle")
    check("Ex 20.4 straddle 25bp -> 31.33 nvol", abs(v - 31.33) < 0.01, f"{v:.3f}")
    # 5. greeks vs finite differences
    g = greeks(F, K, s, T, "payer")
    h = 1e-3
    fd_delta = (bachelier_price(F + h, K, s, T) - bachelier_price(F - h, K, s, T)) / (2 * h)
    fd_gamma = (bachelier_price(F + 1, K, s, T) - 2 * bachelier_price(F, K, s, T) + bachelier_price(F - 1, K, s, T)) / 1.0
    fd_vega = (bachelier_price(F, K, s + h, T) - bachelier_price(F, K, s - h, T)) / (2 * h)
    fd_theta = (bachelier_price(F, K, s, T - h) - bachelier_price(F, K, s, T + h)) / (2 * h)
    check("delta/gamma/vega/theta match finite differences",
          abs(g["delta"] - fd_delta) < 1e-6 and abs(g["gamma"] - fd_gamma) < 1e-3 and abs(g["vega"] - fd_vega) < 1e-5
          and abs(g["theta"] - fd_theta) < 1e-4, f"{g}")
    # 6. BofA primer: 1Y10Y ATM payer 110bp -> breakeven ~44bp (110*0.3989 = 43.9); daily vol 6.93bp
    be = bachelier_price(0, 0, 110, 1)
    check("110nv 1y ATM payer ~ 43.9bp; daily 1-sd 6.93bp", abs(be - 43.88) < 0.05 and abs(110 / math.sqrt(252) - 6.93) < 0.01,
          f"{be:.2f}")
    # 7. straddle breakeven = 2 x payer; daily breakeven = sqrt(2/pi) x daily vol
    check("straddle BE = 2 x ATM payer", abs(straddle_breakeven_bp(110, 1) - 2 * be) < 1e-9)
    check("daily BE = 0.7979 x daily vol", abs(daily_breakeven_bp(110) - 0.797885 * 6.9286) < 1e-3)
    # 8. normal<->lognormal: 20% at 5% rate, T=0.25 ~ 100bp; round-trip; small-vol series F s (1 - s^2 T/24)
    n = normal_from_black(500.0, 0.20, 0.25)
    check("normal_from_black ~ F*sigma (100bp)", abs(n - 100.0) < 0.1, f"{n:.4f}")
    nT = normal_from_black(200.0, 0.1568, 1.0)
    check("Ex 20.4 log vol 15.68% x 2% ~ 31.36 nvol", abs(nT - 31.36) < 0.05, f"{nT:.3f}")
    check("black_from_normal round trip", abs(black_from_normal(500.0, n, 0.25) - 0.20) < 1e-9)
    # 9. forward vol: Darbyshire Ex 20.6 (2Y7Y 50, 1Y1Y7Y 44 -> 1Y7Y in 1Y = 55.35) and Ex 20.5 (84bp)
    check("Ex 20.6 forward-forward vol 55bp", abs(forward_vol(50, 2, 44, 1) - 55.35) < 0.01, f"{forward_vol(50, 2, 44, 1):.2f}")
    check("Ex 20.5 vol of 1y5y5y = 84bp", abs(fwd_swap_vol(39, 59, 2.10, 0.95) - 84.2) < 0.1,
          f"{fwd_swap_vol(39, 59, 2.10, 0.95):.2f}")
    # midcurve: rho=1, same-sign DV01-weighted difference (Credit Suisse FVA example 107bp from 99,37,DV01 1/9.6/8.6)
    mc = midcurve_vol(99, 37, 9.6, 1.0, 8.6, 1.0)
    check("FVA example midcurve vol (rho=1) ~ 107bp", abs(mc - 107.0) < 1.5, f"{mc:.1f}")
    # 10. walk vol (BofA example weights/vars -> 132.3 vs 142.8)
    wv = walk_vol([87.5, 101.8, 113.8, 122.8, 141.5, 143.8, 142.8], [.0417, .0833, .0833, .1667, .25, .25, .125])
    check("walk vol example 132.3bp", abs(wv - 132.3) < 0.2, f"{wv:.2f}")
    # 11. realised vol: constant +-1bp daily moves -> 1bp*sqrt(252)
    r = pd.Series(np.cumsum(np.tile([0.01, -0.01], 60)))
    rv = realized_vol_bp(r, 21).iloc[-1]
    check("realised vol of +-1bp days = 15.87", abs(rv - math.sqrt(252)) < 1e-6, f"{rv:.3f}")
    # 12. grid_residuals: 2-factor synthetic surface + one shocked point must be flagged rich, in both modes
    rng = np.random.default_rng(0)
    n_d, cols = 300, [f"{e}x{t}" for e in ("1m", "3m", "1y") for t in ("2y", "10y", "30y")]
    lvl = np.cumsum(rng.normal(0, 1, n_d))
    slope = np.cumsum(rng.normal(0, .5, n_d))
    ld = np.linspace(.8, 1.2, 9)
    sd = np.linspace(-1, 1, 9)
    Xv = 80 + np.outer(lvl, ld) + np.outer(slope, sd) + rng.normal(0, .05, (n_d, 9))
    Xv[-1, 4] += 6.0
    vw = pd.DataFrame(Xv, columns=cols, index=pd.RangeIndex(n_d))
    out = grid_residuals(vw, n_pc=2)
    check("PCA residual flags the shocked point rich", out["z"].idxmax() == cols[4] and out["z"].max() > 5,
          f"{out['z'].idxmax()} z={out['z'].max():.1f}")
    # macro mode with known coefficients: vol = 50 + 2*pc1 - 1*pc2 + noise, last point +4 -> resid ~ +4
    ex = pd.DataFrame(rng.normal(0, 1, (n_d, 2)), columns=["pc1", "pc2"])
    y = 50 + 2 * ex["pc1"] - ex["pc2"] + rng.normal(0, .1, n_d)
    y.iloc[-1] += 4.0
    o2 = grid_residuals(pd.DataFrame({"a": y}), exog=ex)
    check("macro-vol residual recovers +4bp shock", abs(o2["resid_bp"].iloc[0] - 4.0) < 0.5, f"{o2['resid_bp'].iloc[0]:.2f}")
    # 13. short history is refused, not z-scored
    try:
        grid_residuals(vw.iloc[:20], n_pc=2)
        check("short history raises", False)
    except ValueError:
        check("short history raises", True)
    # 14. CLI loader: two currencies in one table must raise (not average); selecting one returns that ccy's vol
    import io
    rows = ["date,snap,index_id,product,expiry,fwd_start,tenor,strike_offset_bp,nvol_bp"]
    for d in ("2026-01-02", "2026-01-05"):
        rows += [f"{d},eod,USD-SOFR,swaption,1Y,0D,10Y,0,100", f"{d},eod,EUR-ESTR,swaption,1Y,0D,10Y,0,60",
                 f"{d},eod,USD-SOFR,swaption,1Y,1Y,10Y,0,999"]
    txt = chr(10).join(rows)
    try:
        _wide_atm(io.StringIO(txt))
        check("mixed index_id raises", False)
    except ValueError:
        check("mixed index_id raises", True)
    w = _wide_atm(io.StringIO(txt), index_id="EUR-ESTR")
    check("index_id filter keeps EUR spot-start only", float(w.iloc[0, 0]) == 60.0)
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI
def _single(df, col, val, what):
    """Filter df[col]==val, or (val None) require exactly one distinct value: pivoting a mixed table would silently AVERAGE."""
    if col not in df.columns:
        return df
    if val is not None:
        df = df[df[col] == val]
    if df[col].nunique() > 1:
        raise ValueError(f"table holds several {what} {sorted(df[col].astype(str).unique())[:6]}: pass one explicitly")
    return df


def _wide_atm(vol_csv, product="swaption", index_id=None, snap=None):
    df = pd.read_csv(vol_csv, parse_dates=["date"])
    df = df[(df["product"] == product) & (df["strike_offset_bp"] == 0) & (df["fwd_start"].astype(str) == "0D")]
    df = _single(_single(df, "index_id", index_id, "index_id"), "snap", snap, "snap")
    df = df.assign(pt=df["expiry"].astype(str) + "x" + df["tenor"].astype(str))
    return df.pivot_table(index="date", columns="pt", values="nvol_bp")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("price")
    p.add_argument("--F", type=float, required=True)
    p.add_argument("--K", type=float, required=True)
    p.add_argument("--vol", type=float, required=True)
    p.add_argument("--T", type=float, required=True)
    p.add_argument("--side", default="payer", choices=["payer", "receiver", "straddle"])
    p.add_argument("--annuity", type=float, default=1.0)
    q = sub.add_parser("iv")
    q.add_argument("--price", type=float, required=True)
    for a in ("F", "K", "T"):
        q.add_argument(f"--{a}", type=float, required=True)
    q.add_argument("--side", default="payer", choices=["payer", "receiver", "straddle"])
    q.add_argument("--annuity", type=float, default=1.0)
    r = sub.add_parser("ratio")
    r.add_argument("--csv", required=True, help="columns: date, rate_pct (the underlying swap rate, one tail)")
    r.add_argument("--nvol", type=float, required=True, help="current ATMF implied normal vol, bp/yr")
    r.add_argument("--windows", default="21,63")
    g = sub.add_parser("grid")
    g.add_argument("--vol-csv", required=True, help="vol_surface table (ATMF rows are used)")
    g.add_argument("--curve-csv", help="curve_par table (needed for --mode macro)")
    g.add_argument("--mode", default="pca", choices=["pca", "macro"])
    g.add_argument("--index-id", help="vol_surface index_id (required if the table holds several)")
    g.add_argument("--curve-id", help="curve_par curve_id for --mode macro (required if several)")
    g.add_argument("--snap", help="snap to use (required if several)")
    g.add_argument("--n-pc", type=int, default=3)
    g.add_argument("--window", type=int, default=504)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "price":
        px = bachelier_price(a.F, a.K, a.vol, a.T, a.side, a.annuity)
        print(f"price={px:.6f}  greeks(per unit annuity)={greeks(a.F, a.K, a.vol, a.T, a.side)}")
    elif a.cmd == "iv":
        print(f"nvol={implied_vol(a.price, a.F, a.K, a.T, a.side, a.annuity):.4f}")
    elif a.cmd == "ratio":
        s = pd.read_csv(a.csv, parse_dates=["date"]).set_index("date")["rate_pct"]
        for w in (int(x) for x in a.windows.split(",")):
            rv = realized_vol_bp(s, w).iloc[-1]
            print(f"window={w}d realised={rv:.2f}bp/yr  implied/realised={a.nvol / rv if rv > 0 else float('nan'):.3f}")
    elif a.cmd == "grid":
        W = _wide_atm(a.vol_csv, index_id=a.index_id, snap=a.snap)
        ex = None
        if a.mode == "macro":
            c = pd.read_csv(a.curve_csv, parse_dates=["date"])
            c = _single(_single(c[c["start"].astype(str) == "0D"], "curve_id", a.curve_id, "curve_id"), "snap", a.snap, "snap")
            c = c.pivot_table(index="date", columns="tenor", values="par_rate_pct")
            ex = rate_pcs(c, 3)
        print(grid_residuals(W, a.n_pc, ex, a.window).round(2).to_string())
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
