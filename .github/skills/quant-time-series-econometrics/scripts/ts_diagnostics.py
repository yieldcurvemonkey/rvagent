#!/usr/bin/env python3
"""Time-series diagnostics for rates series: ACF / Ljung-Box, OLS with Newey-West (HAC) errors,
Chow and recursive-residual CUSUM break tests, fixed-width fractional differencing with minimum-d
search, GARCH(1,1) MLE, VAR(p) by OLS with Cholesky impulse responses.

Self-contained: numpy, pandas, scipy only.
CLI:  python ts_diagnostics.py --csv series.csv --value-col par_rate_pct --date-col date \
          [--filter tenor=10Y --filter curve_id=USD-SOFR] [--unit-mult 100] [--horizon 5]
      python ts_diagnostics.py --selftest
The CLI takes a canonical long CSV/Parquet (e.g. curve_par), filters to ONE series, converts it to
daily changes in bp (--unit-mult 100 turns pct into bp) and prints the diagnostics below.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import optimize, signal, stats

# --------------------------------------------------------------------------- autocorrelation


def acf(x, nlags: int = 20) -> np.ndarray:
    """Sample autocorrelations r_1..r_nlags (demeaned, divided by T)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)] - np.nanmean(x)
    c0 = x @ x
    return np.array([(x[k:] @ x[:-k]) / c0 for k in range(1, nlags + 1)])


def ljung_box(x, lags: int = 10, dof: int = 0):
    """Ljung-Box Q' = T(T+2) sum r_j^2/(T-j); chi2(lags - dof). dof = fitted ARMA params."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    T = len(x)
    r = acf(x, lags)
    q = T * (T + 2) * np.sum(r**2 / (T - np.arange(1, lags + 1)))
    return q, float(stats.chi2.sf(q, lags - dof))


# --------------------------------------------------------------------------- OLS + HAC


def nw_lags(T: int) -> int:
    """Newey-West truncation l = int(4 (T/100)^(2/9)) (Tsay); Greene's rule is ~T^(1/4)."""
    return int(4 * (T / 100) ** (2 / 9))


def overlap_sums(dx: pd.Series, h: int) -> pd.Series:
    """h-period overlapping change = rolling sum of h one-period changes (bp). Adjacent values share h-1
    terms, so their errors are MA(h-1): OLS/HC t-stats are inflated by about sqrt(h). Use ols_hac."""
    return dx.rolling(h).sum().dropna()


def ols_hac(y, X, lags: int | None = None, kernel: str = "bartlett") -> pd.DataFrame:
    """OLS of y on X (add the constant yourself) with classical, White (HC0) and HAC standard errors.
    kernel="bartlett": Newey-West, w_j = 1 - j/(l+1), always PSD. kernel="uniform": Hansen-Hodrick, w_j = 1
    for j <= l (exact for h-overlap iid data with l = h-1, but can give a negative variance -> nan).
    Returns beta, se_ols, se_hc, se_hac, t_hac."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    T, k = X.shape
    XtXi = np.linalg.inv(X.T @ X)
    beta = XtXi @ X.T @ y
    e = y - X @ beta
    se_ols = np.sqrt(np.diag(XtXi) * (e @ e) / (T - k))
    xe = X * e[:, None]
    S0 = xe.T @ xe
    se_hc = np.sqrt(np.diag(XtXi @ S0 @ XtXi))
    L = nw_lags(T) if lags is None else int(lags)
    S = S0.copy()
    for j in range(1, L + 1):
        G = xe[j:].T @ xe[:-j]
        S += (1.0 if kernel == "uniform" else 1 - j / (L + 1)) * (G + G.T)
    with np.errstate(invalid="ignore"):
        se_hac = np.sqrt(np.diag(XtXi @ S @ XtXi))
    return pd.DataFrame({"beta": beta, "se_ols": se_ols, "se_hc": se_hc, "se_hac": se_hac,
                         "t_hac": beta / se_hac})


# --------------------------------------------------------------------------- structural breaks


def _ssr(y, X):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    return float(e @ e)


def chow(y, X, split: int):
    """Chow F test for a coefficient break at index `split` (first obs of regime 2). Equal-variance
    assumption. F[K, n-2K] = ((SSR_p - SSR_1 - SSR_2)/K) / ((SSR_1 + SSR_2)/(n-2K))."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    n, K = X.shape
    s1, s2, sp = _ssr(y[:split], X[:split]), _ssr(y[split:], X[split:]), _ssr(y, X)
    F = ((sp - s1 - s2) / K) / ((s1 + s2) / (n - 2 * K))
    return F, float(stats.f.sf(F, K, n - 2 * K))


