"""Position-sizing and risk-budget calculators for rates RV packages.

Conventions (same as SKILL.md)
  DV01 in currency per bp, positive = long duration (receive fixed / long bond). Rate changes in bp.
  Risk strip S = DV01 per tenor bucket (signed). Q = covariance of daily bucket changes in bp^2 (changes, never levels).
  c = sqrt(S' Q S) is the one-sigma P&L of the horizon of Q (1 day by default). VaR_5% = 1.645 c, VaR_1% = 2.326 c.
  c is unchanged if every sign in S flips; the SIGN of a hedge trade does flip, so use the skill sign convention.

Usage
  python sizing.py inv-risk --r-bp 12.5 [--target 250000 --cap 50000]
  python sizing.py kelly --mu 0.0723 --sigma 0.1691 [--frac 0.5 --worst-loss 0.2047 --max-dd 0.2]
  python sizing.py covar --curve curve_par.csv --curve-id USD-SOFR --risk risk.csv [--snap eod_ny --window 252]
        curve_par columns: date, snap, curve_id, start, tenor, par_rate_pct (csv or parquet)
        risk.csv columns: tenor, dv01_ccy (signed, positive = long duration)
  python sizing.py --selftest
"""
from __future__ import annotations

import argparse
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

_N = NormalDist()
DAYS_PER_YEAR = 252.0


def z_of(conf: float) -> float:
    """One-sided normal quantile: z_of(0.95)=1.645, z_of(0.99)=2.326."""
    return _N.inv_cdf(conf)


# ---------------------------------------------------------------- vol targeting / DV01 budgets
def inverse_risk_dv01(r_bp_per_yr, target_vol_ccy=250_000.0, cap_ccy=50_000.0):
    """DV01 = target annual P&L vol / package vol in bp per year per unit DV01, capped.
    r_bp_per_yr: annualised vol of the package in bp (spread, fly or outright level). 250k / 12.5 = 20k."""
    r = np.asarray(r_bp_per_yr, float)
    if not np.all(r > 0):  # also rejects NaN
        raise ValueError("package vol must be a positive number")
    return np.minimum(target_vol_ccy / r, cap_ccy)


def stop_based_dv01(risk_budget_ccy, stop_distance_bp):
    """DV01 so that a move of stop_distance_bp against the trade loses exactly the risk budget."""
    if not np.all(np.asarray(stop_distance_bp, float) > 0):
        raise ValueError("stop distance must be a positive number of bp")
    return risk_budget_ccy / stop_distance_bp


def vol_stop_distance_bp(r_bp_per_yr, k=1.5, max_hold_days=63):
    """Adverse move (bp per unit DV01) that triggers the stop: k * annual package vol * sqrt(hold/252).
    With inverse-risk sizing the loss at the stop is target_vol * k * sqrt(hold/252) (0.75 x target for k=1.5, 63d)."""
    return k * np.asarray(r_bp_per_yr, float) * np.sqrt(max_hold_days / DAYS_PER_YEAR)


def ewma_vol(changes, lam=0.94, init=None):
    """RiskMetrics EWMA volatility series (same units as changes, no demeaning). sigma2_t = lam*sigma2_{t-1} + (1-lam)*x_t^2.
    out[t] uses data up to t, so it is the forecast for t+1 (trade on it after the shift, never on the same bar).
    NaN changes are skipped (variance carried). The seed is the mean square of the first 20 values, so treat the
    first ~3 half-lives as burn-in (they use data that is "ahead" of the early bars)."""
    x = np.asarray(changes, float)
    s2 = np.empty(len(x))
    cur = np.nanmean(x[:20] ** 2) if init is None else init ** 2
    for i, v in enumerate(x):
        if np.isfinite(v):
            cur = lam * cur + (1 - lam) * v * v
        s2[i] = cur
    return np.sqrt(s2)


def halflife_to_lambda(halflife_days):
    return 0.5 ** (1.0 / halflife_days)


def portfolio_vol_scalar(unit_cov_ccy, weights, target_vol_ccy):
    """Multiplier k so that k*weights has P&L vol target_vol_ccy. unit_cov_ccy = covariance of unit-package P&L over the
    SAME horizon as target_vol_ccy (daily covariance x 252 for an annual target)."""
    w = np.asarray(weights, float)
    v = float(np.sqrt(w @ np.asarray(unit_cov_ccy, float) @ w))
    return target_vol_ccy / v


