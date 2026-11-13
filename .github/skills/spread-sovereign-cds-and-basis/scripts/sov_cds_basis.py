"""Sovereign CDS and bond-CDS basis tools.

Functions (per 100 notional; spreads in bp; hazard rates as decimals):
  hazard_from_spread      flat hazard rate that prices a CDS at its par spread (market upfront convention)
  upfront                 points upfront for a fixed-coupon CDS, + = protection buyer pays
  spread_from_upfront     inverse: quoted spread implied by points upfront on a fixed coupon
  bond_price_from_hazard  price of a fixed-coupon bond under a flat hazard rate and par recovery
  cds_equivalent_spread   par CDS spread implied by a bond price (solve hazard, then reprice the CDS)
  adjusted_cds            strip the FX (settlement-currency) and delivery-option components from a quote
  usd_asw                 asset & basis swapped spread of a non-USD bond over USD SOFR
  implied_fx_move_on_default   depreciation implied by a USD vs local-currency CDS pair
  jtd_neutral_notional    CDS notional that offsets the jump-to-default loss on a bond holding
  basis_screen            CDS - USD ASW basis, ASW <= CDS inequality slack, rolling z-score

CLI (screen): python sov_cds_basis.py --cds cds_quotes.csv --asw swap_spreads.csv --bonds bond_static.csv
  cds_quotes  (canonical): date, entity, tenor, par_spread_bp [, ask_spread_bp, ccy, settlement]
  swap_spreads (canonical): rows with curve_id == --usd-curve and measure == --measure, ref = bond instrument_id
  bond_static  (canonical): instrument_id, issuer, maturity_date
--selftest checks the Tuckman-Serrat Genworth tables and the Huggins-Schaller JGB USD ASW example.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def _survival(lam, times):
    t = np.asarray(times, float)
    s = np.exp(-lam * t)
    s_prev = np.concatenate([[1.0], s[:-1]])
    dt = np.diff(np.concatenate([[0.0], t]))
    return s, s_prev - s, dt


def _legs(lam, times, dfs, recovery):
    """Risky annuity (PV of 1 %/yr running, default accrual at half period) and contingent leg per 100."""
    df = np.asarray(dfs, float)
    s, pdef, dt = _survival(lam, times)
    rpv01 = float(np.sum(df * dt * (s + 0.5 * pdef)))
    contingent = float(np.sum(df * pdef) * (1.0 - recovery) * 100.0)
    return rpv01, contingent


def hazard_from_spread(spread_bp, times, dfs, recovery=0.40):
    f = lambda lam: _legs(lam, times, dfs, recovery)[0] * spread_bp / 100.0 - _legs(lam, times, dfs, recovery)[1]
    return brentq(f, 1e-12, 10.0, xtol=1e-12)


def upfront(spread_bp, coupon_bp, times, dfs, recovery=0.40):
    lam = hazard_from_spread(spread_bp, times, dfs, recovery)
    rpv01, _ = _legs(lam, times, dfs, recovery)
    return rpv01 * (spread_bp - coupon_bp) / 100.0


def spread_from_upfront(upfront_pts, coupon_bp, times, dfs, recovery=0.40):
    """Quoted (flat-hazard) spread in bp from points upfront (+ = buyer pays) on a fixed-coupon contract."""
    def f(lam):
        rpv01, cont = _legs(lam, times, dfs, recovery)
        return cont - rpv01 * coupon_bp / 100.0 - upfront_pts

    lam = brentq(f, 1e-12, 10.0, xtol=1e-12)
    rpv01, cont = _legs(lam, times, dfs, recovery)
    return 100.0 * cont / rpv01


def bond_price_from_hazard(lam, coupon_pct, times, dfs, recovery=0.40):
    df = np.asarray(dfs, float)
    s, pdef, dt = _survival(lam, times)
    coupons = np.sum(df * coupon_pct * dt * (s + 0.5 * pdef))
    rec = np.sum(df * pdef) * recovery * 100.0
    return float(coupons + rec + df[-1] * s[-1] * 100.0)


def cds_equivalent_spread(price, coupon_pct, times, dfs, recovery=0.40):
    lam = brentq(lambda x: bond_price_from_hazard(x, coupon_pct, times, dfs, recovery) - price, 1e-12, 10.0,
                 xtol=1e-12)
    rpv01, cont = _legs(lam, times, dfs, recovery)
    return 100.0 * cont / rpv01


def adjusted_cds(cds_bp, settlement="physical", fx_share=0.55, do_share=0.06):
    """Huggins-Schaller: pure credit = 0.45 x quote (cash) or 0.39 x quote (physical / CTD-style auction)."""
    k = 1.0 - fx_share - (do_share if str(settlement).lower() != "cash" else 0.0)
    return cds_bp * k


def usd_asw(local_asw_bp, ccbs_bp, cf, icbs_bp=0.0):
    """(local ASW [+ ICBS to the CCBS index] - CCBS) / CF, CF = BPV_USD / BPV_local. ASW + = bond cheap."""
    return (local_asw_bp + icbs_bp - ccbs_bp) / cf


def implied_fx_move_on_default(s_usd_bp, s_local_bp):
    """Fractional fall of the local currency (in USD) on default implied by s_local = s_usd x (1 - d)."""
    return 1.0 - s_local_bp / s_usd_bp


def jtd_neutral_notional(face, dirty_px, recovery=0.40):
    return face * (dirty_px / 100.0 - recovery) / (1.0 - recovery)


def basis_screen(panel, lookback=126, cost_bp=0.0, min_cds_for_ratio=10.0):
    """panel: date, instrument_id, usd_asw_bp, cds_bp [, cds_ask_bp]. Sign: basis = CDS - USD ASW (bp);
    negative = bond cheap vs CDS. slack = USD ASW - CDS ask - cost; > 0 = tradeable violation of ASW <= CDS."""
    p = panel.sort_values(["instrument_id", "date"]).copy()
    ask = p["cds_ask_bp"] if "cds_ask_bp" in p else p["cds_bp"]
    p["basis_bp"] = p["cds_bp"] - p["usd_asw_bp"]
    p["slack_bp"] = p["usd_asw_bp"] - ask.fillna(p["cds_bp"]) - cost_bp
    p["violation"] = p["slack_bp"] > 0
    g = p.groupby("instrument_id")["basis_bp"]
    minp = max(20, lookback // 3)
    mu = g.transform(lambda x: x.rolling(lookback, min_periods=minp).mean())
    sd = g.transform(lambda x: x.rolling(lookback, min_periods=minp).std())
    p["basis_z"] = (p["basis_bp"] - mu) / sd
    p["basis_to_cds"] = np.where(p["cds_bp"].abs() >= min_cds_for_ratio, p["basis_bp"] / p["cds_bp"], np.nan)
    return p


def _tenor_years(t):
    t = str(t).strip().upper()
    return float(t[:-1]) / (12.0 if t.endswith("M") else 1.0)


def _read(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def build_panel(cds, asw, bonds, usd_curve="USD-SOFR", measure="asw_parpar"):
    """Join canonical swap_spreads (USD ASW per bond) with a CDS curve interpolated to each bond's maturity."""
    a = asw[(asw["curve_id"] == usd_curve) & (asw["measure"] == measure)].copy()
    if a.duplicated(["date", "ref"]).any():
        raise ValueError("several ASW rows per date/bond (snaps?): filter to one snap first")
    flip = a["sign_convention"].eq("swap_minus_govt") if "sign_convention" in a else False
    a["usd_asw_bp"] = np.where(flip, -a["value_bp"], a["value_bp"])
    b = bonds.sort_values("valid_from").groupby("instrument_id").last().reset_index() \
        if "valid_from" in bonds else bonds.copy()
    a = a.merge(b[["instrument_id", "issuer", "maturity_date"]], left_on="ref", right_on="instrument_id")
    a["mat_y"] = (pd.to_datetime(a["maturity_date"]) - pd.to_datetime(a["date"])).dt.days / 365.25
    c = cds.copy()
    c["ty"] = c["tenor"].map(_tenor_years)
    if c.duplicated(["date", "entity", "ty"]).any():
        raise ValueError("several CDS quotes per date/entity/tenor (denomination, doc clause?): keep one contract")
    has_ask = "ask_spread_bp" in c
    out = []
    for (d, ent), grp in a.groupby([a["date"].astype(str), "issuer"]):
        cc = c[(c["date"].astype(str) == d) & (c["entity"] == ent)].sort_values("ty")
        if cc.empty:
            continue  # no CDS for this issuer/date: skip, never fill
        g = grp[["date", "instrument_id", "issuer", "mat_y", "usd_asw_bp"]].copy()
        g["cds_bp"] = np.interp(g["mat_y"], cc["ty"], cc["par_spread_bp"])
        if has_ask:
            g["cds_ask_bp"] = np.interp(g["mat_y"], cc["ty"], cc["ask_spread_bp"].fillna(cc["par_spread_bp"]))
        out.append(g)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def _selftest():
    ok = True

    def check(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name}: got {got:.4f}, want {want} +/- {tol}")

    # Tuckman & Serrat (2022) Table 14.10/14.11: Genworth 5y, annual pay, R = 40%, as of 16 Aug 2021
    t = [1, 2, 3, 4, 5]
    dfs = [0.998462, 0.994257, 0.985062, 0.973167, 0.959797]
    lam = hazard_from_spread(558.92, t, dfs)
    check("hazard @558.92bp (%)", 100 * lam, 9.322, 0.002)
    rpv01, cont = _legs(lam, t, dfs, 0.40)
    check("contingent leg", cont, 21.995, 0.002)
    check("upfront @500 coupon", upfront(558.92, 500, t, dfs), 2.319, 0.002)
    check("hazard @450bp (%)", 100 * hazard_from_spread(450, t, dfs), 7.504, 0.002)
    check("upfront @450bp", upfront(450, 500, t, dfs), -2.051, 0.002)
    check("spread from upfront 2.319", spread_from_upfront(2.319, 500, t, dfs), 558.92, 0.1)
    check("spread from upfront -2.051", spread_from_upfront(-2.051, 500, t, dfs), 450.0, 0.1)
    check("5% bond price @9.322%", bond_price_from_hazard(0.09322, 5.0, t, dfs), 94.561, 0.003)
    check("CDS-equivalent spread of 94.561", cds_equivalent_spread(94.561, 5.0, t, dfs), 558.92, 0.3)
    # Huggins & Schaller (2024) p.396: 10Y JGB, 6M ASW -1, 3M/6M ICBS 12, CCBS -64.5, CF 0.95 -> ~79bp
    check("JGB USD ASW", usd_asw(-1.0, -64.5, 0.95, icbs_bp=12.0), 79.47, 0.01)
    check("adjusted CDS cash", adjusted_cds(100, "cash"), 45.0, 1e-9)
    check("adjusted CDS physical", adjusted_cds(100, "physical"), 39.0, 1e-9)
    check("implied FX move", implied_fx_move_on_default(100, 45), 0.55, 1e-9)
    check("JTD notional at par", jtd_neutral_notional(100, 100), 100.0, 1e-9)
    check("JTD notional at 80", jtd_neutral_notional(100, 80), 66.6667, 1e-3)
    # screen: one bond whose USD ASW exceeds the CDS ask on the last day only
    dates = pd.bdate_range("2026-01-01", periods=60)
    panel = pd.DataFrame({"date": dates, "instrument_id": "X", "cds_bp": 30.0, "cds_ask_bp": 32.0,
                          "usd_asw_bp": 20.0 + np.sin(np.arange(60))})
    panel.loc[59, "usd_asw_bp"] = 40.0
    s = basis_screen(panel, lookback=40)
    flags = bool(s["violation"].iloc[-1]) and not s["violation"].iloc[:-1].any() and s["basis_z"].iloc[-1] < -2
    ok &= flags
    print(f"{'PASS' if flags else 'FAIL'} screen flags only the violation day, z < -2")
    check("slack on violation day", s["slack_bp"].iloc[-1], 8.0, 1e-9)
    # panel join: 3.5y bond, CDS 2Y 20 / 5Y 50 -> 35bp; proceeds row ignored; swap_minus_govt flipped
    cds = pd.DataFrame({"date": "2026-01-02", "entity": "IT", "tenor": ["2Y", "5Y"], "par_spread_bp": [20.0, 50.0]})
    asw = pd.DataFrame({"date": "2026-01-02", "curve_id": "USD-SOFR", "measure": ["asw_parpar", "asw_proceeds"],
                        "ref": "B1", "value_bp": [-25.0, 99.0], "sign_convention": "swap_minus_govt"})
    bonds = pd.DataFrame({"instrument_id": ["B1"], "issuer": ["IT"], "maturity_date": ["2029-07-02"]})
    pj = build_panel(cds, asw, bonds)
    check("panel CDS interpolated", pj["cds_bp"].iloc[0], 20.0 + 10.0 * (pj["mat_y"].iloc[0] - 2.0), 1e-9)
    check("panel CDS near 35bp", pj["cds_bp"].iloc[0], 35.0, 0.05)
    check("panel USD ASW sign-flipped, parpar only", pj["usd_asw_bp"].iloc[0] + 100 * (len(pj) - 1), 25.0, 1e-9)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cds")
    ap.add_argument("--asw")
    ap.add_argument("--bonds")
    ap.add_argument("--usd-curve", default="USD-SOFR")
    ap.add_argument("--measure", default="asw_parpar", help="swap_spreads measure (asw_parpar or asw_proceeds)")
    ap.add_argument("--cost-bp", type=float, default=0.0, help="round-trip cost + haircut/capital hurdle in bp")
    ap.add_argument("--lookback", type=int, default=126)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if _selftest() else 1)
    if not (a.cds and a.asw and a.bonds):
        ap.error("--cds, --asw and --bonds are required (or --selftest)")
    panel = build_panel(_read(a.cds), _read(a.asw), _read(a.bonds), a.usd_curve, a.measure)
    if panel.empty:
        sys.exit("no bond/CDS matches: check issuer codes, dates and curve_id")
    res = basis_screen(panel, a.lookback, a.cost_bp)
    last = res[res["date"].astype(str) == res["date"].astype(str).max()].sort_values("slack_bp", ascending=False)
    if a.out:
        res.to_csv(a.out, index=False)
    print(last.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