_BDE_A = {0.10: 0.850, 0.05: 0.948, 0.01: 1.143}  # Brown-Durbin-Evans (1975) boundary constants


def cusum_bde(y, X, alpha: float = 0.05):
    """Brown-Durbin-Evans CUSUM of recursive residuals. Returns (W_t path, boundary, max|W|/boundary).
    Ratio > 1 rejects constant coefficients. Start index is k (needs >= k obs); results depend on
    how much history you burn in, so report k."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    T, k = X.shape
    w = np.empty(T - k)
    for i, t in enumerate(range(k, T)):
        Xt = X[:t]
        A = np.linalg.inv(Xt.T @ Xt)
        b = A @ Xt.T @ y[:t]
        w[i] = (y[t] - X[t] @ b) / np.sqrt(1 + X[t] @ A @ X[t])
    sig = np.sqrt(np.sum((w - w.mean()) ** 2) / (T - k))
    W = np.cumsum(w) / sig
    n = T - k
    bound = _BDE_A[alpha] * (np.sqrt(n) + 2 * np.arange(1, n + 1) / np.sqrt(n))
    return W, bound, float(np.max(np.abs(W) / bound))


# --------------------------------------------------------------------------- ADF and fractional differencing


def adf_t(y, lags: int = 1) -> float:
    """ADF t-statistic, constant, `lags` lagged differences: dy_t = c + b y_{t-1} + sum g_i dy_{t-i}.
    Compare with the 5% constant-case critical value ~ -2.86 (large T). For p-values use statsmodels."""
    y = np.asarray(y, float)
    dy = np.diff(y)
    Y = dy[lags:]
    cols = [np.ones(len(Y)), y[lags:-1]] + [dy[lags - i: -i] for i in range(1, lags + 1)]
    X = np.column_stack(cols)
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ Y
    e = Y - X @ b
    return float(b[1] / np.sqrt(e @ e / (len(Y) - X.shape[1]) * XtXi[1, 1]))


def ffd_weights(d: float, thres: float = 1e-5, max_len: int = 10_000) -> np.ndarray:
    """omega_0 = 1, omega_k = -omega_{k-1}(d-k+1)/k, truncated once |omega_k| < thres."""
    w = [1.0]
    for k in range(1, max_len):
        wk = -w[-1] * (d - k + 1) / k
        if abs(wk) < thres:
            break
        w.append(wk)
    return np.array(w)


def frac_diff_ffd(x: pd.Series, d: float, thres: float = 1e-5) -> pd.Series:
    """Fixed-width-window fractional difference; one weight vector, first len(w)-1 values are NaN."""
    w = ffd_weights(d, thres)
    v = x.to_numpy(float)
    n = len(w)
    out = np.full(len(v), np.nan)
    if len(v) >= n:
        out[n - 1:] = np.convolve(v, w, mode="valid")
    return pd.Series(out, index=x.index)


def min_d(x: pd.Series, grid=None, thres: float = 1e-2, crit: float = -2.8623) -> pd.DataFrame:
    """Smallest d on the grid whose FFD series passes ADF(lags=1, constant) at the 5% critical value.
    Returns the table (d, adf_t, corr_with_original, n_obs, passes); pick the first passing row."""
    grid = np.linspace(0, 1, 11) if grid is None else grid
    rows = []
    for d in grid:
        f = frac_diff_ffd(x, d, thres).dropna()
        if len(f) < 30:  # window as long as the series: nothing left to test
            rows.append((d, np.nan, np.nan, len(f), False))
            continue
        a = adf_t(f.to_numpy())
        rows.append((d, a, float(np.corrcoef(f, x.loc[f.index])[0, 1]), len(f), a < crit))
    return pd.DataFrame(rows, columns=["d", "adf_t", "corr_orig", "n_obs", "passes"])


# --------------------------------------------------------------------------- GARCH(1,1)


def _garch_var(r, omega, alpha, beta, s0):
    u = np.empty(len(r))
    u[0] = s0
    u[1:] = omega + alpha * r[:-1] ** 2
    return signal.lfilter([1.0], [1.0, -beta], u)


def garch11_fit(r) -> dict:
    """Gaussian MLE of r_t = sigma_t z_t, s2_t = omega + alpha r_{t-1}^2 + beta s2_{t-1}, zero mean
    (use daily bp changes). Returns omega, alpha, beta, persistence, long_run_var, loglik, sigma2 (Series
    if r is a Series). Fit on standardised data for conditioning, then rescaled. Needs ~1000+ obs."""
    idx = r.index if isinstance(r, pd.Series) else None
    r = np.asarray(r, float)
    if np.isnan(r).any() or len(r) < 100 or r.std() == 0:
        raise ValueError("garch11_fit needs >= 100 non-NaN, non-constant changes (>= 1000 for usable estimates)")
    sc = r.std()
    z = r / sc
    s0 = float(np.mean(z**2))

    def nll(p):
        a, b = p[1], p[2]
        if a < 0 or b < 0 or a + b >= 0.9999 or p[0] <= 0:
            return 1e10
        s2 = _garch_var(z, p[0], a, b, s0)
        return 0.5 * float(np.sum(np.log(s2) + z**2 / s2))

    best = None
    for a0, b0 in [(0.05, 0.90), (0.10, 0.80), (0.03, 0.95)]:
        res = optimize.minimize(nll, [s0 * (1 - a0 - b0), a0, b0], method="Nelder-Mead",
                                options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 4000})
        if best is None or res.fun < best.fun:
            best = res
    om, a, b = best.x
    s2 = _garch_var(z, om, a, b, s0) * sc**2
    return {"omega": om * sc**2, "alpha": a, "beta": b, "persistence": a + b,
            "long_run_var": om * sc**2 / (1 - a - b), "loglik": -best.fun - 0.5 * len(r) * np.log(2 * np.pi)
            - len(r) * np.log(sc),
            "sigma2": pd.Series(s2, index=idx) if idx is not None else s2}


def garch_kurtosis(alpha: float, beta: float) -> float:
    """Unconditional kurtosis of GARCH(1,1) with Gaussian shocks: 3(1-p^2)/(1-p^2-2 alpha^2), p=a+b."""
    p2 = (alpha + beta) ** 2
    return 3 * (1 - p2) / (1 - p2 - 2 * alpha**2)


def garch_forecast(omega, alpha, beta, s2_next, h):
    """h-step-ahead variance given s2_next = sigma^2_{t+1}: omega(1-p^(h-1))/(1-p) + p^(h-1) s2_next."""
    p = alpha + beta
    geo = (h - 1) if abs(1 - p) < 1e-12 else (1 - p ** (h - 1)) / (1 - p)  # IGARCH: sum of h-1 ones
    return omega * geo + p ** (h - 1) * s2_next


# --------------------------------------------------------------------------- VAR / IRF


def var_ols(Y, p: int = 1):
    """VAR(p) by OLS on a (T x m) array. Returns const (m,), A list of p (m x m) with y_t = c + sum A_i y_{t-i},
    and residual covariance Sigma (dof-corrected)."""
    Y = np.asarray(Y, float)
    T, m = Y.shape
    X = np.column_stack([np.ones(T - p)] + [Y[p - i: T - i] for i in range(1, p + 1)])
    B = np.linalg.lstsq(X, Y[p:], rcond=None)[0]
    E = Y[p:] - X @ B
    A = [B[1 + (i - 1) * m: 1 + i * m].T for i in range(1, p + 1)]
    return B[0], A, E.T @ E / (T - p - m * p - 1)


def irf(A, Sigma, horizon: int = 20, orth: bool = True) -> np.ndarray:
    """Impulse responses Theta_h (h = 0..horizon), shape (horizon+1, m, m); entry [h, i, j] = response of
    variable i to shock j. orth=True uses Cholesky of Sigma, so the VARIABLE ORDER is an identifying
    assumption (first variable is not hit contemporaneously by the others)."""
    m = Sigma.shape[0]
    p = len(A)
    Th = [np.eye(m)]
    for h in range(1, horizon + 1):
        Th.append(sum(A[i - 1] @ Th[h - i] for i in range(1, min(h, p) + 1)))
    Th = np.array(Th)
    return Th @ np.linalg.cholesky(Sigma) if orth else Th


# --------------------------------------------------------------------------- CLI report


def report(x: pd.Series, horizon: int = 1) -> None:
    x = x.dropna()
    print(f"n={len(x)}  mean={x.mean():.3f}  sd={x.std():.3f}  excess_kurt={stats.kurtosis(x):.2f}")
    print("ACF 1-5 of changes:", np.round(acf(x, 5), 3))
    for lg in (5, 20):
        q, pv = ljung_box(x, lg)
        q2, pv2 = ljung_box(x**2, lg)
        print(f"Ljung-Box({lg}): changes p={pv:.3f} | squares p={pv2:.3f}")
    lv = x.cumsum()
    print(f"ADF t (levels, 1 lag) = {adf_t(lv.to_numpy()):.2f}  (5% crit -2.86; fail-to-reject is not proof)")
    xh = x if horizon == 1 else overlap_sums(x, horizon)
    L = max(nw_lags(len(xh)), 2 * horizon)
    h = ols_hac(xh.to_numpy(), np.ones(len(xh)), lags=L)
    hu = ols_hac(xh.to_numpy(), np.ones(len(xh)), lags=horizon - 1, kernel="uniform")
    print(f"mean {horizon}d change {h.beta[0]:.3f} bp (n={len(xh)}): t_ols={h.beta[0] / h.se_ols[0]:.2f}  "
          f"t_hac(NW,l={L})={h.t_hac[0]:.2f}  t_hac(Hansen-Hodrick,l={horizon - 1})={hu.t_hac[0]:.2f}")
    if len(x) > 300:
        xv = x.to_numpy()
        _, _, ratio = cusum_bde(xv[1:], np.column_stack([np.ones(len(xv) - 1), xv[:-1]]))
        print(f"BDE CUSUM on AR(1) of changes: max|W|/bound = {ratio:.2f} ({'BREAK' if ratio > 1 else 'stable'})")
    if len(x) > 1000:
        g = garch11_fit(x.to_numpy())
        print(f"GARCH(1,1): alpha={g['alpha']:.3f} beta={g['beta']:.3f} persistence={g['persistence']:.3f} "
              f"long-run sd={np.sqrt(g['long_run_var']):.2f}  last sd={np.sqrt(g['sigma2'][-1]):.2f}")
    else:
        print("GARCH skipped: < 1000 obs (parameter error ~0.1 at T=1000); use EWMA instead")


def _load(path, filters, value_col, date_col, mult):
    df = pd.read_parquet(path) if str(path).endswith((".parquet", ".pq")) else pd.read_csv(path)
    for f in filters or []:
        k, v = f.split("=", 1)
        df = df[df[k].astype(str) == v]
    s = df.set_index(pd.to_datetime(df[date_col]))[value_col].sort_index().astype(float)
    if s.index.has_duplicates:
        sys.exit("series is not unique after filtering: add --filter for curve_id/tenor/snap/start")
    return s.diff().dropna() * mult


# --------------------------------------------------------------------------- selftest


def selftest() -> int:
    rng = np.random.default_rng(7)
    fails = []

    def check(name, ok, info=""):
        print(("PASS " if ok else "FAIL ") + name + (f"  [{info}]" if info else ""))
        if not ok:
            fails.append(name)

    # 1 ACF / Ljung-Box: white noise passes, AR(1) 0.5 fails and r1 ~ 0.5
    wn = rng.standard_normal(5000)
    ar = signal.lfilter([1], [1, -0.5], rng.standard_normal(5000))
    check("ljung_box white noise p>0.01", ljung_box(wn, 10)[1] > 0.01)
    check("ljung_box AR(1) p<1e-6 and r1~0.5", ljung_box(ar, 10)[1] < 1e-6 and abs(acf(ar, 1)[0] - 0.5) < 0.05,
          f"r1={acf(ar, 1)[0]:.3f}")

    check("ljung_box hand value x=[1,2,3,4], lag 1: r1=.25, Q'=4*6*.0625/3=0.5",
          abs(ljung_box([1, 2, 3, 4], 1)[0] - 0.5) < 1e-12 and abs(acf([1, 2, 3, 4], 1)[0] - 0.25) < 1e-12)

    # 2 HAC: AR(1) phi=.5, sigma=1 -> LRV = 1/(1-.5)^2 = 4, se(mean) = sqrt(4/T); naive se = sqrt(1.333/T)
    T = 40000
    x = signal.lfilter([1], [1, -0.5], rng.standard_normal(T))
    r = ols_hac(x, np.ones(T), lags=60)
    exp_se = np.sqrt(4 / T)
    check("HAC se of mean = sqrt(LRV/T)", abs(r.se_hac[0] / exp_se - 1) < 0.08,
          f"hac={r.se_hac[0]:.5f} exp={exp_se:.5f}")
    check("naive OLS se understates by ~sqrt(3)", abs(r.se_ols[0] / r.se_hac[0] - 1 / np.sqrt(3)) < 0.08)
    # hand-checkable T=3 case: se_hc for mean = sqrt(sum e^2)/n
    h3 = ols_hac([1.0, 2.0, 6.0], np.ones(3), lags=0)
    check("HC se hand value", abs(h3.se_hc[0] - np.sqrt(14) / 3) < 1e-12, f"{h3.se_hc[0]:.6f}")

    # 2b overlapping h=5 sums of iid N(0,1): true LRV = h^2 -> se(mean) = h/sqrt(n). Uniform kernel l=h-1 is exact;
    # Bartlett l=h-1 understates (weights shrink the h-1 autocovariances); naive OLS is off by 1/sqrt(h)
    hh = 5
    z = rng.standard_normal(60000 + hh - 1)
    sh = overlap_sums(pd.Series(z), hh).to_numpy()
    se_true = hh / np.sqrt(len(sh))
    ru = ols_hac(sh, np.ones(len(sh)), lags=hh - 1, kernel="uniform")
    rb = ols_hac(sh, np.ones(len(sh)), lags=hh - 1)
    check("overlap: uniform-kernel HAC se = h/sqrt(n)", abs(ru.se_hac[0] / se_true - 1) < 0.05,
          f"ratio={ru.se_hac[0] / se_true:.3f}")
    check("overlap: Bartlett l=h-1 understates (~0.8)", 0.7 < rb.se_hac[0] / se_true < 0.9,
          f"ratio={rb.se_hac[0] / se_true:.3f}")
    check("overlap: naive se ~ 1/sqrt(h) of truth", abs(ru.se_ols[0] / se_true - 1 / np.sqrt(hh)) < 0.03)

    # 3 breaks. Chow: slope 1 -> 2 at t=300 of 600. CUSUM: intercept 0 -> 1 (it has no power vs a slope break
    # on a zero-mean regressor: recursive residuals still average to zero). A 5% test fires on 5% of null
    # samples, so the "quiet" checks are on the REJECTION RATE over 200 null simulations, not on one draw.
    n = 600
    xx = rng.standard_normal(n)
    X = np.column_stack([np.ones(n), xx])
    yb = np.where(np.arange(n) < 300, 1.0, 2.0) * xx + 0.5 * rng.standard_normal(n)
    Fb, pb = chow(yb, X, 300)
    check("chow detects slope break", pb < 1e-10, f"F={Fb:.1f}")
    n = 300
    rej_c = rej_u = rej_chow = 0
    f_null = []
    reps = 200
    for _ in range(reps):
        xx = rng.standard_normal(n)
        X = np.column_stack([np.ones(n), xx])
        yn = xx + 0.5 * rng.standard_normal(n)
        yi = np.where(np.arange(n) < 150, 0.0, 1.0) + xx + 0.5 * rng.standard_normal(n)
        rej_c += cusum_bde(yn, X)[2] > 1.0
        rej_u += cusum_bde(yi, X)[2] > 1.0
        Fn, pn = chow(yn, X, 150)
        rej_chow += pn < 0.05
        f_null.append(Fn)
    check("chow size ~5% (<12%)", rej_chow / reps < 0.12, f"{rej_chow / reps:.3f}")
    check("chow F mean under H0 = d2/(d2-2) ~ 1.007", abs(np.mean(f_null) - 296 / 294) < 0.15,
          f"{np.mean(f_null):.3f}")
    check("cusum size <= ~5% (<12%)", rej_c / reps < 0.12, f"{rej_c / reps:.3f}")
    check("cusum power vs intercept break > 95%", rej_u / reps > 0.95, f"{rej_u / reps:.3f}")

    # 4 fractional differencing: analytic weights, d=1 is first difference, d=0 identity
    check("ffd d=.5 weights", np.allclose(ffd_weights(0.5, 1e-2), [1, -0.5, -0.125, -0.0625, -0.0390625,
                                                                    -0.02734375, -0.0205078125, -0.01611328125,
                                                                    -0.013092041015625, -0.010910034]))
    s = pd.Series(np.cumsum(rng.standard_normal(400)))
    check("ffd d=1 == diff", np.allclose(frac_diff_ffd(s, 1.0).dropna(), s.diff().dropna()))
    check("ffd d=0 == identity", np.allclose(frac_diff_ffd(s, 0.0), s))
    rw = pd.Series(np.cumsum(rng.standard_normal(3000)))
    md = min_d(rw)
    dstar = md.loc[md.passes, "d"].min()
    # a PURE random walk already passes at d ~0.3 with a truncated window: d* < 1 alone is not evidence of memory
    check("min_d random walk passes well below 1 (<=0.6)", dstar <= 0.6, f"d*={dstar:.1f}")
    check("min_d white noise = 0", min_d(pd.Series(wn)).loc[0, "passes"])
    check("ADF: random walk fails, noise passes", adf_t(rw.to_numpy()) > -2.86 and adf_t(wn) < -10,
          f"rw={adf_t(rw.to_numpy()):.2f}")

    # 5 GARCH(1,1) recovery + analytic helpers
    a_t, b_t, om_t, N = 0.08, 0.90, 0.02, 50000
    e = rng.standard_normal(N)
    rr = np.empty(N)
    s2 = om_t / (1 - a_t - b_t)
    for t in range(N):
        rr[t] = np.sqrt(s2) * e[t]
        s2 = om_t + a_t * rr[t] ** 2 + b_t * s2
    g = garch11_fit(rr)
    check("garch alpha", abs(g["alpha"] - a_t) < 0.02, f"{g['alpha']:.3f}")
    check("garch beta", abs(g["beta"] - b_t) < 0.03, f"{g['beta']:.3f}")
    check("garch persistence", abs(g["persistence"] - 0.98) < 0.01, f"{g['persistence']:.4f}")
    check("garch long-run var = 1", abs(g["long_run_var"] - 1.0) < 0.15, f"{g['long_run_var']:.3f}")
    check("garch kurtosis formula (3(1-p^2)/(1-p^2-2a^2) = 4.4328; excess 1.43)", abs(garch_kurtosis(0.08, 0.90) - 4.4328) < 1e-3,
          f"{garch_kurtosis(0.08, 0.90):.4f}")
    check("garch kurtosis of sample > 3", stats.kurtosis(rr, fisher=False) > 3.5)
    check("garch forecast limits", abs(garch_forecast(0.02, 0.08, 0.90, 4.0, 1) - 4.0) < 1e-12
          and abs(garch_forecast(0.02, 0.08, 0.90, 4.0, 10_000) - 1.0) < 1e-6)

    check("nw_lags 4(T/100)^(2/9): 250->4, 1000->6, 5000->9", [nw_lags(k) for k in (250, 1000, 5000)] == [4, 6, 9])
    check("garch_forecast IGARCH (p=1): omega*(h-1) + s2", abs(garch_forecast(0.1, 0.1, 0.9, 2.0, 5) - (0.4 + 2.0)) < 1e-12)

    # 6 VAR(1) recovery + IRF analytic: Theta_h = A^h, orth Theta_0 = chol(Sigma)
    A0 = np.array([[0.5, 0.2], [0.0, 0.7]])
    S0 = np.array([[1.0, 0.3], [0.3, 0.5]])
    L = np.linalg.cholesky(S0)
    Yv = np.zeros((20000, 2))
    for t in range(1, len(Yv)):
        Yv[t] = A0 @ Yv[t - 1] + L @ rng.standard_normal(2)
    c, Ah, Sg = var_ols(Yv, 1)
    check("var_ols recovers A", np.allclose(Ah[0], A0, atol=0.03), str(np.round(Ah[0], 3).tolist()))
    th = irf([A0], S0, 5, orth=False)
    yy = np.array([1.0, 2.0, 4.0, 3.0, 5.0])  # univariate VAR(1) by hand: dof = T-p-mp-1 = 2
    bb = np.polyfit(yy[:-1], yy[1:], 1)
    ssr = float(np.sum((yy[1:] - np.polyval(bb, yy[:-1])) ** 2))
    check("var_ols Sigma dof-corrected (SSR/2)", abs(var_ols(yy[:, None], 1)[2][0, 0] - ssr / 2) < 1e-10)
    check("irf = A^h", np.allclose(th[3], np.linalg.matrix_power(A0, 3)))
    check("orth irf h0 = chol(Sigma)", np.allclose(irf([A0], S0, 2)[0], L))
    p2 = irf([np.array([[0.5]]), np.array([[0.2]])], np.eye(1), 3, orth=False)[:, 0, 0]
    check("AR(2) irf 1,.5,.45,.325", np.allclose(p2, [1, 0.5, 0.45, 0.325]), str(np.round(p2, 4)))

    print("\nALL PASS" if not fails else f"\nFAILED: {fails}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="canonical long CSV or Parquet")
    ap.add_argument("--value-col", default="par_rate_pct")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--filter", action="append", help="col=value, repeatable (pick ONE series)")
    ap.add_argument("--unit-mult", type=float, default=100.0, help="100 converts pct changes to bp")
    ap.add_argument("--horizon", type=int, default=1, help="test the mean of overlapping h-day changes with HAC")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.csv:
        ap.error("--csv or --selftest required")
    report(_load(a.csv, a.filter, a.value_col, a.date_col, a.unit_mult), a.horizon)


if __name__ == "__main__":
    main()
