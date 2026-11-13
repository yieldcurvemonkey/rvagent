"""Bill yield conversions, bill-OIS spread, financing identity and TGA-gap timing.

Conventions (state them wherever you quote a number):
  * Discount rate, price and simple yields are in percent unless named _px (price per 100).
  * bill_ois_bp = (bill money-market simple yield - matched-tenor OIS) * 100.
    Positive = bill yields above OIS = bill cheap. Some sources print OIS - bill; flip before comparing.
  * basis = day-count denominator of the money-market quote (360 for USD bills and SOFR; check the
    index's day count before using 365).

Usage:
    python -I scripts/bill_yields.py --selftest
    python -I scripts/bill_yields.py bills.csv [--basis 360] [--out out.csv]
    bills.csv columns: date, settle_date, maturity_date, price_px, [ois_pct]
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

# Business days to close a share of the TGA gap after a debt-limit resolution (2013-2023 episodes,
# average across episodes). Knots: (share closed, business days); the (0, 0) knot is added so that a zero share
# returns zero days. Source: BofA, Short July SOFR/FF (30 Jun 2025).
TGA_KNOTS = np.array([
    [0.0, 0], [0.05, 3], [0.10, 5], [0.20, 10], [0.30, 13], [0.40, 21], [0.50, 28],
    [0.60, 30], [0.70, 31], [0.80, 34], [0.90, 43], [1.00, 51],
], dtype=float)


def discount_to_price(disc_pct, days, basis=360):
    """Price per 100 of a discount-rate bill: P = 100 * (1 - d * t / basis)."""
    return 100.0 * (1.0 - np.asarray(disc_pct, float) / 100.0 * np.asarray(days, float) / basis)


def price_to_simple(price_px, days, basis=360):
    """Money-market simple yield in percent: r = (100 / P - 1) * basis / t."""
    p, t = np.asarray(price_px, float), np.asarray(days, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        # non-positive price or day count (matured or bad row) gives NaN, not inf
        return np.where((p > 0) & (t > 0), (100.0 / p - 1.0) * basis / t * 100.0, np.nan)


def discount_to_simple(disc_pct, days, basis=360):
    """Simple yield from a discount rate: r = d / (1 - d * t / basis)."""
    d = np.asarray(disc_pct, float)
    return d / (1.0 - d / 100.0 * np.asarray(days, float) / basis)


def price_to_act365(price_px, days):
    """Actual/365 simple yield in percent (a bond-equivalent style quote), r = (100/P - 1) * 365 / t."""
    return price_to_simple(price_px, days, basis=365)


def bill_ois_bp(bill_simple_pct, ois_pct):
    """Bill minus matched-tenor OIS, in bp. Positive = bill cheap."""
    return (np.asarray(bill_simple_pct, float) - np.asarray(ois_pct, float)) * 100.0


def net_bill_supply(borrowing_need_bn, net_coupon_supply_bn):
    """Net bill supply = marketable borrowing need - net coupon supply (same units, $bn)."""
    return np.asarray(borrowing_need_bn, float) - np.asarray(net_coupon_supply_bn, float)


def business_days_to_close(share):
    """Expected business days after a debt-limit resolution to close `share` (0..1) of the TGA gap."""
    share = np.clip(np.asarray(share, float), 0.0, 1.0)
    return np.interp(share, TGA_KNOTS[:, 0], TGA_KNOTS[:, 1])


def _selftest() -> int:
    ok = True

    def check(name, got, want, tol=1e-9):
        nonlocal ok
        good = bool(np.allclose(got, want, rtol=0, atol=tol))
        ok &= good
        print(("PASS " if good else "FAIL ") + name + f": got {float(np.ravel(got)[0]):.6f}, want {want}")

    # Hand-computed: 4.00% discount, 90 days, act/360 -> P = 99.00, simple = 4.0404%.
    check("discount->price", discount_to_price(4.0, 90), 99.0)
    check("price->simple", price_to_simple(99.0, 90), 4.0404040404, tol=1e-6)
    check("discount->simple", discount_to_simple(4.0, 90), 4.0404040404, tol=1e-6)
    # Identity: simple from discount must equal simple from the implied price (round trip).
    check("round-trip discount/price", discount_to_simple(4.5, 91),
          price_to_simple(discount_to_price(4.5, 91), 91), tol=1e-9)
    # ACT/365 version of the same bill: 99.00 at 90 days -> 4.0404 * 365/360 = 4.0960%.
    check("act365 from price", price_to_act365(99.0, 90), 4.0404040404 * 365 / 360, tol=1e-6)
    # Bill-OIS: bill 4.60, OIS 4.50 -> +10 bp (positive = bill cheap).
    check("bill_ois_bp sign", bill_ois_bp(4.60, 4.50), 10.0, tol=1e-9)
    # Financing identity, BofA FY25/26/27 waterfall ($bn): need - coupons = net bills.
    check("net bills FY25", net_bill_supply(1819, 1505), 314)
    check("net bills FY26", net_bill_supply(2100, 1275), 825)
    check("net bills FY27", net_bill_supply(2100, 1033), 1067)
    # 6m bill: 4.00% discount, 182 days -> 4.0826% simple (the SKILL.md example).
    check("discount->simple 182d", discount_to_simple(4.0, 182), 4.0 / (1 - 0.04 * 182 / 360), tol=1e-9)
    check("discount->simple 182d value", discount_to_simple(4.0, 182), 4.0826, tol=5e-5)
    # Edge: matured bill (0 days) and NaN price must give NaN, not inf or a number.
    bad = price_to_simple(np.array([99.0, np.nan, 99.0]), np.array([0, 90, -5]))
    good = bool(np.all(np.isnan(bad)))
    ok &= good
    print(("PASS " if good else "FAIL ") + "NaN on zero/negative days or NaN price")
    # TGA timing: table knots return exactly, and the curve is monotone.
    check("TGA 50% closed", business_days_to_close(0.50), 28)
    check("TGA 20% closed", business_days_to_close(0.20), 10)
    check("TGA 100% closed", business_days_to_close(1.00), 51)
    check("TGA 0% closed", business_days_to_close(0.0), 0)
    grid = business_days_to_close(np.linspace(0, 1, 201))
    mono = bool(np.all(np.diff(grid) >= 0))
    ok &= mono
    print(("PASS " if mono else "FAIL ") + "TGA days monotone in share")

    print("SELFTEST " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def _cli(argv) -> int:
    ap = argparse.ArgumentParser(description="Bill simple/ACT365 yields and bill-OIS spread from a CSV.")
    ap.add_argument("csv", nargs="?", help="CSV with date, settle_date, maturity_date, price_px, [ois_pct]")
    ap.add_argument("--basis", type=float, default=360.0, help="money-market day-count denominator (default 360)")
    ap.add_argument("--out", help="write output CSV here instead of stdout")
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.csv:
        ap.error("csv path required (or --selftest)")

    df = pd.read_csv(a.csv, parse_dates=["date", "settle_date", "maturity_date"])
    days = (df["maturity_date"] - df["settle_date"]).dt.days.to_numpy()
    out = pd.DataFrame({"date": df["date"].dt.date, "maturity_date": df["maturity_date"].dt.date, "days": days})
    out["simple_pct"] = price_to_simple(df["price_px"].to_numpy(), days, a.basis)
    out["act365_pct"] = price_to_act365(df["price_px"].to_numpy(), days)
    if "ois_pct" in df.columns:
        out["bill_ois_bp"] = bill_ois_bp(out["simple_pct"].to_numpy(), df["ois_pct"].to_numpy())
    text = out.to_csv(index=False, float_format="%.6f")
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
