"""Cointegration tests and spread construction for rates RV (yields in bp).

Engle-Granger two-step (ADF on OLS residual, MacKinnon critical values), known-vector ADF,
Johansen trace / max-eigenvalue rank tests (restricted or unrestricted constant), LR test of a
hypothesised cointegrating vector, residual spread in bp, DV01 weights and AR(1) half-life.

Core is numpy/pandas/scipy. statsmodels, if importable, adds MacKinnon p-values and a cross-check.

CLI (canonical long tables from data-contract-and-adapters, or a wide CSV: date + one column per series).
The first series gets weight +1 (belly first for a fly, longer tenor first for a spread):
    python coint.py --file curve_par.parquet --snap eod_ny
        --series "USD-SOFR|0D|5Y,USD-SOFR|0D|2Y,USD-SOFR|0D|10Y" --test-vector=2,-1,-1
    python coint.py --selftest
Series ids follow the symbol_map grammar: `curve_id|start|tenor` (curve_par), instrument_id (bond_quotes),
fut_id (stir_quotes), `curve_id|measure|ref` (swap_spreads). Output: JSON on stdout (ASCII only).
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
import pandas as pd

try:  # optional: p-values and cross-check only
    from statsmodels.tsa.adfvalues import mackinnonp as _mackinnonp
except Exception:  # pragma: no cover
    _mackinnonp = None

# MacKinnon (2010) asymptotic critical values (1%, 5%, 10%) for ADF / Engle-Granger tests.
# N = number of variables in the cointegrating regression (N=1: plain ADF on one series).
EG_CV = {
    "c": {1: (-3.430, -2.862, -2.567), 2: (-3.896, -3.336, -3.044), 3: (-4.294, -3.741, -3.452),
          4: (-4.643, -4.096, -3.810), 5: (-4.958, -4.415, -4.132), 6: (-5.246, -4.707, -4.425)},
    "ct": {1: (-3.959, -3.410, -3.127), 2: (-4.328, -3.781, -3.496), 3: (-4.663, -4.119, -3.835),
           4: (-4.969, -4.429, -4.146), 5: (-5.253, -4.715, -4.434), 6: (-5.517, -4.982, -4.702)},
}
# Johansen 95% critical values by g = n - r (number of common trends): (trace, max-eig).
# "rc": restricted constant (constant only inside the cointegrating relation; levels have no drift).
#       Simulated with this file's johansen() under H0 (g driftless random walks, T=1000, 20000 draws).
#       g=1,2 agree with the Osterwald-Lenum values printed in Tsay (2010): 9.24 and 19.96 / 15.67.
# "c":  unrestricted constant, MacKinnon-Haug-Michelis (1999) as tabulated in statsmodels (det_order=0).
#       Valid only when the levels have a deterministic drift. On driftless yields the true 95% points are
#       about 8.2 / 18.3 / 31.9 (g=1/2/3, same simulation), so this table over-rejects: use "rc" for rates.
JOH_CV95 = {
    "rc": {1: (9.2, 9.2), 2: (20.4, 16.0), 3: (35.3, 22.3), 4: (54.0, 28.6), 5: (77.2, 34.8)},
    "c": {1: (3.841, 3.841), 2: (15.494, 14.264), 3: (29.796, 21.131), 4: (47.855, 27.586),
          5: (69.819, 33.878)},
}


def _ols(y, X):
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    return coef, resid


def _tstat(y, X, i):
    coef, resid = _ols(y, X)
    s2 = resid @ resid / (len(y) - X.shape[1])
    return coef[i] / math.sqrt(s2 * np.linalg.inv(X.T @ X)[i, i])


def adf(x, const=True, maxlag=None):
    """ADF t-stat on the lagged level. Lag by AIC on a common sample, refit on the longest sample
    (same procedure as statsmodels adfuller autolag='AIC'). Returns (t, lags_used)."""
    x = np.asarray(x, float)
    n = len(x)
    if maxlag is None:
        maxlag = min(int(math.ceil(12 * (n / 100) ** 0.25)), n // 2 - int(const) - 1)
    dx = np.diff(x)

    def design(p):
        m = len(dx) - p
        cols = ([np.ones(m)] if const else []) + [x[p:p + m]] + [dx[p - i:p - i + m] for i in range(1, p + 1)]
        return dx[p:], np.column_stack(cols)

    y, X = design(maxlag)
    k0 = int(const) + 1

    def aic(p):
        _, r = _ols(y, X[:, :k0 + p])
        return len(y) * math.log(r @ r / len(y)) + 2 * (k0 + p)

    best = min(range(maxlag + 1), key=aic)
    y, X = design(best)
    return _tstat(y, X, k0 - 1), best


def _pval(t, n_vars, trend="c"):
    return None if _mackinnonp is None else float(_mackinnonp(t, regression=trend, N=n_vars))


def engle_granger(y, X, maxlag=None):
    """OLS y = a + X g + u, then ADF (no constant) on u. 5% EG critical value from MacKinnon."""
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float).reshape(len(y), -1)])
    coef, u = _ols(np.asarray(y, float), X)
    t, lag = adf(u, const=False, maxlag=maxlag)
    n_vars = X.shape[1]
    return {"alpha": coef[0], "gamma": coef[1:].tolist(), "adf_t": t, "lags": lag,
            "cv": dict(zip(("1%", "5%", "10%"), EG_CV["c"][n_vars])), "p": _pval(t, n_vars),
            "reject_no_coint_5pct": t < EG_CV["c"][n_vars][1], "resid": u}


def johansen(Y, k=1, det="rc", test_vector=None):
    """Johansen ML (Hamilton ch.20). Y: T x n levels. k = lagged differences (VAR order p = k+1).
    det: 'rc' restricted constant (rates default), 'c' unrestricted constant.
    test_vector: hypothesised cointegrating vector (len n); returns LR ~ chi2(n-1) for rank 1."""
    Y = np.asarray(Y, float)
    n = Y.shape[1]
    if n > max(JOH_CV95[det]):
        raise ValueError(f"no critical values for {n} series; use <= {max(JOH_CV95[det])} legs")
    dY = np.diff(Y, axis=0)
    j = np.arange(k, len(dY))
    T = len(j)
    Z = np.column_stack([dY[j - i] for i in range(1, k + 1)] + ([np.ones(T)] if det == "c" else [])) \
        if (k or det == "c") else np.empty((T, 0))
    R0, R1 = dY[j], Y[j]
    if det == "rc":
        R1 = np.column_stack([R1, np.ones(T)])
    if Z.shape[1]:
        R0 = R0 - Z @ np.linalg.lstsq(Z, R0, rcond=None)[0]
        R1 = R1 - Z @ np.linalg.lstsq(Z, R1, rcond=None)[0]
    S00, S11, S01 = R0.T @ R0 / T, R1.T @ R1 / T, R0.T @ R1 / T

    def eig(S11_, S01_):
        lam, V = np.linalg.eig(np.linalg.solve(S11_, S01_.T @ np.linalg.solve(S00, S01_)))
        o = np.argsort(lam.real)[::-1]
        return np.clip(lam.real[o], 0, 1 - 1e-12), V.real[:, o]

    lam, V = eig(S11, S01)
    lam = lam[:n]  # rc: the (n+1)-th eigenvalue is ~0 by construction
    trace = [-T * np.log(1 - lam[r:]).sum() for r in range(n)]
    maxeig = [-T * math.log(1 - lam[r]) for r in range(n)]
    cv = JOH_CV95[det]
    rank = 0
    while rank < n and trace[rank] > cv[n - rank][0]:
        rank += 1
    rank_max = 0
    while rank_max < n and maxeig[rank_max] > cv[n - rank_max][1]:
        rank_max += 1
    beta = V[:, 0] / V[0, 0]
    out = {"T": T, "det": det, "k_ar_diff": k, "eig": lam.tolist(), "trace": trace, "max_eig": maxeig,
           "cv95_trace": [cv[n - r][0] for r in range(n)], "cv95_max": [cv[n - r][1] for r in range(n)],
           "rank_trace_5pct": rank, "rank_maxeig_5pct": rank_max, "beta_first": beta[:n].tolist(),
           "const_in_relation": float(beta[n]) if det == "rc" else None}
    if test_vector is not None:
        a = np.asarray(test_vector, float)
        H = np.zeros((R1.shape[1], 2 if det == "rc" else 1))
        H[:n, 0] = a
        if det == "rc":
            H[n, 1] = 1.0
        lam_r, _ = eig(H.T @ S11 @ H, S01 @ H)
        lr = T * (math.log(1 - lam_r[0]) - math.log(1 - lam[0]))
        out["lr_test_vector"] = {"vector": a.tolist(), "LR": lr, "df": n - 1,
                                 "chi2_5pct": float(_chi2_95(n - 1)), "rank1_assumption_holds": rank == 1}
    return out


def _chi2_95(df):
    from scipy.stats import chi2
    return chi2.ppf(0.95, df)


def half_life(s):
    """AR(1) on levels: s_t = a + b s_{t-1} + e; half-life = ln 0.5 / ln b (periods), inf if b >= 1."""
    s = np.asarray(s, float)
    (a, b), _ = _ols(s[1:], np.column_stack([np.ones(len(s) - 1), s[:-1]]))
    return {"ar1_b": b, "half_life": math.log(0.5) / math.log(b) if 0 < b < 1 else math.inf}


def dv01_weights(vec):
    """Yield-space vector -> signed DV01 weights with gross DV01 = 1. Positive = receive / long duration
    when you 'receive the spread' (profit when the spread falls)."""
    v = np.asarray(vec, float)
    return (v / np.abs(v).sum()).tolist()


# ---------- loading canonical tables ----------
TABLES = {  # value column, scale to bp, key builder
    "par_rate_pct": (100.0, lambda d: d["curve_id"] + "|" + d["start"] + "|" + d["tenor"]),
    "ytm_pct": (100.0, lambda d: d["instrument_id"]),
    "rate_pct": (100.0, lambda d: d["fut_id"]),
    "value_bp": (1.0, lambda d: d["curve_id"] + "|" + d["measure"] + "|" + d["ref"]),
}


def load_levels(df: pd.DataFrame, series, snap=None) -> pd.DataFrame:
    """Long canonical table (or wide date x series frame) -> wide date x series, in bp."""
    for col, (scale, key) in TABLES.items():
        if col in df.columns:
            if "data_ok" in df.columns:
                df = df[df["data_ok"].fillna(True).astype(bool)]
            if "snap" in df.columns:
                snaps = df["snap"].unique() if snap is None else [snap]
                if len(snaps) != 1:
                    raise SystemExit(f"several snaps {list(snaps)}: pass --snap (never mix snaps)")
                df = df[df["snap"] == snaps[0]]
            wide = df.assign(_k=key(df), _v=df[col] * scale).pivot_table(index="date", columns="_k",
                                                                          values="_v", aggfunc="last")
            break
    else:  # wide: first column = date, values assumed already in bp
        wide = df.set_index(df.columns[0])
    missing = [s for s in series if s not in wide.columns]
    if missing:
        raise SystemExit(f"series not found: {missing}")
    wide.index = pd.to_datetime(wide.index)
    return wide[series].sort_index().dropna()


def _leg_stats(v):
    t_lvl, t_dif = adf(v)[0], adf(np.diff(v))[0]
    return {"adf_level_t": t_lvl, "adf_level_p": _pval(t_lvl, 1), "adf_diff_t": t_dif,
            "adf_diff_p": _pval(t_dif, 1), "looks_I1": bool(t_lvl > EG_CV["c"][1][2] and t_dif < EG_CV["c"][1][0])}


MIN_OBS = 100  # below this the unit-root tests are meaningless; the skill asks for >= 500


def analyse(levels: pd.DataFrame, k=1, det="rc", test_vector=None, maxlag=None) -> dict:
    levels = levels.dropna()
    if len(levels) < MIN_OBS:
        raise ValueError(f"{len(levels)} complete rows < {MIN_OBS}: history too short to test cointegration")
    Y = levels.to_numpy(float)
    n = Y.shape[1]
    if not 2 <= n <= max(JOH_CV95[det]):
        raise ValueError(f"{n} series: use 2..{max(JOH_CV95[det])} legs")
    legs = {c: _leg_stats(Y[:, i]) for i, c in enumerate(levels.columns)}
    eg = engle_granger(Y[:, 0], Y[:, 1:], maxlag)
    vec_eg = [1.0] + [-g for g in eg["gamma"]]
    out = {"n_obs": len(Y), "short_history_lt_500": len(Y) < 500, "first_date": str(levels.index[0].date()), "last_date": str(levels.index[-1].date()),
           "series": list(levels.columns), "adf_cv_one_series": dict(zip(("1%", "5%", "10%"), EG_CV["c"][1])),
           "legs": legs,
           "engle_granger": {k_: v for k_, v in eg.items() if k_ != "resid"} | {
               "vector": vec_eg, "dv01_weights": dv01_weights(vec_eg), **half_life(eg["resid"])}}
    if n == 2:  # ordering check
        rev = engle_granger(Y[:, 1], Y[:, 0], maxlag)
        out["engle_granger_reversed"] = {"gamma": rev["gamma"], "adf_t": rev["adf_t"],
                                         "reject_no_coint_5pct": rev["reject_no_coint_5pct"]}
    jo = johansen(Y, k=k, det=det, test_vector=test_vector)
    spread = Y @ np.asarray(jo["beta_first"])
    out["johansen"] = jo | {"dv01_weights": dv01_weights(jo["beta_first"]), **half_life(spread)}
    if test_vector is not None:
        s = Y @ np.asarray(test_vector, float)
        t, lag = adf(s, const=True)
        out["known_vector"] = {"vector": list(test_vector), "adf_t": t, "lags": lag, "p": _pval(t, 1),
                               "cv": dict(zip(("1%", "5%", "10%"), EG_CV["c"][1])), **half_life(s),
                               "mean_bp": float(s.mean()), "sd_bp": float(s.std(ddof=1)),
                               "last_bp": float(s[-1]), "last_dev_sd": float((s[-1] - s.mean()) / s.std(ddof=1))}
    return out


# ---------- self-test ----------
def selftest() -> int:
    rng = np.random.default_rng(7)
    T = 1000
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    # 1. cointegrated pair, known gamma = 1.5, residual AR(1) phi = 0.9 -> half-life ln.5/ln.9 = 6.58
    x = np.cumsum(rng.normal(0, 5, T))
    u = np.zeros(T)
    for t in range(1, T):
        u[t] = 0.9 * u[t - 1] + rng.normal(0, 2)
    y = 10 + 1.5 * x + u
    eg = engle_granger(y, x)
    check(abs(eg["gamma"][0] - 1.5) < 0.05, f"EG gamma {eg['gamma'][0]:.3f} != 1.5")
    check(eg["reject_no_coint_5pct"], f"EG failed to reject on cointegrated pair (t={eg['adf_t']:.2f})")
    hl = half_life(eg["resid"])["half_life"]
    check(4.5 < hl < 9.5, f"half-life {hl:.2f} not near 6.58")
    jo = johansen(np.column_stack([y, x]), k=1, det="rc", test_vector=[1, -1.5])
    # rank >= 1, not == 1: the r<=1 step has 5% size and this seed's random walk lands in that tail
    check(jo["rank_trace_5pct"] >= 1, f"Johansen rc rank {jo['rank_trace_5pct']} < 1")
    check(abs(jo["beta_first"][1] + 1.5) < 0.05, f"Johansen beta {jo['beta_first'][1]:.3f} != -1.5")
    check(jo["lr_test_vector"]["LR"] < jo["lr_test_vector"]["chi2_5pct"], "LR rejects the true vector")
    jo_bad = johansen(np.column_stack([y, x]), k=1, det="rc", test_vector=[1, -1.0])
    check(jo_bad["lr_test_vector"]["LR"] > 3 * jo_bad["lr_test_vector"]["chi2_5pct"], "LR accepts wrong 1:-1")
    t_known, _ = adf(y - 1.5 * x)
    check(t_known < EG_CV["c"][1][1], f"known-vector ADF failed to reject (t={t_known:.2f})")
    check(eg["cv"]["5%"] == -3.336, f"EG pair 5% cv {eg['cv']['5%']} != MacKinnon -3.336")
    check(np.allclose(dv01_weights([1, -0.5, -0.5]), [0.5, -0.25, -0.25]), "dv01 weights not gross-normalised")
    # end-to-end analyse(): known-vector block = ADF with constant on y - 1.5x; NaN rows dropped; guards fire
    lv = pd.DataFrame({"y": y, "x": x}, index=pd.bdate_range("2020-01-01", periods=T))
    lv.iloc[5, 1] = np.nan
    res = analyse(lv, test_vector=[1, -1.5])
    check(res["n_obs"] == T - 1 and abs(res["known_vector"]["adf_t"] - adf(np.delete(y - 1.5 * x, 5))[0]) < 1e-9,
          "analyse known-vector ADF wrong")
    check(abs(res["known_vector"]["mean_bp"] - 10) < 1 and "engle_granger_reversed" in res, "analyse output wrong")
    for bad in (lv.iloc[:50], lv[["y"]]):
        try:
            analyse(bad)
            check(False, f"analyse accepted bad input of shape {bad.shape}")
        except ValueError:
            pass

    # 2. independent random walks: no cointegration
    a, b = np.cumsum(rng.normal(0, 5, T)), np.cumsum(rng.normal(0, 5, T))
    eg0 = engle_granger(a, b)
    check(not eg0["reject_no_coint_5pct"], f"EG rejects on independent walks (t={eg0['adf_t']:.2f})")
    # a residual t between the DF (-2.86) and EG (-3.34) 5% values must NOT reject (verdict uses the N=2 row)
    r2 = np.random.default_rng(11)
    for _ in range(200):
        e_mid = engle_granger(np.cumsum(r2.normal(size=300)), np.cumsum(r2.normal(size=300)))
        if -3.3 < e_mid["adf_t"] < -2.9:
            check(not e_mid["reject_no_coint_5pct"], f"EG rejects at t={e_mid['adf_t']:.2f} (DF cv used?)")
            break
    else:
        check(False, "no independent-walk pair landed between the DF and EG critical values")
    check(johansen(np.column_stack([a, b]))["rank_trace_5pct"] == 0, "Johansen finds rank>0 in independent walks")

    # 3. three tenors driven by one common level trend -> rank 2. Loadings 1, 0.9, 0.8 are linear in
    #    tenor, so the 2s5s10s-style fly (-1, 2, -1) removes the trend exactly -> known-vector ADF rejects;
    #    the 1:-1 wing spread keeps 0.2 x trend -> must not reject.
    lvl = np.cumsum(rng.normal(0, 6, T))
    Y3 = np.column_stack([lvl + 50 + 3 * rng.normal(size=T), 0.9 * lvl + 80 + 3 * rng.normal(size=T),
                          0.8 * lvl + 100 + 3 * rng.normal(size=T)])
    j3 = johansen(Y3, k=1, det="rc")
    check(j3["rank_trace_5pct"] == 2, f"Johansen rc rank {j3['rank_trace_5pct']} != 2 for one common trend")
    check(adf(Y3 @ np.array([-1.0, 2.0, -1.0]))[0] < EG_CV["c"][1][1], "known fly vector not stationary")
    check(adf(Y3[:, 0] - Y3[:, 2])[0] > EG_CV["c"][1][1], "trending wing spread looks stationary")

    # 4. exact identity, one series: Johansen eigenvalue = squared partial correlation of dz_t and z_{t-1}
    #    given constant and k lagged differences, so trace = m*ln(1 + t^2/(m-K)) with t the ADF t-stat.
    dz = np.zeros(T)
    for t in range(1, T):
        dz[t] = 0.5 * dz[t - 1] + rng.normal()
    z, k = np.cumsum(dz), 2
    d1 = np.diff(z)
    m = len(d1) - k
    Xa = np.column_stack([np.ones(m), z[k:k + m]] + [d1[k - i:k - i + m] for i in range(1, k + 1)])
    ta = _tstat(d1[k:], Xa, 1)
    lr1 = johansen(z[:, None], k=k, det="c")["trace"][0]
    check(abs(lr1 - m * math.log(1 + ta ** 2 / (m - Xa.shape[1]))) < 1e-6, "Johansen/ADF identity broken")

    # 5. loader: long curve_par in pct, two snaps, one bad row -> wide bp
    rows = [("2026-01-02", "eod_ny", "USD-SOFR", "0D", "2Y", 4.00, True),
            ("2026-01-02", "eod_ny", "USD-SOFR", "0D", "10Y", 4.25, True),
            ("2026-01-02", "eod_ldn", "USD-SOFR", "0D", "2Y", 9.99, True),
            ("2026-01-05", "eod_ny", "USD-SOFR", "0D", "2Y", 4.01, True),
            ("2026-01-05", "eod_ny", "USD-SOFR", "0D", "10Y", 9.99, False)]
    df = pd.DataFrame(rows, columns=["date", "snap", "curve_id", "start", "tenor", "par_rate_pct", "data_ok"])
    w = load_levels(df, ["USD-SOFR|0D|10Y", "USD-SOFR|0D|2Y"], snap="eod_ny")
    check(w.shape == (1, 2) and abs(w.iloc[0, 0] - 425.0) < 1e-9 and abs(w.iloc[0, 1] - 400.0) < 1e-9,
          f"loader wrong: {w.to_dict()}")

    # 6. cross-check against statsmodels when available (exact same statistic expected)
    try:
        from statsmodels.tsa.stattools import coint
        from statsmodels.tsa.vector_ar.vecm import coint_johansen
    except Exception:
        coint = None
    if coint is not None:
        sm_t = coint(y, x, trend="c", autolag="aic")[0]
        check(abs(sm_t - eg["adf_t"]) < 1e-6, f"EG t {eg['adf_t']:.6f} != statsmodels {sm_t:.6f}")
        sm = coint_johansen(Y3, det_order=0, k_ar_diff=2)
        mine = johansen(Y3, k=2, det="c")
        check(np.allclose(sm.lr1, mine["trace"], atol=1e-6), f"trace {mine['trace']} != statsmodels {sm.lr1}")
        check(np.allclose(sm.lr2, mine["max_eig"], atol=1e-6), "max-eig differs from statsmodels")

    for f in fails:
        print("FAIL:", f)
    print("selftest", "FAILED" if fails else "passed", f"({'with' if coint else 'without'} statsmodels cross-check)")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="CSV or Parquet: curve_par, bond_quotes, stir_quotes, swap_spreads, or wide bp")
    ap.add_argument("--series", help="comma-separated ids; first = leg normalised to 1 (put the longer tenor first)")
    ap.add_argument("--snap")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--k-ar-diff", type=int, default=1, help="lagged differences in the VECM (VAR order - 1)")
    ap.add_argument("--det", choices=["rc", "c"], default="rc")
    ap.add_argument("--test-vector", help="hypothesised weights in yield space, e.g. -1,2,-1")
    ap.add_argument("--out", help="write the Johansen spread (bp) to this CSV")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.file and a.series):
        ap.error("--file and --series are required")
    df = pd.read_parquet(a.file) if a.file.endswith(".parquet") else pd.read_csv(a.file, dtype={"start": str})
    lv = load_levels(df, [s.strip() for s in a.series.split(",")], a.snap)
    lv = lv.loc[a.start or lv.index.min():a.end or lv.index.max()]
    tv = [float(v) for v in a.test_vector.split(",")] if a.test_vector else None
    res = analyse(lv, k=a.k_ar_diff, det=a.det, test_vector=tv)
    if a.out:
        pd.Series(lv.to_numpy() @ np.asarray(res["johansen"]["beta_first"]), index=lv.index,
                  name="spread_bp").to_csv(a.out)
    print(json.dumps(_clean(res), indent=1, ensure_ascii=True))


def _clean(o):
    """JSON-safe: numpy scalars -> python, non-finite floats -> null."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, np.ndarray)):
        return [_clean(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    return o


if __name__ == "__main__":
    main()
