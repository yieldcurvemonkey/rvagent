#!/usr/bin/env python3
"""Lead-lag toolkit for rates RV: which series moves first, how reliably, and how much.

Convention everywhere: lag k > 0 means x LEADS y, i.e. corr(x_t, y_{t+k}). Inputs are CHANGES (first differences) unless noted.

    xcorr_scan            cross-correlation of x_t vs y_{t+k}, k=-L..L, optional AR prewhitening, Bonferroni-sized significance band
    rolling_best_lag      best lag in rolling windows (stability check)
    granger               F-test that lags of x help forecast y (own OLS; matches statsmodels' ssr_ftest)
    granger_table         both directions for lags 1..maxlag, BIC-chosen lag
    lead_lag_beta         y_{t+k} = a + b x_t + e with Newey-West t-stat
    var_fit, irf_chol, fevd_bounds, vma_longrun, information_share_bounds   VAR -> Cholesky IRF, FEVD / info-share min-max over orderings
    bayes_infer           conditional mean (and sd) of an opaque market's move given transparent markets' moves
    levy_signal           rolling Levy-area lead state with hysteresis (x leads y when A > 0)

CLI:
    python lead_lag.py scan FILE --x COL_X --y COL_Y [--max-lag 10] [--no-diff] [--no-prewhiten] [--date-col date]
    python lead_lag.py --selftest
FILE = CSV or Parquet, wide: a date column plus one column per series, already on a common snap (inner-joined on date).
"""
from __future__ import annotations

import argparse
import itertools
import math
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

try:  # optional cross-check only
    from statsmodels.tsa.stattools import grangercausalitytests as _sm_granger
except Exception:  # pragma: no cover
    _sm_granger = None


def _a(x) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


def _pair(x, y):
    """Align x, y and handle NaN. Dropping interior NaN rows would silently shift every lag, so keep the longest
    contiguous NaN-free block (warns when it has to trim). Fix gaps upstream (common calendar, no multi-day diffs)."""
    x, y = _a(x), _a(y)
    if len(x) != len(y):
        raise ValueError("x and y must be aligned (same length)")
    m = ~(np.isnan(x) | np.isnan(y))
    if m.all():
        return x, y
    e = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
    s, f = max(zip(e[::2], e[1::2]), key=lambda se: se[1] - se[0], default=(0, 0))
    warnings.warn(f"NaN present: using the longest contiguous block ({f - s} of {len(x)} obs)")
    return x[s:f], y[s:f]


def _lagmat(v: np.ndarray, p: int) -> np.ndarray:
    """Rows t=p..T-1, columns v_{t-1}..v_{t-p}."""
    return np.column_stack([v[p - j: len(v) - j] for j in range(1, p + 1)]) if p > 0 else np.empty((len(v), 0))


def _ols(X: np.ndarray, y: np.ndarray):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    return b, e


# ---------------------------------------------------------------- cross-correlation
def _prewhiten(x: np.ndarray, y: np.ndarray, pmax: int):
    """Fit AR(p) to x (p by BIC), apply the SAME filter to y. Returns filtered x, y."""
    xd, yd = x - x.mean(), y - y.mean()
    best = (np.inf, 0, np.empty(0))
    for p in range(0, pmax + 1):
        n = len(xd) - p
        if p == 0:
            e = xd
            a = np.empty(0)
        else:
            a, e = _ols(_lagmat(xd, p), xd[p:])
        bic = n * math.log(max(float(e @ e) / n, 1e-300)) + p * math.log(n)
        if bic < best[0]:
            best = (bic, p, a)
    _, p, a = best
    if p == 0:
        return xd, yd
    fx = xd[p:] - _lagmat(xd, p) @ a
    fy = yd[p:] - _lagmat(yd, p) @ a
    return fx, fy


