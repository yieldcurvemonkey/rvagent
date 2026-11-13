#!/usr/bin/env python3
"""Signal IC/IR by horizon, IC decay half-life, signal turnover, and correlation-aware signal combination.

Identities (Grinold & Kahn, Active Portfolio Management, 2nd ed., Ch. 6, 10, 11, 13):
  combine   w = R^-1 x,  x_comb = sqrt(x' R^-1 x)
            x = ICs of standardized scores and R = score correlations, or
            x = IRs of unit-risk signal strategies and R = their return correlations.
  decay     IC_k = IC_1 * delta^(k-1),  half-life = ln 0.5 / ln delta   (k = periods ahead)
  horizon   corr(score, return summed over h) is proportional to (1 - e^-x)/sqrt(x), x = h ln2 / HL.
            Peak at x = 1.2564, i.e. h* = 1.81 HL (value 0.6382). Reconstructed: the book prints the
            maximum (0.6382 at 1.257) but the formula is an image.
  shrink    b' = b * T IC^2 / (1 + T IC^2)   (T = independent observations)
  turnover  mean|ds| / mean|s| = sqrt(2 (1 - rho)) for a Gaussian AR(1) score with lag-1 autocorrelation rho

CLI
  python signal_ic.py --signals signals.parquet --returns unit_returns.csv --strategy fly_mr_v1,carry_v1 \
      --horizons 1,5,21,63 --max-lag 20 --combine-h 21 [--flip fly_mr_v1] [--delay 1]

  --signals  canonical `signals` table (date, strategy_id, package_id, value[, zscore]). Per strategy, zscore is
             used when it is filled on every row, otherwise value (the two are never mixed).
  --returns  date, package_id, ret: one-period return of the UNIT package always held on the same side
             (bp or P&L per unit risk), dated at the END of the period. Never use P&L of a strategy that
             already trades on the signal.
  --flip     strategies to negate so that a positive score means expected positive `ret`
             (e.g. a mean-reversion z-score of a level).
  --delay    1 = first return counted is the period ending t+1 (signal at close t, trade at close t).
             Use 2 to mirror "execute at close t+1".
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq, curve_fit

PEAK_X = brentq(lambda x: np.exp(x) - 1.0 - 2.0 * x, 0.5, 3.0)  # argmax of (1-e^-x)/sqrt(x)


# ---------------------------------------------------------------- closed-form identities
def combine(x, R):
    """Weights w = R^-1 x and combined value sqrt(x' R^-1 x) (IC on scores, or IR on unit-risk strategies)."""
    x = np.asarray(x, float)
    w = np.linalg.solve(np.asarray(R, float), x)
    return w, float(np.sqrt(x @ w))


def shrink_factor(ic, n_obs):
    """Bayesian shrink of a forecast coefficient towards 0: T IC^2 / (1 + T IC^2)."""
    t = n_obs * np.square(ic)
    return t / (1.0 + t)


def half_life(delta):
    return float(np.log(0.5) / np.log(delta))


def delta_from_half_life(hl):
    return 0.5 ** (1.0 / hl)


def horizon_curve(x):
    """Shape of corr(score, cumulative return) vs horizon x = h ln2 / HL."""
    x = np.asarray(x, float)
    return (1.0 - np.exp(-x)) / np.sqrt(x)


def best_horizon(hl):
    """Evaluation / holding horizon that maximises the score's correlation with cumulative return."""
    return PEAK_X * hl / np.log(2.0)


# ---------------------------------------------------------------- estimation on panels (date x package)
def nw_t(u, lag):
    """Newey-West t-stat of mean(u) with Bartlett weights."""
    u = np.asarray(u, float)
    u = u[np.isfinite(u)]
    n = u.size
    e = u - u.mean()
    s = e @ e / n
    for k in range(1, min(int(lag), n - 1) + 1):
        s += 2.0 * (1.0 - k / (lag + 1.0)) * (e[k:] @ e[:-k]) / n
    return float(u.mean() / np.sqrt(s / n))


def forward_returns(ret: pd.DataFrame, h: int, delay: int = 1) -> pd.DataFrame:
    """Sum of ret_{t+delay} .. ret_{t+delay+h-1}, aligned at t."""
    return ret.rolling(h).sum().shift(-(delay + h - 1))


def _std(df):
    return (df - df.mean()) / df.std()


def ic_stats(S: pd.DataFrame, F: pd.DataFrame, nw_lag: int = 0, rank: bool = True) -> dict:
    """Time-series (within-package) IC pooled across packages, NW t, per-package median, cross-sectional IC,
    quintile monotonicity. S = scores, F = forward returns, both wide date x package."""
    S, F = S.align(F, join="inner")
    m = S.notna() & F.notna()
    S, F = S.where(m), F.where(m)
    a, b = (S.rank(), F.rank()) if rank else (S, F)
    za, zb = _std(a), _std(b)
    prod = za * zb
    per_pkg = prod.sum() / (prod.count() - 1)
    u = prod.mean(axis=1).dropna()  # per-date mean of products -> pooled-within IC series
    out = {"ic": float(u.mean()), "nw_t": nw_t(u.values, nw_lag), "ic_pkg_median": float(per_pkg.median()),
           "n_dates": int(u.size), "cs_ic": np.nan, "cs_t": np.nan}
    if S.shape[1] >= 3:
        cs = S.rank(axis=1).corrwith(F.rank(axis=1), axis=1)[m.sum(axis=1) >= 3].dropna()
        if cs.size > 10:
            out["cs_ic"], out["cs_t"] = float(cs.mean()), nw_t(cs.values, nw_lag)
    v, f = za.values.ravel(), F.values.ravel()
    ok = np.isfinite(v) & np.isfinite(f)
    if ok.sum() >= 50:
        q = pd.qcut(v[ok], 5, labels=False, duplicates="drop")
        qm = pd.Series(f[ok]).groupby(q).mean().values
        out["q_steps_up"] = int((np.diff(qm) > 0).sum())
        out["q5_minus_q1"] = float(qm[-1] - qm[0])
    return out


def ic_decay(S: pd.DataFrame, ret: pd.DataFrame, max_lag: int = 20, rank: bool = True):
    """IC_k of s_t vs the single-period return ending t+k (non-overlapping), k = 1..max_lag,
    and the NLS fit IC_k = a * delta^(k-1)."""
    ks = np.arange(1, max_lag + 1)
    ics = np.array([ic_stats(S, ret.shift(-k), rank=rank)["ic"] for k in ks])
    ok = np.isfinite(ics)
    if ok.sum() < 3:  # short history: no fit
        return ks, ics, np.nan, np.nan, np.nan
    try:
        (a, d), _ = curve_fit(lambda k, a, d: a * d ** (k - 1), ks[ok], ics[ok],
                              p0=(float(np.clip(ics[ok][0], -0.99, 0.99)), 0.8),
                              bounds=([-1.0, 1e-6], [1.0, 1.0 - 1e-9]))
    except RuntimeError:
        return ks, ics, np.nan, np.nan, np.nan
    return ks, ics, float(a), float(d), half_life(d)


def persistence(S: pd.DataFrame) -> dict:
    """Lag-1 autocorrelation of the score, its half-life and turnover (mean|ds|/mean|s|) vs AR(1) theory."""
    rho = float(np.nanmedian([S[c].autocorr(1) for c in S.columns]))
    z = _std(S)
    to = float(np.nanmean(np.abs(z.diff()).values) / np.nanmean(np.abs(z).values))
    return {"rho": rho, "score_half_life": half_life(rho) if 0 < rho < 1 else np.nan,
            "turnover": to, "turnover_ar1": float(np.sqrt(2.0 * (1.0 - rho)))}


def lag_rule(ic1, ic2, rho, tol=0.1):
    """Grinold-Kahn: add the old score if IC2 > rho*IC1 (diversify), subtract if IC2 < rho*IC1 (hedge)."""
    edge = ic2 - rho * ic1
    if abs(edge) <= tol * abs(ic1):
        return "latest score only"
    return "smooth: add lagged score" if edge > 0 else "hedge: subtract part of lagged score (use changes)"


def score_corr(frames: dict) -> pd.DataFrame:
    """Correlation of standardized scores pooled over (date, package)."""
    cols = {k: _std(v).stack() for k, v in frames.items()}
    return pd.DataFrame(cols).dropna().corr()


# ---------------------------------------------------------------- self-test (known answers)
def selftest() -> int:
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.4f} want {want:.4f} (tol {tol})")
        if not ok:
            fails.append(name)

    # 1. Grinold-Kahn Ch.10 binary model: vol 9, Var g 16, Var g' 25, Cov(g,g') 5, Cov(r,g) 3, Cov(r,g') 4.
    ic = np.array([3 / (9 * 4), 4 / (9 * 5)])
    w, icc = combine(ic, [[1, 0.25], [0.25, 1]])
    check("G-K two-signal combined IC", icc, 0.1090, 5e-4)
    c = w * 9 / np.array([4, 5])  # back to raw-unit regression coefficients
    check("G-K regression coef c1", c[0], 0.1467, 5e-4)
    check("G-K regression coef c2", c[1], 0.1307, 5e-4)
    # 2. Ch.6: equal ICs 0.0816, correlation 0.5 -> 0.0942
    check("G-K equal-IC pair", combine([0.0816, 0.0816], [[1, .5], [.5, 1]])[1], 0.0942, 2e-4)
    # 3. Ch.13 Now/Later managers, IR 1.5 / 1.2
    for rho, want in ((0.7, 0.815), (0.85, 1.185)):
        w, _ = combine([1.5, 1.2], [[1, rho], [rho, 1]])
        check(f"Now weight at rho={rho}", w[0] / w.sum(), want, 2e-3)
    check("Now/Later IR at rho=0.5", combine([1.5, 1.2], [[1, .5], [.5, 1]])[1], 1.59, 5e-3)
    # 4. decay constants, horizon peak, shrinkage table 11.4
    check("delta for 1-quarter half-life (monthly)", delta_from_half_life(3), 0.7937, 1e-4)
    check("horizon peak x", PEAK_X, 1.257, 1e-3)
    check("horizon peak value", float(horizon_curve(PEAK_X)), 0.6382, 1e-4)
    check("shrink T=36 IC=0.05", shrink_factor(0.05, 36), 0.08, 5e-3)
    check("shrink T=120 IC=0.10", shrink_factor(0.10, 120), 0.55, 5e-3)

    # 5. simulation with planted IC_1 = 0.10 and delta = 0.7937 (half-life 3 periods), 4 packages
    rng = np.random.default_rng(7)
    n, P, K, d, ic1 = 40_000, 4, 40, 0.7937, 0.10
    coef = ic1 * d ** np.arange(K)
    sig_e = np.sqrt(1.0 - (coef ** 2).sum())
    s = rng.standard_normal((n, P))
    r = np.zeros((n, P))
    for k in range(1, K + 1):
        r[k:] += coef[k - 1] * s[:-k]
    r += sig_e * rng.standard_normal((n, P))
    idx = pd.bdate_range("1990-01-01", periods=n)
    S, R = pd.DataFrame(s, idx), pd.DataFrame(r, idx)
    se = 1.0 / np.sqrt(n * P)
    st = ic_stats(S, forward_returns(R, 1), rank=False)
    check("sim IC at h=1 (4 SE)", st["ic"], ic1, 4 * se)
    _, ics, a, dd, hl = ic_decay(S, R, max_lag=10, rank=False)
    check("sim IC_2 (4 SE)", ics[1], ic1 * d, 4 * se)
    check("sim fitted half-life", hl, 3.0, 0.5)
    # 6. AR(1) score turnover: rho 0.9 -> sqrt(0.2)
    x = np.zeros(100_000)
    e = rng.standard_normal(x.size)
    for t in range(1, x.size):
        x[t] = 0.9 * x[t - 1] + e[t]
    pr = persistence(pd.DataFrame({"a": x}))
    check("AR(1) turnover", pr["turnover"], np.sqrt(0.2), 0.01)
    check("AR(1) turnover theory", pr["turnover_ar1"], np.sqrt(0.2), 0.01)
    check("AR(1) score half-life", pr["score_half_life"], np.log(0.5) / np.log(0.9), 0.3)
    # 7. combination on estimated inputs: realized IC of w'z equals sqrt(IC' R^-1 IC)
    z1 = rng.standard_normal(200_000)
    z2 = 0.6 * z1 + 0.8 * rng.standard_normal(z1.size)
    y = 0.08 * z1 + 0.06 * z2 + rng.standard_normal(z1.size)
    Z = np.c_[z1, z2]
    ic_hat = np.array([np.corrcoef(Z[:, i], y)[0, 1] for i in range(2)])
    w, icc = combine(ic_hat, np.corrcoef(Z.T))
    check("combined IC = realized IC of w'z", float(np.corrcoef(Z @ w, y)[0, 1]), icc, 0.005)
    # 8. Newey-West on 5-period overlapping sums of iid shocks: gamma_k = 5 - k, so the Bartlett (lag 4)
    #    long-run variance is 5 + 2(0.8*4 + 0.6*3 + 0.4*2 + 0.2*1) = 17 and t_plain / t_NW = sqrt(17/5).
    e = rng.standard_normal(400_000)
    u = 0.02 + np.convolve(e, np.ones(5), "valid")
    check("NW t ratio (Bartlett lag 4, MA(4))", nw_t(u, 0) / nw_t(u, 4), np.sqrt(17 / 5), 0.05)
    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "PASSED")
    return 1 if fails else 0


