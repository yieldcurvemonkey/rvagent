#!/usr/bin/env python3
"""Regime detection for rates RV series (spreads, flies, swap rates, hedge residuals).

Functions (numpy / pandas in, numpy / pandas out):
  fit_markov_switching  Gaussian Markov-switching regression (HMM) by EM: Hamilton filter + Kim smoother.
  ergodic_probs         long-run share of time in each state.
  expected_durations    1 / (1 - p_jj), in observations.
  vol_regime            log realised-vol z-score with hysteresis: -1 low, 0 normal, +1 high.
  find_breaks           Bai-Perron style multiple breaks (mean or regression) by dynamic programming, m by BIC.
  chow_test             F test for a break at a known date.
  cusum_events          symmetric CUSUM filter on first differences (live "run of size h" alarm).

Conventions: values in bp (curve_par par_rate_pct is converted x100). Transition matrix P is row-stochastic,
P[i, j] = Prob(s_t = j | s_{t-1} = i) (rows = from). State 0 = lowest-volatility state. Filtered probabilities use
data up to t (but full-sample parameters); smoothed probabilities use the whole sample: never trade on them.

CLI (canonical `curve_par` or `signals` table, CSV or Parquet):
  python regimes.py --input curve_par.parquet --curve-id USD-SOFR --tenor 10Y --model vol
  python regimes.py --input signals.csv --package-id USD-SOFR:2Y5Y10Y:fly --model breaks --max-breaks 4
  python regimes.py --input signals.csv --package-id USD-SOFR:2Y5Y10Y:fly --strategy-id fly_mr_v1 --model ms --out ms.csv
  python regimes.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats


# --------------------------------------------------------------------------- Markov chain facts
def ergodic_probs(P) -> np.ndarray:
    """Solve pi = P' pi, sum(pi) = 1 (Hamilton 22.2.26 with row-stochastic P)."""
    P = np.asarray(P, float)
    k = len(P)
    A = np.vstack([np.eye(k) - P.T, np.ones(k)])
    return np.linalg.lstsq(A, np.r_[np.zeros(k), 1.0], rcond=None)[0]


def expected_durations(P) -> np.ndarray:
    return 1.0 / (1.0 - np.diag(np.asarray(P, float)))


# --------------------------------------------------------------------------- Markov switching (EM)
def _estep(y, mu, sig, P):
    """Scaled Hamilton filter, Kim smoother and expected transition counts. mu: (T, k); sig: (k,)."""
    T, k = mu.shape
    logd = stats.norm.logpdf(y[:, None], mu, sig)
    mx = logd.max(1, keepdims=True)
    dens = np.exp(logd - mx)
    filt, pred = np.empty((T, k)), np.empty((T, k))
    p, ll = ergodic_probs(P), 0.0
    for t in range(T):
        pred[t] = p                       # xi_{t|t-1}
        num = p * dens[t]
        c = num.sum()
        filt[t] = num / c                 # xi_{t|t}
        ll += np.log(c) + mx[t, 0]
        p = filt[t] @ P                   # xi_{t+1|t}
    sm = np.empty((T, k))
    sm[-1] = filt[-1]
    for t in range(T - 2, -1, -1):        # Kim: xi_{t|T} = xi_{t|t} * P [xi_{t+1|T} / xi_{t+1|t}]
        sm[t] = filt[t] * (P @ (sm[t + 1] / pred[t + 1]))
        sm[t] /= sm[t].sum()
    trans = (filt[:-1, :, None] * P[None] * (sm[1:] / pred[1:])[:, None, :]).sum(0)
    return filt, sm, trans, ll


def _mstep(y, X, g, switching_var, floor):
    k = g.shape[1]
    beta, ss = np.empty((k, X.shape[1])), np.empty(k)
    for j in range(k):
        Xw = X * g[:, j, None]
        beta[j] = np.linalg.lstsq(Xw.T @ X, Xw.T @ y, rcond=None)[0]   # probability-weighted OLS
        ss[j] = (g[:, j] * (y - X @ beta[j]) ** 2).sum()
    var = ss / g.sum(0) if switching_var else np.full(k, ss.sum() / len(y))
    return beta, np.sqrt(np.maximum(var, floor))


