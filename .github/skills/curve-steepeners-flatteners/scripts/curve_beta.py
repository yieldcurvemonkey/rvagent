"""Steepener/flattener weighting and directionality: leg betas, hedge-ratio menu, spread-vs-level beta,
beta-weighted spread series and bull/bear move-type shares.

Conventions (all rates in bp internally; curve_par stores pct, converted x100):
    spread s = y_long - y_short                      (2s10s = 10y - 2y; positive = upward sloping)
    steepener = receive short leg / pay long leg     ("long the curve"; flattener = opposite signs)
    h = DV01 risk on long leg / DV01 risk on short leg
    steepener P&L per unit of short-leg risk R:  R * (h * dy_long - dy_short)     (bp x currency/bp)
    h = 1 is DV01-neutral; the weighted spread is s_w = h * y_long - y_short.

Hedge-ratio menu (sigma = stdev of yield changes, rho = corr of leg changes; Burghardt et al. 2005 ch.6):
    dv01        h = 1                         zero net DV01; the quoted spread
    vol         h = sig_s / sig_l             "yield beta" assuming rho = 1 (vol-weighted curve)
    reg_long    h = rho * sig_s / sig_l       = OLS slope of dy_s on dy_l ("yield delta"): zero expected P&L
                                                for a given long-leg move
    reg_short   h = sig_s / (rho * sig_l)     = 1 / OLS slope of dy_l on dy_s (minimum-variance hedge of the
                                                long leg with the short leg; the most net-long of the four)
    level       h = beta_s|x / beta_l|x       zero expected P&L for a move in a level factor x (10y, PC1, ...)

CLI (canonical `curve_par` table from data-contract-and-adapters, long format):
    python curve_beta.py --curve-par curve_par.parquet --curve-id USD-SOFR --short 2Y --long 10Y --level 10Y
    python curve_beta.py --curve-par curve_par.csv --curve-id EUR-ESTR --short 5Y --long 30Y --window 250 \
        --horizon 1 --out eur_5s30s_beta.csv
    python curve_beta.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

MOVE_TYPES = ("bull_steep", "bear_flat", "bull_flat", "bear_steep")


# ----------------------------------------------------------------------------------------------- core maths
def hedge_ratio_menu(sig_s: float, sig_l: float, rho: float,
                     beta_s_x: float | None = None, beta_l_x: float | None = None) -> dict:
    """Risk ratio h (long-leg DV01 risk per unit of short-leg DV01 risk) under each weighting rule."""
    menu = {"dv01": 1.0, "vol": sig_s / sig_l, "reg_long": rho * sig_s / sig_l,
            "reg_short": sig_s / (rho * sig_l) if rho > 0 else np.nan}
    if beta_s_x is not None and beta_l_x:
        menu["level"] = beta_s_x / beta_l_x
    return menu


def notionals(risk_short: float, h: float, dv01_short: float, dv01_long: float) -> tuple[float, float]:
    """Leg notionals for a steepener with `risk_short` currency/bp on the short leg (receive) and h x that on the
    long leg (pay). dv01_* = currency per bp per unit notional. Flip both signs for a flattener."""
    return risk_short / dv01_short, -h * risk_short / dv01_long


def ols(y, x) -> dict:
    """OLS of y on x with intercept: slope, intercept, r2, corr, resid sd."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    xc, yc = x - x.mean(), y - y.mean()
    sxx = float(xc @ xc)
    slope = float(xc @ yc) / sxx if sxx > 0 else np.nan
    corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else np.nan
    resid = yc - slope * xc
    return {"slope": slope, "intercept": float(y.mean() - slope * x.mean()), "r2": corr ** 2, "corr": corr,
            "resid_sd": float(resid.std(ddof=2)) if len(x) > 2 else np.nan, "n": int(len(x))}


