"""Lean, self-contained analytics kit for the RV agent: the numerical patterns other skills reuse.

Contents (each has a known-answer check in --selftest):
  Dual / dexp / dlog     forward-mode automatic differentiation (first order, tagged variables)
  solve_curve_gn         discount-factor curve from annual par swaps by weighted Gauss-Newton, Jacobian by AD
  cov_bp, covar, min_var_trade, pca_cov   bp-change covariance, CoVaR + Euler allocation, min-VaR hedge, PCA
  ridge_qr               ridge as augmented least squares solved by QR (never an explicit inverse)
  swaption_normal, implied_nvol_bp       Bachelier swaption price and Newton implied vol
  df_loglinear           log-linear discount-factor interpolation
  lookahead_check        truncation test: does a signal at t change when future rows are removed?
  clean_levels           drop weekends / non-finite rows, never forward-fill
  lin_parts, nested_parts, mp_map        parallel job partitioning with a single-process debug path
  run_manifest           versions + seed + input hashes for reproducible runs

CLI (reads the canonical `curve_par` table, CSV or Parquet):
  python analytics_kit.py var --curve-par curve_par.csv --curve-id USD-SOFR --sens "2Y:-10000,5Y:2500,10Y:10000"
  python analytics_kit.py manifest data/curve_par.csv --seed 7
  python analytics_kit.py --selftest
Units: rates in percent at the API edge, internal decimals where stated; covariance in bp^2 of daily changes;
sensitivities in currency per bp (positive = long duration / receive fixed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from functools import partial

import numpy as np
import pandas as pd
from scipy.stats import norm

# --------------------------------------------------------------------------- forward-mode AD


class Dual:
    """value x and gradient g (dict tag -> d x / d tag). Upcasting is automatic (missing tag = 0)."""
    __slots__ = ("x", "g")

    def __init__(self, x, g=None):
        self.x, self.g = float(x), (g or {})

    @staticmethod
    def var(x, tag):
        return Dual(x, {tag: 1.0})

    @staticmethod
    def _l(o):
        return o if isinstance(o, Dual) else Dual(o)

    def _comb(self, o, ca, cb, x):
        return Dual(x, {k: ca * self.g.get(k, 0.0) + cb * o.g.get(k, 0.0) for k in self.g.keys() | o.g.keys()})

    def __add__(s, o):
        o = Dual._l(o)
        return s._comb(o, 1.0, 1.0, s.x + o.x)
    __radd__ = __add__

    def __sub__(s, o):
        o = Dual._l(o)
        return s._comb(o, 1.0, -1.0, s.x - o.x)

    def __rsub__(s, o):
        return Dual._l(o) - s

    def __neg__(s):
        return Dual(-s.x, {k: -v for k, v in s.g.items()})

    def __mul__(s, o):
        o = Dual._l(o)
        return s._comb(o, o.x, s.x, s.x * o.x)
    __rmul__ = __mul__

    def __truediv__(s, o):
        o = Dual._l(o)
        return s._comb(o, 1.0 / o.x, -s.x / o.x ** 2, s.x / o.x)

    def __rtruediv__(s, o):
        return Dual._l(o) / s

    def __pow__(s, n):  # constant real exponent only
        return Dual(s.x ** n, {k: n * s.x ** (n - 1) * v for k, v in s.g.items()})

    def __repr__(self):
        return f"Dual({self.x:.10g}, {self.g})"


def _lift(a, f, df):
    return Dual(f(a.x), {k: df(a.x) * v for k, v in a.g.items()}) if isinstance(a, Dual) else f(a)


def dexp(a):
    return _lift(a, math.exp, math.exp)


def dlog(a):
    return _lift(a, math.log, lambda x: 1.0 / x)

# --------------------------------------------------------------------------- curve solve


def _df_at(t, nodes_t, ln_v):
    """log-linear DF at integer/real time t from node times (ascending, first > 0) and Dual/float ln DF; v(0)=1."""
    ts = [0.0] + list(nodes_t)
    lv = [0.0] + list(ln_v)
    if t > ts[-1]:  # flat overnight forward beyond last node: extrapolation, flag in outputs
        return dexp(lv[-1] * (t / ts[-1]))
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    w = (t - ts[i]) / (ts[i + 1] - ts[i])
    return dexp((1 - w) * lv[i] + w * lv[i + 1])


def par_rates_annual(ln_v, nodes_t, tenors):
    """Par rate (decimal) of annual fixed vs floating swaps, DCF = 1, tenors in whole years, single curve."""
    out = []
    for n in tenors:
        dfs = [_df_at(j, nodes_t, ln_v) for j in range(1, int(n) + 1)]
        ann = dfs[0]
        for d in dfs[1:]:
            ann = ann + d
        out.append((1.0 - dfs[-1]) / ann)
    return out


def solve_curve_gn(par_pct, tenors, nodes_t=None, weights=None, tol=1e-13, max_iter=50):
    """Weighted Gauss-Newton on ln-DF nodes. Minimises (r - S)' W (r - S); J from Dual numbers.
    Returns dict(v, ln_v, iters, resid, J (m x n, d rate_decimal / d ln v), K (n x m, d ln v / d rate_decimal;
    weighted least-squares sensitivity, ignores the second-order residual term))."""
    S = np.asarray(par_pct, float) / 100.0
    nodes_t = list(tenors if nodes_t is None else nodes_t)
    m, n = len(S), len(nodes_t)
    w = np.ones(m) if weights is None else np.asarray(weights, float)
    x = np.array([-0.02 * t for t in nodes_t])  # prior: flat 2% curve; use yesterday's solved curve in production
    for it in range(1, max_iter + 1):
        duals = [Dual.var(x[i], i) for i in range(n)]
        r = par_rates_annual(duals, nodes_t, tenors)
        res = np.array([d.x for d in r]) - S
        J = np.array([[d.g.get(i, 0.0) for i in range(n)] for d in r])
        # converged if reprices to tol (exactly/under-specified) or the weighted gradient J'W(r-S) vanishes (overspecified)
        if np.max(np.abs(res)) < tol or np.max(np.abs(J.T @ (w * res))) < 1e-14:
            break
        sw = np.sqrt(w)[:, None]
        # lstsq (SVD) rather than normal equations J'WJ: squares the condition number otherwise
        step = np.linalg.lstsq(sw * J, -(sw[:, 0] * res), rcond=None)[0]
        x = x + step
    else:
        raise RuntimeError(f"Gauss-Newton did not converge in {max_iter} iterations, resid {np.max(np.abs(res)):.2e}")
    sw = np.sqrt(w)  # K = (J'WJ)^-1 J'W = pinv(sqrt(W) J) sqrt(W): equals J^-1 when exactly specified, honours weights otherwise
    return dict(v=np.exp(x), ln_v=x, iters=it, resid=res, J=J, K=np.linalg.pinv(sw[:, None] * J) * sw)

# --------------------------------------------------------------------------- covariance, VaR, PCA


def clean_levels(df):
    """Drop weekend and non-finite rows (never forward-fill). Returns (clean, n_dropped)."""
    ok = np.isfinite(df.to_numpy(float)).all(axis=1) & (pd.DatetimeIndex(df.index).dayofweek < 5)
    return df[ok], int((~ok).sum())


def cov_bp(par_pct, min_obs=100):
    """Covariance (bp^2) of daily CHANGES of par rates given in percent (DataFrame, one column per tenor)."""
    d = par_pct.replace([np.inf, -np.inf], np.nan).diff().dropna() * 100.0  # +-inf treated as missing
    if len(d) < min_obs:
        raise ValueError(f"{len(d)} change observations < {min_obs}: covariance not meaningful")
    return d.cov()


def covar(S, Q, alpha=0.05):
    """c = sqrt(S'QS); VaR = z_(1-alpha) c; Euler allocation S_i (QS)_i / c (sums to c; negative = diversifier)."""
    S, Q = np.asarray(S, float), np.asarray(Q, float)
    if not (np.isfinite(S).all() and np.isfinite(Q).all()):
        raise ValueError("non-finite sensitivities or covariance: strip NaN/INF first")
    c = float(np.sqrt(S @ Q @ S))
    return dict(c=c, var=float(norm.ppf(1 - alpha) * c), alloc=S * (Q @ S) / c)


def min_var_trade(Q, S, idx):
    """Trade in instruments `idx` only that minimises c: S_trade = -Q_hh^-1 (Q S)_h. Returns (trade, S_new)."""
    Q, S = np.asarray(Q, float), np.asarray(S, float)
    idx = list(idx)
    t = np.zeros(len(S))
    t[idx] = np.linalg.solve(Q[np.ix_(idx, idx)], -(Q @ S)[idx])
    return t, S + t


def pca_cov(Q):
    """Eigen-decomposition of a covariance (or correlation) matrix, descending. Sign rule (arbitrary but
    deterministic): the largest-|loading| entry of each PC is positive. Returns (eigenvalues, E) with Q = E diag(l) E'."""
    Q = np.asarray(Q, float)
    if not np.isfinite(Q).all():
        raise ValueError("non-finite covariance: strip NaN/INF before the eigen-decomposition")
    lam, E = np.linalg.eigh(Q)
    o = np.argsort(lam)[::-1]
    lam, E = lam[o], E[:, o]
    E = E * np.sign(E[np.abs(E).argmax(axis=0), np.arange(E.shape[1])])
    return lam, E

# --------------------------------------------------------------------------- regularised least squares


def ridge_qr(X, y, lam):
    """Ridge via augmented system [X; sqrt(lam) I] w = [y; 0], solved by QR. No intercept: centre first."""
    from scipy.linalg import solve_triangular
    X, y = np.asarray(X, float), np.asarray(y, float)
    D = X.shape[1]
    Q, R = np.linalg.qr(np.vstack([X, math.sqrt(lam) * np.eye(D)]))
    return solve_triangular(R, Q.T @ np.concatenate([y, np.zeros(D)]))

# --------------------------------------------------------------------------- option pricing


def swaption_normal(F, K, T, vol_bp, kind="payer"):
    """Bachelier swaption premium in % of annuity (x100 = bp running-equivalent per unit annuity).
    F, K in percent; T years; vol in bp/yr. receiver = payer - (F - K) (physical settlement only)."""
    adj = vol_bp * math.sqrt(T) / 100.0
    x = (F - K) / adj
    payer = (F - K) * norm.cdf(x) + adj * norm.pdf(x)
    return payer if kind == "payer" else payer - (F - K)


def implied_nvol_bp(price_pct, F, K, T, kind="payer", start=20.0, tol=1e-10):
    """Newton on vol; vega (price % per bp of vol) = sqrt(T)/100 * pdf(x). Straddle not handled."""
    intrinsic = max(F - K, 0.0) if kind == "payer" else max(K - F, 0.0)
    if kind not in ("payer", "receiver") or T <= 0 or price_pct <= intrinsic:
        raise ValueError("need kind payer/receiver, T > 0 and price above intrinsic value")
    v = start
    for _ in range(50):
        adj = v * math.sqrt(T) / 100.0
        err = swaption_normal(F, K, T, v, kind) - price_pct
        if abs(err) < tol:
            return v
        v -= err / (math.sqrt(T) / 100.0 * norm.pdf((F - K) / adj))
        v = max(v, 1e-6)
    raise RuntimeError("implied vol did not converge")

# --------------------------------------------------------------------------- misc patterns


def df_loglinear(t_nodes, df_nodes, t):
    """Log-linear DF interpolation (piecewise-constant forward). Nodes must be ascending; no extrapolation."""
    t = np.asarray(t, float)
    if t.min() < t_nodes[0] or t.max() > t_nodes[-1]:
        raise ValueError("t outside node range (extrapolation is a decision, not a default)")
    return np.exp(np.interp(t, t_nodes, np.log(df_nodes)))


def lookahead_check(fn, df, probe_idx, atol=1e-12):
    """Truncation test. fn(df) -> Series/DataFrame indexed like df. A causal signal at probe date t is identical
    whether computed on the full frame or on df.loc[:t]. Returns the list of probe dates that differ (empty = ok)."""
    full = fn(df)
    bad = []
    for t in probe_idx:
        a, b = full.loc[t], fn(df.loc[:t]).loc[t]
        if not np.allclose(np.asarray(a, float), np.asarray(b, float), rtol=0, atol=atol, equal_nan=True):
            bad.append(t)
    return bad


def lin_parts(n_atoms, n_threads):
    return np.ceil(np.linspace(0, n_atoms, min(n_threads, n_atoms) + 1)).astype(int)


def nested_parts(n_atoms, n_threads, upper_triang=False):
    """Molecule boundaries for a double loop over a triangle (work for row i is ~i): equal work per molecule."""
    k = min(n_threads, n_atoms)
    parts = [0.0]
    for _ in range(k):
        p = 1 + 4 * (parts[-1] ** 2 + parts[-1] + n_atoms * (n_atoms + 1.0) / k)
        parts.append((-1 + p ** 0.5) / 2.0)
    parts = np.round(parts).astype(int)
    if upper_triang:  # heaviest rows first
        parts = np.append([0], np.cumsum(np.diff(parts)[::-1]))
    return parts


def _expand(kw):
    return kw.pop("func")(**kw)


def mp_map(func, jobs, num_threads=1):
    """Run func(**job) for each job dict. num_threads == 1 is a plain loop (debug path; parallel-only bugs are
    unreadable). func must be a module-level function (picklable under Windows spawn). Order is NOT preserved
    when parallel: have jobs carry their own key."""
    jobs = [dict(j, func=func) for j in jobs]
    if num_threads == 1:
        return [_expand(j) for j in jobs]
    import multiprocessing as mp
    with mp.Pool(num_threads) as pool:
        return list(pool.imap_unordered(_expand, jobs))


def run_manifest(seed=None, inputs=(), extra=None):
    """Everything needed to say 'same inputs, same code, same libraries' next time. Log one per run."""
    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        return h.hexdigest()
    return dict(python=sys.version.split()[0], platform=platform.platform(), numpy=np.__version__,
                pandas=pd.__version__, seed=seed, inputs={str(p): sha(p) for p in inputs}, extra=extra or {})

# --------------------------------------------------------------------------- CLI


def _load(path):
    return pd.read_parquet(path) if str(path).endswith((".parquet", ".pq")) else pd.read_csv(path)


def _tenor_years(t):
    return float(t[:-1]) if t.endswith("Y") else float(t[:-1]) / 12.0


def cmd_var(a):
    cp = _load(a.curve_par)
    cp = cp[(cp.curve_id == a.curve_id) & (cp.start == "0D")]
    if "snap" in cp and cp.snap.nunique() > 1:
        raise SystemExit(f"several snaps {sorted(cp.snap.unique())}: pass a table filtered to one snap (mixing snaps adds noise)")
    wide = cp.pivot(index="date", columns="tenor", values="par_rate_pct")
    wide.index = pd.to_datetime(wide.index)
    wide = wide.sort_index()
    wkday = wide.index.dayofweek < 5  # keep NaN rows: cov_bp drops the changes touching them (no multi-day diffs)
    dropped = int((~wkday).sum())
    wide = wide[wkday]
    sens = dict((k, float(v)) for k, v in (s.split(":") for s in a.sens.split(",")))
    tenors = sorted(sens, key=_tenor_years)
    Q = cov_bp(wide[tenors], a.min_obs)
    n_changes = len(wide[tenors].diff().dropna())
    S = np.array([sens[t] for t in tenors])
    r = covar(S, Q.to_numpy(), a.alpha)
    lam, E = pca_cov(Q.to_numpy())
    print(json.dumps(dict(tenors=tenors, n_changes=n_changes, rows_dropped=dropped, nan_rows=int(wide[tenors].isna().any(axis=1).sum()), c=r["c"], var=r["var"],
                          alpha=a.alpha, alloc=dict(zip(tenors, r["alloc"].round(1))),
                          eigenvalues=lam.round(4).tolist(), pc1=dict(zip(tenors, E[:, 0].round(3)))), indent=1))


def cmd_manifest(a):
    print(json.dumps(run_manifest(a.seed, a.files), indent=1))

# --------------------------------------------------------------------------- selftest


def _job_square(i):
    return i, i * i


def selftest():
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name + (f"  {info}" if info else ""))

    # AD: f = x^6 + exp(x/y) + ln z at (2,1,2): value, gradient (Darbyshire, Coding Interest Rates)
    x, y, z = Dual.var(2, "x"), Dual.var(1, "y"), Dual.var(2, "z")
    f = x ** 6 + dexp(x / y) + dlog(z)
    check("AD value", abs(f.x - 72.08220328) < 1e-7, f"{f.x:.8f}")
    check("AD gradient", all(abs(f.g[k] - v) < 1e-6 for k, v in dict(x=199.389056, y=-14.778112, z=0.5).items()), str(f.g))

    # product / sub / reverse-divide rules, hand-derived: (x y) z + 2x at (2,3,5) -> value 34, grad (17, 10, 6); 2/(x-1) at 3 -> 1, -0.5
    x, y, z = Dual.var(2, "x"), Dual.var(3, "y"), Dual.var(5, "z")
    g = x * y * z + 2 * x
    check("AD product rule", g.x == 34 and (g.g["x"], g.g["y"], g.g["z"]) == (17, 10, 6), str(g.g))
    h2 = 2 / (Dual.var(3, "x") - 1)
    check("AD reverse divide / sub", abs(h2.x - 1) < 1e-15 and abs(h2.g["x"] + 0.5) < 1e-15)

    # Curve: annual par swaps 1Y/2Y at 2.5/3.5 -> analytic bootstrap df1 = 1/(1+r1), df2 = (1 - r2 df1)/(1 + r2)
    r1, r2 = 0.025, 0.035
    d1 = 1 / (1 + r1)
    d2 = (1 - r2 * d1) / (1 + r2)
    s2 = solve_curve_gn([2.5, 3.5], [1, 2])
    check("GN equals analytic bootstrap", np.allclose(s2["v"], [d1, d2], atol=1e-12), f"{s2['v']} iters={s2['iters']}")
    # 4 nodes, rates from Pricing and Trading IRD 3rd ed. Ex 11.1; must reprice to ~0 (minimum validity test)
    S4, T4 = [1.21, 1.635, 1.885, 1.93], [1, 2, 5, 10]
    s4 = solve_curve_gn(S4, T4)
    check("GN reprices inputs", np.max(np.abs(s4["resid"])) < 1e-12, f"{np.max(np.abs(s4['resid'])):.1e}")
    # sensitivity K = J^-1 vs bump-and-re-solve (0.01bp)
    h = 1e-6
    ok_k = True
    for i in range(4):
        Sb = list(S4)
        Sb[i] += h * 100
        vb = solve_curve_gn(Sb, T4)["ln_v"]
        ok_k &= np.allclose((vb - s4["ln_v"]) / h, s4["K"][:, i], rtol=1e-4, atol=1e-6)
    check("K = J^-1 matches bump-and-solve", ok_k)
    # overspecified: 4 nodes {1,5} and 3 swaps still solves with least squares, residual not zero
    # (only a smoke check that the weighted path runs)
    so = solve_curve_gn([1.21, 1.885, 1.93], [1, 5, 10], nodes_t=[1, 10], weights=[1, 1, 1])
    check("overspecified: LS optimum (J'W res = 0), residual not zero",
          np.max(np.abs(so["J"].T @ so["resid"])) < 1e-12 and np.max(np.abs(so["resid"])) > 1e-9, f"iters={so['iters']}")

    # weighted over-specified K = (J'WJ)^-1 J'W must match bump-and-re-solve (pinv(J) alone ignores the weights)
    Sw, Tw, ww = [1.21, 1.9, 1.93], [1, 5, 10], [1, 4, 1.0]
    s_w = solve_curve_gn(Sw, Tw, nodes_t=[1, 10], weights=ww)
    ok_w = True
    for i in range(3):
        Sb = list(Sw)
        Sb[i] += h * 100
        vb = solve_curve_gn(Sb, Tw, nodes_t=[1, 10], weights=ww)["ln_v"]
        ok_w &= np.allclose((vb - s_w["ln_v"]) / h, s_w["K"][:, i], rtol=1e-3, atol=1e-5)
    check("weighted K matches bump-and-solve", ok_w)

    # weights bite: giving the 5Y swap ~zero weight must reproduce the exactly-specified {1Y, 10Y} solve
    sw = solve_curve_gn([1.21, 1.885, 1.93], [1, 5, 10], nodes_t=[1, 10], weights=[1, 1e-12, 1])
    se = solve_curve_gn([1.21, 1.93], [1, 10], nodes_t=[1, 10])
    check("weights: w(5Y)->0 equals exact 1Y/10Y solve", np.allclose(sw["ln_v"], se["ln_v"], atol=1e-6),
          f"{np.abs(sw['ln_v'] - se['ln_v']).max():.1e}")

    # CoVaR fixture (Pricing and Trading IRD 3rd ed. Ch.14). The book prints c = 16,174 from the unrounded covariance;
    # the printed (rounded) matrix gives 16,402 ("about 16,400"), so check both: exact on the rounded Q, 2% vs the book.
    Q = np.array([[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]])
    S = np.array([-10000, 2500, 10000, -4000.0])
    r = covar(S, Q, 0.01)
    c_loop = math.sqrt(sum(S[i] * Q[i, j] * S[j] for i in range(4) for j in range(4)))  # independent route
    check("CoVaR c (rounded Q, exact)", abs(r["c"] - c_loop) < 1e-9 and abs(r["c"] - 16401.98) < 0.01, f"{r['c']:.2f}")
    check("CoVaR c within 2% of book 16,174", abs(r["c"] / 16174 - 1) < 0.02)
    check("VaR 1% = 2.326 c", abs(r["var"] - 2.3263 * r["c"]) < 1, f"{r['var']:.2f}")
    check("Euler allocation sums to c", abs(r["alloc"].sum() - r["c"]) < 1e-6)
    t, Sn = min_var_trade(Q, S, [0])
    cn = covar(Sn, Q)["c"]
    check("min-VaR 2Y trade ~ book +2,948 / c -15.6%", abs(t[0] / 2948 - 1) < 0.05 and abs(1 - cn / r["c"] - 0.156) < 0.01,
          f"trade {t[0]:.0f} c {cn:.0f}")
    # on the rounded Q the exact answer is trade = 26300/8.7 = 3022.99 and c down 16.07% (not the book's 15.6%)
    check("min-VaR 2Y exact on rounded Q", abs(t[0] - 26300 / 8.7) < 1e-6 and abs(1 - cn / r["c"] - 0.16067) < 5e-5)
    t, Sn = min_var_trade(Q, S, [0, 2])
    check("min-VaR first-order condition", np.allclose((Q @ Sn)[[0, 2]], 0, atol=1e-8))
    lam, E = pca_cov(np.array([[2, 1], [1, 2.0]]))
    check("PCA 2x2 eigenvalues 3,1", np.allclose(lam, [3, 1]))
    lam, E = pca_cov(Q)
    check("PCA diagonalises Q", np.allclose(E.T @ Q @ E, np.diag(lam), atol=1e-9) and abs(lam.sum() - np.trace(Q)) < 1e-9)

    # cov_bp: needs >= min_obs, uses changes
    idx = pd.bdate_range("2024-01-01", periods=300)
    lv = pd.DataFrame({"a": np.cumsum(np.full(300, 0.01)), "b": np.cumsum(np.full(300, 0.02))}, index=idx)
    # known answer: percent changes alternating +/-0.05 (= +/-5bp) -> variance 25 bp^2 x n/(n-1), n = 299 changes
    alt = pd.DataFrame({"a": np.cumsum(np.tile([0.05, -0.05], 150)[:300])}, index=idx)
    qa = cov_bp(alt).iloc[0, 0]
    check("cov_bp is bp^2 of changes", abs(qa - 25.0 * 299 / 298) < 0.02, f"{qa:.4f}")
    try:
        cov_bp(lv.iloc[:50])
        check("cov_bp rejects short history", False)
    except ValueError:
        check("cov_bp rejects short history", True)
    inf_df = alt.copy()
    inf_df.iloc[10, 0] = np.inf
    check("cov_bp treats inf as missing", np.isfinite(cov_bp(inf_df).iloc[0, 0]))
    try:
        covar([1.0, np.nan], np.eye(2))
        check("covar rejects non-finite", False)
    except ValueError:
        check("covar rejects non-finite", True)
    wk = pd.DataFrame({"a": [1.0, 2, np.nan, 4]}, index=pd.to_datetime(["2024-01-05", "2024-01-06", "2024-01-08", "2024-01-09"]))
    cl, nd = clean_levels(wk)
    check("clean_levels drops weekend + NaN", nd == 2 and len(cl) == 2)

    # ridge via QR vs normal equations; lam=0 recovers exact beta
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 3))
    b = np.array([1.0, -2.0, 0.5])
    yv = X @ b
    check("ridge lam=0 recovers beta", np.allclose(ridge_qr(X, yv, 0.0), b, atol=1e-10))
    w_ne = np.linalg.solve(X.T @ X + 2.0 * np.eye(3), X.T @ yv)
    check("ridge QR == normal equations", np.allclose(ridge_qr(X, yv, 2.0), w_ne, atol=1e-10))

    # swaption (Pricing and Trading IRD 3rd ed. Ex 20.1): payer F 1.325 K 1.5 T 5 vol 52bp = 0.3816
    p = swaption_normal(1.325, 1.5, 5.0, 52, "payer")
    check("swaption fixture 0.3816", abs(p - 0.3816) < 5e-5, f"{p:.5f}")
    check("put-call parity", abs(p - swaption_normal(1.325, 1.5, 5.0, 52, "receiver") - (1.325 - 1.5)) < 1e-12)
    check("implied vol round trip", abs(implied_nvol_bp(p, 1.325, 1.5, 5.0) - 52) < 1e-6)
    try:
        implied_nvol_bp(0.1, 1.325, 1.5, 5.0, "receiver")  # receiver intrinsic = 0.175 > 0.1: no vol exists
        check("implied vol rejects sub-intrinsic price", False)
    except ValueError:
        check("implied vol rejects sub-intrinsic price", True)

    # log-linear DF: nodes 0/90/181 days = 1, .9975, .9945 -> DF(73d) = 0.99797174 (same source, s.11.1)
    dv = df_loglinear([0, 90, 181], [1.0, 0.9975, 0.9945], [73])[0]
    check("log-linear DF fixture", abs(dv - 0.99797174) < 1e-8, f"{dv:.8f}")

    # look-ahead truncation test must pass a causal signal and catch a leaking one
    s = pd.DataFrame({"x": np.arange(30.0) ** 1.5 % 7}, index=pd.bdate_range("2024-01-01", periods=30))
    probes = s.index[10:20]
    check("lookahead: causal passes", lookahead_check(lambda d: d.rolling(5).mean(), s, probes) == [])
    check("lookahead: leak caught", len(lookahead_check(lambda d: d.rolling(5, center=True).mean(), s, probes)) > 0
          and len(lookahead_check(lambda d: d.shift(-1), s, probes)) > 0
          and len(lookahead_check(lambda d: (d - d.mean()) / d.std(), s, probes)) > 0)  # full-sample z-score

    # partitioning
    parts = nested_parts(100, 4)
    work = [sum(range(a + 1, b + 1)) for a, b in zip(parts[:-1], parts[1:])]
    check("nested_parts balanced", parts[0] == 0 and parts[-1] == 100 and max(work) / min(work) < 1.1, str(work))
    lp = lin_parts(10, 3)
    check("lin_parts covers", lp[0] == 0 and lp[-1] == 10 and len(lp) == 4)
    ser = sorted(mp_map(_job_square, [dict(i=i) for i in range(8)], 1))
    par = sorted(mp_map(_job_square, [dict(i=i) for i in range(8)], 2))
    check("mp_map serial == parallel", ser == par == [(i, i * i) for i in range(8)])

    # manifest: sha256("abc")
    import os
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as fh:
        fh.write(b"abc")
    try:
        mh = run_manifest(1, [fh.name])["inputs"][fh.name]
    finally:
        os.unlink(fh.name)
    check("manifest sha256", mh == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    v = sub.add_parser("var", help="CoVaR, Euler allocation and PCA from a curve_par table")
    v.add_argument("--curve-par", required=True)
    v.add_argument("--curve-id", required=True)
    v.add_argument("--sens", required=True, help='tenor:ccy_per_bp pairs, e.g. "2Y:-10000,5Y:2500"')
    v.add_argument("--alpha", type=float, default=0.05)
    v.add_argument("--min-obs", type=int, default=100)
    v.set_defaults(fn=cmd_var)
    m = sub.add_parser("manifest", help="print run manifest with input hashes")
    m.add_argument("files", nargs="*")
    m.add_argument("--seed", type=int)
    m.set_defaults(fn=cmd_manifest)
    a = ap.parse_args(argv)
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.cmd:
        ap.print_help()
        return
    a.fn(a)


if __name__ == "__main__":
    main()