# ---------------------------------------------------------------- CLI
def _read(path):
    return pd.read_parquet(path) if str(path).lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--signals")
    ap.add_argument("--returns")
    ap.add_argument("--strategy", default="", help="comma list of strategy_id (default: all)")
    ap.add_argument("--flip", default="", help="comma list of strategy_id to negate")
    ap.add_argument("--horizons", default="1,5,21,63")
    ap.add_argument("--max-lag", type=int, default=20)
    ap.add_argument("--combine-h", type=int, default=21)
    ap.add_argument("--delay", type=int, default=1)
    ap.add_argument("--pearson", action="store_true", help="Pearson instead of Spearman IC")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.signals and a.returns):
        ap.error("--signals and --returns are required (or --selftest)")

    sig, ret = _read(a.signals), _read(a.returns)
    for df in (sig, ret):
        df["date"] = pd.to_datetime(df["date"])
    R = ret.pivot_table(index="date", columns="package_id", values="ret").sort_index()
    strategies = [s for s in a.strategy.split(",") if s] or sorted(sig["strategy_id"].unique())
    flips = {s for s in a.flip.split(",") if s}
    hs = [int(h) for h in a.horizons.split(",")]
    rank = not a.pearson

    frames, rows, ic_comb = {}, [], {}
    for sid in strategies:
        sub = sig[sig["strategy_id"] == sid]
        col = "zscore" if "zscore" in sub and sub["zscore"].notna().all() else "value"  # never mix z and bp
        print(f"[{sid}] score column: {col}")
        S = sub.pivot_table(index="date", columns="package_id", values=col)
        S = (-S if sid in flips else S).reindex(R.index)
        frames[sid] = S
        for h in hs:
            st = ic_stats(S, forward_returns(R, h, a.delay), nw_lag=h - 1, rank=rank)
            st["shrink"] = float(shrink_factor(st["ic"], st["n_dates"] / h))
            rows.append({"strategy": sid, "h": h, **st})
        ks, ics, amp, dlt, hl = ic_decay(S, R.shift(-(a.delay - 1)), a.max_lag, rank)
        pr = persistence(S)
        print(f"\n[{sid}] IC_1 {ics[0]:+.4f}  IC_2 {ics[1]:+.4f}  fit a {amp:+.4f} delta {dlt:.4f}"
              f"  IC half-life {hl:.1f}  best horizon ~{best_horizon(hl):.1f} periods")
        print(f"[{sid}] score rho {pr['rho']:.3f}  score half-life {pr['score_half_life']:.1f}"
              f"  turnover {pr['turnover']:.3f}/period (AR1 {pr['turnover_ar1']:.3f})"
              f"  -> {lag_rule(ics[0], ics[1], pr['rho'])}")
        st = ic_stats(S, forward_returns(R, a.combine_h, a.delay), rank=rank)
        ic_comb[sid] = st["ic"] * shrink_factor(st["ic"], st["n_dates"] / a.combine_h)

    print("\nIC by horizon (ic = within-package pooled; nw_t lag h-1; cs = cross-sectional):")
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    if len(frames) >= 2:
        C = score_corr(frames).loc[strategies, strategies]
        x = np.array([ic_comb[s] for s in strategies])
        w, icc = combine(x, C.values)
        ones = np.ones(len(x))
        print(f"\nScore correlation:\n{C.round(2).to_string()}")
        print(f"\nCombination at h={a.combine_h} (shrunk ICs): "
              + ", ".join(f"{s} IC {v:+.4f} w {wi / np.abs(w).sum():+.2f}" for s, v, wi in zip(strategies, x, w)))
        print(f"combined IC {icc:.4f} | equal-weight IC {ones @ x / np.sqrt(ones @ C.values @ ones):.4f}"
              f" | if independent {np.sqrt((x ** 2).sum()):.4f}")
        for i, s in enumerate(strategies):
            keep = [j for j in range(len(x)) if j != i]
            _, ic_wo = combine(x[keep], C.values[np.ix_(keep, keep)]) if keep else (None, 0.0)
            print(f"  marginal IC^2 of {s}: {icc ** 2 - ic_wo ** 2:+.5f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
