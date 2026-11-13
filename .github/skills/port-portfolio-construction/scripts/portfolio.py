"""Combine RV trades into a book: risk decomposition, risk parity, HRP, constrained mean-variance,
PCA-neutral adjustment, VaR-minimising trades, effective bets, Fundamental Law.

Conventions (same as SKILL.md)
  * A "trade" is a package traded in its INTENDED direction. Its P&L series is signed accordingly, so a
    long-only weight w >= 0 means "as traded" (Spinu sign trick). Short a trade = flip the series first.
  * Risk vectors S are DV01 per bp, positive = receive fixed / long duration. Q = covariance of daily bp CHANGES.
  * w are risk multipliers on the trade's reference size (sum to 1 for rp/hrp/ivp unless --target-vol-ccy).

Usage
  python portfolio.py --pnl pnl.csv --method rp|hrp|ivp(inverse-vol)|mv [--alpha alpha.csv] [--lam 5] [--halflife 63]
         [--shrink 0.3] [--gross 1] [--cap 0.35] [--target-vol-ccy 100000] [--out book.csv]
  python portfolio.py --selftest
Input `pnl` (canonical): date, strategy_id, package_id, total_ccy (rows with package_id == ALL are ignored).
Input `alpha` (mv only): package_id, alpha  (expected P&L per unit weight, same ccy and horizon as the P&L series).
  mv rescales P&L to average-trade-vol units, so --lam is unit-free: lam ~ IR_target / (2 * wanted vol in those units).
Only numpy/pandas/scipy are required. ponytail: SLSQP mean-variance, fine to N~50; use a QP solver beyond that.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform


# ---------------------------------------------------------------- covariance input
def cov_from_pnl(pnl: pd.DataFrame, halflife: float | None = None, shrink: float = 0.0) -> pd.DataFrame:
    """Covariance of a (dates x trades) P&L frame. No demeaning (mean is noise at this horizon).
    halflife in observations (None = equal weight). shrink = weight on the diagonal target (0..1)."""
    x = pnl.dropna().to_numpy(float)
    t = len(x)
    if t <= x.shape[1]:
        raise ValueError(f"need more complete rows ({t}) than trades ({x.shape[1]})")
    wt = np.ones(t) if halflife is None else 0.5 ** (np.arange(t)[::-1] / halflife)
    wt = wt / wt.sum()
    s = (x * wt[:, None]).T @ x
    s = (1 - shrink) * s + shrink * np.diag(np.diag(s))
    return pd.DataFrame(s, index=pnl.columns, columns=pnl.columns)


# ---------------------------------------------------------------- risk decomposition
def risk_decomp(w, V) -> pd.DataFrame:
    """sigma_p, standalone risk (SAR), marginal (MCTR), contribution (CTR, sums to sigma_p), relative (RRC, sums to 1)."""
    names = getattr(V, "index", None)
    w = np.asarray(w, float)
    V = np.asarray(V, float)
    sp = float(np.sqrt(w @ V @ w))
    if not sp > 0:
        raise ValueError("book variance is zero or NaN (all-zero weights or degenerate covariance)")
    mctr = V @ w / sp
    ctr = w * mctr
    return pd.DataFrame({"w": w, "sar": np.abs(w) * np.sqrt(np.diag(V)), "mctr": mctr, "ctr": ctr,
                         "rrc": ctr / sp}, index=names).assign(sigma_p=sp)


def effective_bets(w, V) -> float:
    """exp(entropy) of PCA risk shares of the book (Meucci). N for N equal uncorrelated bets, 1 for one factor."""
    lam, W = np.linalg.eigh(np.asarray(V, float))
    f = W.T @ np.asarray(w, float)
    th = f ** 2 * np.clip(lam, 0, None)
    th = th / th.sum()
    th = th[th > 1e-12]
    return float(np.exp(-(th * np.log(th)).sum()))


# ---------------------------------------------------------------- weights
def inverse_vol(V, power: int = 1) -> np.ndarray:
    """power=1 inverse-vol (equal stand-alone vol), power=2 inverse-variance (optimal for diagonal V). Sums to 1."""
    v = np.sqrt(np.diag(np.asarray(V, float))) ** -power
    return v / v.sum()


def risk_parity(V, b=None, tol: float = 1e-10, maxit: int = 10000) -> np.ndarray:
    """Risk budgeting w_i (Vw)_i = b_i w'Vw, long-only. Spinu cyclical coordinate descent. b = 1/N -> equal risk."""
    V = np.asarray(V, float)
    n = len(V)
    b = np.full(n, 1.0 / n) if b is None else np.asarray(b, float) / np.sum(b)
    x = np.sqrt(b / np.diag(V))
    for _ in range(maxit):
        for i in range(n):
            a = V[i] @ x - V[i, i] * x[i]
            x[i] = (-a + np.sqrt(a * a + 4 * V[i, i] * b[i])) / (2 * V[i, i])
        w = x / x.sum()
        if np.abs(w * (V @ w) / (w @ V @ w) - b).max() < tol:
            break
    return w