def var_limit_notional_mm(var_limit_ccy, nvol_bp_annual, dv01_per_mm, k=3.0):
    """Max notional ($mm) = VaR limit / (k-sd daily move in bp * DV01 per mm). Daily sd = annual normal vol / sqrt(252)."""
    daily_sd = nvol_bp_annual / np.sqrt(DAYS_PER_YEAR)
    return var_limit_ccy / (k * daily_sd * dv01_per_mm)


def var_size_contracts(budget_ccy, sigma_ticks, tick_value, conf=0.99):
    """Contracts of a STIR spread: budget / (z * sigma_daily_ticks * tick value)."""
    return budget_ccy / (z_of(conf) * sigma_ticks * tick_value)


# ---------------------------------------------------------------- VaR / risk allocation
def covar(S, Q):
    """c = sqrt(S'QS): one-sigma P&L over the horizon of Q."""
    S = np.asarray(S, float)
    return float(np.sqrt(S @ np.asarray(Q, float) @ S))


def var_from_c(c, conf=0.95):
    """Zero-mean normal VaR = z * c."""
    return z_of(conf) * c


def euler_alloc(S, Q):
    """Aumann-Shapley / Euler contribution of each bucket to c; sums to c. Negative = diversifier."""
    S = np.asarray(S, float)
    return S * (np.asarray(Q, float) @ S) / covar(S, Q)


def var_min_trade(S, Q, idx):
    """Trade in the buckets idx (list of positions) that minimises c: t = -Q_ii^{-1} Q_i. S. Returns (trade vector, new S)."""
    S = np.asarray(S, float)
    Q = np.asarray(Q, float)
    idx = list(idx)
    t = np.linalg.solve(Q[np.ix_(idx, idx)], -Q[idx, :] @ S)
    trade = np.zeros_like(S)
    trade[idx] = t
    return trade, S + trade


def best_single_hedges(S, Q, labels=None):
    """Per bucket: VaR-minimising trade, change in c and % change. Only ONE of these is valid at a time."""
    S = np.asarray(S, float)
    c0 = covar(S, Q)
    rows = []
    for i in range(len(S)):
        trade, S2 = var_min_trade(S, Q, [i])
        rows.append((labels[i] if labels is not None else i, trade[i], covar(S2, Q) - c0, (covar(S2, Q) - c0) / c0))
    return pd.DataFrame(rows, columns=["bucket", "trade_dv01", "delta_c", "pct_c"])


def cantelli_tail_prob(loss_in_sd, sharpe=0.0):
    """Distribution-free bound P(PnL < -L sd) <= 1/(1+(L+SR)^2) (SR in the same units as sd)."""
    return 1.0 / (1.0 + (loss_in_sd + sharpe) ** 2)


# ---------------------------------------------------------------- Kelly
def kelly_single(mu, sigma):
    """Growth-optimal leverage for excess return mu and vol sigma (same period): mu / sigma^2."""
    return mu / sigma ** 2


def kelly_uncertain(mu, sigma, tau_mu=0.0, tau_sigma=0.0):
    """Kelly with parameter uncertainty: mu / (mu^2 + sigma^2 + tau^2). Always below the plug-in mu/sigma^2
    (tau = 0 already gives the second-moment form: mu .08, sigma .19 -> 1.88 versus plug-in 2.22)."""
    return mu / (mu ** 2 + sigma ** 2 + tau_mu ** 2 + tau_sigma ** 2)


def kelly_multi(M, C):
    """F* = C^-1 M for strategies with mean excess returns M and covariance C. Growth = r + F'CF/2, Sharpe = sqrt(F'CF)."""
    return np.linalg.solve(np.asarray(C, float), np.asarray(M, float))


def kelly_leverage_cap(kelly_f, worst_one_period_loss, max_one_period_dd, frac=0.5):
    """min(fractional Kelly, tolerable drawdown / worst historical loss per unit leverage)."""
    return min(frac * kelly_f, max_one_period_dd / worst_one_period_loss)


def bet_size_from_prob(p):
    """Symmetric payoff: S = 2P-1 (Kelly); bounded -1..1."""
    return 2.0 * np.asarray(p, float) - 1.0


