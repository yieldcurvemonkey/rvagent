#!/usr/bin/env python3
"""Leakage-safe ML baselines for rates RV series (bp units).

Contents
  ridge_coef / ridge_df     closed-form ridge on centred data (numpy only)
  build_features / forward_change / walk_forward   point-in-time walk-forward forecast of the
                            forward h-day change of a bp series (ridge, optional gradient boosting)
  ic_stats                  Spearman IC, hit rate, overlap-adjusted t-stat
  kelly_size                S = 2P - 1 sizing from a classifier probability
  shuffle_sharpe            "dumb luck" threshold: Sharpe percentiles of the same sizes shuffled in time
  shape_distance / analog_search   curve-shape (parallel-shift invariant) nearest-neighbour search
  leela_signal              correlation-analog signal (Burton, Dektor, Wheeler, c.2008)

CLI (canonical tables, see data-contract-and-adapters):
  python ml_baseline.py walkforward --curve-par curve_par.csv --curve-id <id> --legs 2Y:-1,5Y:2,10Y:-1 --horizon 5
  python ml_baseline.py analog --curve-par curve_par.csv --curve-id <id> --tenors 2Y,5Y,10Y,30Y --asof 2026-11-10
  python ml_baseline.py --selftest
Conventions: bp throughout; curve_par par_rate_pct x 100 = bp; forward change = x[t+h] - x[t].
Output rows are shaped like the canonical `signals` table. ASCII-only output (Windows consoles).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

try:  # optional
    from sklearn.ensemble import GradientBoostingRegressor
except Exception:  # pragma: no cover
    GradientBoostingRegressor = None


# ----------------------------------------------------------------------------- ridge
def ridge_coef(Xc: np.ndarray, yc: np.ndarray, lam: float) -> np.ndarray:
    """beta = (X'X + lam I)^-1 X'y on CENTRED X, y. Intercept is not penalised (centre first)."""
    p = Xc.shape[1]
    return np.linalg.solve(Xc.T @ Xc + lam * np.eye(p), Xc.T @ yc)


def ridge_df(Xc: np.ndarray, lam: float) -> float:
    """Effective degrees of freedom sum d_j^2 / (d_j^2 + lam) over singular values d_j of X."""
    d = np.linalg.svd(Xc, compute_uv=False)
    return float(np.sum(d ** 2 / (d ** 2 + lam)))


def _fit_predict(Xtr, ytr, Xte, model, lam):
    """Standardise on TRAIN only, fit, predict. model in {'ridge','gbm'}."""
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    ym = ytr.mean()
    if model == "ridge":
        b = ridge_coef(A, ytr - ym, lam)
        return ym + B @ b
    if model == "gbm":
        if GradientBoostingRegressor is None:
            raise RuntimeError("scikit-learn not installed: gbm unavailable")
        m = GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05,
                                      subsample=0.7, random_state=0)
        return m.fit(A, ytr).predict(B)
    raise ValueError(model)


# ----------------------------------------------------------------------------- features / walk-forward
def build_features(x: pd.Series) -> pd.DataFrame:
    """Backward-looking features of a bp level series. Row t uses data up to and including t only."""
    f = pd.DataFrame(index=x.index)
    f["d1"] = x.diff(1)
    f["d5"] = x.diff(5)
    f["d21"] = x.diff(21)
    f["z63"] = (x - x.rolling(63).mean()) / x.rolling(63).std()
    f["z252"] = (x - x.rolling(252, min_periods=252).mean()) / x.rolling(252, min_periods=252).std()
    return f.replace([np.inf, -np.inf], np.nan)  # a flat (stale) window has std 0 -> inf, treat as missing


def forward_change(x: pd.Series, h: int, delay: int = 0) -> pd.Series:
    """Target for row t: x[t+delay+h] - x[t+delay] (bp). Known only at t+delay+h.

    delay=0 assumes you can trade at the snap that produced the features; delay=1 trades one row later.
    """
    return x.shift(-(delay + h)) - x.shift(-delay)


def walk_forward(x: pd.Series, h: int = 5, min_train: int = 504, refit_every: int = 21,
                 model: str = "ridge", lam_grid=(0.01, 0.1, 1.0, 10.0), embargo: int | None = None,
                 feats: pd.DataFrame | None = None, delay: int = 0) -> pd.DataFrame:
    """Prediction at decision date t uses a model fitted on rows i <= t0 - embargo (t0 = last refit <= t).

    embargo defaults to h + delay, so every training label x[i+delay+h]-x[i+delay] was already known at t0.
    Ridge lambda = c * n_train with c chosen on the last 20% of the training window (chronological,
    separated from the fit rows by an h-row gap). Returns DataFrame[pred_bp, actual_bp] by date.
    """
    emb = h + delay if embargo is None else embargo
    F = build_features(x) if feats is None else feats
    y = forward_change(x, h, delay)
    n = len(x)
    Xv, yv = F.to_numpy(float), y.to_numpy(float)
    ok_x = ~np.isnan(Xv).any(1)
    pred = np.full(n, np.nan)
    first = np.flatnonzero(ok_x)[0] if ok_x.any() else n
    for t0 in range(first + min_train, n, refit_every):
        rows = np.flatnonzero(ok_x[: t0 - emb + 1] & ~np.isnan(yv[: t0 - emb + 1]))
        if len(rows) < 100:
            continue
        lam = 1.0
        if model == "ridge":
            cut = rows[int(len(rows) * 0.8)]
            fit_r, val_r = rows[rows <= cut - emb], rows[rows > cut]
            best = np.inf
            for c in lam_grid:
                if len(fit_r) < 50 or len(val_r) < 20:
                    break
                e = np.mean((_fit_predict(Xv[fit_r], yv[fit_r], Xv[val_r], "ridge", c * len(fit_r)) - yv[val_r]) ** 2)
                if e < best:
                    best, lam = e, c
            lam = lam * len(rows)
        t1 = min(t0 + refit_every, n)
        te = np.arange(t0, t1)
        te = te[ok_x[te]]
        if len(te):
            pred[te] = _fit_predict(Xv[rows], yv[rows], Xv[te], model, lam)
    return pd.DataFrame({"pred_bp": pred, "actual_bp": yv}, index=x.index)


def ic_stats(pred: np.ndarray, actual: np.ndarray, h: int = 1) -> dict:
    """Spearman IC, sign hit rate and a t-stat that deflates n by the overlap h (n_eff = n / h)."""
    m = ~(np.isnan(pred) | np.isnan(actual))
    p, a = pred[m], actual[m]
    if len(p) < 10:
        return {"n": int(len(p)), "ic": np.nan, "hit": np.nan, "t": np.nan}
    rp, ra = pd.Series(p).rank().to_numpy(), pd.Series(a).rank().to_numpy()
    ic = float(np.corrcoef(rp, ra)[0, 1])
    neff = max(len(p) / max(h, 1), 3.0)
    t = ic * np.sqrt((neff - 2) / max(1 - ic ** 2, 1e-12))
    return {"n": int(len(p)), "ic": ic, "hit": float(np.mean(np.sign(p) == np.sign(a))), "t": float(t)}


def kelly_size(prob: np.ndarray | float) -> np.ndarray | float:
    """Symmetric-payout Kelly from P(rally) in [0,1]: S = 2P - 1, positive = long duration."""
    return 2.0 * np.asarray(prob) - 1.0


def shuffle_sharpe(size, ret, n_perm: int = 1000, q=(50, 95, 99), seed: int = 0, ann: float = 252.0,
                   block: int = 1) -> dict:
    """Permutation ("dumb luck") benchmark for a sized timing signal.

    size[t] = signed position decided at t (e.g. 2P-1), ret[t] = the realised P&L of a unit position
    over the holding period decided at t. Sharpe = mean(size*ret)/std(size*ret)*sqrt(ann). The sizes are
    shuffled in time n_perm times (same size distribution, same sell fraction, timing destroyed).
    Returns the observed Sharpe, its shuffled percentiles, and the one-sided permutation p-value.
    ann: periods per year of the P&L series. A daily decision with an h-day hold gives overlapping h-day
    P&Ls, so pass ann = 252/h (252 would overstate the Sharpe by sqrt(h)).
    block > 1 shuffles contiguous blocks (use >= h): when the P&L is serially correlated (overlapping holds)
    and sizes are persistent, an i.i.d. shuffle destroys that dependence, so its null is too narrow and the
    p-value too small.
    """
    s, r = np.asarray(size, float), np.asarray(ret, float)
    m = ~(np.isnan(s) | np.isnan(r))
    s, r = s[m], r[m]

    def sh(a):
        sd = a.std(ddof=1)
        return float(a.mean() / sd * np.sqrt(ann)) if sd > 0 else 0.0

    rng = np.random.default_rng(seed)

    def shuf(a):
        if block <= 1:
            return rng.permutation(a)
        parts = [a[i:i + block] for i in range(0, len(a), block)]
        return np.concatenate([parts[j] for j in rng.permutation(len(parts))])

    perm = np.array([sh(shuf(s) * r) for _ in range(n_perm)])
    obs = sh(s * r)
    out = {"sharpe": obs, "p_value": float((1 + np.sum(perm >= obs)) / (n_perm + 1)), "n": int(len(s))}
    out.update({"p%d" % k: float(np.percentile(perm, k)) for k in q})
    return out


# ----------------------------------------------------------------------------- analog search
def shape_distance(c1: np.ndarray, C: np.ndarray, scale: bool = False, max_stretch: float = 2.0) -> np.ndarray:
    """L2 distance between curve c1 (m,) and each row of C (N,m) after removing a parallel shift.

    scale=False: min_k ||c1 - c2 - k||_2 ; the optimal k = mean(c1 - c2), so it is the norm of the
                 demeaned difference.
    scale=True : min_{k1,k2} ||c1 - k1*c2 - k2||_2 with k1 clipped to [1/max_stretch, max_stretch].
    """
    c1c = c1 - c1.mean()
    Cc = C - C.mean(1, keepdims=True)
    if not scale:
        return np.linalg.norm(c1c - Cc, axis=1)
    den = np.maximum((Cc ** 2).sum(1), 1e-12)
    k1 = np.clip((Cc @ c1c) / den, 1.0 / max_stretch, max_stretch)
    return np.linalg.norm(c1c - k1[:, None] * Cc, axis=1)


def analog_search(curves: pd.DataFrame, asof, k: int = 20, h: int = 5, scale: bool = False,
                  metric: str = "shape", min_sep: int = 10, window: int | None = None) -> pd.DataFrame:
    """Nearest historical analogs of curves.loc[asof] (rows = dates, cols = tenors, bp or z-scores).

    Candidates are dates at least h rows before asof (so the forward h-day outcome was known at asof),
    optionally limited to the last `window` rows. Picks greedily and drops anything within min_sep rows
    of an earlier pick (one episode = one analog; min_sep is raised to at least h). metric 'shape' = parallel-shift invariant, 'euclid'
    = plain Euclidean (use for z-scored regime vectors). Weight ~ 1/(dist + 0.05*median dist).
    Returns date, dist, weight, and the per-column forward change; forecast = weighted mean (attrs).
    """
    curves = curves.dropna()
    pos = curves.index.get_loc(pd.Timestamp(asof))
    lo = 0 if window is None else max(0, pos - h - window)
    cand = np.arange(lo, pos - h + 1)
    if len(cand) == 0:
        raise ValueError("no candidate history before asof - h")
    min_sep = max(min_sep, h)  # forward windows of two analogs must not overlap
    C = curves.to_numpy(float)
    q = C[pos]
    if metric == "shape":
        dist = shape_distance(q, C[cand], scale=scale)
    else:
        dist = np.linalg.norm(C[cand] - q, axis=1)
    order = np.argsort(dist)
    picked: list[int] = []
    for j in order:
        if all(abs(cand[j] - cand[i]) >= min_sep for i in picked):
            picked.append(j)
        if len(picked) == k:
            break
    d = dist[picked]
    w = 1.0 / (d + 0.05 * np.median(dist) + 1e-12)
    w = w / w.sum()
    fwd = (curves.shift(-h) - curves).iloc[cand[picked]]
    out = pd.DataFrame({"date": curves.index[cand[picked]], "dist": d, "weight": w}, index=fwd.index)
    out = pd.concat([out, fwd.add_prefix("fwd_")], axis=1)
    out.attrs["forecast"] = (fwd.mul(w, axis=0)).sum()
    return out


# ----------------------------------------------------------------------------- Leela correlation analog
def leela_signal(d: np.ndarray, p: int = 3, n: int = 750, rho_floor: float | None = None) -> np.ndarray:
    """Correlation-analog signal for the NEXT move, one value per day t (NaN until n+p days exist).

    x_t = [d_t ... d_{t-p+1}] normalised to unit length; history rows i in [t-n, t-1] have x_i and
    outcome y_i = d_{i+1}/||x_i||. signal_t = sum_i rho_{i,t} y_i with rho = x_t . x_i (set to 0 below
    rho_floor if given). Trade sign(signal_t). Needs only data through day t.
    """
    d = np.asarray(d, float)
    N = len(d)
    W = np.lib.stride_tricks.sliding_window_view(d, p)  # row j = d[j..j+p-1], day t = j+p-1
    nrm = np.maximum(np.linalg.norm(W, axis=1), 1e-12)
    Xn = W / nrm[:, None]
    out = np.full(N, np.nan)
    for j in range(n, len(W)):  # history rows jj < j have outcome d[jj+p] <= d[t]: known at day t
        t = j + p - 1
        hist = np.arange(j - n, j)
        rho = Xn[hist] @ Xn[j]
        if rho_floor is not None:
            rho = np.where(rho > rho_floor, rho, 0.0)
        y = d[hist + p] / nrm[hist]
        out[t] = float(rho @ y)
    return out


# ----------------------------------------------------------------------------- CLI
def _one_snap(q: pd.DataFrame, snap: str | None) -> pd.DataFrame:
    """Never mix snaps: pick --snap, or require the data to contain exactly one."""
    if snap:
        return q[q["snap"] == snap]
    if q["snap"].nunique() > 1:
        raise SystemExit("several snaps in the data (%s): pass --snap" % ",".join(sorted(q["snap"].unique())))
    return q


def _legs_series(par: pd.DataFrame, curve_id: str, legs: str, snap: str | None) -> pd.Series:
    q = _one_snap(par[(par["curve_id"] == curve_id) & (par["start"] == "0D")], snap)
    q = q.copy()
    q["date"] = pd.to_datetime(q["date"])
    wide = q.pivot_table(index="date", columns="tenor", values="par_rate_pct").sort_index() * 100.0
    x = 0.0
    for leg in legs.split(","):
        ten, w = leg.split(":")
        x = x + float(w) * wide[ten]
    return x.dropna()


def _read(path: str) -> pd.DataFrame:
    if path.lower().endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=["walkforward", "analog"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--curve-par")
    ap.add_argument("--curve-id")
    ap.add_argument("--snap")
    ap.add_argument("--legs", default="2Y:-1,5Y:2,10Y:-1", help="tenor:weight list, bp = sum w * par_rate_pct * 100")
    ap.add_argument("--tenors", default="2Y,5Y,10Y,30Y")
    ap.add_argument("--asof")
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--delay", type=int, default=0, help="rows between the signal snap and trade entry (1 = trade next day)")
    ap.add_argument("--model", default="ridge", choices=["ridge", "gbm"])
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.mode and a.curve_par and a.curve_id):
        ap.error("mode, --curve-par and --curve-id are required")
    par = _read(a.curve_par)
    if a.mode == "walkforward":
        x = _legs_series(par, a.curve_id, a.legs, a.snap)
        res = walk_forward(x, h=a.horizon, model=a.model, delay=a.delay)
        st = ic_stats(res["pred_bp"].to_numpy(), res["actual_bp"].to_numpy(), a.horizon)
        print("n=%d IC=%.3f hit=%.3f t(overlap-adj)=%.2f" % (st["n"], st["ic"], st["hit"], st["t"]))
        sig = res.dropna(subset=["pred_bp"]).rename(columns={"pred_bp": "value"})
        sig = pd.DataFrame({"date": sig.index.date, "snap": a.snap or sorted(par.loc[par["curve_id"] == a.curve_id, "snap"].unique())[0], "strategy_id": "ml_" + a.model,
                            "package_id": a.curve_id + ":" + a.legs, "value": sig["value"].values, "unit": "bp",
                            "horizon_days": a.horizon, "model_version": "ml_baseline_v1"})
    else:
        q = _one_snap(par[(par["curve_id"] == a.curve_id) & (par["start"] == "0D")
                          & par["tenor"].isin(a.tenors.split(","))], a.snap).copy()
        q["date"] = pd.to_datetime(q["date"])
        cv = q.pivot_table(index="date", columns="tenor", values="par_rate_pct")[a.tenors.split(",")].dropna() * 100.0
        asof = a.asof or str(cv.index[-1].date())
        res = analog_search(cv, asof, k=a.k, h=a.horizon)
        print(res.round(2).to_string(index=False))
        print("weighted forward change (bp):", res.attrs["forecast"].round(2).to_dict())
        sig = None
    if a.out and sig is not None:
        sig.to_csv(a.out, index=False)
    return 0


# ----------------------------------------------------------------------------- self-test
def _ou_level(n, phi, sd, seed):
    r = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + r.normal(0, sd)
    return pd.Series(x, index=pd.bdate_range("2012-01-02", periods=n))


def selftest() -> int:
    bad = []

    def check(name, cond, info=""):
        print(("ok   " if cond else "FAIL ") + name + (" " + info if info else ""))
        if not cond:
            bad.append(name)

    rng = np.random.default_rng(1)
    # 1. orthonormal X: ridge = OLS/(1+lam) exactly; df = sum d^2/(d^2+lam)
    Q, _ = np.linalg.qr(rng.normal(size=(200, 4)))
    y = rng.normal(size=200)
    y = y - y.mean()
    ols = Q.T @ y
    check("ridge orthonormal shrink", np.allclose(ridge_coef(Q, y, 0.7), ols / 1.7, atol=1e-10))
    check("ridge df orthonormal", abs(ridge_df(Q, 0.7) - 4 / 1.7) < 1e-9)
    # 2. recovery of known coefficients
    X = rng.normal(size=(5000, 3))
    X = X - X.mean(0)
    b = np.array([1.5, -2.0, 0.0])
    yy = X @ b + rng.normal(0, 0.5, 5000)
    check("ridge recovers beta", np.allclose(ridge_coef(X, yy - yy.mean(), 1.0), b, atol=0.05))
    # 3. Kelly size
    check("kelly 2P-1", abs(float(kelly_size(0.85)) - 0.7) < 1e-12 and abs(float(kelly_size(0.25)) + 0.5) < 1e-12)
    # 4. shape distance: parallel shift -> 0; tilt+shift -> 0 only with scale; different shape > 0
    c = np.array([10.0, 25, 40, 48, 50])
    Cm = np.vstack([c + 37.0, 2.0 * c + 5, c[::-1]])
    d0 = shape_distance(c, Cm)
    d1 = shape_distance(c, Cm, scale=True)
    check("shape distance parallel shift = 0", d0[0] < 1e-9 and d0[1] > 1 and d0[2] > 1, str(d0.round(3)))
    check("shape distance scaled stretch = 0", d1[1] < 1e-9 and d1[0] < 1e-9, str(d1.round(3)))
    # 5. analog search finds the planted shifted copy and respects the h-row rule
    dates = pd.bdate_range("2015-01-01", periods=600)
    base = rng.normal(0, 8, size=(600, 5)).cumsum(0) * 0.05 + rng.normal(0, 15, size=(600, 5))
    curves = pd.DataFrame(base, index=dates, columns=list("abcde"))
    curves.iloc[300] = curves.iloc[599] + 55.0  # planted parallel-shifted twin of "today"
    res = analog_search(curves, dates[599], k=3, h=5, min_sep=10)
    check("analog finds planted twin", res["date"].iloc[0] == dates[300] and res["dist"].iloc[0] < 1e-6)
    curves.iloc[305] = curves.iloc[300] + np.array([4.0, -3.0, 2.0, 0.0, 1.0])  # known forward change after the twin
    res1 = analog_search(curves, dates[599], k=1, h=5)
    check("analog forecast = planted forward change", np.allclose(res1.attrs["forecast"].to_numpy(), [4, -3, 2, 0, 1]),
          str(res1.attrs["forecast"].round(2).tolist()))
    res2 = analog_search(curves, dates[599], k=50, h=5, min_sep=1)
    check("analog excludes last h rows", res2["date"].max() <= dates[599 - 5])
    # 6. Leela. (a) p=1 is exactly sign(d_t) * sum_i d_{i+1}/d_i over the window (analytic identity);
    #    (b) a noisy period-4 pattern is learned from the last 3 moves (known answer: hit rate high)
    r = np.random.default_rng(7)
    d1 = r.normal(size=40)
    s1 = leela_signal(d1, p=1, n=20)
    t = 30
    ref = np.sign(d1[t]) * sum(d1[i + 1] / d1[i] for i in range(t - 20, t))
    check("leela p=1 identity sign(d_t)*sum(d_{i+1}/d_i)", abs(s1[t] - ref) < 1e-9, "%.6f vs %.6f" % (s1[t], ref))
    check("leela signal exists on the last day", not np.isnan(s1[-1]) and np.isnan(s1[18]) and not np.isnan(s1[20]))
    pat = np.array([2.0, -1.0, -3.0, 1.5])
    dd = np.tile(pat, 400) + r.normal(0, 0.3, 1600)
    s = leela_signal(dd, p=3, n=100)
    m = ~np.isnan(s[:-1])
    hit = float(np.mean(np.sign(s[:-1][m]) == np.sign(dd[1:][m])))
    check("leela p=3 learns periodic pattern (hit > 0.8)", hit > 0.8, "hit=%.3f" % hit)
    rw = np.random.default_rng(8).normal(size=1600)
    s = leela_signal(rw, p=3, n=100)
    m = ~np.isnan(s[:-1])
    hit = float(np.mean(np.sign(s[:-1][m]) == np.sign(rw[1:][m])))
    check("leela on white noise ~ 0.5", abs(hit - 0.5) < 0.05, "hit=%.3f" % hit)
    # 6b. shuffle benchmark: informative sizes beat the 99th percentile, uninformed ones do not
    rt = np.random.default_rng(21).normal(0, 1, 1500)
    informed = np.sign(rt) * 0.2 + np.random.default_rng(22).normal(0, 1, 1500) * 0.5  # sizes correlated with ret
    noise = np.random.default_rng(23).normal(0, 1, 1500)
    a_ = shuffle_sharpe(informed, rt, n_perm=500)
    b_ = shuffle_sharpe(noise, rt, n_perm=500)
    check("shuffle: informed sizes beat p99", a_["sharpe"] > a_["p99"] and a_["p_value"] < 0.01, "%.2f > %.2f" % (a_["sharpe"], a_["p99"]))
    check("shuffle: noise sizes inside p99, median ~ 0", b_["sharpe"] < b_["p99"] and abs(b_["p50"]) < 0.5,
          "%.2f p99 %.2f med %.2f" % (b_["sharpe"], b_["p99"], b_["p50"]))
    # 6c. overlapping 20-day P&L (rolling sum of i.i.d. noise, no drift) + persistent sizes: an i.i.d. shuffle
    #     understates the null spread; block shuffling keeps it (known answer: block p95 several times larger)
    rp = np.convolve(np.random.default_rng(31).normal(0, 1, 2019), np.ones(20), "valid")
    sp = np.sign(np.sin(np.arange(2000) / 150.0))  # long runs of +1 / -1
    w1 = shuffle_sharpe(sp, rp, n_perm=400, ann=252 / 20, block=1)
    w2 = shuffle_sharpe(sp, rp, n_perm=400, ann=252 / 20, block=100)
    check("shuffle block: null p95 > 2x i.i.d. when P&L is overlapping", w2["p95"] > 2 * w1["p95"], "%.2f vs %.2f" % (w2["p95"], w1["p95"]))
    # 7. walk-forward: point-in-time invariance (perturb the future, past predictions unchanged)
    x = _ou_level(1800, 0.97, 3.0, 3)
    base_pred = walk_forward(x, h=5, min_train=504)["pred_bp"]
    # T is a refit date t0: a training row i <= t0 whose label ends after T (embargo shorter than
    # delay + h) would let the perturbed future into the fit and change the prediction at T.
    t_first = int(np.flatnonzero(base_pred.notna().to_numpy())[0])
    T = t_first + 21 * 20
    for dl in (0, 1):
        bp = walk_forward(x, h=5, min_train=504, delay=dl)["pred_bp"]
        x2 = x.copy()
        x2.iloc[T + 1:] += np.random.default_rng(9).normal(0, 50, len(x2) - T - 1)
        pert = walk_forward(x2, h=5, min_train=504, delay=dl)["pred_bp"]
        check("walk-forward point-in-time (delay=%d)" % dl, np.array_equal(
            bp.iloc[: T + 1].fillna(-9e9).to_numpy(), pert.iloc[: T + 1].fillna(-9e9).to_numpy())
              and bp.iloc[T - 2:T + 1].notna().all())
    check("forward_change delay", forward_change(x, 5, 1).iloc[3] == x.iloc[9] - x.iloc[4])
    # 8. mean-reverting level: ridge IC clearly positive; noise level: IC near 0
    st = ic_stats(base_pred.to_numpy(), walk_forward(x, h=5, min_train=504)["actual_bp"].to_numpy(), 5)
    check("ridge IC on OU level > 0.15", st["ic"] > 0.15, "ic=%.3f" % st["ic"])
    xn = pd.Series(np.random.default_rng(5).normal(0, 3, 1800).cumsum(), index=x.index)
    rn = walk_forward(xn, h=5, min_train=504)
    stn = ic_stats(rn["pred_bp"].to_numpy(), rn["actual_bp"].to_numpy(), 5)
    check("ridge IC on random walk ~ 0", abs(stn["ic"]) < 0.15, "ic=%.3f" % stn["ic"])
    # 9. interaction target: ridge blind, GBM sees it (skipped without scikit-learn)
    if GradientBoostingRegressor is None:
        print("skip gbm interaction test (scikit-learn not installed)")
    else:
        Xa = np.random.default_rng(11).normal(size=(3000, 3))
        ya = Xa[:, 0] * Xa[:, 1] + np.random.default_rng(12).normal(0, 0.3, 3000)
        tr, te = slice(0, 2000), slice(2000, 3000)
        ic_r = ic_stats(_fit_predict(Xa[tr], ya[tr], Xa[te], "ridge", 10.0), ya[te])["ic"]
        ic_g = ic_stats(_fit_predict(Xa[tr], ya[tr], Xa[te], "gbm", 0.0), ya[te])["ic"]
        check("interaction: ridge ~0, gbm > 0.4", abs(ic_r) < 0.15 and ic_g > 0.4, "ridge=%.2f gbm=%.2f" % (ic_r, ic_g))
    print("SELFTEST " + ("FAILED: " + ", ".join(bad) if bad else "PASSED"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
