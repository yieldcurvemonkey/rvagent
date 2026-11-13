"""ALM hedge-flow arithmetic for structural-demand analysis (pensions, insurers).

Three tools, all in plain numpy/pandas:

  rebalance  Extra receive-fixed DV01 a duration-hedged liability holder must add after a parallel rate shock,
             because liabilities are more convex than the hedge assets (the "forced ALM receiving" channel).
  regcurve   Regulatory liability discount curve with UFR extrapolation beyond the First Smoothing Point
             (Solvency II style: f(h) = w(h;a)*LLFR + (1-w(h;a))*UFR, w = (1-exp(-a h))/(a h)), and how a
             liability's DV01 splits between market rates <= FSP, the LLFR and the (non-market) UFR.
  nowcast    Funded-ratio nowcast: regress monthly % changes of DB plan assets and liabilities on factor changes
             (rates, credit spread, equity for assets only), then apply this month's factor moves.

Conventions: rates in decimal inside functions, pct on the CLI; DV01 in currency per bp, positive = gains when
rates fall (receive-fixed / long duration). A positive `flow_dv01` means the holder must RECEIVE (buy duration).

Usage:
  python alm_hedge_flow.py rebalance --liab-pv 140 --liab-dur 16.66 --liab-conv 211.37 \
      --asset-pv 149.90 --asset-dur 15.56 --asset-conv 141.49 --shock-bp -100
  python alm_hedge_flow.py regcurve --curve-zero data/curve_zero.parquet --curve-id EUR-ESTR --date 2026-11-10 \
      --cashflows liab.csv --fsp 20 --ufr-pct 3.30 --alpha 0.20
  python alm_hedge_flow.py nowcast --macro data/macro_series.parquet --assets-id US-DB-ASSETS \
      --liabs-id US-DB-LIABS --rate-ids US-SWAP-30Y,US-CORP-AA-SPREAD --equity-id US-EQUITY-INDEX \
      --moves US-SWAP-30Y=0.15,US-CORP-AA-SPREAD=-0.05,US-EQUITY-INDEX=2.0
  python alm_hedge_flow.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- rebalance (convexity of ALM hedging)
def duration_match_leverage(liab_pv: float, liab_dur: float, bond_dur: float) -> float:
    """Cash weight M (negative = borrow) so that M*0 + (PV-M)*D_bond = PV*D_liab."""
    return liab_pv - liab_pv * liab_dur / bond_dur


def rebalance_flow(liab_pv, liab_dur, liab_conv, asset_pv, asset_dur, asset_conv,
                   hedge_ratio: float = 1.0, shock_bp: float = -100.0) -> dict:
    """DV01 = D*PV*1e-4; dDV01/dy = -C*PV*1e-4 per unit of y, so dDV01 = -C*PV*1e-8*shock_bp.

    flow_dv01 = hedge_ratio*dDV01_liab - dDV01_asset: receive DV01 needed to restore the hedge ratio.
    """
    l_dv01, a_dv01 = liab_dur * liab_pv * 1e-4, asset_dur * asset_pv * 1e-4
    d_l = -liab_conv * liab_pv * 1e-8 * shock_bp
    d_a = -asset_conv * asset_pv * 1e-8 * shock_bp
    return {"liab_dv01": l_dv01, "asset_dv01": a_dv01, "gap_dv01_now": hedge_ratio * l_dv01 - a_dv01,
            "d_liab_dv01": d_l, "d_asset_dv01": d_a, "flow_dv01": hedge_ratio * d_l - d_a,
            "flow_pct_of_liab_dv01": 100 * (hedge_ratio * d_l - d_a) / l_dv01}


# ---------------------------------------------------------------- regcurve (UFR extrapolation)
def ufr_weight(alpha: float, h) -> np.ndarray:
    """w(h; alpha) = (1 - exp(-alpha h)) / (alpha h); w(0) = 1, w(inf) = 0."""
    h = np.asarray(h, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = (1 - np.exp(-alpha * h)) / (alpha * h)
    return np.where(h > 1e-12, w, 1.0)


def regulatory_zero(t, zmkt, fsp: float, ufr: float, alpha: float, llfr: float) -> np.ndarray:
    """Continuously compounded zero rates. t<=FSP: market. t>FSP: z(T)T = z(FSP)FSP + h*[u + (LLFR-u)w(h)],
    with u = ln(1+UFR) and LLFR given as a continuously compounded forward."""
    t = np.asarray(t, float)
    u, h = np.log1p(ufr), np.maximum(t - fsp, 0.0)
    fwd = u + (llfr - u) * ufr_weight(alpha, h)
    tail = (zmkt(fsp) * fsp + fwd * h) / np.where(t > 0, t, 1.0)
    return np.where(t <= fsp, zmkt(t), tail)


def default_llfr(zmkt, fsp: float, span: float = 5.0) -> float:
    """Market forward from FSP-span to FSP (cont. comp.).
    ponytail: the EUR LLFR also blends forwards beyond the FSP with liquidity weights; pass --llfr if known."""
    a = fsp - span
    return float((zmkt(fsp) * fsp - zmkt(a) * a) / span)


def liability_dv01_split(t, cf, zmkt, fsp, ufr, alpha, llfr=None) -> dict:
    """PV and DV01 (per bp, + = gains when rates fall) of liability cash flows under the regulatory curve,
    split into: market rates <= FSP, the LLFR, and the UFR (not hedgeable with market instruments)."""
    t, cf = np.asarray(t, float), np.asarray(cf, float)
    llfr = default_llfr(zmkt, fsp) if llfr is None else llfr
    z = regulatory_zero(t, zmkt, fsp, ufr, alpha, llfr)
    df = np.exp(-z * t)
    h = np.maximum(t - fsp, 0.0)
    w = ufr_weight(alpha, h)
    beyond = t > fsp
    pv_dv = cf * df * 1e-4
    mkt = np.where(beyond, pv_dv * fsp, pv_dv * t).sum()   # sensitivity to z(<=FSP), LLFR held fixed
    llfr_dv = (pv_dv * h * w)[beyond].sum()
    ufr_dv = (pv_dv * h * (1 - w))[beyond].sum()
    econ = (cf * np.exp(-zmkt(t) * t) * t * 1e-4).sum()  # same cash flows on the pure market curve
    return {"pv": float((cf * df).sum()), "dv01_mkt_le_fsp": float(mkt), "dv01_llfr": float(llfr_dv),
            "dv01_ufr": float(ufr_dv), "dv01_market_hedgeable": float(mkt + llfr_dv),
            "dv01_economic_market_curve": float(econ), "llfr": float(llfr)}


def zero_curve_from_table(curve_zero: pd.DataFrame, curve_id: str, date: str, snap: str | None = None):
    """Linear-in-zero interpolator (decimal, cont. comp.) from canonical `curve_zero` rows; flat beyond nodes."""
    d = curve_zero[(curve_zero["curve_id"] == curve_id) & (pd.to_datetime(curve_zero["date"]) == pd.Timestamp(date))]
    if snap is not None:
        d = d[d["snap"] == snap]
    if d.empty:
        raise SystemExit(f"no curve_zero rows for {curve_id} on {date}")
    if "snap" in d and d["snap"].nunique() > 1:
        raise SystemExit(f"several snaps for {curve_id} on {date}: pass --snap")
    t = (pd.to_datetime(d["node_date"]) - pd.Timestamp(date)).dt.days.to_numpy() / 365.0
    d, t = d[t > 0], t[t > 0]                                   # DF(date) = 1 node carries no rate
    if "zero_rate_pct" in d and d["zero_rate_pct"].notna().all():
        z = d["zero_rate_pct"].to_numpy() / 100
    else:
        z = -np.log(d["discount_factor"].to_numpy()) / t
    o = np.argsort(t)
    t, z = t[o], z[o]
    return lambda x: np.interp(np.asarray(x, float), t, z)


# ---------------------------------------------------------------- nowcast (funded ratio)
def fit_funded_ratio_model(df: pd.DataFrame, assets: str, liabs: str, rate_cols: list[str], equity: str | None,
                           window: int = 36) -> dict:
    """OLS on the last `window` months. Assets: %chg ~ d(rate_cols) + equity %chg. Liabilities: %chg ~ d(rate_cols).
    Rate/spread factors enter as first differences in their own unit; equity as % change."""
    x_r = df[rate_cols].diff()
    y_a, y_l = 100 * df[assets].pct_change(), 100 * df[liabs].pct_change()
    x_a = pd.concat([x_r, 100 * df[equity].pct_change()], axis=1) if equity else x_r
    out = {}
    for name, y, x in (("assets", y_a, x_a), ("liabs", y_l, x_r)):
        m = pd.concat([y, x], axis=1).dropna().tail(window)
        if len(m) < max(12, m.shape[1] + 2):
            raise ValueError(f"{name}: only {len(m)} usable months for {m.shape[1] - 1} factors")
        X = np.column_stack([np.ones(len(m)), m.iloc[:, 1:].to_numpy()])
        b, *_ = np.linalg.lstsq(X, m.iloc[:, 0].to_numpy(), rcond=None)
        out[name] = pd.Series(b, index=["const"] + list(m.columns[1:]))
    return out


def nowcast_funded_ratio(last_assets: float, last_liabs: float, betas: dict, moves: dict) -> dict:
    """Apply factor moves (same units as the fit; equity in %) to the last published assets/liabilities."""
    def pct(b):
        return b["const"] + sum(b[k] * moves.get(k, 0.0) for k in b.index if k != "const")
    a, l_ = last_assets * (1 + pct(betas["assets"]) / 100), last_liabs * (1 + pct(betas["liabs"]) / 100)
    return {"assets": a, "liabs": l_, "funded_ratio_pct": 100 * a / l_,
            "prev_funded_ratio_pct": 100 * last_assets / last_liabs}


def macro_wide(macro: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    """Latest vintage per (series_id, ref_period) from canonical `macro_series`, pivoted wide by ref_period."""
    m = macro[macro["series_id"].isin(ids)].sort_values("pub_ts_utc")
    m = m.drop_duplicates(["series_id", "ref_period"], keep="last")
    return m.pivot(index="ref_period", columns="series_id", values="value").sort_index()[ids]


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok ' if ok else 'FAIL'} {name}: got {got:.6f} want {want:.6f}")
        if not ok:
            fails.append(name)

    # Tuckman & Serrat (2022) Sec.4.8 pension: PV 140, D 16.66, C 211.37; JNJ 20y D 15.56, C 141.49.
    m = duration_match_leverage(140, 16.66, 15.56)
    check("leverage M (book: -9.90)", m, -9.90, 0.01)
    check("portfolio convexity (book: 151.50)", (140 - m) / 140 * 141.49, 151.50, 0.01)
    r = rebalance_flow(140, 16.66, 211.37, 140 - m, 15.56, 141.49, 1.0, -100)
    check("duration gap ~0", r["gap_dv01_now"], 0.0, 1e-6)
    want = (211.37 * 140 - 141.49 * (140 - m)) * 1e-6          # analytic: (C_L PV_L - C_A PV_A) * 1e-8 * 100
    check("rally flow = receive", r["flow_dv01"], want, 1e-9)
    check("selloff flow symmetric", rebalance_flow(140, 16.66, 211.37, 140 - m, 15.56, 141.49, 1.0, 100)["flow_dv01"],
          -want, 1e-9)
    # Independent check by full repricing: zero-coupon 30y liability hedged with levered 10y zeros (cont. comp.).
    y, dy = 0.04, -0.0010
    pv_l, pv_a = np.exp(-y * 30), np.exp(-y * 30) * 3.0        # 3x 10y zeros match a 30y zero's DV01
    dv01 = lambda pv, T, yy: pv * np.exp(-(yy - y) * T) * T * 1e-4
    exact = (dv01(pv_l, 30, y + dy) - dv01(pv_l, 30, y)) - (dv01(pv_a, 10, y + dy) - dv01(pv_a, 10, y))
    approx = rebalance_flow(pv_l, 30, 900, pv_a, 10, 100, 1.0, dy * 1e4)["flow_dv01"]
    check("zero-coupon repricing vs formula", approx, exact, 0.05 * abs(exact))

    # UFR weight: w(0)=1, w(inf)->0, w(0.11,10) = (1-e^-1.1)/1.1
    check("w(0)", float(ufr_weight(0.11, 0.0)), 1.0, 1e-12)
    check("w(0.11,10)", float(ufr_weight(0.11, 10.0)), (1 - np.exp(-1.1)) / 1.1, 1e-12)
    check("w(0.11,1e4)", float(ufr_weight(0.11, 1e4)), 0.0, 1e-3)
    # Regulatory zero converges to ln(1+UFR) far beyond the FSP, whatever the LLFR.
    zr = lambda x: np.full_like(np.asarray(x, float), 0.02)
    check("z(1e5) -> ln(1+UFR)", float(regulatory_zero(1e5, zr, 20, 0.033, 0.11, 0.05)), np.log1p(0.033), 1e-4)

    # Flat market curve at ln(1.033) and LLFR = UFR => regulatory curve = market curve; PV analytic.
    u = np.log1p(0.033)
    flat = lambda x: np.full_like(np.asarray(x, float), u)
    t = np.arange(1, 61, dtype=float)
    cf = np.ones_like(t)
    s = liability_dv01_split(t, cf, flat, 20, 0.033, 0.20, llfr=u)
    check("flat PV", s["pv"], float(np.exp(-u * t).sum()), 1e-10)
    check("DV01 split sums to economic", s["dv01_market_hedgeable"] + s["dv01_ufr"], s["dv01_economic_market_curve"], 1e-10)

    # Finite-difference check of the LLFR sensitivity on an upward-sloping curve.
    slope = lambda x: 0.02 + 0.0005 * np.asarray(x, float)
    s0 = liability_dv01_split(t, cf, slope, 20, 0.033, 0.20, llfr=0.03)
    pv = lambda zf, ll: liability_dv01_split(t, cf, zf, 20, 0.033, 0.20, llfr=ll)["pv"]
    check("LLFR DV01 vs central bump", s0["dv01_llfr"], (pv(slope, 0.0299) - pv(slope, 0.0301)) / 2,
          1e-4 * s0["dv01_llfr"])
    fd = (pv(lambda x: slope(x) - 1e-4, 0.03) - pv(lambda x: slope(x) + 1e-4, 0.03)) / 2
    check("market<=FSP DV01 vs central parallel bump", s0["dv01_mkt_le_fsp"], fd, 1e-4 * s0["dv01_mkt_le_fsp"])
    # Slower convergence (alpha 0.11 vs 0.20) puts more DV01 on the LLFR (market) and less on the UFR.
    s11 = liability_dv01_split(t, cf, slope, 20, 0.033, 0.11, llfr=0.03)
    check("alpha 0.11 raises LLFR DV01", float(s11["dv01_llfr"] > s0["dv01_llfr"]), 1.0, 0)

    # Funded-ratio model recovers known betas from noiseless simulated data.
    rng = np.random.default_rng(7)
    n = 40
    d_rate, d_spr, eq = rng.normal(0, 0.15, n), rng.normal(0, 0.05, n), rng.normal(0, 3.0, n)
    a_pct = 0.1 - 6.0 * d_rate - 4.0 * d_spr + 0.35 * eq
    l_pct = 0.2 - 14.0 * d_rate - 12.0 * d_spr
    df = pd.DataFrame({"r": np.r_[3.0, 3.0 + np.cumsum(d_rate)], "s": np.r_[1.0, 1.0 + np.cumsum(d_spr)],
                       "eq": 100 * np.r_[1.0, np.cumprod(1 + eq / 100)],
                       "A": 1000 * np.r_[1.0, np.cumprod(1 + a_pct / 100)],
                       "L": 1100 * np.r_[1.0, np.cumprod(1 + l_pct / 100)]})
    b = fit_funded_ratio_model(df, "A", "L", ["r", "s"], "eq", window=36)
    check("asset rate beta", b["assets"]["r"], -6.0, 1e-8)
    check("asset equity beta", b["assets"]["eq"], 0.35, 1e-8)
    check("liab rate beta", b["liabs"]["r"], -14.0, 1e-8)
    nc = nowcast_funded_ratio(1000, 1100, b, {"r": 0.10, "s": 0.0, "eq": 2.0})
    want_fr = 100 * 1000 * (1 + (0.1 - 0.6 + 0.7) / 100) / (1100 * (1 + (0.2 - 1.4) / 100))
    check("nowcast funded ratio", nc["funded_ratio_pct"], want_fr, 1e-8)

    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "PASSED")
    return 1 if fails else 0


# ---------------------------------------------------------------- CLI
def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rebalance", help="receive DV01 needed after a parallel shock")
    for k in ("liab-pv", "liab-dur", "liab-conv", "asset-pv", "asset-dur", "asset-conv"):
        r.add_argument(f"--{k}", type=float, required=True)
    r.add_argument("--hedge-ratio", type=float, default=1.0)
    r.add_argument("--shock-bp", type=float, default=-100.0)
    r.add_argument("--dv01-10y", type=float, help="DV01 per unit notional of the 10y swap, to express in 10y-eq")

    g = sub.add_parser("regcurve", help="UFR-extrapolated liability curve and DV01 split")
    g.add_argument("--curve-zero", required=True)
    g.add_argument("--curve-id", required=True)
    g.add_argument("--date", required=True)
    g.add_argument("--snap")
    g.add_argument("--cashflows", required=True, help="CSV with columns t_years,cashflow")
    g.add_argument("--fsp", type=float, default=20.0)
    g.add_argument("--ufr-pct", type=float, default=3.30)
    g.add_argument("--alpha", type=float, nargs="+", default=[0.20, 0.11])
    g.add_argument("--llfr-pct", type=float, help="cont. comp. LLFR; default = market fwd FSP-5 -> FSP")

    n = sub.add_parser("nowcast", help="funded-ratio nowcast from macro_series")
    n.add_argument("--macro", required=True)
    n.add_argument("--assets-id", required=True)
    n.add_argument("--liabs-id", required=True)
    n.add_argument("--rate-ids", required=True, help="comma list: rate/spread series (first-differenced)")
    n.add_argument("--equity-id")
    n.add_argument("--window", type=int, default=36)
    n.add_argument("--moves", required=True, help="id=move,...; rates in series units, equity in %%")
    a = ap.parse_args(argv)

    if a.cmd == "rebalance":
        res = rebalance_flow(a.liab_pv, a.liab_dur, a.liab_conv, a.asset_pv, a.asset_dur, a.asset_conv,
                             a.hedge_ratio, a.shock_bp)
        if a.dv01_10y:
            res["flow_10y_equiv_notional"] = res["flow_dv01"] / a.dv01_10y
        print(pd.Series(res).to_string())
    elif a.cmd == "regcurve":
        zmkt = zero_curve_from_table(_read(a.curve_zero), a.curve_id, a.date, a.snap)
        cfs = _read(a.cashflows)
        llfr = None if a.llfr_pct is None else a.llfr_pct / 100
        rows = {f"alpha={al:g}": liability_dv01_split(cfs["t_years"], cfs["cashflow"], zmkt, a.fsp,
                                                      a.ufr_pct / 100, al, llfr) for al in a.alpha}
        print(pd.DataFrame(rows).to_string())
    else:
        rate_ids = [s for s in a.rate_ids.split(",") if s]
        ids = [a.assets_id, a.liabs_id] + rate_ids + ([a.equity_id] if a.equity_id else [])
        wide = macro_wide(_read(a.macro), ids)
        betas = fit_funded_ratio_model(wide, a.assets_id, a.liabs_id, rate_ids, a.equity_id, a.window)
        moves = {k: float(v) for k, v in (kv.split("=") for kv in a.moves.split(","))}
        missing = set(ids[2:]) - set(moves)
        if missing:
            print(f"warning: no move given for {sorted(missing)}; assumed 0", file=sys.stderr)
        last = wide.dropna(subset=[a.assets_id, a.liabs_id]).iloc[-1]
        print(pd.concat(betas, axis=1).to_string())
        print(pd.Series(nowcast_funded_ratio(last[a.assets_id], last[a.liabs_id], betas, moves)).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
