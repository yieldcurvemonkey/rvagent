#!/usr/bin/env python3
"""Reserve-ampleness monitor for G10 money-market plumbing.

Functions take pandas / numpy objects. Units: rates in percent, spreads in bp, balances in $bn (or the
same currency unit throughout). Conventions: EFFR-IORB = EFFR minus IORB; SOFR-FF = SOFR minus EFFR;
positive TGCR-RRP = excess collateral. See SKILL.md "Conventions".

CLI: python -I scripts/reserve_monitor.py --wide PATH   (prints the latest gauges)
     python -I scripts/reserve_monitor.py --selftest    (known-answer checks; exit 1 on failure)

Wide CSV columns (the adapter builds these from canonical tables; see SKILL.md Inputs):
  date, effr_pct, iorb_pct, sofr_pct, tgcr_pct, on_rrp_rate_pct,
  optional: gcf_pct, tpr_pct, reserves_bn, on_rrp_bn, bank_assets_bn
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

BP = 100.0  # 1 percentage point = 100 bp


def reserves_from_identity(total_assets, currency, tga, on_rrp, foreign_rrp=0.0, other_liabs=0.0):
    """Reserves = Fed assets - currency - TGA - ON RRP - foreign RRP - other liabilities and capital."""
    return total_assets - currency - tga - on_rrp - foreign_rrp - other_liabs


def ampleness_ratio(reserves, on_rrp, bank_assets):
    """Liquidity ratio = (reserves + ON RRP) / bank assets (the RRP-inclusive 'Fed liquidity' variant)."""
    return (reserves + on_rrp) / bank_assets


def ampleness_zone(ratio, abundant=0.13, scarce=0.11):
    """'abundant' above `abundant`, 'scarce' below `scarce`, else 'ample'; 'n/a' for NaN (missing data is never 'ample').
    Thresholds are soft; see SKILL.md."""
    if np.isscalar(ratio):
        if np.isnan(ratio):
            return "n/a"
        return "abundant" if ratio > abundant else ("scarce" if ratio < scarce else "ample")
    r = pd.Series(ratio)
    labels = np.select([r.isna(), r > abundant, r < scarce], ["n/a", "abundant", "scarce"], default="ample")
    return pd.Series(labels, index=r.index)


def spread_gauges(df):
    """Money-market spread gauges in bp from a wide frame of percent rates (see module docstring)."""
    out = pd.DataFrame(index=df.index)
    out["effr_minus_iorb_bp"] = (df["effr_pct"] - df["iorb_pct"]) * BP
    out["sofr_minus_iorb_bp"] = (df["sofr_pct"] - df["iorb_pct"]) * BP
    out["sofr_minus_effr_bp"] = (df["sofr_pct"] - df["effr_pct"]) * BP
    out["tgcr_minus_rrp_bp"] = (df["tgcr_pct"] - df["on_rrp_rate_pct"]) * BP
    if {"gcf_pct", "tpr_pct"} <= set(df.columns):
        out["gcf_minus_tpr_bp"] = (df["gcf_pct"] - df["tpr_pct"]) * BP
    x = out["effr_minus_iorb_bp"]
    # EFFR above IORB = scarce on the historical basis; <NA> (not False) when either rate is missing
    out["scarcity_warning"] = (x > 0).astype("boolean").where(x.notna())
    return out


def rrp_change_from_net_bills(net_bill_bn, beta=0.52):
    """Expected change in ON RRP ($bn) for net new bill supply ($bn). Slope -0.52 from BofA Funding Notes
    (Aug 2025, since Aug 2023); Citi's 80% beta is the alternative. Bills absorb MMF cash, so the sign is negative."""
    return -beta * net_bill_bn


def fit_log_liquidity(x, y):
    """Least-squares fit y = a*ln(x) + b. Returns (a, b, r2)."""
    x = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & (x > 0) & np.isfinite(yy)  # drop NaN and non-positive x (log undefined)
    if ok.sum() < 3:
        raise ValueError("fit_log_liquidity needs at least 3 valid (x > 0) points")
    lx, yy = np.log(x[ok]), yy[ok]
    a, b = np.polyfit(lx, yy, 1)
    resid = yy - (a * lx + b)
    sst = float(np.sum((yy - yy.mean()) ** 2))
    r2 = 1.0 - float(np.sum(resid ** 2)) / sst if sst > 0 else float("nan")
    return float(a), float(b), r2