def leg_stats(dy_s, dy_l, dx=None) -> dict:
    """Vols, correlation and level betas of the two legs' changes (bp). dx defaults to the long leg."""
    dy_s, dy_l = np.asarray(dy_s, float), np.asarray(dy_l, float)
    dx = dy_l if dx is None else np.asarray(dx, float)
    ok = np.isfinite(dy_s) & np.isfinite(dy_l) & np.isfinite(dx)
    dy_s, dy_l, dx = dy_s[ok], dy_l[ok], dx[ok]
    return {"sig_s": float(dy_s.std(ddof=1)), "sig_l": float(dy_l.std(ddof=1)),
            "rho": float(np.corrcoef(dy_s, dy_l)[0, 1]),
            "beta_s_x": ols(dy_s, dx)["slope"], "beta_l_x": ols(dy_l, dx)["slope"], "n": int(ok.sum())}


def move_type_shares(dy_s, dy_l) -> dict:
    """Share of absolute spread movement by mode. Bull/bear = sign of the average leg change; steep/flat = sign
    of the spread change. Shares of sum|ds| sum to 1. front_driven = bull_steep + bear_flat (front leg moved
    more); back_driven = bull_flat + bear_steep. twist = share of |ds| on days the legs moved opposite ways."""
    dy_s, dy_l = np.asarray(dy_s, float), np.asarray(dy_l, float)
    ok = np.isfinite(dy_s) & np.isfinite(dy_l)
    dy_s, dy_l = dy_s[ok], dy_l[ok]
    ds, lvl = dy_l - dy_s, 0.5 * (dy_s + dy_l)
    w = np.abs(ds)
    tot = w.sum()
    if tot == 0:
        return {k: np.nan for k in MOVE_TYPES + ("front_driven", "back_driven", "twist")}
    bull, steep = lvl < 0, ds > 0
    out = {"bull_steep": w[bull & steep].sum() / tot, "bear_flat": w[~bull & ~steep].sum() / tot,
           "bull_flat": w[bull & ~steep].sum() / tot, "bear_steep": w[~bull & steep].sum() / tot}
    out["front_driven"] = out["bull_steep"] + out["bear_flat"]
    out["back_driven"] = out["bull_flat"] + out["bear_steep"]
    out["twist"] = w[np.sign(dy_s) * np.sign(dy_l) < 0].sum() / tot
    return {k: float(v) for k, v in out.items()}