# ---------------------------------------------------------------- data glue
def bucket_changes(curve_par: pd.DataFrame, curve_id: str, snap: str | None = None, start: str = "0D",
                   tenors=None) -> pd.DataFrame:
    """Daily change in bp per tenor from canonical curve_par (rows = dates). Drops days with any missing tenor.
    One snap only: pass `snap` when the table holds several (mixing snaps creates fake changes)."""
    d = curve_par[(curve_par["curve_id"] == curve_id) & (curve_par["start"] == start)]
    if snap is not None:
        d = d[d["snap"] == snap]
    elif d["snap"].nunique() > 1:
        raise ValueError("curve_par has several snaps for this curve; pass snap=")
    wide = d.pivot_table(index="date", columns="tenor", values="par_rate_pct", aggfunc="last").sort_index()
    if tenors is not None:
        missing = [t for t in tenors if t not in wide.columns]
        if missing:
            raise ValueError(f"tenors missing from curve_par: {missing}")
        wide = wide[list(tenors)]
    return (wide.diff() * 100.0).dropna()


def tenor_years(t: str) -> float:
    n, u = float(t[:-1]), t[-1].upper()
    return n * {"Y": 1.0, "M": 1 / 12, "W": 1 / 52, "D": 1 / 365}[u]


def second_moment(ch: pd.DataFrame) -> np.ndarray:
    """Covariance of changes WITHOUT demeaning (mean ~ 0 for daily rate changes; demeaning adds noise): X'X/n."""
    x = ch.values.astype(float)
    return x.T @ x / len(x)