def corr_distance(V) -> np.ndarray:
    """Lopez de Prado: d_ij = sqrt(0.5 (1 - rho_ij)); then distance of distances (Euclidean between rows of d)."""
    V = np.asarray(V, float)
    s = np.sqrt(np.diag(V))
    d = np.sqrt(0.5 * (1 - np.clip(V / np.outer(s, s), -1, 1)))
    return np.sqrt(((d[:, None, :] - d[None, :, :]) ** 2).sum(-1))


def hrp(V) -> np.ndarray:
    """Hierarchical risk parity: single-linkage tree on distance-of-distance, quasi-diagonal order, recursive
    bisection with inverse-variance cluster variance. 0 <= w <= 1, sum = 1."""
    V = np.asarray(V, float)
    n = len(V)
    if n == 1:
        return np.ones(1)
    order = list(leaves_list(linkage(squareform(corr_distance(V), checks=False), "single")))

    def cvar(idx):
        iv = 1 / np.diag(V)[idx]
        w = iv / iv.sum()
        return w @ V[np.ix_(idx, idx)] @ w

    w = np.ones(n)
    stack = [order]
    while stack:
        c = stack.pop()
        if len(c) < 2:
            continue
        h = len(c) // 2
        c1, c2 = c[:h], c[h:]
        v1, v2 = cvar(c1), cvar(c2)
        a = 1 - v1 / (v1 + v2)
        w[c1] *= a
        w[c2] *= 1 - a
        stack += [c1, c2]
    return w


def mean_variance(mu, V, lam: float = 1.0, w0=None, tc: float = 0.0, gross: float | None = None,
                  cap: float | None = None, prior=None, ridge: float = 0.0, long_only: bool = False) -> np.ndarray:
    """max mu'w - lam/2 w'Vw - tc*sum|w-w0| - ridge*||w-prior||^2   s.t. sum|w| <= gross, |w_i| <= cap.
    Unconstrained solution is w = V^-1 mu / lam. |.| is smoothed (1e-10) so SLSQP sees a differentiable problem."""
    mu, V = np.asarray(mu, float), np.asarray(V, float)
    n = len(mu)
    w0 = np.zeros(n) if w0 is None else np.asarray(w0, float)
    prior = w0 if prior is None else np.asarray(prior, float)
    sab = lambda z: np.sqrt(z * z + 1e-10)
    f = lambda w: -(mu @ w) + 0.5 * lam * w @ V @ w + tc * sab(w - w0).sum() + ridge * ((w - prior) ** 2).sum()
    cons = [] if gross is None else [{"type": "ineq", "fun": lambda w: gross - sab(w).sum()}]
    lo = 0.0 if long_only else (-cap if cap else None)
    bnds = [(lo, cap)] * n if (cap or long_only) else None
    r = minimize(f, w0 if np.any(w0) else np.full(n, 1e-3), method="SLSQP", bounds=bnds, constraints=cons,
                 options={"ftol": 1e-14, "maxiter": 1000})
    return r.x


# ---------------------------------------------------------------- factor neutrality
def pca_neutralise(t, E, free=None) -> np.ndarray:
    """Minimum-norm adjustment x so that E'(t+x) = 0 for the given loading columns E (n x k, e.g. PC1).
    x = -E_f (E_f'E_f)^-1 E'... restricted to `free` instruments (bool/idx; others fixed, e.g. keep 30Y).
    Returns the adjusted risk vector t + x. k PCs removed = k degrees of freedom removed (needs k < #free)."""
    t = np.asarray(t, float)
    E = np.asarray(E, float).reshape(len(t), -1)
    m = np.ones(len(t), bool) if free is None else np.isin(np.arange(len(t)), np.where(free)[0] if np.asarray(free).dtype == bool else free)
    Ef = E[m]
    lam = np.linalg.solve(Ef.T @ Ef, E.T @ t)
    x = np.zeros(len(t))
    x[m] = -Ef @ lam
    return t + x