def xcorr_scan(x, y, max_lag: int = 10, prewhiten: bool = True, pmax: int = 5, alpha: float = 0.05) -> pd.DataFrame:
    """corr(x_t, y_{t+k}) for k=-max_lag..max_lag. Columns: lag, corr, n, crit, significant.

    crit is the Bonferroni band over the 2L+1 lags: z_{1-alpha/(2(2L+1))}/sqrt(n). Prewhitening (AR filter fitted to x,
    applied to both) removes the spurious broad cross-correlation that two autocorrelated series show.
    """
    x, y = _pair(x, y)
    if len(x) < 30 + 2 * max_lag + pmax:
        raise ValueError(f"too few observations ({len(x)}) for max_lag={max_lag}; the skill asks for >= 250")
    if prewhiten:
        x, y = _prewhiten(x, y, pmax)
    rows = []
    z = stats.norm.ppf(1 - alpha / (2 * (2 * max_lag + 1)))
    for k in range(-max_lag, max_lag + 1):
        a, b = (x[: len(x) - k], y[k:]) if k >= 0 else (x[-k:], y[: len(y) + k])
        n = len(a)
        r = float(np.corrcoef(a, b)[0, 1]) if n > 3 else np.nan
        crit = z / math.sqrt(n) if n > 3 else np.nan
        rows.append((k, r, n, crit, bool(abs(r) > crit)))
    return pd.DataFrame(rows, columns=["lag", "corr", "n", "crit", "significant"])


def best_lag(scan: pd.DataFrame) -> dict:
    i = scan["corr"].abs().idxmax()
    r = scan.loc[i]
    zero = float(scan.loc[scan["lag"] == 0, "corr"].iloc[0])
    return {"lag": int(r["lag"]), "corr": float(r["corr"]), "corr_lag0": zero, "significant": bool(r["significant"])}


def rolling_best_lag(x, y, window: int, max_lag: int = 5, step: int = 1, prewhiten: bool = False) -> pd.Series:
    """Best lag in each trailing window (no prewhitening by default, for speed). Stable leads repeat; noise jumps around."""
    x, y = _a(x), _a(y)
    out = {}
    for end in range(window, len(x) + 1, step):
        s = xcorr_scan(x[end - window: end], y[end - window: end], max_lag, prewhiten)
        out[end - 1] = best_lag(s)["lag"]
    return pd.Series(out, name="best_lag")


# ---------------------------------------------------------------- Granger
def granger(y, x, p: int) -> dict:
    """H0: lags 1..p of x add nothing to an AR(p) of y. F = ((RSSr-RSSu)/p)/(RSSu/(n-2p-1)); returns F, pvalue, p, n."""
    y, x = _pair(y, x)
    n = len(y) - p
    if n - 2 * p - 1 < 10:
        raise ValueError(f"too few observations ({len(y)}) for Granger with p={p}")
    Y = y[p:]
    ones = np.ones((n, 1))
    Xr = np.hstack([ones, _lagmat(y, p)])
    Xu = np.hstack([Xr, _lagmat(x, p)])
    rss_r = float((_ols(Xr, Y)[1]) @ (_ols(Xr, Y)[1]))
    eu = _ols(Xu, Y)[1]
    rss_u = float(eu @ eu)
    dof = n - 2 * p - 1
    F = ((rss_r - rss_u) / p) / (rss_u / dof)
    return {"F": F, "pvalue": float(stats.f.sf(F, p, dof)), "p": p, "n": n}


def granger_table(x, y, maxlag: int = 6) -> pd.DataFrame:
    """Both directions for lags 1..maxlag. Columns: lag, F_x_to_y, p_x_to_y, F_y_to_x, p_y_to_x, bic_y (BIC of y-equation with x lags)."""
    x, y = _pair(x, y)
    rows = []
    for p in range(1, maxlag + 1):
        a, b = granger(y, x, p), granger(x, y, p)
        n = len(y) - p
        Xu = np.hstack([np.ones((n, 1)), _lagmat(y, p), _lagmat(x, p)])
        e = _ols(Xu, y[p:])[1]
        bic = n * math.log(float(e @ e) / n) + (2 * p + 1) * math.log(n)
        rows.append((p, a["F"], a["pvalue"], b["F"], b["pvalue"], bic))
    return pd.DataFrame(rows, columns=["lag", "F_x_to_y", "p_x_to_y", "F_y_to_x", "p_y_to_x", "bic_y"])


