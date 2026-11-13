#!/usr/bin/env python3
"""Bayesian shrinkage toolkit for RV work (numpy/pandas/scipy only).

Functions
  normal_normal        conjugate update, known noise variance
  eb_shrink            empirical-Bayes (moment) shrinkage of noisy group estimates to the grand mean
  hier_normal          fully Bayesian hierarchical normal model, grid over tau (Gelman BDA 5.4)
  jorion_shrink        Jorion mean shrinkage toward the vol-weighted grand mean
  shrink_ic            Grinold-Kahn style shrinkage of an estimated IC / signal coefficient
  bayes_linreg         Bayesian linear regression, optional evidence (type-II ML) for alpha, beta
  black_litterman      Black-Litterman posterior mean / covariance
  infer_unobserved     conditional (Bayes/MLE) inference of an unobserved market's move

CLI
  python shrinkage.py hier --csv FILE --id-col id --est-col est --se-col se [--prior uniform|halfcauchy]
  python shrinkage.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ----------------------------------------------------------------- conjugate
def normal_normal(mu0, tau0, ybar, sigma, n=1):
    """Posterior of theta ~ N(mu0, tau0^2) given n iid obs with mean ybar, noise sd sigma.

    Returns (post_mean, post_sd, weight_on_data). Posterior precision = prior + n/sigma^2.
    """
    p0, pd_ = 1.0 / tau0**2, n / sigma**2
    mean = (p0 * mu0 + pd_ * ybar) / (p0 + pd_)
    return mean, (p0 + pd_) ** -0.5, pd_ / (p0 + pd_)


# ------------------------------------------------------------ empirical Bayes
def eb_shrink(xbar, se):
    """Moment empirical-Bayes shrinkage (Murphy 5.6): tau2 = max(0, var(xbar) - mean(se^2)).

    Returns DataFrame: est, se, post_mean, post_sd, B (shrinkage weight on the grand mean). Note tau2 = 0
    (all B = 1) is a boundary estimate, not proof of no dispersion: prefer hier_normal when J is small.
    """
    x, s = np.asarray(xbar, float), np.asarray(se, float)
    if len(x) < 2 or not (np.isfinite(x).all() and np.isfinite(s).all() and (s > 0).all()):
        raise ValueError("need >= 2 finite estimates and finite se > 0 (drop NaN rows first)")
    mu = x.mean()
    tau2 = max(0.0, x.var(ddof=1) - np.mean(s**2))
    B = s**2 / (s**2 + tau2)
    vmu = (s**2 + tau2).sum() / len(x) ** 2                       # Var(mu_hat) for the equal-weight grand mean
    return pd.DataFrame({"est": x, "se": s, "post_mean": B * mu + (1 - B) * x,
                         "post_sd": np.sqrt((1 - B) * s**2 + B**2 * vmu), "B": B})


def hier_normal(ybar, se, prior="uniform", A=25.0, tau_max=None, n_grid=4000):
    """Hierarchical normal model ybar_j ~ N(theta_j, se_j^2), theta_j ~ N(mu, tau^2), flat prior on mu.

    Prior on tau: 'uniform' (default; needs J >= 3) or 'halfcauchy' scale A (small J). Grid over tau,
    mu integrated analytically. Returns dict(tau, post_tau, theta_mean, theta_sd, mu_mean, mu_sd).
    """
    y, s = np.asarray(ybar, float), np.asarray(se, float)
    if len(y) < 2 or not (np.isfinite(y).all() and np.isfinite(s).all() and (s > 0).all()):
        raise ValueError("need >= 2 finite estimates and finite se > 0 (drop NaN rows first)")
    if prior == "uniform" and len(y) < 3:
        raise ValueError("uniform prior on tau is improper for J < 3: use prior='halfcauchy'")
    tau_max = tau_max or 10 * max(y.std(ddof=1), s.max())
    tau = np.linspace(1e-6, tau_max, n_grid)
    v = s[None, :] ** 2 + tau[:, None] ** 2                       # (G, J)
    w = 1.0 / v
    Vmu = 1.0 / w.sum(1)
    muhat = (w * y).sum(1) * Vmu
    logp = 0.5 * np.log(Vmu) - 0.5 * np.log(v).sum(1) - 0.5 * (w * (y - muhat[:, None]) ** 2).sum(1)
    if prior == "halfcauchy":
        logp += -np.log1p((tau / A) ** 2)
    elif prior != "uniform":
        raise ValueError("prior must be 'uniform' or 'halfcauchy'")
    p = np.exp(logp - logp.max())
    p /= p.sum()
    B = s[None, :] ** 2 / v                                        # weight on mu given tau
    m = (1 - B) * y + B * muhat[:, None]
    var = (1 - B) * s**2 + B**2 * Vmu[:, None]                    # BDA 5.17 integrating mu out
    tm = (p[:, None] * m).sum(0)
    tv = (p[:, None] * (var + m**2)).sum(0) - tm**2
    mm = (p * muhat).sum()
    return {"tau": tau, "post_tau": p, "theta_mean": tm, "theta_sd": np.sqrt(tv), "mu_mean": mm,
            "mu_sd": np.sqrt((p * (Vmu + muhat**2)).sum() - mm**2)}


# --------------------------------------------------------- mean / IC shrinkage
def jorion_shrink(mu_hat, Sigma, T):
    """Jorion (1986): shrink sample means toward the vol-weighted grand mean. Returns (mu_sh, rho, target)."""
    mu_hat, Sigma = np.asarray(mu_hat, float), np.asarray(Sigma, float)
    N = len(mu_hat)
    Si = np.linalg.inv(Sigma)
    one = np.ones(N)
    tgt = (one @ Si @ mu_hat) / (one @ Si @ one)
    d = mu_hat - tgt
    rho = (N + 2) / ((N + 2) + T * d @ Si @ d)
    return (1 - rho) * mu_hat + rho * tgt * one, rho, tgt


def shrink_ic(ic_hat, T, prior_sd=None):
    """Posterior-mean IC: w = T*s^2/(1+T*s^2), s = prior sd of true IC (default |ic_hat|, which reproduces
    the Grinold-Kahn Table 11.4 factors). Sampling variance of an IC estimate is about 1/T. Returns (ic_post, w)."""
    s = abs(ic_hat) if prior_sd is None else prior_sd
    w = T * s**2 / (1 + T * s**2)
    return ic_hat * w, w


# ------------------------------------------------------- Bayesian regression
def bayes_linreg(X, y, alpha=1.0, beta=1.0, m0=None, evidence=False, n_iter=200):
    """Bayesian linear regression, prior w ~ N(m0, I/alpha), noise precision beta (Bishop 3.3).

    evidence=True iterates alpha, beta by type-II ML (Bishop 3.5). Returns dict(mN, SN, alpha, beta,
    gamma, pred_var(Xnew)). No intercept: standardise X and centre y first. MAP equals ridge with lambda = alpha/beta.
    """
    X, y = np.asarray(X, float), np.asarray(y, float)
    N, M = X.shape
    m0 = np.zeros(M) if m0 is None else np.asarray(m0, float)
    ev = np.linalg.eigvalsh(X.T @ X)
    for _ in range(n_iter if evidence else 1):
        SN = np.linalg.inv(alpha * np.eye(M) + beta * X.T @ X)
        mN = SN @ (alpha * m0 + beta * X.T @ y)
        lam = beta * ev
        gamma = float((lam / (alpha + lam)).sum())
        if not evidence:
            break
        a_new = gamma / max(float((mN - m0) @ (mN - m0)), 1e-12)
        b_new = (N - gamma) / float(((y - X @ mN) ** 2).sum())
        done = abs(a_new - alpha) < 1e-9 * alpha and abs(b_new - beta) < 1e-9 * beta
        alpha, beta = a_new, b_new
        if done:
            break
    SN = np.linalg.inv(alpha * np.eye(M) + beta * X.T @ X)
    mN = SN @ (alpha * m0 + beta * X.T @ y)
    return {"mN": mN, "SN": SN, "alpha": alpha, "beta": beta, "gamma": gamma,
            "pred_var": lambda Xn: 1 / beta + np.einsum("ij,jk,ik->i", np.atleast_2d(Xn), SN, np.atleast_2d(Xn))}


# ---------------------------------------------------------- Black-Litterman
def black_litterman(Sigma, pi, P, v, Omega, tau=0.05):
    """mu_BL = pi + tau S P' (tau P S P' + Omega)^-1 (v - P pi); returns (mu_bl, cov_of_mu_bl)."""
    S, pi, P, v, Om = (np.asarray(a, float) for a in (Sigma, pi, P, v, Omega))
    K = tau * S @ P.T @ np.linalg.inv(tau * P @ S @ P.T + Om)
    return pi + K @ (v - P @ pi), tau * S - K @ P @ (tau * S)


# ----------------------------------------------- unobserved-market inference
def infer_unobserved(Q, x, unknown, mu=None):
    """MLE/posterior mean of the moves Y of `unknown` indices given moves x of all other indices, under
    dR ~ N(mu, Q) (Darbyshire 19.6): solve (Qinv)_YY (Y-mu_Y) = -(Qinv)_Yx (x-mu_x). Equals Q_Yx Q_xx^-1 x."""
    Q = np.asarray(Q, float)
    n = len(Q)
    mu = np.zeros(n) if mu is None else np.asarray(mu, float)
    u = list(np.atleast_1d(unknown))
    k = [i for i in range(n) if i not in u]
    P = np.linalg.inv(Q)
    return mu[u] - np.linalg.solve(P[np.ix_(u, u)], P[np.ix_(u, k)] @ (np.asarray(x, float) - mu[k]))


# ------------------------------------------------------------------- selftest
def _selftest() -> int:
    bad = []

    def check(name, ok):
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            bad.append(name)

    # 1 conjugate: prior N(0,1), one obs y=2 sigma=1 -> mean 1, sd sqrt(.5); equals Ross normal-normal formula
    m, sd, w = normal_normal(0, 1, 2, 1)
    check("normal-normal closed form", abs(m - 1) < 1e-12 and abs(sd - 0.5**0.5) < 1e-12 and abs(w - .5) < 1e-12)
    m, sd, w = normal_normal(1, 2, 5, 3)         # prior sd 2, noise sd 3: weight on data = (1/9)/(1/4+1/9) = 4/13
    check("normal-normal unequal variances", abs(w - 4 / 13) < 1e-12 and abs(m - (1 + 4 * 4 / 13)) < 1e-12)
    m, sd, _ = normal_normal(0, 1, 3, 1, n=4)   # n obs: precision 1+4=5, mean 4*3/5
    check("normal-normal n obs", abs(m - 2.4) < 1e-12 and abs(sd - 5**-0.5) < 1e-12)

    # 2 eight schools (BDA 5.5): complete pooling 7.7 +/- 4.1 ; hierarchical shrinks school A from 28 to ~10
    y = np.array([28, 8, -3, 7, -1, 1, 18, 12.])
    s = np.array([15, 10, 16, 11, 9, 11, 10, 18.])
    wt = 1 / s**2
    pooled, pse = (wt * y).sum() / wt.sum(), wt.sum() ** -0.5
    check("eight schools pooled 7.7 +/- 4.1", abs(pooled - 7.7) < 0.05 and abs(pse - 4.1) < 0.05)
    h = hier_normal(y, s)
    check("eight schools: means 11.4 7.9 6.1 7.6 5.1 6.1 10.7 8.5, E[tau] 6.6",
          np.allclose(h["theta_mean"], [11.4, 7.9, 6.1, 7.6, 5.1, 6.1, 10.7, 8.5], atol=0.06)
          and abs((h["tau"] * h["post_tau"]).sum() - 6.6) < 0.1)
    check("eight schools: posterior sd A > 5 (not tau=0 shortcut)", h["theta_sd"][0] > 5)
    check("eight schools: no-pooling and pooled bracket", abs(h["mu_mean"] - 7.9) < 1.0)
    e = eb_shrink(y, s)
    check("EB moment: tau2 truncated -> full pooling (documented boundary)", np.allclose(e["post_mean"], y.mean()))
    for bad_in in (lambda: hier_normal([1.0, np.nan, 2.0], [1, 1, 1]), lambda: hier_normal([1.0, 2.0], [1, 1])):
        try:
            bad_in()
            check("hier_normal rejects NaN / J<3 uniform", False)
        except ValueError:
            check("hier_normal rejects NaN / J<3 uniform", True)
    check("hier_normal J=2 half-Cauchy runs", np.isfinite(hier_normal([1.0, 2.0], [1, 1], prior="halfcauchy")["theta_mean"]).all())

    # 3 simulation with known params: theta~N(0,1), se=1 -> Bayes risk 0.5 vs MLE 1.0; EB must get close to 0.5
    rng = np.random.default_rng(7)
    J, reps = 30, 400
    mse_mle = mse_eb = mse_h = 0.0
    for _ in range(reps):
        th = rng.normal(0, 1, J)
        yy = th + rng.normal(0, 1, J)
        ss = np.ones(J)
        mse_mle += np.mean((yy - th) ** 2)
        mse_eb += np.mean((eb_shrink(yy, ss)["post_mean"] - th) ** 2)
    mse_mle /= reps
    mse_eb /= reps
    check(f"sim: MLE mse ~1.0 ({mse_mle:.3f})", abs(mse_mle - 1) < 0.06)
    check(f"sim: EB mse ~0.5 to 0.6 ({mse_eb:.3f}), well below MLE", 0.45 < mse_eb < 0.62)
    th = rng.normal(0, 1, 12)
    yy = th + rng.normal(0, 1, 12)
    hh = hier_normal(yy, np.ones(12))
    # independent Monte-Carlo of theta_j from the same tau posterior: mean and sd must match the analytic mix
    Jy, Js = np.array([28, 8, -3, 7, -1, 1, 18, 12.]), np.array([15, 10, 16, 11, 9, 11, 10, 18.])
    h8 = hier_normal(Jy, Js)
    tg = rng.choice(len(h8["tau"]), size=200000, p=h8["post_tau"])
    tt = h8["tau"][tg][:, None]
    vv = Js[None, :] ** 2 + tt**2
    mh = ((Jy / vv).sum(1) / (1 / vv).sum(1))[:, None]
    mud = mh + rng.normal(size=(len(tg), 1)) / np.sqrt((1 / vv).sum(1))[:, None]
    Bj = Js**2 / (Js**2 + tt**2)
    thd = (1 - Bj) * Jy + Bj * mud + np.sqrt((1 - Bj)) * Js * rng.normal(size=(len(tg), 8))
    check("hier_normal mean/sd match Monte Carlo",
          np.allclose(thd.mean(0), h8["theta_mean"], atol=0.15) and np.allclose(thd.std(0), h8["theta_sd"], atol=0.15))
    check("hier_normal posterior tau mass sums to 1, tau mean in (0.3, 2)",
          abs(hh["post_tau"].sum() - 1) < 1e-9 and 0.3 < (hh["tau"] * hh["post_tau"]).sum() < 2)

    # 4 Jorion: target == data -> rho = 1 ; huge T -> rho ~ 0 ; shrunk lies between
    Sg = np.array([[1, .5], [.5, 1.]])
    _, rho1, _ = jorion_shrink([1.0, 1.0], Sg, 100)
    _, rho2, _ = jorion_shrink([0.0, 2.0], Sg, 1e6)
    ms, rho3, tg = jorion_shrink([0.0, 2.0], Sg, 24)
    rho_x = jorion_shrink([0.0, 2.0], np.eye(2), 24)[1]          # (N+2)/((N+2)+T*d'd) = 4/(4+48)
    check("Jorion closed form rho = 4/52", abs(rho_x - 4 / 52) < 1e-12)
    check("Jorion limits", abs(rho1 - 1) < 1e-12 and rho2 < 1e-4 and 0 < rho3 < 1 and 0 < ms[0] < ms[1] < 2 and abs(tg - 1) < 1e-9)

    # 5 Grinold Table 11.4 factors
    got = [round(shrink_ic(ic, T)[1], 2) for T in (36, 60, 120, 240) for ic in (0.05, 0.10)]
    check("Grinold Table 11.4 (36:.08/.26 60:.13/.38 120:.23/.55 240:.38/.71)",
          got == [0.08, 0.26, 0.13, 0.38, 0.23, 0.55, 0.38, 0.71] or got == [0.08, 0.26, 0.13, 0.37, 0.23, 0.55, 0.38, 0.71])
    check("Grinold IC 0 -> 0", shrink_ic(0.0, 60)[0] == 0.0)

    # 6 Bayesian regression: equals ridge lambda=alpha/beta; alpha->0 recovers OLS; evidence recovers noise sd
    X = rng.normal(size=(200, 3))
    wtrue = np.array([1.0, -0.5, 0.0])
    yv = X @ wtrue + rng.normal(0, 0.5, 200)
    r = bayes_linreg(X, yv, alpha=4.0, beta=2.0)
    ridge = np.linalg.solve(X.T @ X + 2.0 * np.eye(3), X.T @ yv)
    check("Bayes regression MAP == ridge(lambda=alpha/beta)", np.allclose(r["mN"], ridge))
    ols = np.linalg.lstsq(X, yv, rcond=None)[0]
    check("alpha->0 recovers OLS", np.allclose(bayes_linreg(X, yv, alpha=1e-9, beta=4.0)["mN"], ols, atol=1e-6))
    ev = bayes_linreg(X, yv, evidence=True)
    check(f"evidence: noise sd ~0.5 ({ev['beta'] ** -0.5:.3f}), gamma<=3", abs(ev["beta"] ** -0.5 - 0.5) < 0.08 and ev["gamma"] <= 3.0)
    from scipy.optimize import minimize          # independent check: maximise the Bishop 3.86 log evidence directly

    Xw = X.copy()
    Xw[:, 2] *= 0.05                                # weakly determined direction so gamma < M matters
    ew = bayes_linreg(Xw, yv, evidence=True)
    def neg_ev(q):
        a_, b_ = np.exp(q)
        A = a_ * np.eye(3) + b_ * Xw.T @ Xw
        m = b_ * np.linalg.solve(A, Xw.T @ yv)
        Ew = b_ / 2 * ((yv - Xw @ m) ** 2).sum() + a_ / 2 * m @ m
        return -(1.5 * np.log(a_) + 100 * np.log(b_) - Ew - 0.5 * np.linalg.slogdet(A)[1] - 100 * np.log(2 * np.pi))
    qo = minimize(neg_ev, np.log([1.0, 1.0]), method="Nelder-Mead", options={"xatol": 1e-9, "fatol": 1e-12}).x
    check("evidence loop == direct maximum of log evidence",
          abs(np.log(ew["alpha"]) - qo[0]) < 5e-3 and abs(np.log(ew["beta"]) - qo[1]) < 5e-3)
    check("predictive var > noise var 1/beta", np.all(ev["pred_var"](X[:5]) > 1 / ev["beta"]))

    # 7 Black-Litterman: no views influence at tau->0; both formulas agree; confident absolute view -> view
    S = np.array([[0.04, 0.01], [0.01, 0.09]])
    pi = np.array([0.02, 0.03])
    P, v = np.array([[1.0, 0.0]]), np.array([0.06])
    mu0, _ = black_litterman(S, pi, P, v, [[0.01]], tau=1e-9)
    mu1, C1 = black_litterman(S, pi, P, v, [[1e-12]], tau=0.05)
    Om, tau = np.array([[0.01]]), 0.05
    Ti = np.linalg.inv(tau * S)
    alt = np.linalg.solve(Ti + P.T @ np.linalg.inv(Om) @ P, Ti @ pi + P.T @ np.linalg.inv(Om) @ v)
    mu2, _ = black_litterman(S, pi, P, v, Om, tau)
    check("BL: tau->0 returns equilibrium", np.allclose(mu0, pi, atol=1e-6))
    check("BL: certain view pins asset 1 to 6%", abs(mu1[0] - 0.06) < 1e-6)
    check("BL: precision form == gain form", np.allclose(mu2, alt))

    # 8 Darbyshire Ex 19.6: Y = 1.294bp then -0.710bp
    Q = [[1, .8, .85, .75], [.8, 1, .87, .84], [.85, .87, 1, .82], [.75, .84, .82, 1]]
    y1 = infer_unobserved(Q, [2.0, 1.0, 2.0], [3])[0]
    y2 = infer_unobserved(Q, [0.5, -1.5, 0.0], [3])[0]
    check(f"Darbyshire 19.6 Y=1.294 ({y1:.3f}), -0.710 ({y2:.3f})", abs(y1 - 1.294) < 5e-4 and abs(y2 + 0.710) < 5e-4)
    Qa = np.array(Q)
    check("inference == Q_Yx Q_xx^-1 x", abs(y1 - Qa[3, :3] @ np.linalg.solve(Qa[:3, :3], [2.0, 1.0, 2.0])) < 1e-9)

    print("SELFTEST " + ("FAILED: " + "; ".join(bad) if bad else "PASSED"))
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    h = sub.add_parser("hier", help="hierarchical shrinkage of noisy estimates in a CSV/Parquet file")
    h.add_argument("--csv", required=True)
    h.add_argument("--id-col", default="id")
    h.add_argument("--est-col", default="est")
    h.add_argument("--se-col", default="se")
    h.add_argument("--prior", default="uniform", choices=["uniform", "halfcauchy"])
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "hier":
        df = pd.read_parquet(a.csv) if a.csv.endswith(".parquet") else pd.read_csv(a.csv)
        df = df.dropna(subset=[a.est_col, a.se_col])
        r = hier_normal(df[a.est_col], df[a.se_col], prior=a.prior)
        out = pd.DataFrame({"id": df[a.id_col], "est": df[a.est_col], "se": df[a.se_col],
                            "post_mean": r["theta_mean"], "post_sd": r["theta_sd"]})
        out["shrink_frac"] = 1 - (out.post_mean - r["mu_mean"]) / (out.est - r["mu_mean"]).replace(0, np.nan)
        print(out.round(4).to_string(index=False))
        print(f"grand mean {r['mu_mean']:.4f} (sd {r['mu_sd']:.4f}); E[tau] = {(r['tau'] * r['post_tau']).sum():.4f}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