def divide_by_loadings(t, e1) -> np.ndarray:
    """Naive PC1 neutralisation (valid only if sum(t) = 0): element-wise t / e1. Overall scale is arbitrary."""
    return np.asarray(t, float) / np.asarray(e1, float)


# ---------------------------------------------------------------- VaR-style trade suggestions
def covar(S, Q) -> float:
    return float(np.sqrt(np.asarray(S) @ np.asarray(Q) @ np.asarray(S)))


def var_allocation(S, Q) -> np.ndarray:
    """Euler / Aumann-Shapley allocation (1/c) diag(S) Q S; sums to c. Negative = diversifier (do not cut it)."""
    S, Q = np.asarray(S, float), np.asarray(Q, float)
    return S * (Q @ S) / covar(S, Q)


def var_min_trades(S, Q) -> np.ndarray:
    """Single-instrument VaR-minimising trade per bucket: T_i = -(QS)_i / q_ii. Only ONE is valid at a time."""
    S, Q = np.asarray(S, float), np.asarray(Q, float)
    return -(Q @ S) / np.diag(Q)


def var_min_subset(S, Q, idx) -> np.ndarray:
    """Multi-instrument VaR-minimising trade using only instruments idx (hedge/compression onto benchmarks)."""
    S, Q = np.asarray(S, float), np.asarray(Q, float)
    idx = list(idx)
    T = np.zeros(len(S))
    T[idx] = np.linalg.solve(Q[np.ix_(idx, idx)], -Q[idx, :] @ S)
    return T


# ---------------------------------------------------------------- Fundamental Law
def fundamental_law(ic: float, breadth: float) -> float:
    """IR = IC * sqrt(BR); BR = independent forecasts per year."""
    return ic * np.sqrt(breadth)


def breadth_from(ir: float, ic: float) -> float:
    return (ir / ic) ** 2


def combined_ic(ic: float, gamma: float) -> float:
    """Two sources with equal IC and correlation gamma."""
    return ic * np.sqrt(2 / (1 + gamma))