def year_end_premium(ff_nov, ff_dec, ff_jan, ff_feb, dec_old=11, jan_old=29, dec_days=31, jan_days=31):
    """Split four month-average FF readings into the Dec FOMC step, the Jan FOMC step and the year-end premium.
    Inputs in percent. Returns (d_dec, d_jan, ye) in percent. Model from Citi, Fixing the plumbing (30 Sep 2019):
    FF_Dec = (dec_old/dec_days) FF_Nov + (1 - dec_old/dec_days) (FF_Nov + dDec + YE);
    FF_Jan = (jan_old/jan_days) (FF_Nov + dDec) + (1 - jan_old/jan_days) (FF_Nov + dDec + dJan); FF_Feb = FF_Nov + dDec + dJan.
    The premium is spread over every post-FOMC day of December (Citi's definition). dec_old / jan_old = days in the month
    at the OLD rate (rate changes effective the day after the meeting). Defaults (11, 29) are the Dec 2019 / Jan 2020
    calendar, giving the published 31/29, 2/29, 31/20, 11/20 weights. Set them to the actual FOMC calendar of the year."""
    dec_new = dec_days - dec_old
    jan_new = jan_days - jan_old
    d_jan = (jan_days / jan_old) * (ff_feb - ff_jan)
    a = (jan_days / jan_old) * ff_jan - (jan_new / jan_old) * ff_feb  # FF_Nov + dDec
    d_dec = a - ff_nov
    ye = (dec_days * ff_dec - dec_old * ff_nov) / dec_new - a
    return d_dec, d_jan, ye


