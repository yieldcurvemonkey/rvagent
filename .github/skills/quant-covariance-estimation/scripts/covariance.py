#!/usr/bin/env python3
"""Covariance estimation for rate-change panels: EWMA, Ledoit-Wolf, Gerber, PCA smoothing, hedges, QLIKE.

All functions take a (T x N) pandas DataFrame / ndarray of CHANGES (bp or % returns, never levels), oldest row first.
Self-contained: numpy, pandas, scipy only (scikit-learn is used in --selftest if installed).

    python -I covariance.py --selftest
    python -I covariance.py cov changes.csv --method ewma --halflife 40
    python -I covariance.py halflife-scan changes.csv --halflives 10 21 42 63 126
    python -I covariance.py hedge changes.csv --halflife 63 --risk 2Y=-10000 5Y=2500 10Y=10000 --hedges 2Y 10Y

Input file: wide table (first column or `date` = date, other columns = changes), or a long `curve_par` table
(columns date, curve_id, start, tenor, par_rate_pct; use --curve-id), converted to daily bp changes.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

def _panel(X) -> np.ndarray:
    """(T x N) float array of CHANGES; rejects NaN/inf and T < 2 instead of returning silent NaN matrices."""
    A = np.asarray(X, dtype=float)
    if A.ndim == 1:
        A = A[:, None]
    if A.ndim != 2 or len(A) < 2:
        raise ValueError("need a (T x N) panel with T >= 2 rows")
    if not np.isfinite(A).all():
        raise ValueError("NaN/inf in panel: drop or repair rows first (see data-quality-and-timeseries-hygiene)")
    return A


# ----------------------------------------------------------------------------- weights / EWMA


def ewma_weights(T: int, halflife: float) -> np.ndarray:
    """Normalised EWMA weights, oldest first. lambda = 0.5**(1/halflife); w_s ~ lambda**s, sum = 1."""
    lam = 0.5 ** (1.0 / halflife)
    w = lam ** np.arange(T - 1, -1, -1)
    return w / w.sum()


def effective_obs(halflife: float) -> float:
    """t_eff = (1+lam)/(1-lam) = 1/sum(w^2) for T >> halflife (8-day half-life -> ~23)."""
    lam = 0.5 ** (1.0 / halflife)
    return (1 + lam) / (1 - lam)


def overlap_eff_obs(T: int, L: int) -> float:
    """Effective independent obs of T daily obs aggregated to overlapping L-day returns (Muller 1993)."""
    return 3.0 * T * L / (2.0 * L * L + 1.0)


def ewma_cov(X, halflife: float = 40.0, demean: bool = False) -> np.ndarray:
    """Zero-mean EWMA covariance: sum_s w_s x_s x_s' with w normalised ((1-lam)/(1-lam^T) lam^s). Default no demeaning."""
    A = _panel(X)
    if demean:
        A = A - (ewma_weights(len(A), halflife)[:, None] * A).sum(0)
    w = ewma_weights(len(A), halflife)
    return (A * w[:, None]).T @ A


def fast_vol_slow_corr(X, hl_vol: float = 21.0, hl_corr: float = 126.0) -> np.ndarray:
    """Sigma = V Omega V: fast-half-life vols, slow-half-life correlation."""
    v = np.sqrt(np.diag(ewma_cov(X, hl_vol)))
    C = ewma_cov(X, hl_corr)
    d = np.sqrt(np.diag(C))
    return np.outer(v, v) * (C / np.outer(d, d))


# ----------------------------------------------------------------------------- shrinkage / factor


def sample_cov(X, demean: bool = False) -> np.ndarray:
    """Divisor-T second-moment matrix (mean NOT removed by default: risk convention)."""
    A = _panel(X)
    if demean:
        A = A - A.mean(0)
    return A.T @ A / len(A)


def ledoit_wolf(X, demean: bool = False):
    """Ledoit-Wolf (2004) shrinkage to mu*I, mu = tr(S)/N. Returns (Sigma, delta). Sigma = (1-d) S + d mu I; trace preserved."""
    A = _panel(X)
    if demean:
        A = A - A.mean(0)
    T, N = A.shape
    S = A.T @ A / T
    mu = np.trace(S) / N
    d2 = np.sum((S - mu * np.eye(N)) ** 2) / N
    b2 = sum(np.sum((np.outer(x, x) - S) ** 2) for x in A) / (T * T * N)
    b2 = min(b2, d2)
    delta = 0.0 if d2 == 0 else b2 / d2
    return (1 - delta) * S + delta * mu * np.eye(N), delta