def fit_markov_switching(y, X=None, k: int = 2, switching_var: bool = True, n_starts: int = 5,
                         max_iter: int = 500, tol: float = 1e-8, seed: int = 0) -> dict:
    """y_t = x_t' beta_{s_t} + sigma_{s_t} e_t. X=None -> switching mean (and variance).
    Use X = [1, y_{t-1}] for MS-AR(1), X = [1, dx_t] for a switching hedge ratio."""
    y = np.asarray(y, float).ravel()
    T = len(y)
    X = np.ones((T, 1)) if X is None else np.asarray(X, float).reshape(T, -1)
    floor = 1e-4 * y.var()                # Hamilton: the mixture likelihood is unbounded as sigma -> 0
    r0 = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    rng = np.random.default_rng(seed)
    best = None
    for s in range(n_starts):
        if s == 0:                        # start from bands of local |residual| (a vol-sorted guess)
            a = pd.Series(np.abs(r0)).rolling(21, min_periods=1, center=True).mean().rank(pct=True).to_numpy()
            g = np.eye(k)[np.minimum((a * k).astype(int), k - 1)]
        else:
            g = rng.dirichlet(np.ones(k), T)
        P = np.full((k, k), 0.1 / max(k - 1, 1))
        np.fill_diagonal(P, 0.9)
        ll_old = -np.inf
        for _ in range(max_iter):
            beta, sig = _mstep(y, X, g, switching_var, floor)
            filt, g, trans, ll = _estep(y, X @ beta.T, sig, P)
            if ll - ll_old <= tol * abs(ll):
                break
            ll_old = ll
            P = trans / trans.sum(1, keepdims=True)
        if best is None or ll > best[0]:
            best = (ll, P, beta, sig, filt, g)
    ll, P, beta, sig, filt, sm = best
    o = np.argsort(sig) if switching_var else np.argsort(beta[:, 0])
    P = P[o][:, o]
    n_par = k * X.shape[1] + (k if switching_var else 1) + k * (k - 1)
    return dict(P=P, beta=beta[o], sigma=sig[o], filtered=filt[:, o], smoothed=sm[:, o], loglik=ll,
                bic=-2 * ll + n_par * np.log(T), durations=expected_durations(P), ergodic=ergodic_probs(P))


