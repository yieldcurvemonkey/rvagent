"""Hedge-ratio estimators on yield / price changes: OLS (+HAC), TLS/Deming, vol-ratio, rolling, EWMA, Kalman
(random-walk beta), block bootstrap, out-of-sample hedge comparison and residual diagnostics.

Conventions (rates in bp internally; curve_par stores pct and is converted x100):
    y = target leg change, x = hedge leg change(s), beta = d(y)/d(x) in change space.
    hedge DV01 = -beta * target DV01   (opposite side); hedge notional = -N_t * (DV01_t / DV01_h) * beta.
    beta = 1 is the DV01-neutral hedge. Hedged P&L per unit of target = y - beta*x; its vol is DV01 * resid sd.
    The leg whose size is fixed (the trade you were asked to hedge) is the dependent variable y.
    Deming slope: delta = var(noise in y) / var(noise in x). delta=1 is orthogonal regression and is only
    meaningful if both legs are in the same units with comparable noise; delta = var(y)/var(x) gives the
    vol-ratio (geometric-mean) hedge sign(rho)*sd_y/sd_x; delta -> infinity gives OLS.

CLI (canonical `curve_par` table from data-contract-and-adapters, CSV or Parquet, long format):
    python hedge_ratios.py --curve-par curve_par.parquet --curve-id USD-SOFR --y 10Y --x 2Y
    python hedge_ratios.py --curve-par curve_par.csv --curve-id EUR-ESTR --y 5Y --x 10Y --horizon 5 --halflife 60
    python hedge_ratios.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats


# ------------------------------------------------------------------------------------------------ helpers
def _clean(y, X):
    y = np.asarray(y, float).ravel()
    X = np.asarray(X, float).reshape(len(y), -1)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    return y[ok], X[ok]


def nw_lags(n: int) -> int:
    """Newey-West rule of thumb: integer part of 4 (n/100)^(2/9)."""
    return int(4 * (n / 100.0) ** (2.0 / 9.0))


def to_changes(levels: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """Non-overlapping `horizon`-row changes of a levels frame (overlapping changes need HAC and inflate t-stats)."""
    return levels.iloc[::horizon].diff().dropna()


# ------------------------------------------------------------------------------------------------ OLS + HAC
def ols_fit(y, X, hac_lags: int | None = None) -> dict:
    """OLS of y on [1, X]. Returns alpha, beta (array), classical and Newey-West (Bartlett) SEs, R2, resid sd."""
    y, X = _clean(y, X)
    n = len(y)
    if n < X.shape[1] + 3:
        raise ValueError(f"too few finite observations ({n}) for {X.shape[1]} regressor(s)")
    Z = np.column_stack([np.ones(n), X])
    ZtZi = np.linalg.pinv(Z.T @ Z)
    b = ZtZi @ Z.T @ y
    e = y - Z @ b
    p = Z.shape[1]
    s2 = float(e @ e) / (n - p)
    L = nw_lags(n) if hac_lags is None else int(hac_lags)
    u = Z * e[:, None]
    S = u.T @ u
    for lag in range(1, L + 1):
        G = u[lag:].T @ u[:-lag]
        S = S + (1.0 - lag / (L + 1.0)) * (G + G.T)
    se_hac = np.sqrt(np.diag(ZtZi @ S @ ZtZi))
    return dict(alpha=float(b[0]), beta=b[1:], se=np.sqrt(np.diag(ZtZi) * s2)[1:], se_hac=se_hac[1:],
                t_hac=b[1:] / se_hac[1:], r2=1.0 - float(e @ e) / float(((y - y.mean()) ** 2).sum()),
                resid_sd=s2 ** 0.5, resid=e, n=n, lags=L)


def hedged_resid(y, x, beta) -> np.ndarray:
    """Hedged P&L per unit of target risk: y - beta*x (same units as y)."""
    return np.asarray(y, float) - np.asarray(beta) * np.asarray(x, float)


# ------------------------------------------------------------------------------------------------ TLS / Deming
def deming_slope(sxx: float, syy: float, sxy: float, delta: float = 1.0) -> float:
    """Deming slope of y on x from second moments; delta = var(noise_y)/var(noise_x)."""
    if sxy == 0.0:
        return 0.0
    d = syy - delta * sxx
    return (d + np.sqrt(d * d + 4.0 * delta * sxy * sxy)) / (2.0 * sxy)


def tls_fit(y, x, delta: float | str = 1.0) -> dict:
    """TLS/Deming of y on x (single regressor). delta='vol' -> var(y)/var(x), i.e. the vol-ratio hedge."""
    y, X = _clean(y, x)
    x = X[:, 0]
    xc, yc = x - x.mean(), y - y.mean()
    sxx, syy, sxy = float(xc @ xc) / len(x), float(yc @ yc) / len(x), float(xc @ yc) / len(x)
    dl = syy / sxx if delta == "vol" else float(delta)
    b = deming_slope(sxx, syy, sxy, dl)
    return dict(beta=b, alpha=float(y.mean() - b * x.mean()), delta=dl, rho=sxy / np.sqrt(sxx * syy),
                sd_y=syy ** 0.5, sd_x=sxx ** 0.5)


def hedge_menu(y, x) -> dict:
    """Slope menu for hedging y with x (all dimensionless risk ratios, beta = hedge DV01 per unit target DV01):
    ols = min-variance; tls = orthogonal; vol = sd_y/sd_x ('yield beta'); reverse = 1/beta(x on y)
    ('yield delta', zero expected P&L); dv01 = 1. For rho > 0: ols <= tls <= reverse."""
    o = ols_fit(y, x)
    rev = ols_fit(x, y)
    t = tls_fit(y, x, 1.0)
    return dict(dv01=1.0, ols=float(o["beta"][0]), tls=t["beta"], vol=np.sign(t["rho"]) * t["sd_y"] / t["sd_x"],
                reverse=1.0 / float(rev["beta"][0]), rho=t["rho"])


def mark_noise_delta(y, x) -> float:
    """Deming delta from mark noise. If a change is d(true) + nu_t - nu_(t-1) (iid mark noise), its lag-1
    autocovariance is -var(nu); so delta = var(nu_y)/var(nu_x) = cov1(dy)/cov1(dx). Returns nan unless both
    lag-1 autocovariances are negative (no detectable noise: use delta=1 only if the legs are alike)."""
    def c1(a):
        a = np.asarray(a, float)
        a = a[np.isfinite(a)]
        a = a - a.mean()
        return float(a[1:] @ a[:-1]) / len(a)
    cy, cx = c1(y), c1(x)
    return cy / cx if cy < 0 and cx < 0 else float("nan")


def hedge_notional(notional_target: float, dv01_target: float, dv01_hedge: float, beta: float = 1.0) -> float:
    """Signed hedge notional (opposite sign to the target). beta=1 is the DV01-neutral hedge."""
    return -notional_target * (dv01_target / dv01_hedge) * beta


# ------------------------------------------------------------------------------------------------ rolling / EWMA
def rolling_beta(y: pd.Series, x: pd.Series, window: int = 63) -> pd.Series:
    """Rolling OLS slope (with intercept): cov/var. Equal weights: lags regime changes and shows ghost effects."""
    return y.rolling(window).cov(x) / x.rolling(window).var()


def ewma_beta(y: pd.Series, x: pd.Series, halflife: float = 60.0, demean: bool = False,
              min_periods: int = 20) -> pd.Series:
    """Exponentially weighted beta. Zero-mean second moments by default (changes have ~0 mean).
    Use .shift(1) before trading on it: the beta known at t uses data through t-1."""
    if demean:
        return y.ewm(halflife=halflife, min_periods=min_periods).cov(x) / x.ewm(halflife=halflife,
                                                                                min_periods=min_periods).var()
    return ((y * x).ewm(halflife=halflife, min_periods=min_periods).mean() /
            (x * x).ewm(halflife=halflife, min_periods=min_periods).mean())


# ------------------------------------------------------------------------------------------------ Kalman
def kalman_beta(y, X, q_ratio: float = 1e-4, burn: int | None = None, kappa: float = 1e4) -> dict:
    """Random-walk regression y_t = a_t + b_t'x_t + e_t, state (a, b) with F = I (filtered, never smoothed).
    R = burn-in OLS residual variance s2; Q = q_ratio * s2 * diag(1, 1/var(x_j)) (state step variance relative to
    noise); diffuse prior P0 = kappa * s2 * diag(1, 1/var(x_j)). q_ratio = 0 -> recursive OLS (= batch OLS).
    Returns beta_pred / alpha_pred (the estimate known BEFORE seeing obs t: use these for hedging and OOS P&L),
    beta_filt, innovations, their variances and the Gaussian log-likelihood."""
    y, X = _clean(y, X)
    n, k = X.shape
    burn = min(n, max(60, n // 4)) if burn is None else int(burn)
    s2 = float(ols_fit(y[:burn], X[:burn])["resid_sd"]) ** 2
    scale = np.diag(np.r_[1.0, 1.0 / X[:burn].var(axis=0)])
    Q, R = q_ratio * s2 * scale, s2
    th, P = np.zeros(k + 1), kappa * s2 * scale
    pred, filt = np.full((n, k + 1), np.nan), np.full((n, k + 1), np.nan)
    inn, fvar, ll = np.full(n, np.nan), np.full(n, np.nan), 0.0
    for t in range(n):
        P = P + Q                                     # predict (F = I)
        h = np.r_[1.0, X[t]]
        pred[t] = th
        f = float(h @ P @ h) + R
        e = y[t] - float(h @ th)
        K = P @ h / f                                 # update
        th = th + K * e
        P = P - np.outer(K, h) @ P
        filt[t], inn[t], fvar[t] = th, e, f
        if t >= k + 2:
            ll += -0.5 * (np.log(2 * np.pi * f) + e * e / f)
    pred[:k + 2] = np.nan
    return dict(alpha_pred=pred[:, 0], beta_pred=pred[:, 1:], beta_filt=filt[:, 1:], innov=inn, innov_var=fvar,
                loglik=ll, q_ratio=q_ratio)


def kalman_tune(y, X, burn: int, grid=(0.0, 1e-5, 1e-4, 1e-3, 1e-2)) -> float:
    """q_ratio maximising the prediction-error likelihood on the first `burn` observations only; then freeze."""
    y, X = _clean(y, X)
    return max(grid, key=lambda q: kalman_beta(y[:burn], X[:burn], q_ratio=q, burn=burn)["loglik"])


# ------------------------------------------------------------------------------------------------ bootstrap, diagnostics
def boot_beta(y, x, B: int = 1000, block: int = 10, method: str = "ols", seed: int = 0) -> dict:
    """Moving-block bootstrap of (y, x) rows. Returns SE and 95% percentile CI of the slope."""
    y, X = _clean(y, x)
    x = X[:, 0]
    n, rng = len(y), np.random.default_rng(seed)
    block = max(1, min(block, n // 2))
    nb = int(np.ceil(n / block))
    out = np.empty(B)
    for i in range(B):
        idx = (rng.integers(0, n - block + 1, nb)[:, None] + np.arange(block)).ravel()[:n]
        yy, xx = y[idx], x[idx]
        if method == "tls":
            out[i] = tls_fit(yy, xx)["beta"]
        else:
            xc = xx - xx.mean()
            out[i] = float(xc @ (yy - yy.mean())) / float(xc @ xc)
    return dict(se=float(out.std(ddof=1)), lo=float(np.percentile(out, 2.5)), hi=float(np.percentile(out, 97.5)))


def ljung_box(e, lags: int = 10) -> tuple[float, float]:
    """Ljung-Box Q and p-value for residual autocorrelation (use instead of Durbin-Watson)."""
    e = np.asarray(e, float)
    e = e[np.isfinite(e)]
    n = len(e)
    e = e - e.mean()
    acf = np.array([float(e[k:] @ e[:-k]) for k in range(1, lags + 1)]) / float(e @ e)
    q = n * (n + 2) * float(np.sum(acf ** 2 / (n - np.arange(1, lags + 1))))
    return q, float(stats.chi2.sf(q, lags))


def half_life(resid_levels) -> float:
    """OU half-life (in observations) of a level-regression residual: slope k of d(e_t) on e_(t-1), -ln2/ln(1+k).
    inf if the residual does not mean-revert."""
    e = np.asarray(resid_levels, float)
    e = e[np.isfinite(e)]
    xc = e[:-1] - e[:-1].mean()
    k = float(xc @ np.diff(e)) / float(xc @ xc)
    return float(-np.log(2) / np.log(1 + k)) if -1 < k < 0 else float("inf")


def oos_table(y: pd.Series, x: pd.Series, split: float = 0.5, halflife: float = 60.0) -> pd.DataFrame:
    """Calibrate on the first `split` of the sample, report hedged-residual vol on the rest (same units as y).
    Rolling methods (ewma, kalman) are evaluated with the beta known before each date."""
    y, x = y.dropna(), x.reindex(y.index).dropna()
    y = y.reindex(x.index)
    cut = int(len(y) * split)
    yi, xi, yo, xo = y.iloc[:cut], x.iloc[:cut], y.iloc[cut:], x.iloc[cut:]
    betas = {"unhedged": 0.0, "dv01 (beta=1)": 1.0, "ols": float(ols_fit(yi, xi)["beta"][0]),
             "tls (delta=1)": tls_fit(yi, xi)["beta"], "vol-ratio": tls_fit(yi, xi, "vol")["beta"]}
    rows = {k: (b, float(hedged_resid(yo, xo, b).std())) for k, b in betas.items()}
    eb = ewma_beta(y, x, halflife).shift(1).iloc[cut:]
    rows[f"ewma hl={halflife:g}"] = (float(eb.iloc[-1]), float(hedged_resid(yo, xo, eb).std()))
    q = kalman_tune(y.values, x.values, burn=cut)
    kb = pd.Series(kalman_beta(y.values, x.values, q_ratio=q, burn=cut)["beta_pred"][:, 0], index=y.index).iloc[cut:]
    rows[f"kalman q={q:g}"] = (float(kb.iloc[-1]), float(hedged_resid(yo, xo, kb).std()))
    df = pd.DataFrame(rows, index=["last_beta", "oos_resid_sd"]).T
    df["vs_unhedged"] = df["oos_resid_sd"] / df.loc["unhedged", "oos_resid_sd"] - 1.0
    return df


# ------------------------------------------------------------------------------------------------ CLI
def load_changes(path: str, curve_id: str, tenors: list[str], start: str = "0D", snap: str | None = None,
                 horizon: int = 1) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.endswith((".parquet", ".pq")) else pd.read_csv(path)
    df = df[(df["curve_id"] == curve_id) & (df["start"] == start) & (df["tenor"].isin(tenors))]
    snaps = df["snap"].unique()
    if snap is None and len(snaps) > 1:
        raise SystemExit(f"several snaps present {list(snaps)}: pass --snap (never mix snaps in one series)")
    if snap is not None:
        df = df[df["snap"] == snap]
    lv = df.pivot(index="date", columns="tenor", values="par_rate_pct").sort_index() * 100.0   # pct -> bp
    if lv.shape[1] != len(set(tenors)):
        raise SystemExit(f"missing tenors for {curve_id}/{start}: found {list(lv.columns)}")
    return to_changes(lv[tenors], horizon)


def report(ch: pd.DataFrame, y: str, xs: list[str], halflife: float, window: int) -> None:
    d = ch.dropna()
    o = ols_fit(d[y], d[xs])
    print(f"n={o['n']} changes  y={y}  x={'+'.join(xs)}  (bp)")
    for i, xn in enumerate(xs):
        lo, hi = o["beta"][i] - 1.96 * o["se_hac"][i], o["beta"][i] + 1.96 * o["se_hac"][i]
        print(f"OLS beta[{xn}] = {o['beta'][i]:.3f}  HAC CI95 [{lo:.3f}, {hi:.3f}]  t(beta=1) = "
              f"{(o['beta'][i] - 1) / o['se_hac'][i]:.2f}  alpha = {o['alpha']:.3f}")
    q, p = ljung_box(o["resid"])
    print(f"R2 = {o['r2']:.3f}  resid sd = {o['resid_sd']:.3f} bp/period  Ljung-Box(10) p = {p:.3f}")
    if len(xs) == 1:
        m = hedge_menu(d[y], d[xs[0]])
        print("menu (hedge DV01 per unit target DV01): " + "  ".join(f"{k}={v:.3f}" for k, v in m.items()))
        print(f"mark-noise delta (nan = none detected) = {mark_noise_delta(d[y], d[xs[0]]):.2f}")
        print(f"rolling {window}: {rolling_beta(d[y], d[xs[0]], window).iloc[-1]:.3f}   "
              f"ewma hl={halflife:g}: {ewma_beta(d[y], d[xs[0]], halflife).iloc[-1]:.3f}")
        print(oos_table(d[y], d[xs[0]], 0.5, halflife).round(3).to_string())
    print("Rule: compare OLS CI with 1.0 and the OOS table before choosing; hedged vol = DV01 x resid sd.")


# ------------------------------------------------------------------------------------------------ self-test
def selftest() -> int:
    bad: list[str] = []

    def check(name, ok, info=""):
        print(("PASS " if ok else "FAIL ") + name + (f"  [{info}]" if info else ""))
        if not ok:
            bad.append(name)

    rng = np.random.default_rng(7)
    # 1. OLS equals least squares; HAC lags rule
    x = rng.normal(0, 3, 500)
    y = 0.8 * x + rng.normal(0, 1.5, 500)
    o = ols_fit(y, x)
    ref = np.linalg.lstsq(np.column_stack([np.ones(500), x]), y, rcond=None)[0]
    check("ols matches lstsq", abs(o["beta"][0] - ref[1]) < 1e-10 and abs(o["alpha"] - ref[0]) < 1e-10)
    check("ols recovers beta 0.8 (known)", abs(o["beta"][0] - 0.8) < 0.04, f"{o['beta'][0]:.3f}")
    check("nw lag rule n=100 -> 4", nw_lags(100) == 4 and nw_lags(1000) == 6)
    # 2. Deming closed form: asymmetric known answer (beta 0.8, delta 2: sxx 1.25, sxy 0.8, syy 1.14)
    check("deming exact asymmetric", abs(deming_slope(1.25, 1.14, 0.8, 2.0) - 0.8) < 1e-12)
    # population moments of y = 1.5 x*, x = x* + eta(sd .5), y noise sd 1 (delta = 4): OLS 1.2, Deming 1.5
    sxx, syy, sxy = 1.25, 1.5 ** 2 + 1.0, 1.5
    check("deming exact errors-in-variables", abs(deming_slope(sxx, syy, sxy, 4.0) - 1.5) < 1e-12
          and abs(sxy / sxx - 1.2) < 1e-12)
    # delta=1 equals first-eigenvector slope; delta=var ratio equals vol ratio; delta large -> OLS
    C = np.array([[2.0, 1.2], [1.2, 3.0]])
    w, v = np.linalg.eigh(C)
    check("deming d=1 == eigenvector slope", abs(deming_slope(2.0, 3.0, 1.2, 1.0) - v[1, 1] / v[0, 1]) < 1e-12)
    check("deming d=syy/sxx == sd ratio", abs(deming_slope(2.0, 3.0, 1.2, 1.5) - np.sqrt(1.5)) < 1e-12)
    check("deming d->inf == OLS", abs(deming_slope(2.0, 3.0, 1.2, 1e9) - 0.6) < 1e-6)
    # 2b. mark-noise delta: random walks + iid mark noise (sd .3 on y, .15 on x) -> delta = 4
    nm = 300000
    wy, wx = np.cumsum(rng.normal(0, 1, nm)), np.cumsum(rng.normal(0, 1, nm))
    dm = mark_noise_delta(np.diff(wy + rng.normal(0, 0.3, nm)), np.diff(wx + rng.normal(0, 0.15, nm)))
    check("mark-noise delta ~ 4", abs(dm - 4.0) < 0.6, f"{dm:.2f}")
    # 3. simulated attenuation: OLS 1.2, TLS(delta=4) 1.5 (known)
    n = 200000
    xs = rng.normal(0, 1, n)
    xo, yo = xs + rng.normal(0, 0.5, n), 1.5 * xs + rng.normal(0, 1.0, n)
    check("sim: OLS attenuated to 1.2", abs(ols_fit(yo, xo)["beta"][0] - 1.2) < 0.02)
    check("sim: Deming(4) recovers 1.5", abs(tls_fit(yo, xo, 4.0)["beta"] - 1.5) < 0.02)
    # 4. identities on any data: fwd*rev = R2 ; ols <= tls <= reverse ; vol = sd ratio
    xx = rng.normal(0, 3, 800)
    yy = 0.7 * xx + rng.normal(0, 2, 800)
    m = hedge_menu(yy, xx)
    f, r = ols_fit(yy, xx), ols_fit(xx, yy)
    check("fwd*rev slope == R2", abs(f["beta"][0] * r["beta"][0] - f["r2"]) < 1e-10)
    check("ols <= tls <= reverse", m["ols"] < m["tls"] < m["reverse"], f"{m['ols']:.3f} {m['tls']:.3f} {m['reverse']:.3f}")
    check("vol menu == sd ratio", abs(m["vol"] - yy.std() / xx.std()) < 1e-9)
    # 5. Treasury Bond Basis 1/12/98 table: 30y hedged with 5y; conventional 341.2mm
    rho, ratio = 0.88, 81.7 / 101.9
    conv = 341.2
    got = [conv * ratio * rho, conv * ratio, conv * ratio / rho]   # min-var, yield beta, yield delta
    check("TBB 1998 hedge table", all(abs(a - b) < 0.2 for a, b in zip(got, [240.7, 273.6, 310.9])),
          " ".join(f"{g:.1f}" for g in got))
    # 6. Tuckman-Serrat 2021 corporate vs UST: sell 100mm * 0.2124/0.1910 * 0.842 = 93.6mm; DV01-neutral 111.2mm
    check("hedge notional (Tuckman JNJ vs UST)", abs(hedge_notional(100, 0.2124, 0.1910, 0.842) + 93.6) < 0.05
          and abs(hedge_notional(100, 0.2124, 0.1910) + 111.2) < 0.05)
    # 7. Kalman: q=0 + diffuse prior == batch OLS ; moving beta tracked; step tracked
    xk = rng.normal(0, 3, 1500)
    yk = 0.9 * xk + rng.normal(0, 1.5, 1500)
    kf = kalman_beta(yk, xk, q_ratio=0.0)
    check("kalman q=0 == batch OLS", abs(kf["beta_filt"][-1, 0] - ols_fit(yk, xk)["beta"][0]) < 2e-3)
    nn = 3000
    bt = np.linspace(0.4, 1.2, nn)
    xt = rng.normal(0, 3, nn)
    yt = bt * xt + rng.normal(0, 1.5, nn)
    kf = kalman_beta(yt, xt, q_ratio=1e-4)
    rm = float(np.sqrt(np.mean((kf["beta_pred"][300:, 0] - bt[300:]) ** 2)))
    rs = float(np.sqrt(np.mean((ols_fit(yt, xt)["beta"][0] - bt[300:]) ** 2)))
    check("kalman tracks drifting beta", rm < 0.12 and rm < 0.6 * rs, f"kalman rmse {rm:.3f} vs static {rs:.3f}")
    ns = 2000
    bs = np.where(np.arange(ns) < 1000, 0.5, 1.0)
    xs2 = rng.normal(0, 3, ns)
    ys2 = bs * xs2 + rng.normal(0, 1.5, ns)
    kf = kalman_beta(ys2, xs2, q_ratio=1e-3)
    check("kalman adapts to beta step", abs(kf["beta_pred"][1400, 0] - 1.0) < 0.15 and
          abs(kf["beta_pred"][990, 0] - 0.5) < 0.15, f"{kf['beta_pred'][1400, 0]:.3f}")
    qt = kalman_tune(ys2, xs2, burn=1500)
    check("kalman_tune picks a positive q when beta moves", qt > 0.0, f"q={qt:g}")
    # 8. EWMA: constant beta recovered; step adopted after ~5 half-lives
    s_x = pd.Series(rng.normal(0, 3, 1000))
    s_y = pd.Series(np.where(np.arange(1000) < 500, 0.5, 1.0)) * s_x + rng.normal(0, 0.5, 1000)
    eb = ewma_beta(s_y, s_x, halflife=30)
    check("ewma tracks step", abs(eb.iloc[499] - 0.5) < 0.1 and abs(eb.iloc[650] - 1.0) < 0.1,
          f"{eb.iloc[499]:.3f} {eb.iloc[650]:.3f}")
    # one half-life after the step half the weight is post-step: beta ~ 0.75 (pins the half-life -> lambda mapping)
    check("ewma half-life weight (0.75 one half-life after step)", abs(eb.iloc[529] - 0.75) < 0.07, f"{eb.iloc[529]:.3f}")
    rb = rolling_beta(s_y, s_x, 60)
    check("rolling beta (equal weights) ok", abs(rb.iloc[499] - 0.5) < 0.1 and abs(rb.iloc[600] - 1.0) < 0.1)
    # 9. HAC: iid -> ratio ~1 ; 5-period overlapping sums -> HAC SE much larger than classical
    u, vv = rng.normal(size=6000), rng.normal(size=6000)
    d = u * 0.5 + vv
    ov = lambda a: pd.Series(a).rolling(5).sum().dropna().values
    o1 = ols_fit(d, u)
    o2 = ols_fit(ov(d), ov(u), hac_lags=8)
    check("HAC ~ classical for iid", 0.8 < o1["se_hac"][0] / o1["se"][0] < 1.25, f"{o1['se_hac'][0] / o1['se'][0]:.2f}")
    check("HAC inflates overlapping SE", 1.5 < o2["se_hac"][0] / o2["se"][0] < 3.0, f"{o2['se_hac'][0] / o2['se'][0]:.2f}")
    # 9b. HAC equals an independent Newey-West (Bartlett) computation by the partialled-out recipe
    # (a_t = r_t e_t, r = x demeaned; v = sum a^2 + 2 sum_h (1 - h/(L+1)) sum a_t a_(t+h); se = sqrt(v) / sum r^2)
    xh, yh = ov(u[:400]), ov(d[:400])
    oh = ols_fit(yh, xh, hac_lags=6)
    r_, a_ = xh - xh.mean(), (xh - xh.mean()) * oh["resid"]
    v_ = float(a_ @ a_) + 2 * sum((1 - h / 7.0) * float(a_[:-h] @ a_[h:]) for h in range(1, 7))
    check("HAC matches independent Newey-West formula", abs(oh["se_hac"][0] - v_ ** 0.5 / float(r_ @ r_)) < 1e-10)
    # simulation: for 5-overlap sums the classical SE is ~0.54 of the true sampling sd and HAC(4) recovers most of it
    bs, se_h, se_c = [], [], []
    for _ in range(300):
        ua, va = rng.normal(size=1000), rng.normal(size=1000)
        oo = ols_fit(ov(0.5 * ua + va), ov(ua), hac_lags=4)
        bs.append(oo["beta"][0]); se_h.append(oo["se_hac"][0]); se_c.append(oo["se"][0])
    sd_true = float(np.std(bs, ddof=1))
    check("overlap: classical SE ~0.54 of true sd, HAC 0.7-0.95", 0.45 < np.mean(se_c) / sd_true < 0.65 and
          0.7 < np.mean(se_h) / sd_true < 0.95, f"classical/true {np.mean(se_c) / sd_true:.2f}, hac/true {np.mean(se_h) / sd_true:.2f}")
    # 10. Ljung-Box and half-life on AR(1) with known phi
    e = np.zeros(4000)
    for t in range(1, 4000):
        e[t] = 0.9 * e[t - 1] + rng.normal()
    check("Ljung-Box rejects AR(1)", ljung_box(e)[1] < 1e-6 and ljung_box(rng.normal(size=4000))[1] > 0.01)
    qm = np.mean([ljung_box(rng.normal(size=500))[0] for _ in range(300)])
    check("Ljung-Box Q mean ~ lags under H0 (chi2 mean 10)", abs(qm - 10) < 1.2, f"{qm:.2f}")
    check("half-life of AR(1) 0.9 ~ 6.6", abs(half_life(e) - np.log(2) / -np.log(0.9)) < 1.5, f"{half_life(e):.2f}")
    # 11. bootstrap SE close to analytic for iid data
    xb = rng.normal(0, 3, 1500)
    yb = 0.8 * xb + rng.normal(0, 1.5, 1500)
    ob = ols_fit(yb, xb)
    bb = boot_beta(yb, xb, B=600, block=5)
    check("bootstrap SE ~ analytic", abs(bb["se"] / ob["se"][0] - 1) < 0.25, f"{bb['se']:.4f} vs {ob['se'][0]:.4f}")
    # 12. fly regression weights: residual of OLS is orthogonal to slope and level (known OLS property)
    y2, y10, e5 = rng.normal(0, 4, 1000), rng.normal(0, 5, 1000), rng.normal(0, 1, 1000)
    y5 = 0.4 * y2 + 0.6 * y10 + e5
    fly = 2 * y5 - y2 - y10
    of = ols_fit(fly, np.column_stack([y10 - y2, y5]))
    b1, b2 = of["beta"]
    comb = -(1 - b1) * y2 + (2 - b2) * y5 - (1 + b1) * y10
    check("fly weights leave resid uncorrelated with slope and level",
          abs(np.corrcoef(comb, y10 - y2)[0, 1]) < 1e-9 and abs(np.corrcoef(comb, y5)[0, 1]) < 1e-9)
    # 13. oos table runs and ranks sensibly on stable beta (hedging beats unhedged by a wide margin)
    ix = pd.RangeIndex(1200)
    tx = pd.Series(rng.normal(0, 3, 1200), index=ix)
    ty = 0.8 * tx + pd.Series(rng.normal(0, 1, 1200), index=ix)
    t = oos_table(ty, tx, 0.5, 60)
    check("oos table: ols hedge cuts vol >60%", t.loc["ols", "vs_unhedged"] < -0.6, f"{t.loc['ols', 'vs_unhedged']:.2f}")
    print("ALL PASSED" if not bad else f"FAILED: {bad}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--curve-par", help="canonical curve_par table (csv/parquet)")
    ap.add_argument("--curve-id")
    ap.add_argument("--y", help="target tenor, e.g. 10Y (dependent variable = the leg whose size is fixed)")
    ap.add_argument("--x", nargs="+", help="hedge tenor(s), e.g. 2Y or 5Y 30Y")
    ap.add_argument("--start", default="0D", help="forward start (default spot-starting)")
    ap.add_argument("--snap", default=None)
    ap.add_argument("--horizon", type=int, default=1, help="change horizon in rows (non-overlapping)")
    ap.add_argument("--halflife", type=float, default=60.0)
    ap.add_argument("--window", type=int, default=63)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.curve_par and a.curve_id and a.y and a.x):
        ap.error("need --curve-par --curve-id --y --x (or --selftest)")
    ch = load_changes(a.curve_par, a.curve_id, [a.y] + a.x, a.start, a.snap, a.horizon)
    report(ch, a.y, a.x, a.halflife, a.window)
    return 0


if __name__ == "__main__":
    sys.exit(main())