def shrink_to_diag(S: np.ndarray, delta: float) -> np.ndarray:
    """(1-delta) S + delta diag(S): diagonal kept, correlations scaled by (1-delta)."""
    return (1 - delta) * S + delta * np.diag(np.diag(S))


def pca_factor_cov(S: np.ndarray, k: int) -> np.ndarray:
    """Keep top-k eigenpairs; set the N-k trailing eigenvalues to their average (noise averaging). PD, trace preserved."""
    lam, U = np.linalg.eigh(S)
    lam, U = lam[::-1], U[:, ::-1]
    kappa = lam[k:].mean() if k < len(lam) else 0.0
    lam2 = np.concatenate([lam[:k], np.full(len(lam) - k, kappa)])
    return (U * lam2) @ U.T


def smooth_corr(S: np.ndarray, k: int, vols: np.ndarray | None = None) -> np.ndarray:
    """Darbyshire smoothing: PCA on the CORRELATION matrix, keep k PCs, rescale diagonal to 1, then re-apply vols."""
    d = np.sqrt(np.diag(S))
    C = S / np.outer(d, d)
    lam, U = np.linalg.eigh(C)
    lam, U = lam[::-1], U[:, ::-1]
    R = (U[:, :k] * lam[:k]) @ U[:, :k].T
    s = np.sqrt(np.diag(R))
    R = R / np.outer(s, s)
    v = d if vols is None else np.asarray(vols, dtype=float)
    return np.outer(v, v) * R


def nearest_psd(S: np.ndarray, floor: float = 1e-10) -> np.ndarray:
    """Clip negative eigenvalues (needed for Gerber matrices, which are not guaranteed PSD); rescale diag if S was a correlation."""
    lam, U = np.linalg.eigh((S + S.T) / 2)
    return (U * np.maximum(lam, floor)) @ U.T


# ----------------------------------------------------------------------------- Gerber


def robust_scale(X) -> np.ndarray:
    """Zero-centred MAD scale, 1.4826 * median|x|: equals the std for normal data but ignores outliers."""
    return 1.4826 * np.median(np.abs(np.asarray(X, dtype=float)), axis=0)


def gerber_corr(X, c: float = 0.5, scale: np.ndarray | None = None) -> np.ndarray:
    """Gerber statistic G_ij = (U_ij - D_ij)/(U_ij + D_ij).

    Threshold h_k = c * scale_k (scale defaults to the sample std; pass robust_scale(X) if gross outliers are present). U counts obs where both moves exceed +h or both below -h (concordant); D counts obs where
    one exceeds +h and the other is below -h (discordant). Obs inside either band count in neither. Not guaranteed PSD.
    """
    A = _panel(X)
    h = c * (A.std(0, ddof=0) if scale is None else np.asarray(scale, dtype=float))
    up, dn = (A >= h).astype(float), (A <= -h).astype(float)
    U = up.T @ up + dn.T @ dn
    D = up.T @ dn + dn.T @ up
    den = U + D
    with np.errstate(invalid="ignore", divide="ignore"):
        G = np.where(den > 0, (U - D) / den, 0.0)
    np.fill_diagonal(G, 1.0)
    return G


def gerber_cov(X, c: float = 0.5, vols: np.ndarray | None = None, psd: bool = True, robust: bool = False) -> np.ndarray:
    """Gerber covariance = diag(vols) G diag(vols); vols default to sample std. psd=True clips negative eigenvalues.
    robust=True uses MAD scale for the thresholds (and for vols if not given)."""
    A = _panel(X)
    sc = robust_scale(A) if robust else None
    v = (sc if robust else A.std(0, ddof=0)) if vols is None else np.asarray(vols, dtype=float)
    G = gerber_corr(A, c, sc)
    if psd:
        G = nearest_psd(G)
        s = np.sqrt(np.diag(G))
        G = G / np.outer(s, s)
    return np.outer(v, v) * G


# ----------------------------------------------------------------------------- risk / hedge


def var_multiplier(Q: np.ndarray, S: np.ndarray) -> float:
    """c = sqrt(S' Q S): 1-sd P&L per horizon in S's units. VaR95 = 1.645 c; VaR99 = 2.326 c."""
    S = np.asarray(S, dtype=float)
    return float(np.sqrt(S @ Q @ S))