# ---------------------------------------------------------------- selftest
def _selftest() -> int:
    ok = True

    def chk(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok &= bool(cond)

    # Fundamental Law (Grinold-Kahn): 200 names x 2/yr, IC 0.0577 -> IR 1.154; breadth back-out; gamma 0.5 case
    chk("law IR=1.154", abs(fundamental_law(0.0577, 400) - 1.154) < 1e-3)
    chk("breadth=(IR/IC)^2", abs(breadth_from(1.154, 0.0577) - 400) < 1)
    chk("combined IC 0.0942", abs(combined_ic(0.0816, 0.5) - 0.0942) < 1e-4)

    # risk parity: equal correlation -> w proportional to 1/vol; budgets honoured; diagonal budget -> sqrt(b)/vol
    vol = np.array([1.0, 2.0, 4.0])
    C = np.full((3, 3), 0.3) + 0.7 * np.eye(3)
    V = np.outer(vol, vol) * C
    w = risk_parity(V)
    chk("rp equal corr -> inverse vol", np.allclose(w, (1 / vol) / (1 / vol).sum(), atol=1e-6))
    chk("rp RRC equal", np.allclose(risk_decomp(w, V)["rrc"], 1 / 3, atol=1e-6))
    b = np.array([0.5, 0.25, 0.25])
    Vd = np.diag(vol ** 2)
    wb = risk_parity(Vd, b)
    chk("rp budgets, diagonal", np.allclose(wb, np.sqrt(b) / vol / (np.sqrt(b) / vol).sum(), atol=1e-6))
    chk("rp equal vol uncorrelated -> 1/N", np.allclose(risk_parity(np.eye(4)), 0.25, atol=1e-8))

    # risk decomposition: sum CTR = sigma_p
    rd = risk_decomp([0.2, 0.5, 0.3], V)
    chk("sum CTR = sigma_p", abs(rd["ctr"].sum() - rd["sigma_p"].iloc[0]) < 1e-10)

    # HRP: Lopez de Prado distance example, and diagonal V -> inverse variance
    rho = np.array([[1, .7, .2], [.7, 1, -.2], [.2, -.2, 1.]])
    D = corr_distance(rho)
    chk("HRP distance-of-distance", abs(D[0, 1] - 0.5659) < 1e-4 and abs(D[0, 2] - 0.9747) < 1e-4
        and abs(D[1, 2] - 1.1225) < 1e-4)
    vd = np.array([1.0, 2.0, 4.0, 8.0])
    wh = hrp(np.diag(vd))
    chk("HRP diagonal -> inverse variance", np.allclose(wh, (1 / vd) / (1 / vd).sum(), atol=1e-9))
    wh2 = hrp(V)
    chk("HRP sums to 1, long-only", abs(wh2.sum() - 1) < 1e-12 and wh2.min() >= 0)

    # mean-variance unconstrained = V^-1 mu / lam
    mu = np.array([0.02, 0.01, 0.015])
    Vm = np.array([[0.04, 0.01, 0.0], [0.01, 0.09, 0.02], [0.0, 0.02, 0.0625]])
    wm = mean_variance(mu, Vm, lam=2.0)
    chk("MV analytic", np.allclose(wm, np.linalg.solve(Vm, mu) / 2.0, atol=1e-5))
    wc = mean_variance(mu, Vm, lam=2.0, cap=0.1, gross=0.25)
    chk("MV respects cap and gross", np.abs(wc).max() <= 0.1 + 1e-6 and np.abs(wc).sum() <= 0.25 + 1e-6)
    wr = mean_variance(mu, Vm, lam=2.0, prior=np.array([0.3, 0.3, 0.3]), ridge=1e6)
    chk("MV ridge pins to prior", np.allclose(wr, 0.3, atol=1e-3))

    # PCA neutralisation: PC1 of the source's 2Y/5Y/10Y/30Y example; pay 2s5s10s-style risk t=(-1,2,-1,0)
    e1 = np.array([0.65, 0.59, 0.44, 0.20])
    t = np.array([-1.0, 2.0, -1.0, 0.0])
    a = divide_by_loadings(t[:3], e1[:3])
    a = a * 1.94 / a[1]
    chk("divide-by-loadings ~[-0.89,1.94,-1.30]", np.allclose(a, [-0.89, 1.94, -1.30], atol=0.02))
    tm = pca_neutralise(t, e1, free=[0, 1, 2])
    chk("minimal adjustment ~[-1.07,1.94,-1.05,0]", np.allclose(tm, [-1.07, 1.94, -1.05, 0], atol=0.02))
    chk("PC1 exposure zero", abs(e1 @ tm) < 1e-12 and tm[3] == 0)
    t2 = pca_neutralise(t, e1)
    chk("full-norm = (I - ee'/e'e) t", np.allclose(t2, t - e1 * (e1 @ t) / (e1 @ e1)))

    # VaR: Darbyshire-style 4-bucket book (rounded Q): identities, then source-level numbers within rounding
    Q = np.array([[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]])
    S = np.array([-10000, 2500, 10000, -4000.0])
    c = covar(S, Q)
    chk("allocation sums to c", abs(var_allocation(S, Q).sum() - c) < 1e-6)
    T = var_min_trades(S, Q)
    chk("single trade zeroes marginal risk", all(abs((Q @ (S + np.eye(4)[i] * T[i]))[i]) < 1e-6 for i in range(4)))
    chk("best single trade cuts ~16% (2Y)", abs((covar(S + np.eye(4)[0] * T[0], Q) - c) / c + 0.16) < 0.02)
    T2 = var_min_subset(S, Q, [0, 2])
    chk("2Y&10Y dual ~(+8,562,-9,476)", abs(T2[0] - 8562) < 100 and abs(T2[2] + 9476) < 150)
    chk("dual >= every single", covar(S + T2, Q) <= min(covar(S + np.eye(4)[i] * T[i], Q) for i in range(4)))

    # effective bets
    chk("eff bets uncorrelated = N", abs(effective_bets(np.ones(5), np.eye(5)) - 5) < 1e-9)
    chk("eff bets one factor ~ 1", effective_bets(np.ones(3), np.ones((3, 3)) + 1e-9 * np.eye(3)) < 1.001)

    rng = np.random.default_rng(1)
    X = rng.multivariate_normal([0, 0], [[1, .5], [.5, 4]], 200000)

    # effective bets analytic: V=diag(1,4), w=(1,1) -> theta=(0.2,0.8) -> exp(entropy)
    chk("eff bets analytic 1.649", abs(effective_bets(np.ones(2), np.diag([1.0, 4.0])) - np.exp(-(0.2 * np.log(0.2) + 0.8 * np.log(0.8)))) < 1e-9)

    # mean-variance turnover cost: huge tc pins weights to w0
    wt_ = mean_variance(mu, Vm, lam=2.0, w0=np.array([0.1, 0.1, 0.1]), tc=10.0)
    chk("MV turnover cost pins to w0", np.allclose(wt_, 0.1, atol=1e-3))

    # EWMA weights the RECENT rows: vol 1 for 300 days then vol 3 for 60 days, half-life 20 -> close to 9, not 1
    r2 = np.random.default_rng(2)
    xs = np.concatenate([r2.normal(0, 1, 300), r2.normal(0, 3, 60)])
    ew = cov_from_pnl(pd.DataFrame({"a": xs}), halflife=20).iloc[0, 0]
    chk("EWMA favours recent obs", ew > 5.0)
    # shrink: diagonal untouched, off-diagonal scaled by (1 - shrink)
    cs = cov_from_pnl(pd.DataFrame(X[:5000], columns=["a", "b"]), shrink=0.4).to_numpy()
    c0 = cov_from_pnl(pd.DataFrame(X[:5000], columns=["a", "b"])).to_numpy()
    chk("shrink scales off-diagonals only", np.allclose(np.diag(cs), np.diag(c0)) and abs(cs[0, 1] - 0.6 * c0[0, 1]) < 1e-12)

    # cov_from_pnl: recovers a known covariance from simulated data
    cv = cov_from_pnl(pd.DataFrame(X, columns=["a", "b"]))
    chk("cov_from_pnl ~ truth", np.allclose(cv.to_numpy(), [[1, .5], [.5, 4]], atol=0.03))
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pnl")
    ap.add_argument("--method", default="rp", choices=["rp", "hrp", "ivp", "mv"])
    ap.add_argument("--alpha")
    ap.add_argument("--lam", type=float, default=5.0)
    ap.add_argument("--halflife", type=float)
    ap.add_argument("--shrink", type=float, default=0.3)
    ap.add_argument("--gross", type=float)
    ap.add_argument("--cap", type=float)
    ap.add_argument("--target-vol-ccy", type=float)
    ap.add_argument("--min-obs", type=int, default=100)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.pnl:
        ap.error("--pnl required")
    df = pd.read_parquet(a.pnl) if a.pnl.endswith(".parquet") else pd.read_csv(a.pnl)
    df = df[df["package_id"] != "ALL"]
    wide = df.pivot_table(index="date", columns="package_id", values="total_ccy", aggfunc="sum").dropna()
    if len(wide) < max(a.min_obs, wide.shape[1] + 1):
        sys.exit(f"need >= {max(a.min_obs, wide.shape[1] + 1)} complete overlapping days, have {len(wide)}: "
                 "use backtest P&L for young trades or drop them")
    V = cov_from_pnl(wide, a.halflife, a.shrink)
    if a.method == "rp":
        w = risk_parity(V.to_numpy())
    elif a.method == "hrp":
        w = hrp(V.to_numpy())
    elif a.method == "ivp":
        w = inverse_vol(V.to_numpy(), 1)  # inverse-vol = equal stand-alone risk
    else:
        if not a.alpha:
            sys.exit("--alpha required for mv")
        al = pd.read_csv(a.alpha).set_index("package_id")["alpha"].reindex(V.index)
        if al.isna().any():
            sys.exit(f"missing alpha for {list(al.index[al.isna()])}")
        sc = float(np.sqrt(np.diag(V.to_numpy()).mean()))  # unit-free lam: P&L measured in average-trade vols
        w = mean_variance(al.to_numpy() / sc, V.to_numpy() / sc ** 2, a.lam, gross=a.gross, cap=a.cap)
    if a.target_vol_ccy:
        w = w * a.target_vol_ccy / np.sqrt(w @ V.to_numpy() @ w)
    out = risk_decomp(w, V)
    out.index.name = "package_id"
    out["eff_bets"] = effective_bets(w, V.to_numpy())
    print(out.round(4).to_string())
    if a.out:
        out.to_csv(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
