"""Dynamic Nelson-Siegel(-Svensson) curve fit with fixed decay, factor time series and residuals.

Zero form, time-scale parametrisation (x = tau / lam, tau in years):
    z(tau) = b0 + b1 * (1 - e^-x) / x + b2 * [(1 - e^-x) / x - e^-x]   (+ b3 * same hump in lam2 for NSS)
Equivalent forward form: f(tau) = b0 + b1 e^-x + b2 x e^-x (+ b3 x2 e^-x2).
b0 = long level z(inf), b0 + b1 = instantaneous short rate, -b1 ~ slope (long - short), b2 = curvature.
Default lam = 1/(0.0609*12) = 1.368y (Diebold-Li monthly 0.0609): curvature peaks at 1.793*lam ~ 2.45y.

Units: input zero/par rates in percent; betas in percent; residuals in bp = market - model
(positive = market yield above model = cheap to receive / buy).

CLI (canonical tables from data-contract-and-adapters):
    python nelson_siegel.py --input curve_zero.parquet --curve-id USD-SOFR --out ns_usd
    python nelson_siegel.py --input curve_par.csv --table curve_par --curve-id USD-GOVT-US --grid
    python nelson_siegel.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd

DL_LAMBDA = 1.0 / (0.0609 * 12.0)  # years; Diebold-Li 0.0609 per month


def ns_loadings(tau, lam: float, lam2: float | None = None) -> np.ndarray:
    """Columns: level, slope, curvature (and second curvature for NSS)."""
    def hump_pair(t, l):
        x = np.asarray(t, float) / l
        safe = np.where(x > 1e-8, x, 1.0)
        slope = np.where(x > 1e-8, (1.0 - np.exp(-x)) / safe, 1.0 - x / 2.0)
        return slope, slope - np.exp(-x)
    s1, c1 = hump_pair(tau, lam)
    cols = [np.ones_like(s1), s1, c1]
    if lam2:
        cols.append(hump_pair(tau, lam2)[1])
    return np.column_stack(cols)


def fit_curve(tau, z, lam: float = DL_LAMBDA, lam2: float | None = None, w=None):
    """OLS (optionally weighted) fit of one curve. Returns (betas, model_z)."""
    tau, z = np.asarray(tau, float), np.asarray(z, float)
    X = ns_loadings(tau, lam, lam2)
    sw = np.sqrt(np.ones_like(z) if w is None else np.asarray(w, float))
    beta = np.linalg.lstsq(X * sw[:, None], z * sw, rcond=None)[0]
    return beta, X @ beta


def grid_lambda(curves, grid, lam2: float | None = None) -> float:
    """Pick one lam minimising pooled SSE over a list of (tau, z) curves. Freeze it afterwards."""
    sse = [sum(float(np.sum((z - fit_curve(t, z, lam, lam2)[1]) ** 2)) for t, z in curves) for lam in grid]
    return float(grid[int(np.argmin(sse))])


def fit_panel(long: pd.DataFrame, lam: float = DL_LAMBDA, lam2: float | None = None):
    """long: columns date, tau_years, rate_pct, label. Returns (betas df indexed by date, residual long df)."""
    names = ["b0_level", "b1_slope", "b2_curv"] + (["b3_curv2"] if lam2 else [])
    rows, res = [], []
    for d, g in long.groupby("date", sort=True):
        g = g[g["tau_years"] > 0].sort_values("tau_years")
        if len(g) < len(names) + 2:
            continue  # ponytail: needs >= k+2 nodes; ask for more tenors rather than fit a saturated curve
        beta, model = fit_curve(g["tau_years"], g["rate_pct"], lam, lam2)
        r_bp = (g["rate_pct"].to_numpy() - model) * 100.0
        rows.append({"date": d, **dict(zip(names, beta)), "rmse_bp": float(np.sqrt(np.mean(r_bp ** 2))),
                     "mad_bp": float(np.mean(np.abs(r_bp))), "n_nodes": len(g)})
        res.append(pd.DataFrame({"date": d, "label": g["label"].to_numpy(), "tau_years": g["tau_years"].to_numpy(),
                                 "market_pct": g["rate_pct"].to_numpy(), "model_pct": model, "resid_bp": r_bp}))
    betas = pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(columns=names)
    return betas, (pd.concat(res, ignore_index=True) if res else pd.DataFrame())


def ar1_forecast(series: pd.Series, h: int):
    """Diebold-Li style AR(1) by OLS: x_t = c + phi x_{t-1}. Returns (c, phi, h-step forecast)."""
    x = np.asarray(series.dropna(), float)
    A = np.column_stack([np.ones(len(x) - 1), x[:-1]])
    c, phi = np.linalg.lstsq(A, x[1:], rcond=None)[0]
    if abs(1.0 - phi) < 1e-12:
        return c, phi, x[-1] + h * c
    mu = c / (1.0 - phi)
    return c, phi, mu + phi ** h * (x[-1] - mu)


_TENOR = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([DWMY])\s*$", re.I)


def tenor_years(t: str) -> float:
    m = _TENOR.match(str(t))
    if not m:
        raise ValueError(f"cannot parse tenor {t!r}")
    n, u = float(m.group(1)), m.group(2).upper()
    return n * {"D": 1 / 365.0, "W": 7 / 365.0, "M": 1 / 12.0, "Y": 1.0}[u]


def load_long(path: str, table: str, curve_id: str, snap: str | None) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.lower().endswith(".parquet") else pd.read_csv(path)
    df = df[df["curve_id"] == curve_id]
    if snap:
        df = df[df["snap"] == snap]
    if "data_ok" in df:
        df = df[df["data_ok"].astype(str).str.lower() != "false"]
    if df.empty:
        raise SystemExit(f"no rows for curve_id={curve_id} snap={snap}; ask the data adapter for the curve")
    if "snap" in df and df["snap"].nunique() > 1:
        raise SystemExit(f"several snaps {sorted(df['snap'].unique())}: pass --snap so curves are not pooled")
    d = pd.to_datetime(df["date"])
    if table == "curve_zero":
        tau = (pd.to_datetime(df["node_date"]) - d).dt.days / 365.0  # ACT/365F, as in the contract
        z = df["zero_rate_pct"] if "zero_rate_pct" in df else pd.Series(np.nan, index=df.index)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = z.fillna(-100.0 * np.log(df["discount_factor"]) / tau)
        label = df["tenor"] if "tenor" in df else tau.round(2).astype(str)
    else:  # curve_par: spot-starting par rates; NS on par rates is a smoother, loadings refer to par
        df = df[df["start"].astype(str).str.upper() == "0D"]
        d = pd.to_datetime(df["date"])
        tau = df["tenor"].map(tenor_years)
        z, label = df["par_rate_pct"], df["tenor"]
    out = pd.DataFrame({"date": d.dt.date, "tau_years": tau.astype(float), "rate_pct": z.astype(float),
                        "label": label.astype(str)})
    return out[out["tau_years"] > 0].dropna()


def _selftest() -> int:
    from scipy.integrate import quad
    fails = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            fails.append(name)

    # 1. Analytic loading values at tau = lam: slope 1-1/e, curvature 1-2/e; beta (4,-2,1) -> z = 3 exactly.
    L = ns_loadings([1.7], 1.7)[0]
    check("slope loading at tau=lam is 1-1/e", abs(L[1] - (1 - np.exp(-1))) < 1e-12)
    check("curvature loading at tau=lam is 1-2/e", abs(L[2] - (1 - 2 * np.exp(-1))) < 1e-12)
    check("z(lam) = 3.000 for beta (4,-2,1)", abs(L @ [4, -2, 1] - 3.0) < 1e-12)
    # 2. Limits: z(0+) = b0 + b1, z(inf) = b0.
    b = np.array([4.0, -2.0, 1.0])
    check("z(0+) = b0 + b1", abs(ns_loadings([1e-10], 1.3)[0] @ b - 2.0) < 1e-8)
    check("z(inf) = b0", abs(ns_loadings([1e5], 1.3)[0] @ b - 4.0) < 1e-4)
    # 3. Zeros built independently by integrating the NSS forward curve; fit must recover betas exactly.
    tb, lam, lam2 = np.array([3.5, -1.8, 2.2, -1.1]), 1.5, 8.0
    fwd3 = lambda t: tb[0] + tb[1] * np.exp(-t / lam) + tb[2] * (t / lam) * np.exp(-t / lam)
    fwd4 = lambda t: fwd3(t) + tb[3] * (t / lam2) * np.exp(-t / lam2)
    tau = np.array([0.25, 0.5, 1, 2, 3, 4, 5, 7, 10, 12, 15, 20, 25, 30])
    z3 = np.array([quad(fwd3, 0, t, epsabs=1e-13)[0] / t for t in tau])
    z4 = np.array([quad(fwd4, 0, t, epsabs=1e-13)[0] / t for t in tau])
    beta3, m3 = fit_curve(tau, z3, lam)
    check("NS fit recovers betas from integrated forwards", np.allclose(beta3, tb[:3], atol=1e-8))
    check("NS residuals < 1e-6 bp", np.max(np.abs(z3 - m3)) * 100 < 1e-6)
    beta4, _ = fit_curve(tau, z4, lam, lam2)
    check("NSS fit recovers betas incl. second hump", np.allclose(beta4, tb, atol=1e-7))
    # 4. Pooled grid search recovers the true decay.
    grid = np.round(np.arange(0.5, 4.01, 0.1), 2)
    check("grid_lambda recovers lam=1.5", abs(grid_lambda([(tau, z3)], grid) - 1.5) < 1e-9)
    # 5. Panel fit: residual sign is market - model in bp.
    long = pd.DataFrame({"date": ["2026-01-02"] * len(tau), "tau_years": tau, "rate_pct": z3 + (tau == 10) * 0.05,
                         "label": [f"{t:g}Y" for t in tau]})
    _, res = fit_panel(long, lam)
    r10 = float(res.loc[res["label"] == "10Y", "resid_bp"].iloc[0])
    check("10y bumped +5bp shows positive (cheap) residual", 2.0 < r10 < 5.0)
    # 6. AR(1): exact x_t = 1 + 0.9 x_{t-1}; mean 10; 5-step forecast is analytic.
    x = [0.0]
    for _ in range(60):
        x.append(1 + 0.9 * x[-1])
    c, phi, fc = ar1_forecast(pd.Series(x), 5)
    check("AR(1) recovers c=1, phi=0.9", abs(c - 1) < 1e-8 and abs(phi - 0.9) < 1e-10)
    check("AR(1) 5-step forecast", abs(fc - (10 + 0.9 ** 5 * (x[-1] - 10))) < 1e-8)
    # 7. Tenor parsing and the Diebold-Li curvature peak near 30 months.
    check("tenor parse", tenor_years("6M") == 0.5 and tenor_years("10Y") == 10.0)
    tau_fine = np.linspace(0.05, 10, 20000)
    peak = tau_fine[np.argmax(ns_loadings(tau_fine, DL_LAMBDA)[:, 2])]
    check("DL curvature peak ~ 29-30 months", 2.4 < peak < 2.5)
    print("selftest:", "OK" if not fails else f"{len(fails)} FAILED")
    return 1 if fails else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fixed-decay Nelson-Siegel(-Svensson) fit: betas, residuals (bp).")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--input", help="curve_zero or curve_par CSV/Parquet")
    p.add_argument("--table", default="curve_zero", choices=["curve_zero", "curve_par"])
    p.add_argument("--curve-id")
    p.add_argument("--snap")
    p.add_argument("--lam", type=float, default=DL_LAMBDA, help="decay in years (default 1.368 = Diebold-Li)")
    p.add_argument("--lam2", type=float, help="second decay in years -> NSS")
    p.add_argument("--grid", action="store_true", help="choose lam on pooled sample (0.3..6y), then freeze")
    p.add_argument("--forecast-h", type=int, default=0, help="AR(1) forecast horizon in observations")
    p.add_argument("--out", default="ns", help="output prefix: <out>_betas.csv, <out>_resid.csv")
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not (a.input and a.curve_id):
        p.error("--input and --curve-id are required")
    long = load_long(a.input, a.table, a.curve_id, a.snap)
    lam = a.lam
    if a.grid:
        curves = [(g["tau_years"].to_numpy(), g["rate_pct"].to_numpy()) for _, g in long.groupby("date")]
        lam = grid_lambda(curves, np.round(np.arange(0.3, 6.01, 0.1), 2), a.lam2)
    betas, res = fit_panel(long, lam, a.lam2)
    betas.to_csv(f"{a.out}_betas.csv")
    res.to_csv(f"{a.out}_resid.csv", index=False)
    print(f"curve={a.curve_id} lam={lam:.3f}y lam2={a.lam2} dates={len(betas)}")
    if len(betas):
        print(betas.tail(1).round(4).to_string())
        last = res[res["date"] == res["date"].max()][["label", "market_pct", "model_pct", "resid_bp"]]
        print(last.round(3).to_string(index=False))
    if a.forecast_h and len(betas) > 30:
        for col in [c for c in betas.columns if c.startswith("b")]:
            c, phi, fc = ar1_forecast(betas[col], a.forecast_h)
            print(f"{col}: phi={phi:.4f} last={betas[col].iloc[-1]:.4f} h={a.forecast_h} forecast={fc:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