def min_var_hedge(Q: np.ndarray, S: np.ndarray, idx) -> np.ndarray:
    """Trade in buckets idx minimising c of (S + trade): trade = -Q_mm^-1 Q_m. S. Returns full-length trade vector.

    Solve, never invert. Wrong-signed hedges for near-singular Q_mm: shrink Q first.
    """
    idx = list(idx)
    S = np.asarray(S, dtype=float)
    x = -np.linalg.solve(Q[np.ix_(idx, idx)], Q[idx, :] @ S)
    t = np.zeros(len(S))
    t[idx] = x
    return t


# ----------------------------------------------------------------------------- evaluation


def qlike(realized: np.ndarray, forecast_var: np.ndarray) -> float:
    """Patton QLIKE = mean(r^2/f - ln(r^2/f) - 1) for f = forecast variance (lower is better; penalises under-forecast)."""
    r2 = np.asarray(realized, dtype=float) ** 2
    f = np.asarray(forecast_var, dtype=float)
    ok = (r2 > 0) & (f > 0)
    z = r2[ok] / f[ok]
    return float(np.mean(z - np.log(z) - 1))


def halflife_scan(X: pd.DataFrame, halflives, warmup: int = 252) -> pd.Series:
    """Mean QLIKE of one-step-ahead zero-mean EWMA variance forecasts, averaged over columns, per half-life."""
    X = pd.DataFrame(X)
    if len(X) < warmup + 30 or X.isna().any().any():
        raise ValueError(f"need >= warmup+30 = {warmup + 30} rows and no NaN (got {len(X)}); lower --warmup or supply more history")
    out = {}
    for h in halflives:
        f = (X ** 2).ewm(halflife=h, adjust=True).mean().shift(1)
        out[h] = float(np.mean([qlike(X[c].values[warmup:], f[c].values[warmup:]) for c in X]))
    return pd.Series(out, name="qlike")


# ----------------------------------------------------------------------------- IO / CLI


def load_changes(path: str, curve_id: str | None = None, snap: str | None = None) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.endswith((".parquet", ".pq")) else pd.read_csv(path)
    if "par_rate_pct" in df.columns:  # long canonical curve_par -> daily bp changes by tenor
        if curve_id:
            df = df[df["curve_id"] == curve_id]
        if "start" in df.columns:
            df = df[df["start"].astype(str) == "0D"]
        if "snap" in df.columns:  # never mix snaps inside one series
            if snap:
                df = df[df["snap"] == snap]
            elif df["snap"].nunique() > 1:
                raise ValueError(f"several snaps {sorted(df['snap'].unique())}: pass --snap")
        if "curve_id" in df.columns and df["curve_id"].nunique() > 1:
            raise ValueError(f"several curve_id {sorted(df['curve_id'].unique())}: pass --curve-id")
        df = df.pivot_table(index="date", columns="tenor", values="par_rate_pct", aggfunc="last").sort_index()
        unit = {"Y": 1.0, "M": 1 / 12, "W": 1 / 52, "D": 1 / 365}
        yrs = lambda t: float(t[:-1]) * unit.get(t[-1], 1e9) if t[:-1].replace(".", "").isdigit() else 1e9
        return (df[sorted(df.columns, key=yrs)].diff() * 100).dropna(how="all").dropna()
    first = "date" if "date" in df.columns else df.columns[0]
    return df.set_index(first).sort_index().dropna()