def analyse(y_s: pd.Series, y_l: pd.Series, y_x: pd.Series | None = None, window: int = 250,
            horizon: int = 1, short_window: int = 60) -> tuple[dict, pd.DataFrame]:
    """y_* = yield levels in bp indexed by date. Changes over `horizon` business days (non-overlapping when
    horizon > 1, anchored so the last observation is always used). Returns (summary for the last `window` changes,
    daily frame with spreads and rolling betas). Raises ValueError with < 30 changes. `spread_w` applies the CURRENT h
    to the whole history (descriptive only, not a backtest series); `h_level_rolling` is lagged one observation so it
    only uses changes known before that date."""
    df = pd.concat({"y_s": y_s, "y_l": y_l, "y_x": y_l if y_x is None else y_x}, axis=1).dropna().sort_index()
    df["spread"] = df["y_l"] - df["y_s"]
    ch = df[["y_s", "y_l", "y_x"]].iloc[(len(df) - 1) % horizon::horizon].diff().dropna()
    if len(ch) < 30:
        raise ValueError(f"need >= 30 clean yield changes, have {len(ch)}")
    last = ch.iloc[-window:]
    st = leg_stats(last["y_s"], last["y_l"], last["y_x"])
    menu = hedge_ratio_menu(st["sig_s"], st["sig_l"], st["rho"], st["beta_s_x"], st["beta_l_x"])
    d_spread = last["y_l"] - last["y_s"]
    dirn = ols(d_spread, last["y_x"])
    h = menu.get("level", menu["reg_long"])
    dirn_w = ols(h * last["y_l"] - last["y_s"], last["y_x"])
    recent = ch.iloc[-short_window:]
    st_r = leg_stats(recent["y_s"], recent["y_l"], recent["y_x"])
    h_recent = st_r["beta_s_x"] / st_r["beta_l_x"] if st_r["beta_l_x"] else np.nan
    df["spread_w"] = h * df["y_l"] - df["y_s"]
    # rolling level-neutral h (beta_s|x / beta_l|x) on the change frame, mapped back to dates
    cov = ch.rolling(window, min_periods=max(20, window // 2)).cov()
    var_x = cov.xs("y_x", level=1)["y_x"]
    roll_h = (cov.xs("y_s", level=1)["y_x"] / var_x) / (cov.xs("y_l", level=1)["y_x"] / var_x)
    df["h_level_rolling"] = roll_h.shift(1).reindex(df.index).ffill()   # shift(1): no look-ahead
    summary = {
        **{f"h_{k}": v for k, v in menu.items()}, **st,
        "spread_bp": float(df["spread"].iloc[-1]), "spread_w_bp": float(df["spread_w"].iloc[-1]),
        "dir_beta_spread_on_level": dirn["slope"], "dir_corr_R": dirn["corr"], "dir_r2": dirn["r2"],
        "dir_beta_weighted_on_level": dirn_w["slope"],
        "spread_change_sd_bp": float(d_spread.std(ddof=1)),
        "h_level_recent": float(h_recent), "h_used": float(h),
        "h_unstable": bool(abs(h_recent - h) > 0.25 * abs(h)) if np.isfinite(h_recent) else True,
        **{f"share_{k}": v for k, v in move_type_shares(last["y_s"], last["y_l"]).items()},
        "asof": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
        "window_changes": int(len(last)), "horizon_days": horizon,
    }
    return summary, df


# ----------------------------------------------------------------------------------------------- I/O
def load_curve_par(path: str, curve_id: str, start: str = "0D", snap: str | None = None) -> pd.DataFrame:
    """Wide frame date x tenor of par rates in bp from the canonical long `curve_par` table."""
    t = pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)
    t = t[(t["curve_id"] == curve_id) & (t["start"].astype(str) == start)]
    if "data_ok" in t.columns:
        t = t[t["data_ok"].fillna(True).astype(bool)]
    if snap is not None:
        t = t[t["snap"] == snap]
    elif "snap" in t.columns and t["snap"].nunique() > 1:
        t = t[t["snap"] == t["snap"].mode().iloc[0]]
    if t.empty:
        raise SystemExit(f"no curve_par rows for curve_id={curve_id} start={start}")
    t = t.assign(date=pd.to_datetime(t["date"]))
    return t.pivot_table(index="date", columns="tenor", values="par_rate_pct", aggfunc="last") * 100.0


# ----------------------------------------------------------------------------------------------- self-test
def _selftest() -> int:
    fails = []

    # 1) Burghardt et al. (2005) four hedge ratios: $100mm OTR 30y hedged with 5y, 1/12/98.
    #    sig_5 = 101.9, sig_30 = 81.7 (annualised bp), rho = 0.88; conventional (DV01) hedge = $341.2mm of 5y.
    #    Published: yield beta 273.6, yield delta 310.9, minimum variance 240.7.
    m = hedge_ratio_menu(sig_s=101.9, sig_l=81.7, rho=0.88)
    conv = 341.2
    got = {k: conv / m[k] for k in ("vol", "reg_long", "reg_short")}
    for k, want in {"vol": 273.6, "reg_long": 310.9, "reg_short": 240.7}.items():
        if abs(got[k] - want) > 0.6:
            fails.append(f"Burghardt {k}: {got[k]:.1f} vs {want}")

    # 2) DV01-neutral notionals (Clarus 2014 rule): N_short = DV01_long / DV01_short x N_long
    n_s, n_l = notionals(50_000, 1.0, dv01_short=470.0, dv01_long=880.0)   # per 1mm notional, illustrative
    if abs(n_s * 470.0 + n_l * 880.0) > 1e-6 or n_l >= 0:
        fails.append("dv01-neutral notionals")
    n_s, n_l = notionals(50_000, 0.6, dv01_short=470.0, dv01_long=880.0)   # beta-weighted: long-leg risk = 0.6 x short
    if abs(n_s * 470.0 - 50_000) > 1e-6 or abs(-n_l * 880.0 - 0.6 * 50_000) > 1e-6:
        fails.append("beta-weighted notionals")

    # 3) Simulated legs with known beta: dy_s = 0.6 dy_l + e, sd(dy_l) = 5, sd(e) = 2.
    rng = np.random.default_rng(7)
    n = 20_000
    dl = rng.normal(0, 5.0, n)
    ds = 0.6 * dl + rng.normal(0, 2.0, n)
    idx = pd.bdate_range("2000-01-03", periods=n + 1)
    y_l = pd.Series(np.r_[300.0, 300.0 + np.cumsum(dl)], idx)
    y_s = pd.Series(np.r_[200.0, 200.0 + np.cumsum(ds)], idx)
    summ, _ = analyse(y_s, y_l, window=n, short_window=n)
    sig_s, rho = np.sqrt(0.36 * 25 + 4), 0.6 * 5 / np.sqrt(0.36 * 25 + 4)
    checks = {"h_reg_long": 0.6, "h_level": 0.6, "h_vol": sig_s / 5.0, "h_reg_short": sig_s / (rho * 5.0),
              "dir_beta_spread_on_level": 0.4, "dir_beta_weighted_on_level": 0.0}
    for k, want in checks.items():
        if abs(summ[k] - want) > 0.02:
            fails.append(f"sim {k}: {summ[k]:.4f} vs {want:.4f}")

    # 4) Move-type shares, deterministic: (dy_s, dy_l) -> bull-steep 1, bear-flat 2, bull-flat 2, bear-steep 3
    sh = move_type_shares([-2, 3, -1, 1], [-1, 1, -3, 4])
    for k, want in {"bull_steep": 1 / 8, "bear_flat": 2 / 8, "bull_flat": 2 / 8, "bear_steep": 3 / 8,
                    "front_driven": 3 / 8, "twist": 0.0}.items():
        if abs(sh[k] - want) > 1e-12:
            fails.append(f"move-type {k}: {sh[k]} vs {want}")

    # 5) horizon sampling is anchored at the last observation; short history is refused; rolling h is lagged
    _, fr = analyse(y_s, y_l, window=250, horizon=5)
    s5, _ = analyse(y_s.iloc[:-3], y_l.iloc[:-3], window=250, horizon=5)
    if s5["asof"] != str(idx[-4].date()) or abs(fr["h_level_rolling"].iloc[-1] - 0.6) > 0.1:
        fails.append("horizon anchoring / rolling h")
    try:
        analyse(y_s.iloc[:10], y_l.iloc[:10])
        fails.append("short history not refused")
    except ValueError:
        pass

    for f in fails:
        print("FAIL", f)
    print("selftest", "FAILED" if fails else "passed")
    return 1 if fails else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--curve-par", help="canonical curve_par CSV/Parquet")
    p.add_argument("--curve-id", help="e.g. USD-SOFR, EUR-ESTR, USD-GOVT-US")
    p.add_argument("--start", default="0D", help="forward start of both legs (default spot 0D)")
    p.add_argument("--snap", default=None)
    p.add_argument("--short", default="2Y")
    p.add_argument("--long", default="10Y")
    p.add_argument("--level", default=None, help="level tenor for betas/directionality (default = long leg)")
    p.add_argument("--window", type=int, default=250, help="number of changes in the estimation window")
    p.add_argument("--short-window", type=int, default=60, help="recent window for the stability check")
    p.add_argument("--horizon", type=int, default=1, help="change horizon in business days (5 = weekly)")
    p.add_argument("--out", help="write the daily frame (spreads, rolling h) to CSV")
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not (a.curve_par and a.curve_id):
        p.error("--curve-par and --curve-id are required (or --selftest)")
    wide = load_curve_par(a.curve_par, a.curve_id, a.start, a.snap)
    for t in {a.short, a.long, a.level or a.long}:
        if t not in wide.columns:
            raise SystemExit(f"tenor {t} not in curve_par for {a.curve_id}; have {sorted(wide.columns)}")
    summ, frame = analyse(wide[a.short], wide[a.long], wide[a.level] if a.level else None,
                          a.window, a.horizon, a.short_window)
    summ.update(curve_id=a.curve_id, short=a.short, long=a.long, level=a.level or a.long, start=a.start)
    print(pd.Series(summ).to_string())
    if a.out:
        frame.to_csv(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