def selftest():
    fails = []

    def check(name, got, want, tol=1e-6):
        if not np.allclose(np.asarray(got, dtype=float), np.asarray(want, dtype=float), atol=tol, rtol=0):
            fails.append(f"{name}: got {got}, want {want}")

    # Identity with the Jun 2025 BofA vintage (assets 6,728; currency 2,390; TGA 277; ON RRP 576; other 55 -> reserves 3,430)
    check("identity_bofa_jun25", reserves_from_identity(6728, 2390, 277, 576, 0, 55), 3430)
    check("identity_toy", reserves_from_identity(100, 20, 10, 5, 5, 0), 60)

    check("ratio_toy", ampleness_ratio(2400, 100, 20000), 0.125)
    if ampleness_zone(0.125) != "ample" or ampleness_zone(0.14) != "abundant" or ampleness_zone(0.10) != "scarce":
        fails.append("ampleness_zone scalar labels wrong")
    zones = ampleness_zone(pd.Series([0.125, 0.14, 0.10])).tolist()
    if zones != ["ample", "abundant", "scarce"]:
        fails.append(f"ampleness_zone series labels wrong: {zones}")

    # Snapshots from Conks, Money Market Update, 6 Oct 2025 (3 Oct 2025 prints) and 26 Oct 2025 (23 Oct 2025 prints)
    snap = pd.DataFrame(
        {
            "effr_pct": [4.09, 4.11],
            "iorb_pct": [4.15, 4.15],
            "sofr_pct": [4.18, 4.24],
            "tgcr_pct": [4.16, 4.21],
            "on_rrp_rate_pct": [4.00, 4.00],
        },
        index=pd.to_datetime(["2025-10-03", "2025-10-23"]),
    )
    g = spread_gauges(snap)
    check("3oct_sofr_iorb", g["sofr_minus_iorb_bp"].iloc[0], 3)
    check("3oct_effr_iorb", g["effr_minus_iorb_bp"].iloc[0], -6)
    check("3oct_sofr_effr", g["sofr_minus_effr_bp"].iloc[0], 9)
    check("3oct_tgcr_rrp", g["tgcr_minus_rrp_bp"].iloc[0], 16)
    check("23oct_sofr_iorb", g["sofr_minus_iorb_bp"].iloc[1], 9)
    check("23oct_effr_iorb", g["effr_minus_iorb_bp"].iloc[1], -4)
    if bool(g["scarcity_warning"].iloc[0]) or bool(g["scarcity_warning"].iloc[1]):
        fails.append("scarcity_warning should be False when EFFR is below IORB")

    check("rrp_drain_100bn_bills", rrp_change_from_net_bills(100.0), -52.0)

    # Known-parameter log fit must recover the parameters exactly
    x = np.array([5.0, 10.0, 20.0, 40.0])
    a, b, r2 = fit_log_liquidity(x, -10.0 * np.log(x) + 20.0)
    check("logfit_a", a, -10.0)
    check("logfit_b", b, 20.0)
    check("logfit_r2", r2, 1.0)

    # Year-end decomposition round trip with known dDec, dJan, YE (percent)
    nov, d_dec0, d_jan0, ye0 = 5.00, -0.25, -0.10, -0.04
    ff_dec = (11 / 31) * nov + (20 / 31) * (nov + d_dec0 + ye0)
    ff_jan = (29 / 31) * (nov + d_dec0) + (2 / 31) * (nov + d_dec0 + d_jan0)
    ff_feb = nov + d_dec0 + d_jan0
    got = year_end_premium(nov, ff_dec, ff_jan, ff_feb)
    check("ye_decomposition", got, [d_dec0, d_jan0, ye0], tol=1e-9)
    # Different FOMC calendar (Dec step effective day 11, Jan step effective day 29): forward model written independently
    ff_dec = (10 / 31) * nov + (21 / 31) * (nov + d_dec0 + ye0)
    ff_jan = (28 / 31) * (nov + d_dec0) + (3 / 31) * (nov + d_dec0 + d_jan0)
    check("ye_decomposition_alt_calendar", year_end_premium(nov, ff_dec, ff_jan, ff_feb, dec_old=10, jan_old=28),
          [d_dec0, d_jan0, ye0], tol=1e-9)

    # Missing data must never read as "ample" or "no warning"
    if ampleness_zone(float("nan")) != "n/a" or ampleness_zone(pd.Series([np.nan, 0.12])).tolist() != ["n/a", "ample"]:
        fails.append("ampleness_zone must return n/a for NaN")
    gn = spread_gauges(pd.DataFrame({"effr_pct": [np.nan], "iorb_pct": [4.15], "sofr_pct": [4.18], "tgcr_pct": [4.16],
                                     "on_rrp_rate_pct": [4.0]}))
    if not pd.isna(gn["scarcity_warning"].iloc[0]):
        fails.append("scarcity_warning must be NA when EFFR is missing")
    try:
        fit_log_liquidity([1.0, 2.0], [1.0, 2.0])
        fails.append("fit_log_liquidity must reject fewer than 3 points")
    except ValueError:
        pass
    check("logfit_drops_nan", fit_log_liquidity([5.0, 10.0, np.nan, 20.0, 40.0], [-10 * np.log(v) + 20 for v in [5.0, 10.0, 7.0, 20.0, 40.0]])[0], -10.0)

    if fails:
        for f in fails:
            print("SELFTEST FAIL", f)
        return 1
    print("selftest OK")
    return 0


def load_wide(path):
    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").sort_index()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reserve-ampleness gauges (see SKILL.md).")
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks")
    ap.add_argument("--wide", help="wide CSV with date and percent-rate columns")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.wide:
        df = load_wide(a.wide)
        g = spread_gauges(df).tail(5)
        num = g.select_dtypes("number").round(1)
        print(num.join(g.drop(columns=num.columns)).to_string())
        if {"reserves_bn", "on_rrp_bn", "bank_assets_bn"} <= set(df.columns):
            r = ampleness_ratio(df["reserves_bn"], df["on_rrp_bn"], df["bank_assets_bn"])
            print(pd.DataFrame({"liquidity_ratio": r, "zone": ampleness_zone(r)}).tail(5).to_string())
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
