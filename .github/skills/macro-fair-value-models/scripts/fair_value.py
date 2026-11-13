"""Macro fair-value regressions for rates (yields, forwards, curves, spreads).

y_t = a + sum_k b_k x_{k,t} + e_t, estimated in levels on a rolling or expanding window.
Outputs an out-of-sample fair value (coefficients fitted through t-gap, applied to x_t), the residual
(actual - fair value; for yields positive = cheap), z = residual / in-window regression SE, Newey-West
HAC t-stats, residual AR(1) half-life, attribution of a move to drivers, and the curve-wide
PCA-macro variant (regress curve PC scores on macro drivers, map back to tenors).

Inputs are canonical tables (see data-contract-and-adapters): curve_par (par/forward rates, pct),
macro_series (release vintages, aligned point-in-time on pub_ts_utc), or a wide panel CSV/Parquet
(date + columns) for anything else (FX, vol, commodity series landed by an adapter).

Examples
  python fair_value.py --curve-par curve_par.parquet --macro macro_series.parquet \
      --y "curve_par:USD-SOFR|5Y|5Y" --x "ois1y1y=curve_par:USD-SOFR|1Y|1Y" \
      --x "ism=macro:US-ISM-MFG" --expect ois1y1y:+ --expect ism:+ --freq W-WED --window 520
  python fair_value.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- core estimation
def _design(X) -> np.ndarray:
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    return np.column_stack([np.ones(len(X)), X])


def default_hac_lags(T: int) -> int:
    """Lazarus-Lewis-Stock-Watson (2018) rule L = ceil(1.3 sqrt(T)); levels residuals are very persistent."""
    return int(np.ceil(1.3 * np.sqrt(T)))


def nw_cov(Z: np.ndarray, e: np.ndarray, lags: int) -> np.ndarray:
    """Newey-West (Bartlett kernel) HAC covariance of OLS coefficients. Z includes the constant."""
    u = Z * e[:, None]
    S = u.T @ u
    for l in range(1, lags + 1):
        G = u[l:].T @ u[:-l]
        S += (1.0 - l / (lags + 1.0)) * (G + G.T)
    A = np.linalg.inv(Z.T @ Z)
    return A @ S @ A


def fit(y: pd.Series, X: pd.DataFrame, hac_lags: int | None = None) -> dict:
    """Full-sample OLS in levels with HAC and plain OLS standard errors."""
    df = pd.concat([y.rename("_y"), X], axis=1).dropna()
    yv, Z = df["_y"].to_numpy(float), _design(df[X.columns].to_numpy(float))
    b, *_ = np.linalg.lstsq(Z, yv, rcond=None)
    e = yv - Z @ b
    T, p = Z.shape
    se_reg = float(np.sqrt(e @ e / (T - p)))
    dev = yv - yv.mean()
    L = default_hac_lags(T) if hac_lags is None else hac_lags
    names = ["const"] + list(X.columns)
    se_hac = np.sqrt(np.diag(nw_cov(Z, e, L)))
    se_ols = se_reg * np.sqrt(np.diag(np.linalg.inv(Z.T @ Z)))
    return dict(coef=pd.Series(b, names), se_hac=pd.Series(se_hac, names), se_ols=pd.Series(se_ols, names),
                t_hac=pd.Series(b / se_hac, names), r2=float(1 - e @ e / (dev @ dev)), se=se_reg,
                resid=pd.Series(e, df.index), n=T, hac_lags=L)


def rolling_fair_value(y: pd.Series, X: pd.DataFrame, window: int = 520, mode: str = "rolling",
                       min_obs: int | None = None, gap: int = 1) -> pd.DataFrame:
    """Out-of-sample fair value. For each t the fit uses obs [t-gap-window+1, t-gap] (rolling) or
    [0, t-gap] (expanding); gap=1 means nothing dated t enters the coefficients (no look-ahead)."""
    df = pd.concat([y.rename("_y"), X], axis=1).dropna()
    yv, Z = df["_y"].to_numpy(float), _design(df[X.columns].to_numpy(float))
    min_obs = min_obs or window
    p, rows = Z.shape[1], []
    for t in range(min_obs + gap - 1, len(df)):
        end = t - gap + 1
        start = 0 if mode == "expanding" else max(0, end - window)
        if end - start < max(min_obs, p + 2):
            continue
        Zw, yw = Z[start:end], yv[start:end]
        b, *_ = np.linalg.lstsq(Zw, yw, rcond=None)
        e = yw - Zw @ b
        se = float(np.sqrt(e @ e / (len(e) - p)))
        dev = yw - yw.mean()
        fv = float(Z[t] @ b)
        rows.append((df.index[t], yv[t], fv, yv[t] - fv, (yv[t] - fv) / se, se,
                     float(1 - e @ e / (dev @ dev)), end - start, *b))
    cols = ["date", "y", "fair_value", "resid", "z", "se", "r2", "n_fit", "coef_const"] + \
           [f"coef_{c}" for c in X.columns]
    return pd.DataFrame(rows, columns=cols).set_index("date")


def attribute(coef: pd.Series, x_from: pd.Series, x_to: pd.Series) -> pd.Series:
    """Model-implied change split by driver: b_k * (x_k,to - x_k,from). Sum = fitted change."""
    b = coef.drop("const")
    return b * (x_to - x_from).reindex(b.index)


def half_life(resid: pd.Series) -> float:
    """AR(1) half-life of the residual in observations: -ln2 / ln(phi)."""
    e = np.asarray(pd.Series(resid).dropna(), float)
    if len(e) < 3:
        return float("nan")
    e = e - e.mean()
    phi = float(e[1:] @ e[:-1] / (e[:-1] @ e[:-1]))
    if phi <= 0:
        return 0.0
    return float("inf") if phi >= 1 else float(-np.log(2) / np.log(phi))


def pca_macro_fair_value(Y: pd.DataFrame, X: pd.DataFrame, k: int = 2) -> dict:
    """Curve-wide macro FV: PCA on yield levels, regress the first k PC scores on X, map back.
    IN-SAMPLE (PCA, betas and z all use the whole sample, as the published versions do): descriptive
    valuation only. For a traded signal, fit on data through t-1 and apply the fit to X at t.
    sens[m, j] = d yield_j / d x_m = sum_i B[m, i] W[j, i] (betas on PCs -> betas on yields)."""
    df = pd.concat([Y, X], axis=1, keys=["Y", "X"]).dropna()
    Yv, Xv = df["Y"].to_numpy(float), df["X"].to_numpy(float)
    mu = Yv.mean(axis=0)
    _, s, Vt = np.linalg.svd(Yv - mu, full_matrices=False)
    W = Vt[:k].T
    Z = _design(Xv)
    B, *_ = np.linalg.lstsq(Z, (Yv - mu) @ W, rcond=None)
    fitted = mu + (Z @ B) @ W.T
    idx, cols = df.index, list(Y.columns)
    resid = pd.DataFrame(Yv - fitted, idx, cols)
    return dict(fitted=pd.DataFrame(fitted, idx, cols), resid=resid, z=resid / resid.std(ddof=1),
                sens=pd.DataFrame(B[1:] @ W.T, list(X.columns), cols),
                var_explained=pd.Series(s[:k] ** 2 / (s ** 2).sum(), [f"PC{i + 1}" for i in range(k)]))


# ---------------------------------------------------------------- canonical-table helpers
def load(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def curve_series(cp: pd.DataFrame, key: str, snap: str | None = None) -> pd.Series:
    curve_id, start, tenor = key.split("|")
    m = cp[(cp["curve_id"] == curve_id) & (cp["start"].astype(str) == start) & (cp["tenor"].astype(str) == tenor)]
    if "data_ok" in m:
        m = m[m["data_ok"].astype(str).str.lower() != "false"]
    if snap:
        m = m[m["snap"] == snap]
    if m["snap"].nunique() > 1:
        raise SystemExit(f"{key}: mixed snaps {sorted(m['snap'].unique())}; pass --snap")
    if m.empty:
        raise SystemExit(f"{key}: no rows in curve_par")
    return m.set_index(pd.to_datetime(m["date"]))["par_rate_pct"].astype(float).sort_index()


def macro_asof(macro: pd.DataFrame, series_id: str, dates, cutoff_utc: str = "21:00") -> pd.Series:
    """Point-in-time value on each date: the latest vintage of the most recent ref_period whose
    pub_ts_utc <= date + cutoff (UTC). Revisions never leak backwards."""
    m = macro[macro["series_id"] == series_id].copy()
    if m.empty:
        raise SystemExit(f"{series_id}: no rows in macro_series")
    m["pub"] = pd.to_datetime(m["pub_ts_utc"], utc=True)
    m = m.sort_values("pub", kind="stable")
    known, vals = {}, []
    for rp, v in zip(m["ref_period"].astype(str), m["value"].astype(float)):
        known[rp] = v
        vals.append(known[max(known)])
    state = pd.Series(vals, index=m["pub"]).groupby(level=0).last()
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    hh, mm = (int(p) for p in cutoff_utc.split(":"))
    cut = idx.tz_localize("UTC") + pd.Timedelta(hours=hh, minutes=mm)
    pos = state.index.searchsorted(cut, side="right") - 1
    out = np.where(pos >= 0, state.to_numpy()[np.clip(pos, 0, None)], np.nan)
    return pd.Series(out, index=idx, name=series_id)


def parse_sel(s: str):
    alias, _, rest = s.partition("=") if "=" in s else (None, "", s)
    table, _, key = rest.partition(":")
    return alias or rest, table, key


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--curve-par", help="canonical curve_par CSV/Parquet")
    ap.add_argument("--macro", help="canonical macro_series CSV/Parquet")
    ap.add_argument("--panel", help="wide CSV/Parquet: date + one column per series")
    ap.add_argument("--y", help="target selector: curve_par:<curve_id|start|tenor> | macro:<series_id> | panel:<col>")
    ap.add_argument("--x", action="append", default=[], help="[alias=]selector; repeat per driver")
    ap.add_argument("--expect", action="append", default=[], help="alias:+ or alias:- expected coefficient sign")
    ap.add_argument("--snap", help="snap to use from curve_par (never mix snaps)")
    ap.add_argument("--cutoff-utc", default="21:00", help="macro releases known by date+HH:MM UTC (default 21:00)")
    ap.add_argument("--freq", help="resample to e.g. W-WED (weekly Wednesday closes) before fitting")
    ap.add_argument("--window", type=int, default=520, help="obs per fit (520 = ~2y daily or ~10y weekly)")
    ap.add_argument("--mode", choices=["rolling", "expanding"], default="rolling")
    ap.add_argument("--gap", type=int, default=1, help="1 = coefficients through t-1 (out-of-sample)")
    ap.add_argument("--y-unit", choices=["pct", "bp"], help="unit of y; residuals reported in bp (pct assumed for curve_par, required otherwise)")
    ap.add_argument("--attr-from", help="date: attribute the change from this date to the last date to drivers")
    ap.add_argument("--out", help="write the rolling fair-value series to this CSV")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.y or not a.x:
        ap.error("--y and at least one --x are required")

    tabs = {"curve_par": load(a.curve_par) if a.curve_par else None,
            "panel": load(a.panel) if a.panel else None}
    if tabs["panel"] is not None:
        tabs["panel"] = tabs["panel"].set_index(pd.to_datetime(tabs["panel"]["date"])).drop(columns="date")
    macro = load(a.macro) if a.macro else None

    def market(table, key):
        if table == "curve_par" and tabs["curve_par"] is not None:
            return curve_series(tabs["curve_par"], key, a.snap)
        if table == "panel" and tabs["panel"] is not None:
            return tabs["panel"][key].astype(float).sort_index()
        return None

    sels = [parse_sel(a.y)] + [parse_sel(s) for s in a.x]
    series = {al: market(t, k) for al, t, k in sels if t != "macro"}
    missing = [al for al, t, _ in sels if t != "macro" and series[al] is None]
    if missing:
        raise SystemExit(f"no table loaded for {missing}")
    dates = pd.DatetimeIndex(sorted(set().union(*[s.index for s in series.values()]))) if series else None
    for al, t, k in sels:
        if t == "macro":
            if macro is None:
                raise SystemExit("--macro required for macro: selectors")
            if dates is None:
                raise SystemExit("need at least one market series to define dates")
            series[al] = macro_asof(macro, k, dates, a.cutoff_utc)
    data = pd.DataFrame(series).sort_index().dropna()
    if data.empty:
        raise SystemExit("no dates where the target and every driver are all available")
    if a.freq:  # last real observation in each bin (no future-dated bin labels)
        data = data.groupby(pd.Grouper(freq=a.freq)).tail(1)
    y_alias = sels[0][0]
    y, X = data[y_alias], data[[s[0] for s in sels[1:]]]
    if not a.y_unit and sels[0][1] != "curve_par":
        ap.error("--y-unit (pct or bp) is required when the target is not a curve_par series")
    unit = a.y_unit or "pct"
    bp = 100.0 if unit == "pct" else 1.0

    f = fit(y, X)
    print(f"Full sample {data.index[0].date()}..{data.index[-1].date()}  n={f['n']}  R2={f['r2']:.2f}  "
          f"SE={f['se'] * bp:.1f}bp  HAC lags={f['hac_lags']}  resid half-life={half_life(f['resid']):.0f} obs")
    print(pd.DataFrame({"coef": f["coef"], "t_hac": f["t_hac"], "t_ols": f["coef"] / f["se_ols"]}).round(3).to_string())
    for e in a.expect:
        al, sign = e.rsplit(":", 1)
        if al in f["coef"] and np.sign(f["coef"][al]) != (1 if sign == "+" else -1):
            print(f"FLAG wrong-signed: {al} coef {f['coef'][al]:.3f}, expected {sign}")

    r = rolling_fair_value(y, X, a.window, a.mode, gap=a.gap)
    if r.empty:
        print(f"not enough data for a {a.window}-obs window (have {len(data)})")
        return 1
    last = r.iloc[-1]
    print(f"\n{a.mode} {a.window}-obs out-of-sample, last {r.index[-1].date()}: y={last.y:.4f} FV={last.fair_value:.4f} "
          f"resid={last.resid * bp:+.1f}bp z={last.z:+.2f} SE={last.se * bp:.1f}bp R2={last.r2:.2f}  "
          f"out-of-sample resid half-life={half_life(r.resid):.0f} obs")
    for c in X.columns:
        flips = float((np.sign(r[f"coef_{c}"]) != np.sign(f["coef"][c])).mean())
        print(f"  {c}: last coef {last[f'coef_{c}']:.4f}; share of windows with sign != full-sample: {flips:.0%}")
    if a.attr_from:
        if pd.Timestamp(a.attr_from) > data.index[-1]:
            raise SystemExit(f"--attr-from {a.attr_from} is after the last date {data.index[-1].date()}")
        d0 = data.index[data.index.searchsorted(pd.Timestamp(a.attr_from))]
        coef = pd.Series({"const": last.coef_const, **{c: last[f"coef_{c}"] for c in X.columns}})
        con = attribute(coef, X.loc[d0], X.iloc[-1]) * bp
        act = (y.iloc[-1] - y.loc[d0]) * bp
        print(f"\nAttribution {d0.date()}..{data.index[-1].date()} (last-window coefs, bp):")
        print(con.round(1).to_string())
        print(f"model-implied {con.sum():+.1f}  actual {act:+.1f}  unexplained {act - con.sum():+.1f}")
    if a.out:
        r.assign(resid_bp=r.resid * bp, se_bp=r.se * bp).to_csv(a.out)
        print(f"wrote {a.out}")
    return 0


# ---------------------------------------------------------------- self-test (known answers)
def selftest() -> int:
    rng = np.random.default_rng(7)
    fails = []

    def check(ok, msg):
        print(("PASS " if ok else "FAIL ") + msg)
        if not ok:
            fails.append(msg)

    def ar1(n, phi, sd):
        e = rng.normal(0, sd, n)
        for t in range(1, n):
            e[t] += phi * e[t - 1]
        return e

    # 1. exact linear relation -> exact coefficients, zero SE
    idx = pd.bdate_range("2015-01-01", periods=300)
    X = pd.DataFrame(rng.normal(size=(300, 2)), idx, ["a", "b"])
    y_exact = 1.5 + 2 * X.a - 0.5 * X.b
    f = fit(y_exact, X)
    check(np.allclose(f["coef"].values, [1.5, 2.0, -0.5], atol=1e-10) and f["se"] < 1e-9,
          "exact OLS recovers (1.5, 2, -0.5)")
    re = rolling_fair_value(y_exact, X, window=100)
    check(np.abs(re.resid).max() < 1e-9, "rolling out-of-sample FV reproduces an exact relation")

    # 2. published attribution: JPM 10y UST FV coefficients applied to 30y YTD moves (21 Aug 2026) -> +29bp
    #    levels on 21-Aug-26 (1y1y 4.11, FRI 92.6, 5y5y BE 2.07, Fed B/S 20.7, dummy 0) minus YTD changes
    coef = pd.Series([9.56, 0.414, -0.04, 0.284, -0.127, 0.144], ["const", "ois1y1y", "fri", "be5y5y", "fedbs", "tariff"])
    x1 = pd.Series([4.11, 92.6, 2.07, 20.7, 0.0], coef.index[1:])
    x0 = x1 - pd.Series([0.98, 0.1, 0.02, -0.2, -1.0], coef.index[1:])
    con = attribute(coef, x0, x1) * 100
    check(abs(con.sum() - 29) < 0.5 and abs(con["tariff"] + 14.4) < 1e-9, f"attribution sums to +29bp ({con.sum():.1f})")

    # 3. rolling out-of-sample FV on I(1) driver + AR(1) residual with known beta 0.8
    n = 1500
    idx = pd.bdate_range("2018-01-01", periods=n)
    x = pd.DataFrame({"x": np.cumsum(rng.normal(0, 0.05, n)) + 2.0}, idx)
    y = 0.5 + 0.8 * x.x + ar1(n, 0.9, 0.03)
    r = rolling_fair_value(y, x, window=500)
    check(abs(r.coef_x.median() - 0.8) < 0.03, f"rolling beta median {r.coef_x.median():.3f} ~ 0.8")
    check(r.index[0] == idx[500], "first fair value uses exactly the 500 prior obs")
    check(np.allclose(r.z, r.resid / r.se), "z = resid / in-window SE")
    y2 = y.copy()
    y2.iloc[-1] += 5.0
    r2 = rolling_fair_value(y2, x, window=500)
    check(abs(r2.fair_value.iloc[-1] - r.fair_value.iloc[-1]) < 1e-12, "gap=1: today's y cannot move today's FV")
    check(0.6 < r.z.std() < 1.8, f"out-of-sample z has unit-like scale ({r.z.std():.2f})")

    # 4. residual half-life of AR(1) phi=0.9 is ln2/-ln0.9 = 6.58 obs
    hl = half_life(pd.Series(ar1(20000, 0.9, 1.0)))
    check(abs(hl / 6.579 - 1) < 0.1, f"AR(1) half-life {hl:.2f} ~ 6.58")

    # 5. HAC: AR(1) regressor and AR(1) errors (rho=0.8) inflate the slope SE by sqrt((1+.64)/(1-.64))=2.13
    n = 20000
    idx = pd.RangeIndex(n)
    xr = pd.DataFrame({"x": ar1(n, 0.8, 1.0)}, idx)
    f = fit(pd.Series(1 + 0.5 * xr.x + ar1(n, 0.8, 1.0), idx), xr)
    ratio = f["se_hac"]["x"] / f["se_ols"]["x"]
    check(1.7 < ratio < 2.6, f"HAC/OLS SE ratio {ratio:.2f} ~ 2.13 under autocorrelation")
    xi = pd.DataFrame({"x": rng.normal(size=n)}, idx)
    fi = fit(pd.Series(1 + 0.5 * xi.x + rng.normal(size=n), idx), xi)
    ratio_iid = fi["se_hac"]["x"] / fi["se_ols"]["x"]
    check(0.85 < ratio_iid < 1.15, f"HAC/OLS SE ratio {ratio_iid:.2f} ~ 1 for iid data")

    # 6. PCA-macro: yields = mu + X B L' + noise -> sensitivity matrix B L' recovered
    n, ten = 800, ["2y", "5y", "10y", "30y"]
    L, _ = np.linalg.qr(rng.normal(size=(4, 2)))
    Bt = np.array([[0.6, 0.2], [0.3, -0.4], [-0.2, 0.1]])
    Xm = pd.DataFrame(rng.normal(size=(n, 3)), columns=["growth", "infl", "fedbs"])
    truth = np.array([3.8, 3.9, 4.3, 4.9]) + Xm.to_numpy() @ Bt @ L.T
    Ym = pd.DataFrame(truth + rng.normal(0, 0.01, (n, 4)), columns=ten)
    pm = pca_macro_fair_value(Ym, Xm, k=2)
    err = np.abs(pm["sens"].to_numpy() - Bt @ L.T).max()
    check(err < 0.01, f"PCA-macro sensitivity matrix recovered (max err {err:.4f})")
    ferr = np.abs(pm["fitted"].to_numpy() - truth).max()
    check(ferr < 0.005, f"PCA-macro fair values match the noiseless truth (max err {ferr:.4f})")
    check(abs(pm["resid"].to_numpy().std() - 0.01) < 0.003, "PCA-macro residual SD ~ noise SD 0.01")

    # 7. point-in-time macro alignment: nothing leaks backwards (22:30Z release is after the 21:00 cutoff),
    #    and a late revision of an older month does not replace the newest month
    macro = pd.DataFrame({"series_id": "S", "ref_period": ["2026-08", "2026-09", "2026-10", "2026-09"],
                          "value": [1.0, 2.0, 3.0, 2.5],
                          "pub_ts_utc": ["2026-09-15T12:30:00Z", "2026-10-15T12:30:00Z",
                                         "2026-11-13T22:30:00Z", "2026-11-16T12:30:00Z"]})
    got = [float(v) for v in macro_asof(macro, "S", ["2026-10-14", "2026-10-15", "2026-11-13", "2026-11-14", "2026-11-16"])]
    check(got == [1.0, 2.0, 2.0, 3.0, 3.0], f"as-of values {got} == [1, 2, 2, 3, 3]")

    print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