def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("cov")
    a.add_argument("path")
    a.add_argument("--curve-id")
    a.add_argument("--snap")
    a.add_argument("--method", choices=["sample", "ewma", "lw", "gerber", "pca", "fastslow"], default="ewma")
    a.add_argument("--halflife", type=float, default=40.0)
    a.add_argument("--k", type=int, default=3)
    b = sub.add_parser("halflife-scan")
    b.add_argument("path")
    b.add_argument("--curve-id")
    b.add_argument("--snap")
    b.add_argument("--halflives", type=float, nargs="+", default=[10, 21, 42, 63, 126])
    c = sub.add_parser("hedge")
    c.add_argument("path")
    c.add_argument("--curve-id")
    c.add_argument("--snap")
    c.add_argument("--halflife", type=float, default=63.0)
    c.add_argument("--risk", nargs="+", required=True, help="COL=exposure per bp, e.g. 2Y=-10000")
    c.add_argument("--hedges", nargs="+", required=True)
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.cmd:
        ap.print_help()
        return 0
    X = load_changes(args.path, args.curve_id, args.snap)
    pd.set_option("display.width", 200, "display.precision", 4)
    if args.cmd == "cov":
        m = args.method
        S = {"sample": lambda: sample_cov(X), "ewma": lambda: ewma_cov(X, args.halflife),
             "lw": lambda: ledoit_wolf(X)[0], "gerber": lambda: gerber_cov(X),
             "pca": lambda: pca_factor_cov(ewma_cov(X, args.halflife), args.k),
             "fastslow": lambda: fast_vol_slow_corr(X, 21, 126)}[m]()
        print(f"# {m}; T={len(X)}, N={X.shape[1]}, eig min/max = {np.linalg.eigvalsh(S)[[0, -1]]}")
        print(pd.DataFrame(S, X.columns, X.columns))
    elif args.cmd == "halflife-scan":
        print(halflife_scan(X, args.halflives).to_string())
    else:
        Q = ewma_cov(X, args.halflife)
        S = pd.Series({k: 0.0 for k in X.columns})
        for kv in args.risk:
            k, v = kv.split("=")
            if k not in S.index:
                raise SystemExit(f"--risk column {k!r} not in {list(X.columns)}")
            S[k] = float(v)
        bad = [h for h in args.hedges if h not in S.index]
        if bad:
            raise SystemExit(f"--hedges {bad} not in {list(X.columns)}")
        t = min_var_hedge(Q, S.values, [list(X.columns).index(h) for h in args.hedges])
        print(f"c before = {var_multiplier(Q, S.values):,.1f}   c after = {var_multiplier(Q, S.values + t):,.1f}")
        print(pd.Series(t, X.columns, name="hedge_trade").to_string())
    return 0


# ----------------------------------------------------------------------------- selftest