def covar_report(curve_par, curve_id, risk: pd.DataFrame, snap=None, window=252) -> dict:
    risk = risk.copy()
    risk = risk.iloc[np.argsort([tenor_years(t) for t in risk["tenor"]])]
    ten = list(risk["tenor"])
    ch = bucket_changes(curve_par, curve_id, snap, tenors=ten).tail(window)
    if len(ch) < max(100, len(ten) + 1):
        raise ValueError(f"only {len(ch)} daily changes; need >= max(100, n_buckets+1)")
    Q = second_moment(ch)
    S = risk["dv01_ccy"].values.astype(float)
    c = covar(S, Q)
    return {"c": c, "var95": var_from_c(c, 0.95), "var99": var_from_c(c, 0.99), "n_obs": len(ch),
            "alloc": pd.Series(euler_alloc(S, Q), index=ten), "hedges": best_single_hedges(S, Q, ten)}


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    fails = []

    def check(name, got, want, rel=1e-6, abs_=0.0):
        ok = abs(got - want) <= max(abs_, rel * abs(want))
        if not ok:
            fails.append(f"{name}: got {got!r} want {want!r}")

    # 1 inverse-risk DV01: 250k / 12.5bp = 20k; R = 4 hits the 50k cap
    check("inv_risk", float(inverse_risk_dv01(12.5)), 20_000.0)
    check("inv_risk_cap", float(inverse_risk_dv01(4.0)), 50_000.0)
    check("stop_dv01", stop_based_dv01(500_000, 25.0), 20_000.0)
    check("vol_stop", float(vol_stop_distance_bp(12.5)), 9.375)
    check("loss_at_stop", float(inverse_risk_dv01(12.5) * vol_stop_distance_bp(12.5)), 187_500.0)
    # 2 normal quantiles
    check("z95", z_of(0.95), 1.6449, rel=1e-4)
    check("z99", z_of(0.99), 2.3263, rel=1e-4)
    # 3 structure riskiness (published: 10Y outright 452, 5s10s 164, 2s5s10s 149, 5s10s30s 123, 2s5s/10s30s 238; 000s DV01)
    Q = np.array([[7.5, 10.5, 8.5, 4.3], [10.5, 20.7, 19.2, 10.1], [8.5, 19.2, 20.4, 12.5], [4.3, 10.1, 12.5, 10.4]])
    for w, want in [((0, 0, 100, 0), 452), ((0, -100, 100, 0), 164), ((-50, 100, -50, 0), 149),
                    ((0, -50, 100, -50), 123), ((-50, 50, 50, -50), 238)]:
        check(f"c{w}", covar(np.array(w, float), Q), want, rel=0.005)
        check(f"c_flip{w}", covar(-np.array(w, float), Q), covar(np.array(w, float), Q), rel=1e-12)
    # 4 Euler allocation sums to c; diagonal Q analytic: alloc_i = S_i^2 q_i / c
    S = np.array([-10000.0, 2500.0, 10000.0, -4000.0])
    check("euler_sum", float(euler_alloc(S, Q).sum()), covar(S, Q), rel=1e-12)
    Qd = np.diag([4.0, 9.0])
    Sd = np.array([3.0, 2.0])
    check("euler_diag", float(euler_alloc(Sd, Qd)[0]), 9 * 4 / np.sqrt(9 * 4 + 4 * 9), rel=1e-12)
    # 5 VaR-minimising hedge, analytic: Q=[[1,.5],[.5,1]], S=(1,0), hedge in bucket 2 -> trade -0.5, c = sqrt(0.75)
    Q2 = np.array([[1.0, 0.5], [0.5, 1.0]])
    tr, S2 = var_min_trade(np.array([1.0, 0.0]), Q2, [1])
    check("hedge_trade", float(tr[1]), -0.5)
    check("hedge_c", covar(S2, Q2), np.sqrt(0.75), rel=1e-12)
    tr2, S3 = var_min_trade(S, Q, [0, 2])
    if np.max(np.abs((Q @ S3)[[0, 2]])) > 1e-6:
        fails.append("multi hedge: first-order condition Q_i S_min = 0 violated")
    # 6 VaR-limit sizing (10y swap, Oct 2009 desk note: 174 nvol, $863/mm DV01, $10mm limit -> ~$352mm)
    check("var_limit", float(var_limit_notional_mm(10e6, 174, 863)), 352.0, rel=0.005)
    # 7 STIR spread VaR sizing: 50,000 / (2.33 * 25) ~ 858 (source rounds to ~850)
    check("stir_var", float(var_size_contracts(50_000, 1.0, 25.0, 0.99)), 850.0, rel=0.02)  # source: ~850 spreads
    # 8 Kelly: excess return 7.231%, sd 16.91% -> 2.528; uncertainty lowers it (mu .08 sd .19: 1.88 -> 1.81 / 1.52)
    check("kelly", kelly_single(0.07231, 0.1691), 2.528, rel=1e-3)
    check("kelly_tau0", kelly_uncertain(0.08, 0.19), 1.88, rel=0.005)
    check("kelly_tau_mu", kelly_uncertain(0.08, 0.19, tau_mu=0.04), 1.81, rel=0.005)
    check("kelly_tau_sig", kelly_uncertain(0.08, 0.19, tau_sigma=0.1), 1.52, rel=0.005)
    check("kelly_cap", kelly_leverage_cap(2.528, 0.2047, 0.2), 0.2 / 0.2047, rel=1e-9)
    M = np.array([0.1396, 0.0294, -0.0073])
    C = np.array([[0.1109, 0.0200, 0.0183], [0.0200, 0.0372, 0.0269], [0.0183, 0.0269, 0.0420]])
    F = kelly_multi(M, C)
    for i, want in enumerate([1.2919, 1.1723, -1.4882]):
        check(f"kelly_multi{i}", float(F[i]), want, rel=0.003)
    check("kelly_sharpe", float(np.sqrt(F @ C @ F)), 0.4751, rel=1e-3)
    check("cantelli", cantelli_tail_prob(2.0, 3.0), 1 / 26.0)
    # 9 EWMA vol recovers a constant-vol series; lambda from half-life
    rng = np.random.default_rng(7)
    x = rng.normal(0, 5.0, 4000)
    check("ewma", float(ewma_vol(x, 0.97)[-1]), 5.0, rel=0.25)
    check("halflife", halflife_to_lambda(11) ** 11, 0.5, rel=1e-12)
    xn = x.copy()
    xn[100] = np.nan
    check("ewma_nan", float(ewma_vol(xn, 0.97)[-1]), float(ewma_vol(x, 0.97)[-1]), rel=0.02)
    # vol scalar: unit cov diag(4,9) bp^2 x weights (1,1) -> vol sqrt(13); target 2*sqrt(13) -> k = 2
    check("vol_scalar", portfolio_vol_scalar(np.diag([4.0, 9.0]), [1.0, 1.0], 2 * np.sqrt(13.0)), 2.0, rel=1e-12)
    # second moment is NOT demeaned: constant +1bp/day drift has second moment 1, not 0
    check("second_moment", float(second_moment(pd.DataFrame({"a": np.ones(50)}))[0, 0]), 1.0, rel=1e-12)
    # 10 pipeline: simulate bucket changes with KNOWN covariance, build curve_par, recover c within sampling error
    ten = ["2Y", "5Y", "10Y", "30Y"]
    Qt = np.array([[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]])
    n = 6000
    dy_bp = rng.multivariate_normal(np.zeros(4), Qt, size=n)
    lv = 3.0 + np.cumsum(dy_bp, axis=0) / 100.0
    dates = pd.bdate_range("2000-01-03", periods=n)
    rows = [(d, "eod_ny", "TEST", "0D", t, lv[i, j]) for i, d in enumerate(dates) for j, t in enumerate(ten)]
    cp = pd.DataFrame(rows, columns=["date", "snap", "curve_id", "start", "tenor", "par_rate_pct"])
    risk = pd.DataFrame({"tenor": ["30Y", "2Y", "10Y", "5Y"], "dv01_ccy": [-4000.0, -10000.0, 10000.0, 2500.0]})
    rep = covar_report(cp, "TEST", risk, window=n)
    check("pipeline_c", rep["c"], covar(np.array([-10000.0, 2500.0, 10000.0, -4000.0]), Qt), rel=0.03)
    check("pipeline_alloc_sum", float(rep["alloc"].sum()), rep["c"], rel=1e-9)
    if fails:
        print("SELFTEST FAILED")
        for f in fails:
            print("  -", f)
        return 1
    print("selftest ok")
    return 0