# ---------------------------------------------------------------- lead-lag beta (HAC)
def lead_lag_beta(x, y, k: int, nw_lags: int | None = None) -> dict:
    """OLS of y_{t+k} on x_t (k>0: x leads) with Newey-West (Bartlett) standard errors. Returns beta, se, t, r2, n."""
    x, y = _pair(x, y)
    a, b = (x[: len(x) - k], y[k:]) if k >= 0 else (x[-k:], y[: len(y) + k])
    n = len(a)
    if n < 20:
        raise ValueError(f"too few observations ({n}) for a lead-lag beta")
    X = np.column_stack([np.ones(n), a])
    beta, e = _ols(X, b)
    L = int(4 * (n / 100) ** (2 / 9)) if nw_lags is None else nw_lags
    L = min(L, n - 2)  # use max(L_nw, h-1) for overlapping h-bar horizons
    s = X * e[:, None]
    S = s.T @ s / n
    for l in range(1, L + 1):
        G = s[l:].T @ s[:-l] / n
        S += (1 - l / (L + 1)) * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X / n)
    cov = XtXi @ S @ XtXi / n
    se = math.sqrt(cov[1, 1])
    r2 = 1 - float(e @ e) / float(((b - b.mean()) ** 2).sum())
    return {"beta": float(beta[1]), "se": se, "t": float(beta[1]) / se, "r2": r2, "n": n, "lag": k}


# ---------------------------------------------------------------- VAR, Cholesky IRF, FEVD, information share
def var_fit(Z, p: int):
    """OLS VAR(p) with constant on Z (T x n, changes). Returns (A list of n x n, Omega, const)."""
    Z = np.asarray(Z, float)
    T, n = Z.shape
    X = np.hstack([np.ones((T - p, 1))] + [Z[p - j: T - j] for j in range(1, p + 1)])
    B, *_ = np.linalg.lstsq(X, Z[p:], rcond=None)
    E = Z[p:] - X @ B
    Omega = E.T @ E / (T - p - X.shape[1])
    A = [B[1 + j * n: 1 + (j + 1) * n].T for j in range(p)]
    return A, Omega, B[0]


def _theta(A, H: int) -> np.ndarray:
    n, p = A[0].shape[0], len(A)
    th = [np.eye(n)]
    for h in range(1, H + 1):
        th.append(sum(A[j - 1] @ th[h - j] for j in range(1, min(h, p) + 1)))
    return np.array(th)  # (H+1, n, n): response of var i at h to unit shock j


def _impact(Omega: np.ndarray, order) -> np.ndarray:
    """Cholesky impact matrix; column m = shock named by variable m, orthogonalised with `order` (first = most exogenous)."""
    o = list(order)
    P = np.linalg.cholesky(Omega[np.ix_(o, o)])
    B = np.zeros_like(Omega)
    B[np.ix_(o, range(len(o)))] = P
    out = np.zeros_like(Omega)
    for j, v in enumerate(o):
        out[:, v] = B[:, j]
    return out


def irf_chol(A, Omega, H: int = 12, order=None) -> np.ndarray:
    """Orthogonalised IRF array (H+1, var, shock). Ordering changes the answer: report it, try the reverse."""
    n = Omega.shape[0]
    return _theta(A, H) @ _impact(Omega, range(n) if order is None else order)


def fevd_bounds(A, Omega, H: int = 12):
    """Forecast-error variance shares (var x shock) at horizon H: (min over orderings, max over orderings). n <= 6."""
    n = Omega.shape[0]
    th = _theta(A, H - 1)
    lo, hi = np.full((n, n), np.inf), np.full((n, n), -np.inf)
    for o in itertools.permutations(range(n)):
        c = (th @ _impact(Omega, o)) ** 2
        s = c.sum(axis=0)
        s = s / s.sum(axis=1, keepdims=True)
        lo, hi = np.minimum(lo, s), np.maximum(hi, s)
    return lo, hi


def vma_longrun(A) -> np.ndarray:
    """Long-run impact of a unit shock on the LEVEL of each variable when Z are price changes: (I - sum A_j)^-1.
    Only a rough psi when the levels are cointegrated (VAR in differences is misspecified): estimate psi from a VECM."""
    return np.linalg.inv(np.eye(A[0].shape[0]) - sum(A))