def selftest() -> int:
    from scipy.stats import multivariate_normal as mvn

    fails: list[str] = []

    def check(name, ok, msg=""):
        print(("PASS " if ok else "FAIL ") + name + (f"  [{msg}]" if msg else ""))
        if not ok:
            fails.append(name)

    rng = np.random.default_rng(7)

    # 1. EWMA weights: halflife and effective-obs identities (analytic).
    w = ewma_weights(5000, 8.0)
    check("ewma weights sum to 1 and halve every halflife", abs(w.sum() - 1) < 1e-12 and abs(w[-1 - 8] / w[-1] - 0.5) < 1e-12)
    check("effective obs (1+lam)/(1-lam) = 1/sum(w^2); 8d half-life ~ 23", abs(1 / (w ** 2).sum() - effective_obs(8.0)) < 1e-6
          and abs(effective_obs(8.0) - 23.1) < 0.1, f"{effective_obs(8.0):.2f}")
    lam = 0.94
    check("lambda 0.94 <-> half-life 11.2 obs", abs(np.log(0.5) / np.log(lam) - 11.2) < 0.05)
    check("overlap eff obs L=5,T=250 (formula gives 73.5)", abs(overlap_eff_obs(250, 5) - 73.53) < 0.01)

    # 2. EWMA cov of a constant outer product is that product; recursion equivalence for large T.
    x = np.array([1.0, -2.0, 0.5])
    Xc = np.tile(x, (300, 1))
    check("ewma of constant vector returns x x'", np.allclose(ewma_cov(Xc, 20), np.outer(x, x)))
    A = rng.standard_normal((400, 3))
    lam = 0.5 ** (1 / 30)
    Sr = np.outer(A[0], A[0])
    for a in A[1:]:  # RiskMetrics recursion (after burn-in it equals the normalised-weight form)
        Sr = (1 - lam) * np.outer(a, a) + lam * Sr
    check("recursion S_t=(1-l)xx'+l S_{t-1} matches normalised weights after burn-in", np.allclose(Sr, ewma_cov(A, 30), atol=lam ** 400 * 50 + 1e-9),
          f"{np.abs(Sr - ewma_cov(A, 30)).max():.2e}")

    # 3. Ledoit-Wolf: matches scikit-learn (if present), trace preserved, PD when T<N, beats sample vs true=I.
    B = rng.standard_normal((40, 50))
    Slw, d = ledoit_wolf(B)
    check("LW delta in [0,1], trace preserved", 0 <= d <= 1 and abs(np.trace(Slw) - np.trace(sample_cov(B))) < 1e-9, f"delta={d:.3f}")
    check("LW PD while sample cov (T<N) is singular", np.linalg.eigvalsh(Slw).min() > 1e-6 and np.linalg.eigvalsh(sample_cov(B)).min() < 1e-9)
    check("LW closer to true I than sample (T=40, N=50)", np.linalg.norm(Slw - np.eye(50)) < np.linalg.norm(sample_cov(B) - np.eye(50)))
    try:
        from sklearn.covariance import LedoitWolf
        m = LedoitWolf(assume_centered=True).fit(B)
        check("LW matches scikit-learn LedoitWolf(assume_centered)", np.allclose(m.covariance_, Slw, atol=1e-8) and abs(m.shrinkage_ - d) < 1e-8)
    except ImportError:
        print("SKIP sklearn comparison (not installed)")

    # 4. Gerber: analytic orthant probabilities of a bivariate normal.
    rho, T = 0.6, 400_000
    Z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], size=T)
    g0 = gerber_corr(Z, c=0.0)[0, 1]
    check("Gerber c=0 equals (2/pi) arcsin(rho)", abs(g0 - 2 / np.pi * np.arcsin(rho)) < 0.01, f"{g0:.4f} vs {2 / np.pi * np.arcsin(rho):.4f}")
    h = 0.5
    p_same = mvn.cdf([-h, -h], mean=[0, 0], cov=[[1, rho], [rho, 1]])
    p_opp = mvn.cdf([-h, -h], mean=[0, 0], cov=[[1, -rho], [-rho, 1]])
    g_th = (p_same - p_opp) / (p_same + p_opp)
    g5 = gerber_corr(Z, c=0.5)[0, 1]
    check("Gerber c=0.5 equals orthant-probability formula", abs(g5 - g_th) < 0.01, f"{g5:.4f} vs {g_th:.4f}")
    # robustness: 1% opposite-sign outliers wreck Pearson; Gerber survives. Gross outliers also inflate the std used for
    # thresholds, so with 40-sigma outliers Gerber needs a robust (MAD) scale.
    Zo = Z[:20_000].copy()
    Zo[:200] = np.array([8.0, -8.0])
    pear, ger = np.corrcoef(Zo.T)[0, 1], gerber_corr(Zo, 0.5)[0, 1]
    check("Gerber robust to 1% 8-sigma outliers (Pearson collapses)", pear < 0.15 and abs(ger - g_th) < 0.06, f"pearson={pear:.2f} gerber={ger:.2f}")
    Zg = Z[:20_000].copy()
    Zg[:200] = np.array([40.0, -40.0])
    gs, gr = gerber_corr(Zg, 0.5)[0, 1], gerber_corr(Zg, 0.5, robust_scale(Zg))[0, 1]
    check("gross outliers: std thresholds break Gerber, MAD scale fixes it", abs(gs - g_th) > 0.15 and abs(gr - g_th) < 0.06, f"std={gs:.2f} mad={gr:.2f}")
    Gc = gerber_cov(rng.standard_normal((300, 8)), psd=True)
    check("gerber_cov(psd=True) is PSD with symmetric output", np.linalg.eigvalsh(Gc).min() > -1e-9 and np.allclose(Gc, Gc.T))

    # 5. PCA factor cov / smoothing: simulate a 2-factor world with known covariance.
    N, K, T = 30, 2, 60
    L = rng.standard_normal((N, K)) * np.array([2.0, 1.0])
    true = L @ L.T + 0.25 * np.eye(N)
    Xp = rng.standard_normal((T, K)) @ L.T + 0.5 * rng.standard_normal((T, N))
    Sp = sample_cov(Xp)
    Sk = pca_factor_cov(Sp, K)
    lam_k = np.sort(np.linalg.eigvalsh(Sk))[::-1]
    check("pca_factor_cov: trace preserved, trailing eigenvalues equal, PD", abs(np.trace(Sk) - np.trace(Sp)) < 1e-9
          and np.ptp(lam_k[K:]) < 1e-9 and lam_k.min() > 0)
    def gmv_realised(Sh):  # realised variance (under the true cov) of the min-variance portfolio built from Sh
        w = np.linalg.solve(Sh, np.ones(N))
        w /= w.sum()
        return w @ true @ w
    r_s, r_p, r_t = gmv_realised(Sp), gmv_realised(Sk), gmv_realised(true)
    check("pca_factor_cov: GMV realised variance well below sample's (T=60,N=30)", r_p < 0.7 * r_s and r_p >= r_t - 1e-12,
          f"true {r_t:.3f} <= pca {r_p:.3f} < 0.7 x sample {r_s:.3f}")
    R = smooth_corr(Sp, 3)
    dd = np.sqrt(np.diag(R))
    check("smooth_corr keeps vols and diag-1 correlation", np.allclose(dd, np.sqrt(np.diag(Sp))) and np.linalg.eigvalsh(R).min() > -1e-9)

    # 6. Hedges: analytic two-bucket formula S_f = -S0 q12/q22, c_min = |S0| sqrt(q11 - q12^2/q22); published book (rounded Q).
    Q2 = np.array([[4.0, 3.0], [3.0, 9.0]])
    t = min_var_hedge(Q2, [1000.0, 0.0], [1])
    check("two-bucket min-variance hedge closed form", abs(t[1] + 1000 * 3 / 9) < 1e-9 and abs(var_multiplier(Q2, [1000.0, t[1]]) - 1000 * np.sqrt(4 - 9 / 9)) < 1e-6)
    Qd = np.array([[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]])
    Sd = np.array([-10000, 2500, 10000, -4000.0])
    c0 = var_multiplier(Qd, Sd)
    check("book multiplier ~16,174 (Darbyshire 2022, rounded Q so 3% tol)", abs(c0 / 16174 - 1) < 0.03, f"{c0:,.0f}")
    fly = min_var_hedge(Qd, [-1, 2, -1, 0], [1])
    check("2s5s10s min-var on 5Y ~ -0.344 (Darbyshire 2022)", abs(fly[1] + 0.344) < 0.005, f"{fly[1]:.3f}")
    t2 = min_var_hedge(Qd, Sd, [0, 2])
    check("2Y&10Y hedge cuts c by ~70% (Darbyshire 2022)", 0.68 < 1 - var_multiplier(Qd, Sd + t2) / c0 < 0.75)

    # 7. QLIKE minimised at the true variance; half-life scan prefers short in switching vol, long in constant vol.
    r = rng.standard_normal(200_000) * 2.0
    scales = np.array([0.5, 0.8, 1.0, 1.25, 2.0]) * 4.0
    check("QLIKE minimised at the true variance", int(np.argmin([qlike(r, np.full_like(r, s)) for s in scales])) == 2)
    # analytic level: z = r^2/f ~ chi2(1) at the true variance, E[z] = 1 and E[ln z] = psi(1/2) + ln 2 = -(gamma + ln 2), so QLIKE = gamma + ln 2 = 1.2704
    check("QLIKE at true variance = euler_gamma + ln 2 = 1.2704 (-1 term present)", abs(qlike(r, np.full_like(r, 4.0)) - (np.euler_gamma + np.log(2))) < 0.01,
          f"{qlike(r, np.full_like(r, 4.0)):.4f}")
    for T_, N_ in [(2, 3), (3, 2), (5, 2)]:  # tiny samples where the raw b2 exceeds d2: delta must be clipped at 1
        Bt = np.random.default_rng(1).standard_normal((T_, N_))
        check(f"LW delta clipped to <= 1 (T={T_}, N={N_})", ledoit_wolf(Bt)[1] <= 1.0 + 1e-12)
    for bad in (np.array([[1.0, np.nan], [2.0, 3.0], [1.0, 1.0]]), np.ones((1, 2))):
        try:
            ewma_cov(bad)
            check("panel guard rejects NaN / T<2", False)
        except ValueError:
            check("panel guard rejects NaN / T<2", True)
    const = pd.DataFrame(rng.standard_normal((4000, 3)))
    sw = pd.DataFrame(rng.standard_normal((4000, 3)) * np.repeat(np.tile([1.0, 4.0], 8), 250)[:, None])
    sc, ss = halflife_scan(const, [5, 250]), halflife_scan(sw, [5, 250])
    check("scan: long half-life wins in constant vol; short wins in switching vol", sc.idxmin() == 250 and ss.idxmin() == 5,
          f"const={sc.round(3).to_dict()} switch={ss.round(3).to_dict()}")

    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(_cli())
