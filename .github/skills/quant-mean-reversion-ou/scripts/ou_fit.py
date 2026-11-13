#!/usr/bin/env python3
"""OU / mean-reversion toolkit for rates RV residuals (spreads, flies, model residuals).

Functions take numpy arrays or pandas Series (levels, e.g. bp). Time unit = one observation (dt=1) unless dt given.

    fit_ou            AR(1)->OU (kappa, mu, sigma, half-life, CI); method "ar1" (OLS) or "mle" (closed form)
    rolling_ou        rolling AR(1) phi / half-life
    adf, kpss         unit-root / stationarity tests (own implementation; statsmodels only for p-values)
    hurst_std, variance_ratio   scaling diagnostics (VR with heteroskedasticity-robust z)
    ou_expected_path, ou_sharpe   ex-ante path, +/-2sd band and Sharpe over horizon h
    optimal_symmetric_band        Bertram cycle-time optimal entry/exit band
    leung_li_levels               Leung-Li optimal exit b* and entry d* (one-shot, no stop-loss)
    fit_mvou, spread_is_ou        multivariate OU (VAR(1) -> Theta) and the left-eigenvector test
    diagnose                      one-call report with a verdict

CLI:
    python ou_fit.py diagnose FILE.csv --value-col value [--date-col date] [--group-col package_id] [--cost-bp 0.5]
    python ou_fit.py bands --kappa 0.063 --sigma 0.5 --cost 0.5      (kappa per obs, sigma per sqrt(obs), cost in series units)
    python ou_fit.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd
from scipy import integrate, optimize, special
from scipy.linalg import expm, logm

try:  # optional: only used for p-values and cross-checks
    from statsmodels.tsa.stattools import mackinnonp as _mackinnonp
except Exception:  # pragma: no cover
    _mackinnonp = None

LN2 = math.log(2.0)
ADF_CRIT = {"1%": -3.43, "5%": -2.86, "10%": -2.57}          # asymptotic, constant, no trend
KPSS_CRIT = {"10%": 0.347, "5%": 0.463, "2.5%": 0.574, "1%": 0.739}  # level stationarity


def _arr(x) -> np.ndarray:
    """Floats with NaNs dropped (gaps are closed, so reindex or fill gaps upstream if spacing matters)."""
    a = np.asarray(x, dtype=float).ravel()
    return a[~np.isnan(a)]


# ------------------------------------------------------------------ OU fit
def fit_ou(x, dt: float = 1.0, method: str = "ar1") -> dict:
    """Fit dx = kappa (mu - x) dt + sigma dW from levels x sampled every dt.

    Returns kappa (per time unit), mu, sigma (per sqrt time unit), sd_eq = sigma/sqrt(2 kappa), half_life = ln2/kappa
    (time units), phi = exp(-kappa dt), phi_se, half_life_lo/hi (95%, delta method on phi) .
    Not mean-reverting (phi <= 0 or >= 1): kappa, half_life = NaN (one canonical sentinel).
    """
    x = _arr(x)
    n = len(x) - 1
    if n < 10:
        raise ValueError("need >= 11 observations")
    xl, xc = x[:-1], x[1:]
    if method == "mle":  # closed form, Leung & Li (2016) ch.2
        Xx, Xy, Xxx, Xxy, Xyy = xl.sum(), xc.sum(), (xl**2).sum(), (xl * xc).sum(), (xc**2).sum()
        th = (Xy * Xxx - Xx * Xxy) / (n * (Xxx - Xxy) - (Xx**2 - Xx * Xy))
        num = Xxy - th * Xx - th * Xy + n * th**2
        den = Xxx - 2 * th * Xx + n * th**2
        phi = num / den
        mu = th
        a = mu * (1 - phi)
        e = xc - a - phi * xl
        s2e = float(np.mean(e**2))
    else:
        vx = np.var(xl)
        phi = float(np.cov(xl, xc, bias=True)[0, 1] / vx)
        a = float(xc.mean() - phi * xl.mean())
        e = xc - a - phi * xl
        s2e = float(e @ e / (n - 2))
        mu = a / (1 - phi) if phi != 1 else np.nan
    se_phi = math.sqrt(s2e / float(np.sum((xl - xl.mean()) ** 2)))
    out = dict(n=n, phi=float(phi), phi_se=se_phi, mu=float(mu), kappa=np.nan, sigma=np.nan, sd_eq=np.nan,
               half_life=np.nan, half_life_lo=np.nan, half_life_hi=np.nan, resid_sd=math.sqrt(s2e))
    if 0.0 < phi < 1.0:
        kappa = -math.log(phi) / dt
        out.update(kappa=kappa, sigma=math.sqrt(s2e * 2 * kappa / (1 - phi**2)),
                   half_life=LN2 / kappa)
        out["sd_eq"] = out["sigma"] / math.sqrt(2 * kappa)
        hl = lambda p: (-LN2 * dt / math.log(p)) if 0 < p < 1 else (math.inf if p >= 1 else np.nan)
        out["half_life_lo"], out["half_life_hi"] = hl(phi - 1.96 * se_phi), hl(phi + 1.96 * se_phi)
    return out


def rolling_ou(x: pd.Series, window: int = 250, dt: float = 1.0) -> pd.DataFrame:
    """Rolling AR(1): phi = cov(x_t, x_{t-1}) / var(x_{t-1}); half-life NaN when phi outside (0,1)."""
    x = pd.Series(x, dtype=float)
    phi = x.rolling(window).cov(x.shift(1)) / x.shift(1).rolling(window).var()
    with np.errstate(all="ignore"):
        hl = np.where((phi > 0) & (phi < 1), -LN2 * dt / np.log(phi.where((phi > 0) & (phi < 1))), np.nan)
    return pd.DataFrame({"phi": phi, "half_life": hl}, index=x.index)


# ------------------------------------------------------------------ tests
def _ols_t(y, X, j):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    s2 = e @ e / (len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    return beta[j], beta[j] / math.sqrt(cov[j, j]), e, X.shape[1]


def _adf_reg(x, p, start):
    d = np.diff(x)
    idx = np.arange(start, len(d))
    X = [np.ones(len(idx)), x[idx]] + [d[idx - k] for k in range(1, p + 1)]
    return d[idx], np.column_stack(X)


def adf(x, lags: int | None = None, maxlag: int | None = None) -> dict:
    """ADF with constant: dx_t = a + b x_{t-1} + sum g_k dx_{t-k}. H0 b=0 (unit root). Lags by AIC (common sample) unless given.
    Critical values are asymptotic (1%/5%/10% = -3.43/-2.86/-2.57); p-value from statsmodels MacKinnon if installed."""
    x = _arr(x)
    n = len(x)
    if lags is None:
        maxlag = maxlag if maxlag is not None else int(math.ceil(12 * (n / 100.0) ** 0.25))
        maxlag = min(maxlag, n // 4)
        aic = {}
        for p in range(maxlag + 1):
            y, X = _adf_reg(x, p, maxlag)
            _, _, e, k = _ols_t(y, X, 1)
            aic[p] = len(y) * math.log(e @ e / len(y)) + 2 * k
        lags = min(aic, key=aic.get)
    y, X = _adf_reg(x, lags, lags)
    b, t, _, _ = _ols_t(y, X, 1)
    pv = float(_mackinnonp(t, regression="c", N=1)) if _mackinnonp else np.nan
    return dict(stat=float(t), pvalue=pv, lags=int(lags), rho=float(1 + b), reject_5pct=bool(t < ADF_CRIT["5%"]),
                crit=ADF_CRIT)


def kpss(x, nlags: int | None = None) -> dict:
    """KPSS level-stationarity (H0 stationary). Newey-West long-run variance, lag default int(12 (n/100)^0.25)."""
    x = _arr(x)
    n = len(x)
    nlags = int(12 * (n / 100.0) ** 0.25) if nlags is None else nlags
    e = x - x.mean()
    s2 = e @ e / n
    for j in range(1, nlags + 1):
        s2 += 2 * (1 - j / (nlags + 1)) * (e[j:] @ e[:-j]) / n
    stat = float(np.sum(np.cumsum(e) ** 2) / (n**2 * s2))
    return dict(stat=stat, nlags=nlags, reject_stationarity_5pct=bool(stat > KPSS_CRIT["5%"]), crit=KPSS_CRIT)


def hurst_std(x, min_lag: int = 2, max_lag: int | None = None) -> float:
    """Hurst exponent from slope of log std(x_{t+l}-x_t) vs log l (levels). 0.5 = random walk, <0.5 mean reverting.
    (A deterministic trend cancels in differences only if detrended; a pure trend reads ~1.)"""
    x = _arr(x)
    max_lag = max_lag or min(100, len(x) // 4)
    lags = np.unique(np.round(np.logspace(math.log10(min_lag), math.log10(max_lag), 20)).astype(int)) if max_lag > min_lag else []
    if len(lags) < 3:  # too short for a scaling fit
        return float("nan")
    sd = np.array([np.std(x[l:] - x[:-l]) for l in lags])
    return float(np.polyfit(np.log(lags), np.log(sd), 1)[0])


def variance_ratio(x, q: int) -> dict:
    """Lo-MacKinlay VR(q) on first differences of levels with heteroskedasticity-robust z*. VR<1: mean reversion."""
    dx = np.diff(_arr(x))
    T = len(dx)
    m = dx.mean()
    d0 = dx - m
    s1 = d0 @ d0
    c = np.cumsum(np.insert(dx, 0, 0.0))
    dq = c[q:] - c[:-q] - q * m
    vr = float((dq @ dq / (len(dq) * q)) / (s1 / T))
    theta = 0.0
    for j in range(1, q):
        delta = np.sum(d0[j:] ** 2 * d0[:-j] ** 2) / s1**2 * T
        theta += (2 * (q - j) / q) ** 2 * delta
    z = (vr - 1) * math.sqrt(T) / math.sqrt(theta) if theta > 0 else np.nan
    return dict(q=q, vr=vr, z_robust=float(z))


# ------------------------------------------------------------------ ex-ante path and Sharpe
def ou_expected_path(x0, kappa, mu, sigma, horizons) -> pd.DataFrame:
    h = np.asarray(horizons, dtype=float)
    mean = mu + (x0 - mu) * np.exp(-kappa * h)
    sd = sigma * np.sqrt((1 - np.exp(-2 * kappa * h)) / (2 * kappa))
    return pd.DataFrame({"h": h, "mean": mean, "sd": sd, "lo2": mean - 2 * sd, "hi2": mean + 2 * sd})


def ou_sharpe(x0, kappa, mu, sigma, h, periods_per_year: float = 252.0) -> dict:
    """Ex-ante Sharpe of the convergence trade over horizon h (obs): |E[x_h]-x0| / sd(x_h), and annualised by sqrt(ppy/h).
    Falls with h for h beyond ~half-life; compare horizons, do not read the headline number as a forecast."""
    p = ou_expected_path(x0, kappa, mu, sigma, [h]).iloc[0]
    raw = abs(p["mean"] - x0) / p["sd"]
    return dict(h=h, exp_move=float(p["mean"] - x0), sd=float(p["sd"]), sharpe=float(raw),
                sharpe_ann=float(raw * math.sqrt(periods_per_year / h)))


# ------------------------------------------------------------------ optimal bands
def ou_cycle_time(a: float) -> float:
    """E[first passage -a -> +a] of the standardised OU dX=-X dt+sqrt2 dW, in units of 1/kappa: pi*erfi(a/sqrt2)."""
    return math.pi * float(special.erfi(a / math.sqrt(2)))


def optimal_symmetric_band(kappa, sigma, cost, mu=0.0) -> dict:
    """Bertram-type symmetric band: enter at mu -/+ a*sd_eq, reverse at mu +/- a*sd_eq. Maximise (a - c/2)/T(a)
    where c = round-trip cost / sd_eq. cost in series units (bp). Zero cost -> a*=0 (degenerate: trade continuously)."""
    sd_eq = sigma / math.sqrt(2 * kappa)
    c = cost / sd_eq
    ce = c / 2
    if c <= 0:
        return dict(a=0.0, entry_dist=0.0, sd_eq=sd_eq, note="zero cost: degenerate optimum")
    foc = lambda a: ou_cycle_time(a) - (a - ce) * math.sqrt(2 * math.pi) * math.exp(a * a / 2)
    a = optimize.brentq(foc, ce + 1e-9, 12.0)
    T = ou_cycle_time(a) / kappa
    return dict(a=a, entry_dist=a * sd_eq, entry_low=mu - a * sd_eq, entry_high=mu + a * sd_eq, sd_eq=sd_eq,
                hold_obs=T, profit_per_flip=2 * a * sd_eq - cost, rate_per_obs=(2 * a * sd_eq - cost) / T)


def _lf_int(x, theta, mu, sigma, r, sign, power):
    """int_0^inf u^(r/mu - 1 + power) exp(sign*c (x-theta) u - u^2/2) du, c = sqrt(2 mu/sigma^2)."""
    c = math.sqrt(2 * mu / sigma**2)
    s = sign * c * (x - theta)
    ex = r / mu - 1 + power
    f = lambda u: u**ex * math.exp(s * u - u * u / 2)
    m = max(s, 0.0)
    hi = m + 12.0
    pts = [m] if m > 0 else None
    return integrate.quad(f, 0, hi, points=pts, limit=200)[0]


def leung_li_levels(theta, mu, sigma, r, c_s, c_b=None) -> dict:
    """Leung-Li (2016) one-shot OU long-the-spread problem: exit b* solves F(b)=(b-c_s)F'(b);
    entry d* solves G(d)(V'(d)-1)=G'(d)(V(d)-d-c_b). mu = speed, theta = mean, sigma = vol, r = discount rate (same
    time unit), costs in series units. For the short side apply to -x. d*=nan => never enter."""
    c_b = c_s if c_b is None else c_b
    c = math.sqrt(2 * mu / sigma**2)
    F = lambda x: _lf_int(x, theta, mu, sigma, r, +1, 0)
    dF = lambda x: c * _lf_int(x, theta, mu, sigma, r, +1, 1)
    G = lambda x: _lf_int(x, theta, mu, sigma, r, -1, 0)
    dG = lambda x: -c * _lf_int(x, theta, mu, sigma, r, -1, 1)
    sd = sigma / math.sqrt(2 * mu)
    Lstar = (mu * theta + r * c_s) / (mu + r)
    h = lambda b: F(b) - (b - c_s) * dF(b)
    lo = max(Lstar, c_s) + 1e-9
    hi = max(lo, theta) + sd
    while h(hi) > 0:
        hi += sd
        if hi > theta + 50 * sd:
            raise RuntimeError("no exit level found")
    b = optimize.brentq(h, lo, hi) if h(lo) > 0 else lo
    V = lambda x: (b - c_s) * F(x) / F(b)
    dV = lambda x: (b - c_s) * dF(x) / F(b)
    k = lambda d: G(d) * (dV(d) - 1) - dG(d) * (V(d) - d - c_b)
    grid = np.linspace(b - 1e-6, theta - 8 * sd, 200)
    kv = [k(d) for d in grid]
    d = np.nan
    for i in range(len(grid) - 1):
        if kv[i] * kv[i + 1] < 0:
            d = optimize.brentq(k, grid[i + 1], grid[i])
            break
    return dict(b=b, d=d, L_star=Lstar, sd_eq=sd, first_passage_exit=lambda x: F(x) / F(b))


# ------------------------------------------------------------------ multivariate OU
def fit_mvou(X, dt: float = 1.0) -> dict:
    """VAR(1) -> MVOU dX = -Theta (X - mu) dt + S dB. A = exp(-Theta dt) from OLS with constant; Theta = -logm(A)/dt.
    Returns Theta, mu, S S' (via the Kronecker-sum relation), eigenvalues of Theta, half-lives (ln2/Re eig), stable flag."""
    X = np.asarray(X, dtype=float)
    Y, Z = X[1:], np.column_stack([np.ones(len(X) - 1), X[:-1]])
    B, *_ = np.linalg.lstsq(Z, Y, rcond=None)
    c, A = B[0], B[1:].T
    E = Y - Z @ B
    m = X.shape[1]
    Sig_dt = E.T @ E / (len(E) - m - 1)
    mu = np.linalg.solve(np.eye(m) - A, c)
    Theta = -np.real(logm(A)) / dt
    ev = np.linalg.eigvals(Theta)
    I = np.eye(m)
    K = np.kron(I, Theta) + np.kron(Theta, I)  # vec(Theta S + S Theta') for column-stacked vec
    SS = np.linalg.solve(np.eye(m * m) - expm(-K * dt), K @ Sig_dt.reshape(-1, order="F"))
    SS = SS.reshape(m, m, order="F")
    return dict(Theta=Theta, mu=mu, SS=(SS + SS.T) / 2, A=A, eigvals=ev, half_lives=LN2 / np.real(ev),
                stable=bool(np.all(np.real(ev) > 0)))


def spread_is_ou(Theta, w) -> float:
    """Relative residual of w'Theta = lambda w' (0 = w is a left eigenvector, so w'X is a univariate OU)."""
    w = np.asarray(w, dtype=float)
    v = w @ Theta
    lam = (v @ w) / (w @ w)
    return float(np.linalg.norm(v - lam * w) / max(np.linalg.norm(v), 1e-300))


# ------------------------------------------------------------------ one-call report
def diagnose(x, dt: float = 1.0, cost: float | None = None, ppy: float = 252.0) -> dict:
    """Fit, test and (optionally) band a residual series. Verdict thresholds are defaults, see SKILL.md.
    dt = time per observation (half-life, kappa in those units; gates and horizons below are in observations).
    z_now uses full-sample mu and sd_eq (a live read, not a back-test signal: look-ahead if used historically)."""
    x = _arr(x)
    f = fit_ou(x, dt)
    out = dict(n=len(x), fit=f, adf=adf(x), kpss=kpss(x), hurst=hurst_std(x),
               vr={q: variance_ratio(x, q) for q in (2, 5, 10)})
    hl = f["half_life"]
    out["z_now"] = float((x[-1] - f["mu"]) / f["sd_eq"]) if f["sd_eq"] == f["sd_eq"] else np.nan
    hard, soft = [], []  # hard = SKILL gate failures (refuse OU timing); soft = flags (one = WEAK, two or more = REJECT)
    if not (hl == hl):
        hard.append("AR(1) phi outside (0,1): not mean-reverting")
    else:
        hl_obs = hl / dt
        if hl_obs < 2:
            hard.append("half-life < 2 obs: faster than the sampling can trade")
        if len(x) < 5 * hl_obs:
            hard.append("sample < 5 half-lives")
        if f["half_life_hi"] == math.inf:
            hard.append("95% CI for half-life is unbounded (phi CI reaches 1)")
        if hl_obs > 90:
            hard.append("half-life > 90 obs: random-walk-like over a tradable horizon")
        elif hl_obs > 40:
            out["note"] = "half-life 40-90 obs: carry-dominated, trade only with the breakeven rule"
    if not out["adf"]["reject_5pct"]:
        soft.append("ADF does not reject unit root at 5%")
    if out["kpss"]["reject_stationarity_5pct"]:
        soft.append("KPSS rejects stationarity at 5%")
    if out["hurst"] >= 0.5:
        soft.append("Hurst >= 0.5")
    reasons = hard + soft
    out["verdict"] = "REJECT" if (hard or len(soft) >= 2) else ("WEAK" if soft else "OK")
    out["reasons"] = reasons
    if f["kappa"] == f["kappa"]:
        out["sharpe_by_h"] = [dict(ou_sharpe(x[-1], f["kappa"], f["mu"], f["sigma"], h * dt, ppy * dt), h=h) for h in (5, 10, 20)]
        if cost is not None:
            out["band"] = optimal_symmetric_band(f["kappa"], f["sigma"], cost, f["mu"])
    return out


# ------------------------------------------------------------------ simulation helpers + selftest
def simulate_ou(n, kappa, mu, sigma, x0=None, seed=0, dt=1.0):
    rng = np.random.default_rng(seed)
    phi = math.exp(-kappa * dt)
    s = sigma * math.sqrt((1 - phi**2) / (2 * kappa))
    x = np.empty(n)
    x[0] = mu if x0 is None else x0
    e = rng.standard_normal(n) * s
    for i in range(1, n):
        x[i] = mu + phi * (x[i - 1] - mu) + e[i]
    return x


def _selftest() -> None:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (" " + info if info else ""))
        ok &= bool(cond)

    kappa, mu, sigma = 0.05, -3.0, 1.0  # half-life 13.86 obs
    x = simulate_ou(40000, kappa, mu, sigma, seed=1)
    f = fit_ou(x)
    check("fit_ou recovers kappa", abs(f["kappa"] / kappa - 1) < 0.08, f"{f['kappa']:.4f} vs {kappa}")
    check("fit_ou recovers mu", abs(f["mu"] - mu) < 0.3, f"{f['mu']:.3f}")
    check("fit_ou recovers sigma", abs(f["sigma"] / sigma - 1) < 0.012, f"{f['sigma']:.3f}")
    check("half-life = ln2/kappa", abs(f["half_life"] - LN2 / f["kappa"]) < 1e-9)
    check("CI brackets truth", f["half_life_lo"] < LN2 / kappa < f["half_life_hi"])
    fm = fit_ou(x, method="mle")
    check("closed-form MLE == OLS (kappa, mu)", abs(fm["kappa"] - f["kappa"]) < 1e-6 * f["kappa"] + 1e-9
          and abs(fm["mu"] - f["mu"]) < 1e-6 * abs(f["mu"]) + 1e-8, f"{fm['kappa']:.6f} vs {f['kappa']:.6f}")
    ff = fit_ou(simulate_ou(40000, 0.5, 0.0, 2.0, seed=3))
    check("fast OU (kappa .5, sigma 2) recovered", abs(ff["kappa"] / 0.5 - 1) < 0.05 and abs(ff["sigma"] / 2 - 1) < 0.02,
          f"{ff['kappa']:.3f} {ff['sigma']:.3f}")
    rw = np.cumsum(np.random.default_rng(2).standard_normal(5000))
    check("random walk: fit_ou half-life is NaN or very long", not (fit_ou(rw)["half_life"] < 150))
    check("ADF rejects on OU", adf(x[:3000])["reject_5pct"], f"t={adf(x[:3000])['stat']:.2f}")
    check("ADF keeps unit root on RW", not adf(rw)["reject_5pct"], f"t={adf(rw)['stat']:.2f}")
    check("KPSS rejects on RW", kpss(rw)["reject_stationarity_5pct"], f"{kpss(rw)['stat']:.2f}")
    xf = simulate_ou(3000, 0.4, 0.0, 1.0, seed=11)
    check("KPSS accepts fast OU (slow OU over-rejects: size distortion)", not kpss(xf)["reject_stationarity_5pct"], f"{kpss(xf)['stat']:.2f}")
    h_rw, h_ou = hurst_std(rw), hurst_std(x)
    check("Hurst ~0.5 on RW, <0.35 on OU", abs(h_rw - 0.5) < 0.08 and h_ou < 0.35, f"{h_rw:.3f} / {h_ou:.3f}")
    v_rw, v_ou = variance_ratio(rw, 10), variance_ratio(x, 10)
    phi_ = math.exp(-kappa)
    vr_true = (1 - phi_**10) / (10 * (1 - phi_))  # analytic VR(q) of an AR(1) in levels
    check("VR(10) ~1 on RW; == (1-phi^q)/(q(1-phi)) on OU; z* < -3",
          abs(v_rw["vr"] - 1) < 0.25 and abs(v_ou["vr"] - vr_true) < 0.03 and v_ou["z_robust"] < -3,
          f"{v_rw['vr']:.2f} / {v_ou['vr']:.3f} vs {vr_true:.3f}")
    try:
        from statsmodels.tsa.stattools import adfuller, kpss as sm_kpss
        a_sm = adfuller(x[:3000], maxlag=2, regression="c", autolag=None)[0]
        check("ADF stat == statsmodels (fixed lags)", abs(adf(x[:3000], lags=2)["stat"] - a_sm) < 1e-6)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            k_sm = sm_kpss(rw, regression="c", nlags=int(12 * (len(rw) / 100) ** 0.25))[0]
        check("KPSS stat == statsmodels", abs(kpss(rw)["stat"] - k_sm) < 1e-6)
    except ImportError:
        print("SKIP statsmodels cross-checks (not installed)")
    # analytic OU moments
    p = ou_expected_path(10.0, 0.1, 0.0, 2.0, [LN2 / 0.1]).iloc[0]
    check("expected path: half the gap at the half-life", abs(p["mean"] - 5.0) < 1e-9)
    rs, h_ = np.random.default_rng(9), 11  # finite-horizon mean and sd vs simulated paths from x0 (kappa .1, sigma 2, mu 0)
    xs_ = np.full(200000, 10.0)
    for _ in range(h_):
        xs_ = math.exp(-0.1) * xs_ + 2.0 * math.sqrt((1 - math.exp(-0.2)) / 0.2) * rs.standard_normal(len(xs_))
    p11 = ou_expected_path(10.0, 0.1, 0.0, 2.0, [h_]).iloc[0]
    check("expected path mean and sd at h=11 == simulation", abs(xs_.mean() - p11["mean"]) < 0.02 and abs(xs_.std() / p11["sd"] - 1) < 0.01,
          f"{xs_.mean():.3f}/{xs_.std():.3f} vs {p11['mean']:.3f}/{p11['sd']:.3f}")
    check("sd(h->inf) -> sigma/sqrt(2k)", abs(ou_expected_path(0, 0.1, 0, 2.0, [1e4]).iloc[0]["sd"] - 2 / math.sqrt(0.2)) < 1e-9)
    # optimal band: T(a) vs quadrature, FOC, monotone in cost
    a_ = 1.3
    quad = math.sqrt(2 * math.pi) * integrate.quad(lambda y: math.exp(y * y / 2), 0, a_)[0]
    check("cycle time pi*erfi(a/sqrt2) == quadrature", abs(ou_cycle_time(a_) - quad) < 1e-9)
    b0 = optimal_symmetric_band(0.1, 1.0, 0.5)
    b1 = optimal_symmetric_band(0.1, 1.0, 1.0)
    check("band widens with cost; zero cost -> 0", b1["a"] > b0["a"] and optimal_symmetric_band(0.1, 1.0, 0.0)["a"] == 0.0,
          f"a={b0['a']:.3f},{b1['a']:.3f}")
    grid = np.linspace(0.05, 5, 4000)
    c_ = (0.5 / b0["sd_eq"]) / 2
    best = grid[np.argmax([(g - c_) / ou_cycle_time(g) for g in grid])]
    check("band optimum == brute-force grid", abs(best - b0["a"]) < 0.01, f"{b0['a']:.3f} vs {best:.3f}")
    rng = np.random.default_rng(5)
    dt_, N = 0.005, 4000
    a_t = 1.0 - 0.5826 * math.sqrt(2 * dt_)  # Broadie-Glasserman-Kou barrier shift for discrete monitoring
    xs, t, alive = np.full(N, -a_t), np.zeros(N), np.ones(N, bool)
    ph, sd_ = math.exp(-dt_), math.sqrt(1 - math.exp(-2 * dt_))
    for _ in range(6000):
        if not alive.any():
            break
        xs[alive] = ph * xs[alive] + sd_ * rng.standard_normal(alive.sum())
        t[alive] += dt_
        alive &= xs < a_t
    check("MC first passage -1 -> +1 == pi*erfi(1/sqrt2)", abs(t.mean() / ou_cycle_time(1.0) - 1) < 0.06,
          f"{t.mean():.3f} vs {ou_cycle_time(1.0):.3f}")
    # Leung-Li: F(x)/F(b) is E exp(-r tau); b*, d* satisfy their equations and match published-comparison values
    ll = leung_li_levels(0.0, 8.0, 0.3, 0.05, 0.02)
    check("Leung-Li exit b* = 0.198 (mu=8,sigma=.3,r=.05,c=.02)", abs(ll["b"] - 0.198) < 0.002, f"{ll['b']:.4f}")
    check("Leung-Li b* >= L* = (mu theta + r c_s)/(mu + r)", ll["b"] >= ll["L_star"] and abs(ll["L_star"] - 0.05 * 0.02 / 8.05) < 1e-12)
    check("Leung-Li entry d* below mean, roughly symmetric", -0.21 < ll["d"] < -0.15, f"{ll['d']:.4f}")
    ll2 = leung_li_levels(0.0, 8.0, 0.1, 0.05, 0.02)
    ll3 = leung_li_levels(0.0, 8.0, 0.5, 0.05, 0.02)
    check("b* rises with sigma (0.068, 0.198, 0.329)", abs(ll2["b"] - 0.068) < 0.002 and abs(ll3["b"] - 0.329) < 0.003,
          f"{ll2['b']:.3f},{ll3['b']:.3f}")
    bb = 0.2
    dts = 0.004
    barr = bb - 0.5826 * 0.3 * math.sqrt(dts)
    ph, sdn = math.exp(-8 * dts), 0.3 * math.sqrt((1 - math.exp(-16 * dts)) / 16)
    xs, tt, alive = np.zeros(4000), np.zeros(4000), np.ones(4000, bool)
    while alive.any():  # no censoring: first passage here takes ~4 years
        xs[alive] = ph * xs[alive] + sdn * rng.standard_normal(alive.sum())
        tt[alive] += dts
        alive &= xs < barr
    mc = np.exp(-0.05 * tt).mean()
    check("Leung-Li F(x)/F(b) == MC E[exp(-r tau)]", abs(_lf_int(0, 0, 8, .3, .05, 1, 0) / _lf_int(bb, 0, 8, .3, .05, 1, 0) - mc) < 0.012, f"{mc:.4f}")
    # MVOU
    Theta = np.array([[0.20, 0.0], [-0.15, 0.05]])
    Aa = expm(-Theta)
    SS = np.array([[1.0, 0.2], [0.2, 0.5]])
    I2 = np.eye(4)
    K = np.kron(np.eye(2), Theta) + np.kron(Theta, np.eye(2))
    Sg = np.linalg.solve(K, (I2 - expm(-K)) @ SS.reshape(-1, order="F")).reshape(2, 2, order="F")
    L = np.linalg.cholesky(Sg)
    Xm = np.zeros((60000, 2))
    Xm[0] = [1.0, -1.0]
    eps = np.random.default_rng(7).standard_normal((60000, 2)) @ L.T
    mu_m = np.array([2.0, -1.0])
    for i in range(1, len(Xm)):
        Xm[i] = mu_m + Aa @ (Xm[i - 1] - mu_m) + eps[i]
    fm = fit_mvou(Xm)
    check("MVOU Theta recovered", np.max(np.abs(fm["Theta"] - Theta)) < 0.01, f"max err {np.max(np.abs(fm['Theta'] - Theta)):.4f}")
    check("MVOU mu recovered", np.max(np.abs(fm["mu"] - mu_m)) < 0.5)
    check("MVOU S S' recovered", np.max(np.abs(fm["SS"] - SS)) < 0.1, f"{np.round(fm['SS'], 3).tolist()}")
    # left eigenvector of Theta for eigenvalue 0.05: solve w'Theta = 0.05 w'
    vals, vecs = np.linalg.eig(Theta.T)
    wl = np.real(vecs[:, np.argmin(np.abs(vals - 0.05))])
    check("spread_is_ou: left eigenvector -> 0, generic weights -> >0", spread_is_ou(Theta, wl) < 1e-9
          and spread_is_ou(Theta, [1.0, 0.5]) > 0.05)
    rep = diagnose(x[:2000], cost=0.5)
    check("diagnose OK on clean OU", rep["verdict"] in ("OK", "WEAK"), rep["verdict"] + " " + "; ".join(rep["reasons"]))
    check("diagnose REJECT on random walk", diagnose(rw)["verdict"] == "REJECT")
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    if not ok:
        sys.exit(1)