# --------------------------------------------------------------------------- rule-based vol regime
def vol_regime(dy: pd.Series, win: int = 21, z_win: int = 504, z_hi: float = 1.0, z_lo: float = -1.0,
               band: float = 0.5) -> pd.DataFrame:
    """dy: daily changes in bp. Trailing windows only (causal); shift by one day before trading on it."""
    rv = dy.rolling(win).std()
    lrv = np.log(rv.where(rv > 0))
    roll = lrv.rolling(z_win, min_periods=z_win // 2)
    z = (lrv - roll.mean()) / roll.std()
    return pd.DataFrame({"rv_bp": rv, "z": z, "state": _hysteresis(z.to_numpy(), z_hi, z_lo, band)}, index=dy.index)


def _hysteresis(z, z_hi, z_lo, band) -> list:
    """Enter high at z >= z_hi, leave below z_hi - band; enter low at z <= z_lo, leave above z_lo + band."""
    state, out = 0, []
    for v in z:
        if np.isnan(v):
            out.append(np.nan)
            continue
        if (state == 1 and v < z_hi - band) or (state == -1 and v > z_lo + band):
            state = 0
        if state == 0:
            state = 1 if v >= z_hi else (-1 if v <= z_lo else 0)
        out.append(state)
    return out


# --------------------------------------------------------------------------- change points
def _ssr_ending_at(j, h, Cxx, Cxy, Cyy):
    """SSR of segments [i, j) for every i in 0..j-h, from cumulative moment sums."""
    i = np.arange(0, j - h + 1)
    XX, Xy = Cxx[j] - Cxx[i], Cxy[j] - Cxy[i]
    b = np.linalg.solve(XX + 1e-12 * np.eye(XX.shape[-1]), Xy[..., None])[..., 0]
    return (Cyy[j] - Cyy[i]) - (Xy * b).sum(1)


def find_breaks(y, X=None, max_breaks: int = 5, trim: float = 0.15, min_size: int | None = None) -> dict:
    """Global SSR-minimising partition for m = 0..max_breaks breaks (Bai-Perron); m chosen by BIC.
    Returns break indices (first observation of each new regime) and per-segment coefficients."""
    y = np.asarray(y, float).ravel()
    T = len(y)
    X = np.ones((T, 1)) if X is None else np.asarray(X, float).reshape(T, -1)
    p = X.shape[1]
    h = min_size or max(int(trim * T), p + 2)
    M = min(max_breaks, T // h - 1)
    Cxx = np.concatenate([np.zeros((1, p, p)), np.cumsum(X[:, :, None] * X[:, None, :], 0)])
    Cxy = np.concatenate([np.zeros((1, p)), np.cumsum(X * y[:, None], 0)])
    Cyy = np.r_[0.0, np.cumsum(y * y)]
    cost = np.full((M + 1, T + 1), np.inf)
    arg = np.zeros((M + 1, T + 1), int)
    for j in range(h, T + 1):
        s = _ssr_ending_at(j, h, Cxx, Cxy, Cyy)       # s[i] = SSR(i, j)
        cost[0, j] = s[0]
        for m in range(1, M + 1):
            c = cost[m - 1, : j - h + 1] + s
            arg[m, j] = int(np.argmin(c))
            cost[m, j] = c[arg[m, j]]
    bic = np.array([T * np.log(cost[m, T] / T) + ((m + 1) * p + m) * np.log(T) for m in range(M + 1)])
    m = int(np.argmin(bic))
    brk, j = [], T
    for mm in range(m, 0, -1):
        j = arg[mm, j]
        brk.append(j)
    brk = sorted(brk)
    edges = [0] + brk + [T]
    segs = []
    for a, b in zip(edges[:-1], edges[1:]):
        coef = np.linalg.lstsq(X[a:b], y[a:b], rcond=None)[0]
        segs.append(dict(start=a, end=b, n=b - a, coef=coef, resid_sd=float(np.std(y[a:b] - X[a:b] @ coef))))
    return dict(breaks=brk, segments=segs, bic=bic, n_breaks=m, min_size=h)


def chow_test(y, X, k_break: int) -> tuple[float, float]:
    """F = [(S_pooled - S1 - S2)/p] / [(S1 + S2)/(T - 2p)] ~ F(p, T - 2p). Assumes equal variances."""
    y = np.asarray(y, float).ravel()
    X = np.asarray(X, float).reshape(len(y), -1)
    T, p = X.shape

    def ssr(a, b):
        r = y[a:b] - X[a:b] @ np.linalg.lstsq(X[a:b], y[a:b], rcond=None)[0]
        return float(r @ r)
    s1, s2 = ssr(0, k_break), ssr(k_break, T)
    F = ((ssr(0, T) - s1 - s2) / p) / ((s1 + s2) / (T - 2 * p))
    return F, float(stats.f.sf(F, p, T - 2 * p))


def cusum_events(x, h: float) -> list[int]:
    """Symmetric CUSUM filter on first differences (E_{t-1}[x_t] = x_{t-1}); index of each event, then reset."""
    x = np.asarray(x, float)
    sp = sn = 0.0
    ev = []
    for i in range(1, len(x)):
        d = x[i] - x[i - 1]
        sp, sn = max(0.0, sp + d), min(0.0, sn + d)
        if sn < -h:
            sn = 0.0
            ev.append(i)
        elif sp > h:
            sp = 0.0
            ev.append(i)
    return ev


# --------------------------------------------------------------------------- I/O
def load_series(path, curve_id=None, tenor=None, start="0D", snap=None, package_id=None,
                strategy_id=None) -> pd.Series:
    df = pd.read_parquet(path) if str(path).lower().endswith((".parquet", ".pq")) else pd.read_csv(path)
    if "data_ok" in df.columns:
        df = df[df["data_ok"].fillna(True).astype(bool)]
    if "par_rate_pct" in df.columns:                     # curve_par
        q = (df["curve_id"] == curve_id) & (df["tenor"] == tenor) & (df["start"].astype(str) == start)
        if snap:
            q &= df["snap"] == snap
        d = df[q]
        if d["snap"].nunique() > 1:
            sys.exit("several snaps matched: pass --snap (never mix snaps in one series)")
        s = pd.Series(d["par_rate_pct"].to_numpy() * 100.0, index=pd.to_datetime(d["date"]))
    elif "package_id" in df.columns:                     # signals
        q = df["package_id"] == package_id
        if snap:
            q &= df["snap"] == snap
        if strategy_id:
            q &= df["strategy_id"] == strategy_id
        d = df[q]
        if "unit" in d.columns and set(d["unit"].dropna()) - {"bp"}:
            print(f"warning: unit is {sorted(set(d['unit'].dropna()))}, not bp", file=sys.stderr)
        s = pd.Series(d["value"].to_numpy(float), index=pd.to_datetime(d["date"]))
    else:
        sys.exit("input must be a canonical curve_par or signals table")
    s = s.dropna()                                       # NaN would poison the cumulative sums in find_breaks
    if s.empty:
        sys.exit("no rows matched the filters")
    if s.index.duplicated().any():
        sys.exit("duplicate dates after filtering: pass --snap / --strategy-id")
    return s.sort_index().astype(float)


def run_cli(a) -> None:
    s = load_series(a.input, a.curve_id, a.tenor, a.start, a.snap, a.package_id, a.strategy_id)
    on_changes = a.on == "changes" or (a.on == "auto" and a.model in ("ms", "vol"))
    x = s.diff().dropna() if on_changes else s
    print(f"series: {len(s)} obs {s.index[0].date()}..{s.index[-1].date()}; model={a.model} on "
          f"{'daily changes' if on_changes else 'levels'} (bp)")
    if a.model == "ms":
        if len(x) < 750:
            print(f"warning: {len(x)} obs < 750; HMM states and durations will be unstable", file=sys.stderr)
        r = fit_markov_switching(x.to_numpy(), k=a.states)
        np.set_printoptions(precision=4, suppress=True)
        print("P (rows=from):\n", r["P"], "\nsigma:", r["sigma"], "mean:", r["beta"][:, 0],
              "\nexpected durations (obs):", r["durations"], "ergodic:", r["ergodic"], "BIC:", round(r["bic"], 1))
        out = pd.DataFrame(r["filtered"], index=x.index, columns=[f"p_state{j}" for j in range(a.states)])
        out.insert(0, "value_bp", x)
        out["state"] = out.filter(like="p_state").to_numpy().argmax(1)
    elif a.model == "vol":
        out = vol_regime(x, win=a.win, z_win=a.z_win)
    elif on_changes:                                       # breaks in the mean of changes / residuals
        r = find_breaks(x.to_numpy(), max_breaks=a.max_breaks, trim=a.trim)
        print("BIC by number of breaks:", np.round(r["bic"], 1), "-> chosen", r["n_breaks"])
        out = pd.DataFrame([dict(start=x.index[g["start"]].date(), end=x.index[g["end"] - 1].date(), n=g["n"],
                                 mean_bp=g["coef"][0], sd_bp=g["resid_sd"]) for g in r["segments"]])
        out["shift_vs_prev_bp"] = out["mean_bp"].diff()
    else:                                                  # levels: AR(1) per regime, y_t = c + phi y_{t-1}
        v = x.to_numpy()                                   # (iid-error BIC on raw persistent levels over-fits)
        r = find_breaks(v[1:], np.c_[np.ones(len(v) - 1), v[:-1]], max_breaks=a.max_breaks, trim=a.trim)
        print("BIC by number of breaks:", np.round(r["bic"], 1), "-> chosen", r["n_breaks"])
        rows = []
        for g in r["segments"]:
            c, phi = g["coef"]
            ok = 0 < phi < 1
            rows.append(dict(start=x.index[g["start"] + 1].date(), end=x.index[g["end"]].date(), n=g["n"],
                             mu_bp=c / (1 - phi) if ok else np.nan, phi=phi,
                             half_life_obs=-np.log(2) / np.log(phi) if ok else np.nan,
                             level_mean_bp=v[g["start"] + 1:g["end"] + 1].mean(), resid_sd_bp=g["resid_sd"]))
        out = pd.DataFrame(rows)
        out["mu_shift_vs_prev_bp"] = out["mu_bp"].diff()
    if a.out:
        out.to_csv(a.out)
        print(f"wrote {a.out}")
    print(out.tail(12).to_string())


# --------------------------------------------------------------------------- self-test
def selftest() -> None:
    # 1) analytic chain facts: Hamilton (1994) GNP, p11 = 0.90, p22 = 0.75 -> durations 10 and 4, pi1 = 0.25/0.35
    P = np.array([[0.90, 0.10], [0.25, 0.75]])
    assert np.allclose(expected_durations(P), [10.0, 4.0])
    assert np.allclose(ergodic_probs(P), [0.25 / 0.35, 0.10 / 0.35])

    # 2) simulated 2-state switching regression with known parameters
    rng = np.random.default_rng(7)
    T, Pt = 3000, np.array([[0.98, 0.02], [0.04, 0.96]])
    s = np.zeros(T, int)
    for t in range(1, T):
        s[t] = rng.random() < Pt[s[t - 1], 1]
    x = rng.normal(0, 1, T)
    b_true, sig_true = np.array([[0.0, 0.5], [0.0, 1.2]]), np.array([1.0, 3.0])
    y = b_true[s, 0] + b_true[s, 1] * x + sig_true[s] * rng.normal(0, 1, T)
    r = fit_markov_switching(y, np.c_[np.ones(T), x])
    assert np.allclose(r["sigma"], sig_true, rtol=0.1), r["sigma"]
    assert np.allclose(r["beta"][:, 1], b_true[:, 1], atol=0.15), r["beta"]
    assert np.allclose(np.diag(r["P"]), np.diag(Pt), atol=0.015), r["P"]
    acc_s = (r["smoothed"].argmax(1) == s).mean()
    acc_f = (r["filtered"].argmax(1) == s).mean()
    assert acc_s > 0.93 and acc_f > 0.88, (acc_s, acc_f)

    # 3) vol regime: sigma 1 -> 3 for 200 days -> 1
    sd = np.r_[np.ones(1000), 3 * np.ones(200), np.ones(300)]
    st = vol_regime(pd.Series(rng.normal(0, 1, len(sd)) * sd))["state"].to_numpy()
    first_hi = 1000 + int(np.argmax(st[1000:] == 1))
    # z > +1 flags ~16% of days in a stable regime by construction; the 3x block must be flagged fast and kept
    assert first_hi <= 1010 and (st[1030:1200] == 1).mean() > 0.9 and (st[600:1000] == 1).mean() < 0.3, first_hi
    # 3b) log-vol z is symmetric: scaling vol by 3 and by 1/3 gives z of equal size and opposite sign
    e3 = np.random.default_rng(11).normal(0, 1, 1100)
    zc = [vol_regime(pd.Series(e3 * np.where((np.arange(1100) >= 1000) & (np.arange(1100) < 1040), c, 1.0)))
          ["z"].iloc[1030] for c in (3.0, 1 / 3)]
    assert zc[0] > 3 and abs(zc[0] + zc[1]) < 0.3, zc
    # 3c) hysteresis: enter at +-1, leave only inside +-0.5
    hz = _hysteresis([np.nan, 0, 1.2, 0.7, 0.4, -1.1, -0.7, -0.4, 1.0], 1.0, -1.0, 0.5)
    assert np.array_equal(hz, [np.nan, 0, 1, 1, 0, -1, -1, 0, 1], equal_nan=True), hz

    # 4) breaks in mean at 300 and 700 (means 0, 3, 1; sd 1)
    yb = np.r_[np.zeros(300), 3 * np.ones(400), np.ones(300)] + rng.normal(0, 1, 1000)
    rb = find_breaks(yb, max_breaks=4)
    assert rb["n_breaks"] == 2 and np.allclose(rb["breaks"], [300, 700], atol=5), rb["breaks"]
    assert np.allclose([g["coef"][0] for g in rb["segments"]], [0, 3, 1], atol=0.2)

    # 4b) persistent level, AR(1) form: equilibrium 10 -> 4 bp at 600 (phi 0.95) is found; a random walk gives none
    rng3 = np.random.default_rng(3)
    e = np.zeros(1500)
    for t in range(1, 1500):
        e[t] = 0.95 * e[t - 1] + rng3.normal()
    yl = np.r_[np.full(600, 10.0), np.full(900, 4.0)] + e
    ra = find_breaks(yl[1:], np.c_[np.ones(1499), yl[:-1]])
    mus = [g["coef"][0] / (1 - g["coef"][1]) for g in ra["segments"]]
    assert ra["n_breaks"] == 1 and abs(ra["breaks"][0] + 1 - 600) <= 15 and np.allclose(mus, [10, 4], atol=2), mus
    rw = np.cumsum(rng3.normal(0, 1, 1500))
    assert find_breaks(rw[1:], np.c_[np.ones(1499), rw[:-1]])["n_breaks"] == 0

    # 5) Chow F equals the dummy-interaction F; detects a hedge-ratio break 0.5 -> 1.0
    xc = rng.normal(0, 1, 600)
    yc = np.where(np.arange(600) < 300, 0.5, 1.0) * xc + rng.normal(0, 0.5, 600)
    Xc = np.c_[np.ones(600), xc]
    F, pv = chow_test(yc, Xc, 300)
    D = (np.arange(600) >= 300)[:, None] * Xc
    Xu = np.c_[Xc, D]
    su = np.sum((yc - Xu @ np.linalg.lstsq(Xu, yc, rcond=None)[0]) ** 2)
    sr = np.sum((yc - Xc @ np.linalg.lstsq(Xc, yc, rcond=None)[0]) ** 2)
    assert np.isclose(F, ((sr - su) / 2) / (su / (600 - 4))) and pv < 1e-6, (F, pv)

    # 6) CUSUM filter: steady +1 per step with h = 2.5 fires every 3rd step, same for -1
    assert cusum_events(np.arange(10.0), 2.5) == [3, 6, 9] == cusum_events(-np.arange(10.0), 2.5)
    print("selftest passed")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--input", help="canonical curve_par or signals table (.csv or .parquet)")
    ap.add_argument("--curve-id")
    ap.add_argument("--tenor")
    ap.add_argument("--start", default="0D")
    ap.add_argument("--snap")
    ap.add_argument("--package-id")
    ap.add_argument("--strategy-id", help="signals: pick one strategy_id when several share the package_id")
    ap.add_argument("--model", choices=["ms", "vol", "breaks"], default="vol")
    ap.add_argument("--on", choices=["auto", "levels", "changes"], default="auto",
                    help="auto: changes for ms/vol, levels for breaks")
    ap.add_argument("--states", type=int, default=2)
    ap.add_argument("--win", type=int, default=21)
    ap.add_argument("--z-win", type=int, default=504)
    ap.add_argument("--max-breaks", type=int, default=5)
    ap.add_argument("--trim", type=float, default=0.15)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.input:
        run_cli(a)
    else:
        ap.error("pass --input or --selftest")


if __name__ == "__main__":
    main()
