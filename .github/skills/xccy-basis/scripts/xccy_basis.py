"""Cross-currency basis helpers: FX-implied basis (<= 1Y), forward from basis, USD ASW, hedged yield, roll.

Conventions (same as SKILL.md)
  basis_bp  = spread added to the NON-USD leg (leg_a) against USD flat; negative = USD premium ("wide").
  Prices    = USD per 1 unit of the non-USD currency. USDxxx pairs (USDJPY = JPY per USD) are inverted.
  Rates     = percent per annum, SIMPLE over the FX window (<= 1Y, one period), each in its own day count.
  parity    F/S = (1 + r_usd*d/dc_usd) / (1 + (r_ccy + basis)*d/dc_ccy),  d = days from spot to forward value date.
  USD ASW   = (ASW_foreign - CCBS) / CF,  CF = BPV_usd / BPV_foreign (all spreads in bp, same sign convention).
  Hedged    = asset yield + (F/S - 1) * dc/d * 100 in the investor's home currency (F, S = home per asset).

Usage
  python xccy_basis.py --fx fx_rates.csv --par curve_par.csv --pair EURUSD --usd-curve USD-SOFR
         --ccy-curve EUR-ESTR --tenors 1M,3M,6M,1Y [--date 2026-11-10] [--snap eod_ldn] [--out implied.csv]
  python xccy_basis.py --selftest
Inputs (canonical tables): `fx_rates` (date, snap, pair, tenor, value_date, outright_fx; SPOT row required) and
`curve_par` (date, snap, curve_id, start=0D, tenor, par_rate_pct). Valid only where the OIS fixed leg pays once
(tenor <= 1Y; check swap_conventions.fixed_freq == 'T' or the tenor <= payment frequency).
AUD and NZD quote against term bank bills, not OIS: an OIS-implied figure will not match the quoted basis.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

# ponytail: day counts hard-coded; the authority is rate_indices.day_count (verify NOK, which has ON ACT/365).
DC = {"USD": 360, "EUR": 360, "CHF": 360, "SEK": 360, "GBP": 365, "JPY": 365, "CAD": 365,
      "AUD": 365, "NZD": 365, "NOK": 365}


def fwd_from_basis(spot, r_usd, r_ccy, basis_bp, days, dc_usd=360, dc_ccy=360):
    """Outright forward (USD per ccy) from spot, simple rates (pct) and basis (bp on the ccy leg)."""
    num = 1.0 + np.asarray(r_usd, float) / 100.0 * days / dc_usd
    den = 1.0 + (np.asarray(r_ccy, float) + np.asarray(basis_bp, float) / 100.0) / 100.0 * days / dc_ccy
    return np.asarray(spot, float) * num / den


def implied_basis_bp(spot, fwd, r_usd, r_ccy, days, dc_usd=360, dc_ccy=360):
    """Inverse of fwd_from_basis: the FX-implied ccy rate minus the ccy OIS rate, in bp (negative = USD premium)."""
    x = (1.0 + np.asarray(r_usd, float) / 100.0 * days / dc_usd) * np.asarray(spot, float) / np.asarray(fwd, float)
    implied_pct = (x - 1.0) * dc_ccy / days * 100.0
    return (implied_pct - np.asarray(r_ccy, float)) * 100.0


def to_usd_per_ccy(pair, x):
    """Return (ccy, quote in USD per ccy). EURUSD stays; USDJPY is inverted (JPY per USD -> USD per JPY)."""
    base, quote = pair[:3], pair[3:]
    if quote == "USD":
        return base, np.asarray(x, float)
    if base == "USD":
        return quote, 1.0 / np.asarray(x, float)
    raise ValueError(f"{pair} is not a USD cross")


def usd_asw_bp(asw_foreign_bp, ccbs_bp, cf=1.0):
    """USD ASW of a foreign bond asset-swapped and basis-swapped into USD: (ASW - CCBS) / CF."""
    return (np.asarray(asw_foreign_bp, float) - np.asarray(ccbs_bp, float)) / cf


def hedged_yield_pct(asset_yield_pct, spot_home_per_asset, fwd_home_per_asset, days, dc_home=360):
    """Asset yield plus annualised forward-points carry of selling the asset currency forward (home terms)."""
    carry = (np.asarray(fwd_home_per_asset, float) / np.asarray(spot_home_per_asset, float) - 1.0) * dc_home / days
    return np.asarray(asset_yield_pct, float) + carry * 100.0


def roll_pay_bp(tenors_y, basis_bp, T, h=0.25):
    """Roll-down of PAYING a tenor-T basis over h years: b(T-h) - b(T) on the linearly interpolated curve.
    NaN if T-h or T lies outside the curve nodes (np.interp would silently clamp and report a zero roll)."""
    x = np.asarray(tenors_y, float)
    if not (x[0] <= T - h and T <= x[-1]) or np.any(np.diff(x) <= 0):
        return float("nan")
    return float(np.interp(T - h, x, basis_bp) - np.interp(T, x, basis_bp))


def implied_table(fx, par, pair, usd_curve, ccy_curve, tenors, dc=DC):
    """FX-implied basis (bp) by tenor from one date/snap of fx_rates and curve_par (start 0D). Tenors <= 1Y only."""
    ccy, _ = to_usd_per_ccy(pair, 1.0)
    fx = fx[fx["pair"] == pair].set_index("tenor")
    if fx.index.has_duplicates:
        raise ValueError("duplicate tenors: filter fx_rates to one date and snap first")
    need = ["SPOT", *tenors]
    if any(t not in fx.index for t in need) or fx.loc[need, "value_date"].isna().any():
        raise ValueError("fx_rates needs a SPOT row plus every requested tenor, each with a value_date")
    s = float(to_usd_per_ccy(pair, fx.loc["SPOT", "outright_fx"])[1])
    spot_vd = pd.Timestamp(fx.loc["SPOT", "value_date"])
    par = par[par["start"] == "0D"].set_index(["curve_id", "tenor"])["par_rate_pct"]
    if par.index.has_duplicates:
        raise ValueError("duplicate curve_par rows: filter to one date and snap first")
    rows = []
    for t in tenors:
        d = (pd.Timestamp(fx.loc[t, "value_date"]) - spot_vd).days
        if d <= 0 or d > 372:
            raise ValueError(f"{t}: {d} days; the single-period formula is valid to 1Y only")
        f = float(to_usd_per_ccy(pair, fx.loc[t, "outright_fx"])[1])
        b = implied_basis_bp(s, f, par[(usd_curve, t)], par[(ccy_curve, t)], d, dc["USD"], dc[ccy])
        rows.append({"pair": pair, "tenor": t, "days": d, "implied_basis_bp": float(b)})
    return pd.DataFrame(rows)


def _read(p):
    return pd.read_parquet(p) if str(p).endswith(".parquet") else pd.read_csv(p)


# ---------------------------------------------------------------------------------------------- selftest
def selftest():
    # Published anchors only (a round trip alone would pass with a shared day-count or sign error).
    # (1) Aikin, STIR Futures 2e, EUR/USD 23 Jan 2012: S 1.2960, 92d, EUR 1.12, USD 0.56.
    f0 = float(fwd_from_basis(1.2960, 0.56, 1.12, 0.0, 92))
    assert abs((f0 - 1.2960) * 1e4 - (-18.49)) < 0.02, f0            # -18.49 pips theoretical
    f75 = float(fwd_from_basis(1.2960, 0.56, 1.12, -75.0, 92))
    assert abs(f75 - 1.2966) < 0.00005, f75                          # +6 pips with -75bp basis
    assert abs(float(implied_basis_bp(1.2960, f75, 0.56, 1.12, 92)) + 75.0) < 1e-6
    assert abs(float(implied_basis_bp(1.2960, 1.2966, 0.56, 1.12, 92)) + 75.0) < 2.0   # rounded market quote
    # (2) Darbyshire PTIRD Ex 7.1/7.2: O/N, USD 1%, EUR 5%, spot 1.20.
    assert abs(float(fwd_from_basis(1.20, 1.0, 5.0, 0.0, 1)) - 1.19987) < 6e-6
    assert abs(float(fwd_from_basis(1.20, 1.0, 5.0, -100.0, 1)) - 1.19990) < 6e-6
    # (3) Huggins & Schaller FIRVA: 10Y JGB, ASW 11, CCBS -64.5, CF 0.95 -> 79.5bp.
    assert abs(float(usd_asw_bp(11.0, -64.5, 0.95)) - 79.47) < 0.01
    # (4) Hedging a EUR asset from USD: the basis improves hedged yield by ~|basis| (analytic identity).
    h_basis = hedged_yield_pct(0.0, 1.2960, f75, 92); h_flat = hedged_yield_pct(0.0, 1.2960, f0, 92)
    assert abs((h_basis - h_flat) * 100 - 75.0) < 1.0, (h_basis, h_flat)
    # (5) Roll of paying vs the published EUR/USD curve (JPM, 27 Mar 2015, Exhibit 1): carry 1.4 / 0.7 / 0.0.
    ten = [0.25, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]; b = [-24, -25, -28, -32, -35, -36, -38, -38, -39, -39, -38, -38]
    for T, pub in ((0.5, 1.3), (1, 1.4), (2, 0.7), (5, 0.2), (10, 0.0)):
        assert abs(roll_pay_bp(ten, b, T) - pub) < 0.5, (T, roll_pay_bp(ten, b, T))
    assert np.isnan(roll_pay_bp(ten, b, 0.25))                       # no node before 3M: NaN, not a fake zero
    # (6) USDxxx inversion + table path with the Aikin inputs (single-payment OIS par = simple rate).
    assert abs(float(to_usd_per_ccy("USDJPY", 150.0)[1]) - 1 / 150.0) < 1e-12
    fx = pd.DataFrame({"pair": "EURUSD", "tenor": ["SPOT", "3M"], "outright_fx": [1.2960, 1.2966],
                       "value_date": ["2012-01-25", "2012-04-26"]})
    par = pd.DataFrame({"curve_id": ["USD-SOFR", "EUR-ESTR"], "start": "0D", "tenor": "3M", "par_rate_pct": [0.56, 1.12]})
    out = implied_table(fx, par, "EURUSD", "USD-SOFR", "EUR-ESTR", ["3M"])
    assert out.loc[0, "days"] == 92 and abs(out.loc[0, "implied_basis_bp"] + 75.0) < 2.0, out
    # USDJPY orientation: same economics quoted as JPY per USD must give the same basis sign.
    fj = pd.DataFrame({"pair": "USDJPY", "tenor": ["SPOT", "3M"], "outright_fx": [1 / 1.2960, 1 / 1.2966],
                       "value_date": ["2012-01-25", "2012-04-26"]})
    pj = par.assign(curve_id=["USD-SOFR", "JPY-TONA"])
    oj = implied_table(fj, pj, "USDJPY", "USD-SOFR", "JPY-TONA", ["3M"], dc={**DC, "JPY": 360})
    assert abs(oj.loc[0, "implied_basis_bp"] + 75.0) < 2.0, oj
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fx"); ap.add_argument("--par"); ap.add_argument("--pair")
    ap.add_argument("--usd-curve"); ap.add_argument("--ccy-curve")
    ap.add_argument("--tenors", default="1M,3M,6M,1Y"); ap.add_argument("--date"); ap.add_argument("--snap")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not (a.fx and a.par and a.pair and a.usd_curve and a.ccy_curve):
        ap.error("need --fx --par --pair --usd-curve --ccy-curve (or --selftest)")
    fx, par = _read(a.fx), _read(a.par)
    for df in (fx, par):
        df["date"] = pd.to_datetime(df["date"])
    d = pd.Timestamp(a.date) if a.date else min(fx["date"].max(), par["date"].max())
    fx, par = fx[fx["date"] == d], par[par["date"] == d]
    if a.snap:
        fx, par = fx[fx["snap"] == a.snap], par[par["snap"] == a.snap]
    elif fx["snap"].nunique() > 1 or par["snap"].nunique() > 1:
        sys.exit("several snaps present; pass --snap (never mix snaps)")
    out = implied_table(fx, par, a.pair, a.usd_curve, a.ccy_curve, a.tenors.split(","))
    out.insert(0, "date", d.date())
    (out.to_csv(a.out, index=False) if a.out else print(out.to_string(index=False)))


if __name__ == "__main__":
    main()