# ---------------------------------------------------------------- CLI
def _read(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path, parse_dates=["date"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("inv-risk", help="inverse-risk DV01 sizing")
    a.add_argument("--r-bp", type=float, required=True, help="annualised package vol, bp")
    a.add_argument("--target", type=float, default=250_000.0)
    a.add_argument("--cap", type=float, default=50_000.0)
    k = sub.add_parser("kelly", help="Kelly leverage and caps")
    k.add_argument("--mu", type=float, required=True, help="mean excess return per period (decimal)")
    k.add_argument("--sigma", type=float, required=True)
    k.add_argument("--tau-mu", type=float, default=0.0)
    k.add_argument("--tau-sigma", type=float, default=0.0)
    k.add_argument("--frac", type=float, default=0.5)
    k.add_argument("--worst-loss", type=float, help="worst historical one-period loss per unit leverage")
    k.add_argument("--max-dd", type=float, help="tolerable one-period equity drawdown")
    c = sub.add_parser("covar", help="CoVaR, Euler allocation, best single hedges from curve_par and a risk strip")
    c.add_argument("--curve", required=True)
    c.add_argument("--curve-id", required=True)
    c.add_argument("--risk", required=True)
    c.add_argument("--snap")
    c.add_argument("--window", type=int, default=252)
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.cmd == "inv-risk":
        print(f"DV01 = {float(inverse_risk_dv01(args.r_bp, args.target, args.cap)):,.0f} ccy/bp")
    elif args.cmd == "kelly":
        f = kelly_uncertain(args.mu, args.sigma, args.tau_mu, args.tau_sigma)
        print(f"full Kelly {kelly_single(args.mu, args.sigma):.3f}; with parameter uncertainty {f:.3f}; fractional ({args.frac}) {args.frac * f:.3f}")
        if args.worst_loss and args.max_dd:
            print(f"capped leverage {kelly_leverage_cap(f, args.worst_loss, args.max_dd, args.frac):.3f}")
    elif args.cmd == "covar":
        r = covar_report(_read(args.curve), args.curve_id, pd.read_csv(args.risk), args.snap, args.window)
        print(f"obs {r['n_obs']}  c {r['c']:,.0f}  VaR95 {r['var95']:,.0f}  VaR99 {r['var99']:,.0f}")
        print("Euler allocation (sums to c; negative = diversifier):\n" + r["alloc"].round(0).to_string())
        print("Best single hedge per bucket (only one is valid at a time):\n" + r["hedges"].round(3).to_string(index=False))
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
