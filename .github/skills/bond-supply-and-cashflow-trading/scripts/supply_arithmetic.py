"""Supply and cash-flow arithmetic for government-bond supply trades (pure functions, no data access).

Conventions: amounts in one currency unit per call (e.g. bn), rates in bp, yields in percent (bond-equivalent).
  ncr(...)                    Net cash requirement = gross - redemptions - free-float coupons - net CB holdings change
  net_coupon_and_bills(...)   US-style waterfall: net coupon supply, net bill supply = borrowing need - net coupon
  soma_addons(...)            Fed-style rollover cap: redeemed vs reinvested (add-on) amounts, split by date and tenor
  single_price_award(...)     Uniform-price auction fill: lowest yield first, everyone at the stop-out yield
  free_float_after_purchase() Free float by asset after a pro-rata central-bank purchase with captive holders
  dv01_supply(...)            Supply in DV01 (currency per bp) = notional x modified duration x 1e-4
  realized_yield(...)         Horizon yield (bond-equivalent) of a bond held to maturity at a coupon reinvestment rate
  hedge_beta / curve_adjusted_spread  (ASW_country - ASW_DE) - beta x weighted EA maturity-matched spread to Germany
  auction_strength(...)       Mean z-score of (-tail, bid-to-cover, ...) vs the previous N auctions of the same tenor

CLI:
    python supply_arithmetic.py strength --auctions auctions.csv --issuer US --instruments BOND:X,BOND:Y [--lookback 12]
    python supply_arithmetic.py --selftest
`strength` reads the canonical `auctions` table (tail_bp, bid_to_cover; any extra --cols are added, higher = stronger).
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
import pandas as pd


def ncr(gross, redemptions, free_float_coupons, cb_net_change=0.0):
    """Net cash requirement. cb_net_change > 0 = central bank net buyer (absorbs supply); < 0 = QT (adds to NCR)."""
    return gross - redemptions - free_float_coupons - cb_net_change


def net_coupon_and_bills(borrowing_need, gross_coupons, coupons_maturing, fed_rollover=0.0, buybacks=0.0):
    """Net coupon to public = gross - (maturing - Fed rollover) - buybacks; net bills = need - net coupon."""
    net_coupon = gross_coupons - (coupons_maturing - fed_rollover) - buybacks
    return {"net_coupon": net_coupon, "net_bills": borrowing_need - net_coupon}


def soma_addons(coupon_mid, coupon_end, bills, cap, offered_mid, offered_end):
    """Rollover-cap mechanics. coupon_mid/end: coupon maturities mid/end month; bills: bill maturities; cap: runoff cap.
    offered_mid/end: dict tenor -> offering size on that date. Returns redeemed/reinvested amounts and tenor add-ons."""
    coupons = coupon_mid + coupon_end
    red_coupon = min(coupons, cap)
    reinvest_coupon = coupons - red_coupon
    red_bills = min(bills, max(cap - coupons, 0.0))
    reinvest_bills = bills - red_bills
    mid_share = coupon_mid / coupons if coupons else 0.0
    add = {}
    for share, off, side in ((mid_share, offered_mid, "mid"), (1 - mid_share, offered_end, "end")):
        tot = sum(off.values())
        for k, v in off.items():
            add[(side, k)] = reinvest_coupon * share * v / tot if tot else 0.0
    return {"redeemed_coupons": red_coupon, "reinvested_coupons": reinvest_coupon, "redeemed_bills": red_bills,
            "reinvested_bills": reinvest_bills, "add_ons": add}


def single_price_award(bids, offering):
    """bids: list of (yield, amount). Returns (stop_yield, fills) with fills[i] aligned to bids; bids at the stop are
    prorated. Raises if bids do not cover the offering."""
    order = sorted(range(len(bids)), key=lambda i: bids[i][0])
    left, fills, stop = offering, [0.0] * len(bids), None
    for y in sorted({b[0] for b in bids}):
        grp = [i for i in order if bids[i][0] == y]
        amt = sum(bids[i][1] for i in grp)
        if amt <= 0:
            continue
        take = min(amt, left)
        for i in grp:
            fills[i] = bids[i][1] * take / amt
        left -= take
        stop = y
        if left <= 1e-12:
            return stop, fills
    raise ValueError("bids do not cover the offering")


def free_float_after_purchase(weights, captive_share, purchase_share):
    """weights: asset -> share of total market (sums to 1); captive_share: asset -> share of that asset held by
    constrained holders; purchase_share: share of the whole market bought pro rata (each asset loses the same
    fraction of its OWN size). Returns asset -> free float as a share of total market, before and after
    (an 'after' below 0 means the purchase exceeds the free float: infeasible without the captive holders selling)."""
    out = {}
    for a, w in weights.items():
        before = w * (1 - captive_share.get(a, 0.0))
        after = before - w * purchase_share  # the central bank buys from the free float
        out[a] = (before, after)
    return out


def dv01_supply(notional, mod_duration):
    """Currency per bp for a notional (currency) with modified duration (years)."""
    return notional * mod_duration * 1e-4


def realized_yield(price, coupon_pct, years, reinvest_pct, freq=2):
    """Bond-equivalent horizon yield (%) buying at `price` (per 100, on a coupon date, so price = dirty) and holding to
    maturity, coupons reinvested at reinvest_pct (compounded freq times a year)."""
    n = int(round(years * freq))
    c, r = coupon_pct / freq, reinvest_pct / 100.0 / freq
    fv_c = c * n if r == 0 else c * ((1 + r) ** n - 1) / r
    return freq * ((100.0 + fv_c) / price) ** (1.0 / n) * 100.0 - freq * 100.0


def hedge_beta(bond_spread_mm_bp, ea_mm_spread_bp):
    """Ratio (not a regression beta): the bond's own spread to the maturity-matched German par yield divided by the
    weighted euro-area maturity-matched spread to Germany. Fix it at entry."""
    return bond_spread_mm_bp / ea_mm_spread_bp


def curve_adjusted_spread(asw_country_bp, asw_de_bp, ea_mm_spread_bp, beta):
    """Level of the curve-adjusted spread vs Germany: (ASW_country - ASW_DE) - beta x EA_mm_spread. Trade P&L is the
    change in this level between entry and exit, with beta held at its entry value."""
    return (asw_country_bp - asw_de_bp) - beta * ea_mm_spread_bp


def auction_strength(df: pd.DataFrame, cols=("tail_bp", "bid_to_cover"), lookback=12, n_last=2):
    """df sorted by auction_date for ONE tenor. Each column is z-scored vs its previous `lookback` observations
    (point in time, current obs excluded); tail_bp is sign-flipped (through = strong). Returns the per-auction mean
    z-score and the rolling mean over the last n_last auctions."""
    z = {}
    for c in cols:
        x = df[c].astype(float) * (-1.0 if c == "tail_bp" else 1.0)
        mu = x.shift(1).rolling(lookback, min_periods=max(4, lookback // 2)).mean()
        sd = x.shift(1).rolling(lookback, min_periods=max(4, lookback // 2)).std(ddof=1)
        z[c] = (x - mu) / sd.where(sd > 0)  # constant history: no z-score rather than inf
    out = pd.DataFrame(z, index=df.index)
    out["strength"] = out.mean(axis=1)
    out["strength_last_n"] = out["strength"].rolling(n_last).mean()
    return out


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    fails = []

    def chk(name, got, want, tol=1e-9):
        if not (abs(got - want) <= tol):
            fails.append(f"{name}: got {got!r}, want {want!r}")

    # US waterfall (BofA, WAM note, Jul 2025): FY26 need 2100, net coupon 1275 -> net bills 825; FY27 1067; FY25 314
    for need, nc, nb in ((2100, 1275, 825), (2100, 1033, 1067), (1819, 1505, 314)):
        r = net_coupon_and_bills(need, nc, 0.0)
        chk(f"net bills need={need}", r["net_bills"], nb)
    r = net_coupon_and_bills(100, 60, 40, fed_rollover=10, buybacks=5)  # 60 - (40-10) - 5 = 25 ; bills 75
    chk("net coupon", r["net_coupon"], 25)
    chk("net bills", r["net_bills"], 75)
    # NCR: QT adds to NCR 1:1 (Citi: EUR329bn without QT vs 619bn with -> ECB net change -290)
    chk("ncr qt", ncr(1500, 997, 177, -290) - ncr(1500, 997, 177, 0), 290)
    # SOMA add-on (BofA auction primer): 80 maturing (60 mid, 20 end), cap 60 -> 20 reinvested, 15 mid, 3y gets 7.5
    s = soma_addons(60, 20, 0, 60, {"3y": 50, "10y": 30, "30y": 20}, {"2y": 1, "5y": 1})
    chk("soma reinvest", s["reinvested_coupons"], 20)
    chk("soma 3y mid", s["add_ons"][("mid", "3y")], 7.5)
    chk("soma end total", sum(v for (k, _), v in s["add_ons"].items() if k == "end"), 5.0)
    s = soma_addons(40, 0, 30, 60, {"3y": 1}, {})  # coupons 40 < cap 60: 20 of bills roll off, 10 reinvested
    chk("soma bills redeemed", s["redeemed_bills"], 20)
    chk("soma bills reinvested", s["reinvested_bills"], 10)
    # Single-price auction (BofA primer): offering 100; 3%x30, 3.5%x50, 4%x20, 4.5%x10 -> stop 4, last bidder 0
    stop, f = single_price_award([(3.0, 30), (3.5, 50), (4.0, 20), (4.5, 10)], 100)
    chk("stop", stop, 4.0)
    chk("fills", sum(abs(a - b) for a, b in zip(f, [30, 50, 20, 0])), 0.0)
    stop, f = single_price_award([(3.0, 30), (4.0, 100)], 80)  # bids at the stop are prorated: 50 of 100
    chk("prorata", f[1], 50.0)
    # Free float (Duering 2021): halves for asset 1 (30% -> 15%), 50% -> 35% for asset 2
    ff = free_float_after_purchase({"a1": 0.5, "a2": 0.5}, {"a1": 0.4}, 0.30)
    chk("ff a1 before", ff["a1"][0], 0.30)
    chk("ff a1 after", ff["a1"][1], 0.15)
    chk("ff a2 after", ff["a2"][1], 0.35)
    chk("dv01", dv01_supply(10e9, 8.0), 8e6)
    # Realized yield (Tuckman & Serrat, 4th ed.): 2.375% 30y at 100.6875 -> 1.778% @0%, 2.343% @2.343%, 3.207% @5%
    chk("ry 0%", realized_yield(100.6875, 2.375, 30, 0.0), 1.778, 5e-3)
    chk("ry 5%", realized_yield(100.6875, 2.375, 30, 5.0), 3.207, 5e-3)
    chk("ry = ytm", realized_yield(100.6875, 2.375, 30, 2.343), 2.343, 5e-3)
    # Curve-adjusted spread: bond 80bp over Germany m/m, EA average 50bp -> beta 1.6. Entry: ASW_c-ASW_DE = 80, EA 50 ->
    # level 0. Exit with the EA spread +10bp and the bond +16bp (moves exactly with beta): P&L = 0; bond +20bp: 4bp
    beta = hedge_beta(80.0, 50.0)
    chk("beta", beta, 1.6)
    l0 = curve_adjusted_spread(100.0, 20.0, 50.0, beta)
    chk("level0", l0, 0.0)
    chk("pnl beta-neutral", curve_adjusted_spread(116.0, 20.0, 60.0, beta) - l0, 0.0)
    chk("pnl idio", curve_adjusted_spread(120.0, 20.0, 60.0, beta) - l0, 4.0)
    # Strength: tail series [0]*12 with sd -> constant series gives NaN, so use a known ramp for bid_to_cover
    d = pd.DataFrame({"tail_bp": [1.0, -1.0] * 6 + [-3.0], "bid_to_cover": [2.0, 2.4] * 6 + [2.2]})
    z = auction_strength(d, lookback=12)
    prior = np.array([1.0, -1.0] * 6)
    want_tail = (3.0 - (-prior).mean()) / (-prior).std(ddof=1)  # -tail = +3 vs prior -tail mean 0
    chk("z tail", z["tail_bp"].iloc[-1], want_tail)
    chk("z btc", z["bid_to_cover"].iloc[-1], (2.2 - 2.2) / np.array([2.0, 2.4] * 6).std(ddof=1))
    print("selftest", "FAILED" if fails else "passed")
    for m in fails:
        print("  -", m)
    return 1 if fails else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", choices=["strength"])
    ap.add_argument("--auctions")
    ap.add_argument("--issuer")
    ap.add_argument("--instruments", help="comma-separated instrument_ids of ONE tenor (same line family)")
    ap.add_argument("--cols", default="tail_bp,bid_to_cover")
    ap.add_argument("--lookback", type=int, default=12)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.cmd != "strength" or not a.auctions:
        ap.error("use: strength --auctions <file> [--issuer ..] [--instruments ..]")
    df = pd.read_parquet(a.auctions) if a.auctions.lower().endswith((".parquet", ".pq")) else pd.read_csv(a.auctions)
    if a.issuer:
        df = df[df["issuer"] == a.issuer]
    if a.instruments:
        df = df[df["instrument_id"].isin(a.instruments.split(","))]
    df = df.dropna(subset=a.cols.split(",")).sort_values("auction_date").reset_index(drop=True)
    z = auction_strength(df, tuple(a.cols.split(",")), a.lookback)
    z.insert(0, "auction_date", df["auction_date"].astype(str))
    print(json.dumps(json.loads(z.tail(8).to_json(orient="records")), indent=1))


if __name__ == "__main__":
    main()