def information_share_bounds(psi, Omega):
    """Hasbrouck information shares IS_j = (psi F)_j^2 / (psi Omega psi'), F = Cholesky of Omega; (min, max) over orderings.

    psi = common long-run row (1 x n) of one security quoted in n markets. Diagonal Omega -> min == max.
    """
    psi = _a(psi)
    n = len(psi)
    var_w = float(psi @ Omega @ psi)
    lo, hi = np.full(n, np.inf), np.full(n, -np.inf)
    for o in itertools.permutations(range(n)):
        o = list(o)
        F = np.linalg.cholesky(Omega[np.ix_(o, o)])
        s = np.zeros(n)
        s[o] = (psi[o] @ F) ** 2 / var_w
        lo, hi = np.minimum(lo, s), np.maximum(hi, s)
    return lo, hi


# ---------------------------------------------------------------- Bayesian opaque-market inference
def bayes_infer(Q, known, x, unknown=None, mu_known=None, mu_unknown=None) -> dict:
    """Conditional normal: E[Y|x] = mu_Y + Q_Yx Q_xx^-1 (x - mu_x); also cov = Q_YY - Q_Yx Q_xx^-1 Q_xY.

    Q is a COVARIANCE of moves (unit-diagonal correlation gives answers in the units of x). known = indices of
    transparent markets, x = their moves since the last reset (same units). Linear solve, never invert Q.
    Equivalent to solving (Q^-1)_YY (Y-mu_Y) = -(Q^-1)_Yx (x-mu_x).
    """
    Q = np.asarray(Q, float)
    K = list(known)
    U = [i for i in range(len(Q)) if i not in K] if unknown is None else list(unknown)
    x = _a(x)
    mk = np.zeros(len(K)) if mu_known is None else _a(mu_known)
    mu = np.zeros(len(U)) if mu_unknown is None else _a(mu_unknown)
    Qxx, Qyx = Q[np.ix_(K, K)], Q[np.ix_(U, K)]
    mean = mu + Qyx @ np.linalg.solve(Qxx, x - mk)
    cov = Q[np.ix_(U, U)] - Qyx @ np.linalg.solve(Qxx, Qyx.T)
    return {"mean": mean, "cov": cov, "sd": np.sqrt(np.clip(np.diag(cov), 0, None))}


# ---------------------------------------------------------------- Levy area
def levy_signal(x, y, window: int = 20, norm_mult: int = 5, enter: float = 1.5, exit_: float = 0.5) -> pd.DataFrame:
    """Rolling signed (Levy) area of the (x,y) path over `window` bars, A_t = 0.5 * sum (x'_i dy_i - y'_i dx_i), where x', y'
    are anchored at the window start. A > 0: x leads y. z = A / rolling std of A over norm_mult*window; state +1 (x leads) when
    z > enter, -1 when z < -enter, 0 when |z| < exit_, otherwise unchanged (hysteresis). x, y are LEVELS (or cumulated changes).
    """
    x, y = pd.Series(_a(x)), pd.Series(_a(y))
    dx, dy = x.diff(), y.diff()
    A = np.full(len(x), np.nan)
    for t in range(window, len(x)):
        sl = slice(t - window + 1, t + 1)
        xa, ya = x.values[sl] - x.values[t - window], y.values[sl] - y.values[t - window]
        A[t] = 0.5 * np.sum(xa * dy.values[sl] - ya * dx.values[sl])
    A = pd.Series(A)
    z = A / A.rolling(norm_mult * window, min_periods=window).std()
    state, cur = [], 0  # state is known at the close of bar t: act from t+1 (shift before trading)
    for v in z.values:
        if not np.isnan(v):
            if v > enter:
                cur = 1
            elif v < -enter:
                cur = -1
            elif abs(v) < exit_:
                cur = 0
        state.append(cur)
    return pd.DataFrame({"area": A, "z": z, "state": state})


# ---------------------------------------------------------------- CLI
def _load(path: str, date_col: str) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)
    return df.set_index(date_col).sort_index() if date_col in df.columns else df


