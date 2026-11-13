"""Butterfly (fly) weights and residuals: 50/50, maturity, regression, PCA, min-variance.

Conventions (same as SKILL.md)
  legs = (A, B, C) = (short wing, belly, long wing); y in percent; fly_bp = 100*(2*yB - yA - yC)
  positive fly = belly cheap (high yield). Weights are RISK (DV01) weights w = (wA, wB, wC) for the
  RECEIVE-belly package: wB > 0 (receive), wings < 0 (pay). Weighted fly = sum_i w_i*y_i, and
  P&L of the receive-belly package = -R * d(weighted fly in bp), R = risk per bp for weight 1.
  Notional_i = w_i * R / dv01_i, dv01_i = DV01 per unit notional (positive).

Usage
  python fly_weights.py --curve curve_par.csv --curve-id USD-SOFR --legs 2Y,5Y,10Y [--start 0D]
         [--snap eod_ny] [--window 126] [--pca-window 252] [--dv01 a,b,c]
  python fly_weights.py --selftest
Input table `curve_par`: date, snap, curve_id, start, tenor, par_rate_pct (csv or parquet).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

BASE = np.array([-1.0, 2.0, -1.0])


def scale_belly(w, belly=2.0):
    w = np.asarray(w, float)
    return w * belly / w[1]


# ---------------------------------------------------------------- weight schemes (risk terms)
def w_5050(belly=2.0):
    """50/50 DV01 (1:2:1): wings carry equal risk, sum of risks = 0."""
    return BASE * belly / 2.0


def w_maturity(m, belly=2.0):
    """Maturity-weighted: (m2-m1)*r1 = (m3-m2)*r3, r1+r3 = belly (linear-steepening assumption)."""
    m1, m2, m3 = m
    r1 = belly * (m3 - m2) / (m3 - m1)
    r3 = belly * (m2 - m1) / (m3 - m1)
    return np.array([-r1, belly, -r3])


def w_regression(dy, belly=2.0):
    """Direction-adjusted weights. dy: (n,3) yield changes of (A,B,C), any consistent unit.
    Fit d(fly) = a + b1*d(slope) + b2*dyB, fly = 2B-A-C, slope = C-A, then
    w = (-(1-b1), 2-b2, -(1+b1)): the package is uncorrelated in-sample with slope and belly."""
    dy = np.asarray(dy, float)
    f = 2 * dy[:, 1] - dy[:, 0] - dy[:, 2]
    X = np.column_stack([np.ones(len(dy)), dy[:, 2] - dy[:, 0], dy[:, 1]])
    _, b1, b2 = np.linalg.lstsq(X, f, rcond=None)[0]
    return scale_belly([-(1 - b1), 2 - b2, -(1 + b1)], belly), (b1, b2)


def w_belly_on_wings(dy, belly=1.0):
    """Min-variance via OLS of belly on the wings (changes): risk weights = betas (Tuckman style)."""
    dy = np.asarray(dy, float)
    X = np.column_stack([np.ones(len(dy)), dy[:, 0], dy[:, 2]])
    _, bA, bC = np.linalg.lstsq(X, dy[:, 1], rcond=None)[0]
    return np.array([-bA, 1.0, -bC]) * belly


def w_minvar(cov, belly=2.0):
    """Belly pinned, wings minimise Var(sum w_i dy_i): w_wings = -inv(Q_ww) Q_wb * belly."""
    Q = np.asarray(cov, float)
    wing = [0, 2]
    if np.linalg.cond(Q[np.ix_(wing, wing)]) > 1e10:
        raise ValueError("wing covariance is ill-conditioned (cond > 1e10)")
    ww = -np.linalg.solve(Q[np.ix_(wing, wing)], Q[wing, 1] * belly)
    return np.array([ww[0], belly, ww[1]])


def w_pca3(cov, belly=2.0):
    """PC3 (smallest eigenvector) of the 3-leg covariance, scaled so belly = `belly`.
    Orthogonal to PC1 and PC2 in risk space. Not DV01-neutral; sign flips cancel in the scaling."""
    vals, vecs = np.linalg.eigh(np.asarray(cov, float))
    return scale_belly(vecs[:, 0], belly)


def w_pc_neutral(dv01, loadings, belly_notional=100.0, belly_idx=1):
    """Notionals of the other legs so that sum_i N_i*dv01_i*L[k,i] = 0 for each PC row k.
    n legs need n-1 PC rows for an exact solve (3 legs: PC1 and PC2); more legs -> min-norm solution."""
    A = np.asarray(loadings, float) * np.asarray(dv01, float)
    others = [i for i in range(A.shape[1]) if i != belly_idx]
    x = np.linalg.lstsq(A[:, others], -A[:, belly_idx] * belly_notional, rcond=None)[0]
    n = np.zeros(A.shape[1])
    n[belly_idx] = belly_notional
    n[others] = x
    return n


def w_project_off(base, pcs, belly=2.0):
    """Minimal-change PC-neutral adjustment: w = x - P (P'P)^-1 P' x (pcs: (n,k) columns)."""
    P = np.asarray(pcs, float).reshape(len(base), -1)
    x = np.asarray(base, float)
    return scale_belly(x - P @ np.linalg.solve(P.T @ P, P.T @ x), belly)


def w_divide(base, pc1, belly=2.0):
    """Divide-by-loadings PC1 hedge; exact only if sum(base)=0; explodes when a loading ~ 0."""
    return scale_belly(np.asarray(base, float) / np.asarray(pc1, float), belly)


def w_cash_duration(dur, belly=1.0):
    """Cash- AND duration-neutral market-value weights (bond fly, belly MV = `belly`):
    MV_A + MV_C = -belly and D_A*MV_A + D_C*MV_C = -D_B*belly. Wings then are not 50/50 in risk."""
    d = np.asarray(dur, float)
    M = np.array([[1.0, 1.0], [d[0], d[2]]])
    a, c = np.linalg.solve(M, [-belly, -d[1] * belly])
    return np.array([a, belly, c])


def risk_to_notional(w, dv01_per_unit, risk=1.0):
    return np.asarray(w, float) * risk / np.asarray(dv01_per_unit, float)


# ---------------------------------------------------------------- series, diagnostics, residuals
def fly_series(y_pct: pd.DataFrame, w) -> pd.Series:
    """Weighted fly in bp: 100*sum w_i*y_i (y in percent), columns ordered (A,B,C)."""
    return 100.0 * (y_pct.iloc[:, :3] * np.asarray(w, float)).sum(axis=1)


def directionality(y_pct: pd.DataFrame, w, window=63) -> dict:
    """R2 and beta of the weighted fly to the belly level, plus correlations to belly and slope (changes, last `window`)."""
    f = fly_series(y_pct, w)
    b, s = y_pct.iloc[:, 1] * 100, (y_pct.iloc[:, 2] - y_pct.iloc[:, 0]) * 100
    df = pd.concat([f, b, s], axis=1, keys=["f", "b", "s"]).dropna()
    lv = df.iloc[-252:] if len(df) > 252 else df
    r2 = float(np.corrcoef(lv.f, lv.b)[0, 1] ** 2) if len(lv) > 3 else np.nan
    d = df.diff().dropna().iloc[-window:]
    return {"r2_levels_belly": r2,
            "beta_levels_belly": float(np.polyfit(lv.b, lv.f, 1)[0]) if len(lv) > 3 else np.nan,
            "corr_chg_belly": float(d.f.corr(d.b)), "corr_chg_slope": float(d.f.corr(d.s))}


def residual_z(fly: pd.Series, belly: pd.Series, slope: pd.Series | None = None, window=126):
    """Trailing-window residual: fit fly ~ a + b*belly (+ c*slope) on the window ending at t (levels, no
    future data), take the residual at t, z = residual / std of in-window residuals. Act from t+1.
    Levels regression: use for rich/cheap ranking only (serial correlation); hedge weights come from changes.
    Returns (resid, z, r2)."""
    belly = belly.reindex(fly.index)
    slope = None if slope is None else slope.reindex(fly.index)
    X = [np.ones(len(fly)), belly.to_numpy(float)] + ([slope.to_numpy(float)] if slope is not None else [])
    X, y = np.column_stack(X), fly.to_numpy(float)
    res, zz, r2 = (np.full(len(y), np.nan) for _ in range(3))
    for t in range(window - 1, len(y)):
        sl = slice(t - window + 1, t + 1)
        if not np.isfinite(X[sl]).all() or not np.isfinite(y[sl]).all():
            continue
        beta = np.linalg.lstsq(X[sl], y[sl], rcond=None)[0]
        e = y[sl] - X[sl] @ beta
        sd = e.std(ddof=X.shape[1])
        res[t], zz[t] = e[-1], e[-1] / sd if sd > 0 else np.nan
        r2[t] = 1 - e.var() / y[sl].var() if y[sl].var() > 0 else np.nan
    return pd.Series(res, fly.index), pd.Series(zz, fly.index), pd.Series(r2, fly.index)


# ---------------------------------------------------------------- CLI
def load_legs(path, curve_id, legs, start="0D", snap=None):
    df = pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)
    m = (df.curve_id == curve_id) & (df.start == start) & (df.tenor.isin(legs))
    if snap and "snap" in df:
        m &= df.snap == snap
    df = df[m]
    if "snap" in df and df.snap.nunique() > 1:
        raise SystemExit("several snaps in file: pass --snap")
    wide = df.pivot_table(index="date", columns="tenor", values="par_rate_pct").reindex(columns=legs)
    wide.index = pd.to_datetime(wide.index)
    wide = wide.sort_index().dropna()
    if wide.empty:
        raise SystemExit(f"no complete rows for {curve_id} start={start} legs={legs}: check curve_id/start/tenors")
    return wide


def report(y, window, pca_window, dv01=None):
    if len(y) < max(window, 60) + 1:
        raise SystemExit(f"history too short: {len(y)} rows, need > {max(window, 60)}")
    dy = y.diff().dropna() * 100
    tail = dy.iloc[-pca_window:]
    cov = np.cov(tail.to_numpy().T)
    schemes = {"50/50": w_5050(), "regression": w_regression(tail.to_numpy())[0],
               "pca3": w_pca3(cov), "minvar": w_minvar(cov)}
    rows = []
    for name, w in schemes.items():
        f = fly_series(y, w)
        r, z, r2 = residual_z(f, y.iloc[:, 1] * 100, window=window)
        d = directionality(y, w)
        rows.append({"scheme": name, "wA": w[0], "wB": w[1], "wC": w[2], "sum_risk": w.sum(),
                     "fly_bp": f.iloc[-1], "resid_bp": r.iloc[-1], "z": z.iloc[-1], "r2_vs_belly": d["r2_levels_belly"],
                     "corr_chg_slope": d["corr_chg_slope"]})
        if dv01 is not None:
            rows[-1]["notionals_per_1_risk"] = np.round(risk_to_notional(w, dv01), 6).tolist()
    return pd.DataFrame(rows).round(3)


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    bad = []

    def check(name, got, want, tol):
        ok = np.allclose(got, want, atol=tol)
        print(("ok   " if ok else "FAIL ") + name, np.round(got, 4))
        if not ok:
            bad.append(name)

    # 1. minimal-change PC1-neutral (published: -1.1002, 2, -1.0780 for PC1 = 0.660/0.604/0.447)
    pc1 = [0.660, 0.604, 0.447]
    check("min-change PC1", w_project_off(BASE, pc1), [-1.1002, 2, -1.0780], 5e-4)
    # 2. divide-by-loadings (published: approx -0.91, 2, -1.35)
    check("divide by PC1", w_divide(BASE, pc1), [-0.91, 2, -1.35], 0.01)
    # 3. PC3 of the 3-5-10 covariance (published weights -0.90, 1, -0.46; inputs rounded to 0.1)
    C = [[7.1, 8.9, 5.5], [8.9, 14.0, 13.0], [5.5, 13.0, 17.5]]
    check("PC3 3-5-10", w_pca3(C, belly=1.0), [-0.90, 1.0, -0.46], 0.02)
    # 4. PC1/PC2-neutral 10s20s30s: receive 100 20y -> pay 49.56 10y, 53.60 30y (rounded loadings)
    L = [[3.44, 3.73, 3.77], [0.07, 1.02, 1.35]]
    check("PC1+PC2 neutral 10-20-30", w_pc_neutral([0.09347, 0.17064, 0.23600], L, 100.0)[[0, 2]], [-49.56, -53.60], 0.1)
    # 5. maturity weights 2-5-10: risks 1.25 / 0.75
    check("maturity 2-5-10", w_maturity((2, 5, 10)), [-1.25, 2, -0.75], 1e-9)
    # 5b. cash- and duration-neutral bond fly, durations 2/5/10: MV -0.625 / 1 / -0.375
    check("cash+duration neutral", w_cash_duration((2, 5, 10)), [-0.625, 1, -0.375], 1e-9)
    # 6. regression recovers known betas: fly = b1*slope + b2*belly + e, built exactly
    rng = np.random.default_rng(1)
    n, b1, b2 = 20000, 0.15, 0.30
    a, s, e = rng.normal(size=n), rng.normal(size=n) * 0.5, rng.normal(size=n) * 0.3
    p = ((2 - b2) * a - (1 + b1) * s - e) / 2
    dy = np.column_stack([p, a, p + s])
    w, (g1, g2) = w_regression(dy, belly=2 - b2)
    check("regression betas", [g1, g2], [b1, b2], 0.02)
    check("regression weights", w, [-(1 - b1), 2 - b2, -(1 + b1)], 0.03)
    f = 2 * dy[:, 1] - dy[:, 0] - dy[:, 2]
    resid_fly = dy @ w
    cs = [np.corrcoef(resid_fly, x)[0, 1] for x in (dy[:, 2] - dy[:, 0], dy[:, 1])]
    check("regression fly ~ uncorrelated with slope, belly", cs, [0, 0], 0.02)
    # 7. min-variance beats nearby weights; belly-on-wings and min-var agree
    X = rng.normal(size=(5000, 3)) @ np.array([[1, .8, .6], [0, .6, .5], [0, 0, .4]])
    Q = np.cov(X.T)
    wm = w_minvar(Q)
    v = lambda w_: w_ @ Q @ w_
    worse = all(v(wm) <= v(wm + d) for d in ([.05, 0, 0], [-.05, 0, 0], [0, 0, .05], [0, 0, -.05]))
    print(("ok   " if worse else "FAIL ") + "min-var is a minimum")
    if not worse:
        bad.append("min-var")
    check("belly-on-wings = min-var", w_belly_on_wings(X, belly=2.0), wm, 0.03)
    # 8. simulated 3-factor world: PCA fly has ~0 covariance with PC1, PC2 scores
    Lf = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    F = rng.normal(size=(20000, 3)) * np.array([5.0, 2.0, 0.7])
    wp = w_pca3(np.cov((F @ Lf.T).T), belly=2.0)
    expo = np.abs(Lf[:, :2].T @ wp) / np.abs(wp).sum()
    check("PCA fly exposure to PC1/PC2", expo, [0, 0], 0.01)
    check("PCA fly loads on PC3 direction", abs(wp @ Lf[:, 2]) / np.linalg.norm(wp), 1.0, 1e-6)
    # 8b. units: y = (1.00, 2.00, 2.50)% -> 2*2.00 - 1.00 - 2.50 = 0.50% = +50bp (a missing x100 would give 0.5)
    check("fly_series bp", fly_series(pd.DataFrame([[1.0, 2.0, 2.5]]), BASE).to_numpy(), [50.0], 1e-9)
    # 8c. directionality: legs A, C ~fixed (1e-4 noise), so fly ~ 2*belly - const: R2 ~ 1, beta (bp/bp) ~ 2
    yb = pd.Series(rng.normal(size=300).cumsum() * 0.01 + 3.0, pd.bdate_range("2020-01-01", periods=300))
    yy = pd.DataFrame({"A": 1.0 + 1e-4 * rng.normal(size=300), "B": yb, "C": 2.0 + 1e-4 * rng.normal(size=300)}, yb.index)
    dd = directionality(yy, BASE)
    check("directionality R2, beta", [dd["r2_levels_belly"], dd["beta_levels_belly"]], [1.0, 2.0], 2e-3)
    dn = directionality(yy, -BASE)  # opposite package: beta -2, R2 still 1 (guards against r instead of r^2)
    check("directionality R2, beta (reversed)", [dn["r2_levels_belly"], dn["beta_levels_belly"]], [1.0, -2.0], 2e-3)
    # 8d. report() runs end to end on a synthetic curve and returns finite weights/fly
    yr = pd.DataFrame({"A": 1.0 + 0.3 * yb, "B": yb, "C": 0.5 + 0.6 * yb + rng.normal(size=300) * 0.01}, yb.index)
    rp = report(yr, 126, 252)
    ok = len(rp) == 4 and np.isfinite(rp[["wA", "wB", "wC", "fly_bp"]].to_numpy()).all()
    print(("ok   " if ok else "FAIL ") + "report() end to end")
    if not ok:
        bad.append("report")
    # 9. residual z flags a shocked point
    idx = pd.bdate_range("2020-01-01", periods=400)
    belly = pd.Series(rng.normal(size=400).cumsum() + 300, idx)
    fly = 5 + 0.4 * belly + rng.normal(size=400)
    fly.iloc[-1] += 6.0
    r, z, r2 = residual_z(fly, belly, window=126)
    ok = 4.0 < r.iloc[-1] < 8.0 and z.iloc[-1] > 3.0 and abs(r.iloc[-20:-1]).max() < 5
    print(("ok   " if ok else "FAIL ") + "residual z", round(r.iloc[-1], 2), round(z.iloc[-1], 2))
    if not ok:
        bad.append("residual z")
    print("SELFTEST " + ("FAILED: " + ", ".join(bad) if bad else "PASSED"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--curve")
    ap.add_argument("--curve-id")
    ap.add_argument("--legs", default="2Y,5Y,10Y")
    ap.add_argument("--start", default="0D")
    ap.add_argument("--snap")
    ap.add_argument("--window", type=int, default=126, help="residual regression/z window (days)")
    ap.add_argument("--pca-window", type=int, default=252, help="window for covariance-based weights (days)")
    ap.add_argument("--dv01", help="comma list of DV01 per unit notional for the 3 legs")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.curve and a.curve_id):
        ap.error("--curve and --curve-id required")
    legs = a.legs.split(",")
    y = load_legs(a.curve, a.curve_id, legs, a.start, a.snap)
    dv = [float(x) for x in a.dv01.split(",")] if a.dv01 else None
    print(report(y, a.window, a.pca_window, dv).to_string(index=False))


if __name__ == "__main__":
    main()