# ------------------------------------------------------------------ CLI
def _load(path, value_col, date_col, group_col):
    df = pd.read_parquet(path) if str(path).lower().endswith((".parquet", ".pq")) else pd.read_csv(path)
    if date_col in df:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
    groups = df.groupby(group_col) if group_col and group_col in df else [("all", df)]
    return groups


def _fmt(rep: dict, name: str) -> str:
    f = rep["fit"]
    lines = [f"== {name}: n={rep['n']} verdict={rep['verdict']}",
             f"   mu={f['mu']:.3f} sigma={f['sigma']:.3f} sd_eq={f['sd_eq']:.3f} kappa={f['kappa']:.4f} "
             f"half_life={f['half_life']:.1f} [{f['half_life_lo']:.1f}, {f['half_life_hi']:.1f}] obs; z_now={rep['z_now']:.2f}",
             f"   ADF t={rep['adf']['stat']:.2f} p={rep['adf']['pvalue']:.3f} lags={rep['adf']['lags']} | "
             f"KPSS={rep['kpss']['stat']:.3f} | Hurst={rep['hurst']:.2f} | "
             + " ".join(f"VR({q})={v['vr']:.2f}(z*={v['z_robust']:.1f})" for q, v in rep["vr"].items())]
    for r in rep["reasons"]:
        lines.append("   - " + r)
    for s in rep.get("sharpe_by_h", []):
        lines.append(f"   h={s['h']:>3}: E[move]={s['exp_move']:+.2f} sd={s['sd']:.2f} sharpe={s['sharpe']:.2f} ann={s['sharpe_ann']:.1f}")
    if "band" in rep:
        b = rep["band"]
        lines.append(f"   band: enter at +/-{b['entry_dist']:.2f} from mu (a={b['a']:.2f} sd_eq), hold~{b.get('hold_obs', float('nan')):.1f} obs")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("diagnose")
    d.add_argument("path")
    d.add_argument("--value-col", default="value")
    d.add_argument("--date-col", default="date")
    d.add_argument("--group-col", default=None)
    d.add_argument("--dt", type=float, default=1.0)
    d.add_argument("--cost-bp", type=float, default=None)
    b = sub.add_parser("bands")
    b.add_argument("--kappa", type=float, required=True)
    b.add_argument("--sigma", type=float, required=True)
    b.add_argument("--cost", type=float, required=True)
    b.add_argument("--mu", type=float, default=0.0)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "diagnose":
        for name, g in _load(a.path, a.value_col, a.date_col, a.group_col):
            print(_fmt(diagnose(g[a.value_col].to_numpy(), a.dt, a.cost_bp), str(name)))
    elif a.cmd == "bands":
        print(optimal_symmetric_band(a.kappa, a.sigma, a.cost, a.mu))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