def _cli_scan(a) -> int:
    df = _load(a.file, a.date_col)[[a.x, a.y]]
    if not a.no_diff:
        df = df.diff()  # diff BEFORE any NaN handling: a gap must not become a multi-day change; _pair keeps the longest clean block
    sc = xcorr_scan(df[a.x], df[a.y], a.max_lag, not a.no_prewhiten)
    bl = best_lag(sc)
    print(sc.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("best:", bl, "(lag>0: x leads y)")
    print(granger_table(df[a.x], df[a.y], min(a.max_lag, 6)).to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    print("beta:", lead_lag_beta(df[a.x], df[a.y], bl["lag"]))
    return 0


def _selftest() -> int:
    rng = np.random.default_rng(7)
    fails = []

    def check(name, ok, info=""):
        print(("ok   " if ok else "FAIL ") + name + (" " + info if info else ""))
        if not ok:
            fails.append(name)

    # 1. cross-correlation with a known 3-step lead on an autocorrelated driver
    N = 4000
    ex = rng.standard_normal(N)
    x = np.zeros(N)
    for t in range(1, N):
        x[t] = 0.4 * x[t - 1] + ex[t]
    y = np.zeros(N)
    y[3:] = 0.6 * x[:-3]
    y += 0.8 * rng.standard_normal(N)
    bl = best_lag(xcorr_scan(x, y, 8))
    check("xcorr best lag = +3, significant", bl["lag"] == 3 and bl["significant"] and bl["corr"] > 0, str(bl))
    bl2 = best_lag(xcorr_scan(y, x, 8))
    check("swap roles -> lag -3", bl2["lag"] == -3, str(bl2))
    # 2. HAC beta recovers 0.6
    lb = lead_lag_beta(x, y, 3)
    check("lead-lag beta ~ 0.6", abs(lb["beta"] - 0.6) < 3 * lb["se"] and abs(lb["beta"] - 0.6) < 0.06, f"{lb['beta']:.3f}+-{lb['se']:.3f}")
    # 3. Granger: y_t = .5 y_{t-1} + .4 x_{t-2} + e, x independent AR(1)
    N = 3000
    ex = rng.standard_normal(N)
    xg = np.zeros(N)
    for t in range(1, N):
        xg[t] = 0.3 * xg[t - 1] + ex[t]
    yg = np.zeros(N)
    for t in range(2, N):
        yg[t] = 0.5 * yg[t - 1] + 0.4 * xg[t - 2] + rng.standard_normal()
    g_fw, g_bw = granger(yg, xg, 2), granger(xg, yg, 2)
    check("granger x->y rejects", g_fw["pvalue"] < 1e-10, f"F={g_fw['F']:.1f}")
    check("granger y->x does not reject", g_bw["pvalue"] > 0.01, f"p={g_bw['pvalue']:.3f}")
    if _sm_granger is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = _sm_granger(pd.DataFrame({"y": yg, "x": xg}), maxlag=2)[2][0]["ssr_ftest"]
        check("granger F equals statsmodels", abs(r[0] - g_fw["F"]) < 1e-6 * max(1, g_fw["F"]), f"{r[0]:.4f} vs {g_fw['F']:.4f}")
    # 4. VAR(1) recovery, IRF identities, FEVD bounds
    A0 = np.array([[0.5, 0.0], [0.3, 0.2]])
    Om = np.array([[1.0, 0.5], [0.5, 1.0]])
    Lc = np.linalg.cholesky(Om)
    N = 30000
    Z = np.zeros((N, 2))
    sh = rng.standard_normal((N, 2)) @ Lc.T
    for t in range(1, N):
        Z[t] = A0 @ Z[t - 1] + sh[t]
    A, Omh, _ = var_fit(Z, 1)
    check("VAR recovers A", np.abs(A[0] - A0).max() < 0.03, str(np.round(A[0], 3).tolist()))
    irf = irf_chol([A0], Om, 3)
    check("IRF h=0 is Cholesky factor", np.allclose(irf[0], Lc))
    check("IRF h=1 is A P", np.allclose(irf[1], A0 @ Lc))
    lo, hi = fevd_bounds([A0], Om, 8)
    check("FEVD min<=max, ordering matters when shocks correlated", (lo <= hi + 1e-12).all() and (hi - lo).max() > 0.01 and (lo.sum(1) <= 1 + 1e-9).all() and (hi.sum(1) >= 1 - 1e-9).all())
    lo_d, hi_d = fevd_bounds([A0], np.eye(2), 8)
    check("FEVD bounds collapse when shocks uncorrelated", np.allclose(lo_d, hi_d))
    # 5. information share: analytic 2x2
    rho = 0.6
    Om2 = np.array([[1.0, rho], [rho, 1.0]])
    psi = np.array([0.5, 0.5])
    lo, hi = information_share_bounds(psi, Om2)
    vw = psi @ Om2 @ psi
    is1_first = (0.5 + 0.5 * rho) ** 2 / vw
    check("info share max for mkt1 = analytic", abs(hi[0] - is1_first) < 1e-12, f"{hi[0]:.4f} vs {is1_first:.4f}")
    check("info share bounds sum consistent", abs(lo[0] + hi[1] - 1) < 1e-12)
    d_lo, d_hi = information_share_bounds(np.array([0.7, 0.3]), np.diag([1.0, 4.0]))
    check("info share diagonal Omega: analytic", np.allclose(d_lo, d_hi) and abs(d_lo[0] - 0.49 / (0.49 + 0.09 * 4)) < 1e-12)
    # 6. Bayesian opaque-market inference: published 2y example, moves in bp
    Q = np.array([[1, .8, .85, .75], [.8, 1, .87, .84], [.85, .87, 1, .82], [.75, .84, .82, 1]])
    r1 = bayes_infer(Q, [0, 1, 2], [2.0, 1.0, 2.0])["mean"][0]
    r2 = bayes_infer(Q, [0, 1, 2], [0.5, -1.5, 0.0])["mean"][0]
    check("Bayes opaque 2y: +1.294 and -0.710", abs(r1 - 1.294) < 5e-4 and abs(r2 + 0.710) < 5e-4, f"{r1:.4f} {r2:.4f}")
    # 7. Levy area: y follows x by 5 bars -> x leads, state mostly +1 and the reverse is -1
    N = 1500
    xl = np.cumsum(rng.standard_normal(N))
    yl = np.r_[np.zeros(5), xl[:-5]] + 0.2 * rng.standard_normal(N)
    s = levy_signal(xl, yl, 20)
    s_rev = levy_signal(yl, xl, 20)
    check("Levy area sign: x leads y", s["area"].mean() > 0 and s_rev["area"].mean() < 0 and (s["state"] == 1).mean() > (s["state"] == -1).mean(),
          f"mean A={s['area'].mean():.3f}")
    # 8. extra identities: reordered Cholesky impact, long-run VMA, HAC se vs statsmodels, rolling lag, NaN gap, short history
    imp = _impact(Om, [1, 0])
    check("reordered impact: P P' = Omega and first-ordered var takes the whole common shock", np.allclose(imp @ imp.T, Om) and abs(imp[1, 0]) < 1e-12 and imp[0, 1] > 0)
    th = _theta([A0], 400)
    check("vma_longrun = sum of Theta", np.allclose(vma_longrun([A0]), th.sum(0), atol=1e-9))
    try:
        import statsmodels.api as sm
        n_ = len(x) - 3
        Xs = np.column_stack([np.ones(n_), x[:-3]])
        se_sm = sm.OLS(y[3:], Xs).fit(cov_type="HAC", cov_kwds={"maxlags": int(4 * (n_ / 100) ** (2 / 9)), "use_correction": False}).bse[1]
        check("HAC se equals statsmodels", abs(se_sm - lb["se"]) < 1e-9, f"{se_sm:.5f} vs {lb['se']:.5f}")
    except ImportError:
        pass
    rb = rolling_best_lag(x, y, 600, 5, step=300)
    check("rolling best lag stable at +3", (rb == 3).all(), str(rb.tolist()))
    xn, yn = x[:1500].copy(), y[:1500].copy()
    xn[700] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bn = best_lag(xcorr_scan(xn, yn, 8))
    check("interior NaN: longest block kept, lag unchanged", bn["lag"] == 3, str(bn))
    try:
        xcorr_scan(x[:20], y[:20], 8)
        check("short history raises", False)
    except ValueError:
        check("short history raises", True)
    print("PASS" if not fails else "FAILED: " + ", ".join(fails))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("scan")
    s.add_argument("file")
    s.add_argument("--x", required=True)
    s.add_argument("--y", required=True)
    s.add_argument("--max-lag", type=int, default=10)
    s.add_argument("--no-diff", action="store_true", help="inputs are already changes; do not difference")
    s.add_argument("--no-prewhiten", action="store_true")
    s.add_argument("--date-col", default="date")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "scan":
        return _cli_scan(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
