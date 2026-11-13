#!/usr/bin/env python3
"""Invoice spread, futures DV01 and CTD-based hedge ratios for physically delivered bond futures.

Conventions (see SKILL.md): rates in percent, spreads in bp, prices per 100 face, DV01 in currency per bp.
invoice spread = forward matched-maturity swap rate - futures-implied forward yield of the CTD   (swap minus govt;
negative for USD when swaps trade below Treasuries). Pricing is "street" compounding with `freq` coupons a year
(2 = UST/gilt/JGB semi-annual; 1 = Bund/OAT annual) and ACT/ACT accrued for the stub period.

    python invoice_spread.py --selftest
    python invoice_spread.py invoice --fut-price 112.5 --cf 0.8123 --coupon-pct 4.25 --maturity 2034-08-15 \
        --delivery 2026-12-31 --swap-fwd-pct 3.95
    python invoice_spread.py basket --csv basket.csv --delivery 2026-12-31 --fut-price 112.5 --nvol-bp 95 --years 0.1
    python invoice_spread.py contracts --swap-notional 100e6 --swap-dv01-per-mm 640 --fut-dv01 63.1
basket.csv columns: instrument_id, coupon_pct, maturity_date, conversion_factor, fwd_yield_pct (forward yield of that
bond on the delivery date, from the user's forward/carry model); optional beta (yield beta to the CTD, default 1).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq


# --------------------------------------------------------------------------- bond maths
def schedule(maturity, settle, freq: int = 2):
    """Return (n, w): coupons remaining after `settle` and fraction w in (0,1] of the current period still to run."""
    maturity, settle = pd.Timestamp(maturity), pd.Timestamp(settle)
    step = 12 // freq
    eom = maturity.is_month_end

    def coupon(k: int) -> pd.Timestamp:  # k-th coupon date counting back from maturity
        d = maturity - pd.DateOffset(months=step * k)
        return d + pd.offsets.MonthEnd(0) if eom else d

    k = 0
    while coupon(k) > settle:
        k += 1
    prev, nxt = coupon(k), coupon(k - 1) if k > 0 else None
    if nxt is None:
        raise ValueError("settle on/after maturity")
    return k, (nxt - settle).days / (nxt - prev).days


def dirty_price(y_pct, coupon_pct, n: int, w: float, freq: int = 2):
    """Dirty price per 100 at yield y_pct (works on arrays of y)."""
    y = np.asarray(y_pct, dtype=float) / 100.0
    v = 1.0 / (1.0 + y / freq)
    c = coupon_pct / freq
    t = w + np.arange(n)
    pv = (c * v[..., None] ** t).sum(-1) + 100.0 * v ** (w + n - 1)
    return pv


def clean_price(y_pct, coupon_pct, n, w, freq=2):
    return dirty_price(y_pct, coupon_pct, n, w, freq) - coupon_pct / freq * (1.0 - w)


def yield_from_clean(clean, coupon_pct, n, w, freq=2):
    return brentq(lambda y: clean_price(y, coupon_pct, n, w, freq) - clean, -20.0, 60.0, xtol=1e-12)


def dv01_per100(y_pct, coupon_pct, n, w, freq=2, h_bp=0.5):
    """Clean-price change per 1bp (positive = long duration), central difference."""
    h = h_bp / 100.0
    return (clean_price(y_pct - h, coupon_pct, n, w, freq) - clean_price(y_pct + h, coupon_pct, n, w, freq)) / (2 * h_bp)


def conversion_factor(coupon_pct, months, notional_pct=6.0, freq=2):
    """Exchange conversion factor: price at the notional yield of 1 unit of par, remaining term `months` (already
    rounded down to the quarter or month as the contract specifies), 4 dp. Priced from the first day of the delivery
    month; w = fraction of a coupon period to the first coupon."""
    per = 12 // freq
    n = -(-months // per)
    w = (months - per * (n - 1)) / per
    return round(float(clean_price(notional_pct, coupon_pct, n, w, freq)) / 100.0, 4)


# --------------------------------------------------------------------------- invoice spread
def futures_implied_yield(fut_price, cf, coupon_pct, maturity, delivery, freq=2):
    """Yield of the CTD at its invoice price (futures x CF, clean) settling on the delivery date."""
    n, w = schedule(maturity, delivery, freq)
    return yield_from_clean(fut_price * cf, coupon_pct, n, w, freq)


def invoice_spread_bp(swap_fwd_pct, fut_implied_yield_pct):
    """Swap minus govt, bp. Cash ASW in EGB markets is the opposite sign (govt minus swap)."""
    return (swap_fwd_pct - fut_implied_yield_pct) * 100.0


def futures_dv01_rot(ctd_fwd_dv01_per_contract, cf):
    """Rule of thumb #1: futures DV01 = CTD forward DV01 / CF."""
    return ctd_fwd_dv01_per_contract / cf


def hedge_contracts(dv01_to_hedge, fut_dv01_per_contract):
    return dv01_to_hedge / fut_dv01_per_contract


def swaption_notional_per_1000(fut_dv01, swap_dv01_per_mm):
    """$mn of swap notional per 1,000 contracts so the swaption DV01 equals the futures-option DV01 (Board).
    Both DV01s must be in the same units per 100 face (e.g. 4.72 / 4.01 -> 117.7). With dollar DV01s use
    1000 * DV01_per_contract / DV01_per_$mm of swap instead."""
    return 100.0 * fut_dv01 / swap_dv01_per_mm


# --------------------------------------------------------------------------- basket: OA DV01 and P-weighted DV01
def _prep(basket: pd.DataFrame, delivery, freq):
    rows = []
    for r in basket.itertuples(index=False):
        n, w = schedule(r.maturity_date, delivery, freq)
        rows.append((n, w))
    b = basket.copy()
    need = ["coupon_pct", "conversion_factor", "fwd_yield_pct"]
    if b[need].isna().any().any():  # NaN would silently win argmin/min and corrupt the CTD tag
        raise ValueError("basket has NaN in " + ", ".join(need))
    b["n"], b["w"] = zip(*rows)
    if "beta" not in b:
        b["beta"] = 1.0
    return b


def converted_prices(b: pd.DataFrame, shift_bp=0.0, freq=2):
    """Forward clean price / CF of every deliverable after a parallel yield shift (betas scale the shift)."""
    return np.array([float(clean_price(r.fwd_yield_pct + r.beta * shift_bp / 100.0, r.coupon_pct, r.n, r.w, freq))
                     / r.conversion_factor for r in b.itertuples(index=False)])


def theoretical_futures(b, shift_bp=0.0, freq=2):
    """Zero-option-value futures price: min over deliverables of forward price / CF (the short picks the cheapest)."""
    return converted_prices(b, shift_bp, freq).min()


def oa_dv01_per100(b, freq=2, h_bp=5.0):
    """Futures DV01 (per 100 face of futures price): central difference of the zero-time-value theoretical futures
    price min_i(fwd_i/CF_i) over +-h_bp parallel shifts. This is the switch payoff only (no time value, wildcard or
    EOM), kinked at cusps and smoothed only by the +-h_bp window: it is not a full option-adjusted DV01."""
    return (theoretical_futures(b, -h_bp, freq) - theoretical_futures(b, h_bp, freq)) / (2 * h_bp)


def ctd_probabilities(b, sigma_bp, freq=2, nodes=201):
    """P(bond is CTD) when the parallel yield move to delivery is N(0, sigma_bp); Gauss-Hermite quadrature.
    The CTD indicator is a step function, so accuracy is ~0.01-0.02 in P at 201 nodes (~0.05 at 61)."""
    x, wt = np.polynomial.hermite_e.hermegauss(nodes)
    wt = wt / wt.sum()
    p = np.zeros(len(b))
    for xi, wi in zip(x, wt):
        p[int(np.argmin(converted_prices(b, sigma_bp * xi, freq)))] += wi
    return p


def p_weighted_dv01_per100(b, sigma_bp, freq=2):
    """JPM-style P-weighted BPV: sum_i P(i is CTD) * DV01_i / CF_i at current forward yields (per 100 face)."""
    p = ctd_probabilities(b, sigma_bp, freq)
    d = np.array([dv01_per100(r.fwd_yield_pct, r.coupon_pct, r.n, r.w, freq) / r.conversion_factor
                  for r in b.itertuples(index=False)])
    return float((p * d).sum()), p, d


# --------------------------------------------------------------------------- self-test
def selftest() -> int:
    bad = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(("ok   " if ok else "FAIL ") + f"{name}: got {got:.6f} want {want:.6f}")
        if not ok:
            bad.append(name)

    # 1. pricer: par bond on a coupon date, and a closed-form 4% 10y bond at 6%
    check("par bond = 100", float(clean_price(5.0, 5.0, 20, 1.0)), 100.0, 1e-9)
    closed = 100 * (0.04 / 0.06 + (1 - 0.04 / 0.06) * 1.03 ** -20)
    check("4% 10y at 6% closed form", float(clean_price(6.0, 4.0, 20, 1.0)), closed, 1e-9)
    # 2. conversion factor: 10.375% bond, term 16 3/4y (201 months) at 8% -> published CF 1.2168 (Salomon, Oct 1990)
    check("CF 10.375% 16.75y @8%", conversion_factor(10.375, 201, 8.0), 1.2168, 5e-5)
    # 3. implied-yield round trip and spread sign
    n, w = schedule("2034-08-15", "2026-12-31")
    p = float(clean_price(4.10, 4.25, n, w))
    check("yield round trip", yield_from_clean(p, 4.25, n, w), 4.10, 1e-9)
    check("invoice spread sign (swap<govt -> negative)", invoice_spread_bp(3.95, 4.20), -25.0, 1e-9)
    f = 110.0
    cf = 0.9000
    fy = futures_implied_yield(f, cf, 4.25, "2034-08-15", "2026-12-31")
    check("futures-implied yield reprices", float(clean_price(fy, 4.25, n, w)), f * cf, 1e-7)
    # 4. hedge arithmetic from the sources
    check("Burghardt futures DV01 59.14/0.9734", futures_dv01_rot(59.14, 0.9734), 60.76, 0.01)
    check("Burghardt hedge ratio 7762.40/60.76", hedge_contracts(7762.40, 60.76), 127.8, 0.05)
    check("Citi FV notional per 1000", swaption_notional_per_1000(4.72, 4.01), 117.7, 0.05)
    check("Citi TY notional per 1000", swaption_notional_per_1000(7.52, 6.25), 120.3, 0.05)
    # 5. OA DV01: single bond equals the rule of thumb; two bonds far from the cusp equal the CTD's rule of thumb
    mk = lambda rows: pd.DataFrame(rows, columns=["coupon_pct", "maturity_date", "conversion_factor", "fwd_yield_pct"])
    one = _prep(mk([(4.25, "2034-08-15", 0.9, 4.2)]), "2026-12-31", 2)
    r = one.iloc[0]
    rot = dv01_per100(r.fwd_yield_pct, r.coupon_pct, r.n, r.w) / r.conversion_factor
    check("OA = RoT, single bond", oa_dv01_per100(one), rot, 2e-4 * rot)
    # CF 0.90 / 0.60 with similar maturities: bond A is CTD by a wide margin (conv. price 3 points lower)
    two = _prep(mk([(4.25, "2034-08-15", 0.9, 4.2), (6.0, "2035-02-15", 0.6, 4.2)]), "2026-12-31", 2)
    conv = converted_prices(two)
    ctd = int(np.argmin(conv))
    rc = two.iloc[ctd]
    rot2 = dv01_per100(rc.fwd_yield_pct, rc.coupon_pct, rc.n, rc.w) / rc.conversion_factor
    check("OA = RoT of CTD far from cusp", oa_dv01_per100(two), rot2, 5e-3 * rot2)
    # 6. P-weighted DV01: tiny vol -> CTD only; weights sum to 1; between the bounds near a cusp
    pw0, p0, d0 = p_weighted_dv01_per100(two, 0.01)
    check("P-weighted, sigma->0 = CTD RoT", pw0, d0[ctd], 1e-9)
    # known answer: two bonds whose converted prices cross at shift s*; P(higher-yield CTD) = 1 - Phi(s*/sigma)
    from scipy.stats import norm
    for dy in (0.05, 0.02):
        b3 = two.copy()
        b3.loc[1, "fwd_yield_pct"] = brentq(lambda y: clean_price(y, 6.0, b3.n[1], b3.w[1]) / 0.6 - conv[ctd], 0.0, 15.0) + dy
        sx = brentq(lambda s: np.diff(converted_prices(b3, s))[0], -100.0, 100.0)
        hi = int(np.argmin(converted_prices(b3, sx + 5.0)))
        _, p3, _ = p_weighted_dv01_per100(b3, 20.0)
        want = 1.0 - norm.cdf(sx / 20.0)
        check(f"P(CTD) vs normal cdf (cross {sx:.1f}bp, sigma 20)", float(p3[hi]), want, 0.02)
    # engineer a cusp: set bond B's forward yield so both convert to the same price, then add vol
    b2 = two.copy()
    target = conv[ctd]
    b2.loc[1, "fwd_yield_pct"] = brentq(lambda y: clean_price(y, 6.0, b2.n[1], b2.w[1]) / 0.6 - target, 0.0, 15.0)
    pw, p, d = p_weighted_dv01_per100(b2, 20.0)
    check("probabilities sum to 1", p.sum(), 1.0, 1e-9)
    if min(p) < 0.05:
        bad.append("cusp probabilities")
        print(f"FAIL cusp: both bonds should have P(CTD) > 0.05, got {p}")
    check("P-weighted within [min,max] of BPV/CF", float(min(max(pw, d.min()), d.max())), pw, 1e-9)
    print("SELFTEST " + ("FAILED: " + ", ".join(bad) if bad else "PASSED"))
    return 1 if bad else 0


# --------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("invoice", help="CTD futures-implied yield and invoice spread vs a forward swap rate")
    a.add_argument("--fut-price", type=float, required=True)
    a.add_argument("--cf", type=float, required=True)
    a.add_argument("--coupon-pct", type=float, required=True)
    a.add_argument("--maturity", required=True)
    a.add_argument("--delivery", required=True, help="delivery (swap effective) date")
    a.add_argument("--swap-fwd-pct", type=float, required=True, help="par rate of the delivery-start, CTD-maturity swap")
    a.add_argument("--freq", type=int, default=2)
    b = sub.add_parser("basket", help="CTD, OA DV01 and P-weighted DV01 from a joined basket CSV/Parquet")
    b.add_argument("--csv", required=True)
    b.add_argument("--delivery", required=True)
    b.add_argument("--fut-price", type=float)
    b.add_argument("--nvol-bp", type=float, default=90.0, help="normal vol of yields, bp per year")
    b.add_argument("--years", type=float, default=0.1, help="time to delivery in years")
    b.add_argument("--freq", type=int, default=2)
    c = sub.add_parser("contracts", help="DV01-neutral contract count for a swap leg")
    c.add_argument("--swap-notional", type=float, required=True)
    c.add_argument("--swap-dv01-per-mm", type=float, required=True)
    c.add_argument("--fut-dv01", type=float, required=True, help="DV01 per contract (RoT or OA)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.cmd == "invoice":
        y = futures_implied_yield(args.fut_price, args.cf, args.coupon_pct, args.maturity, args.delivery, args.freq)
        print(f"futures-implied CTD yield {y:.4f}%  invoice spread (swap - govt) {invoice_spread_bp(args.swap_fwd_pct, y):+.2f}bp")
    elif args.cmd == "basket":
        df = pd.read_parquet(args.csv) if args.csv.endswith(".parquet") else pd.read_csv(args.csv)
        bk = _prep(df, args.delivery, args.freq)
        conv = converted_prices(bk, 0.0, args.freq)
        sigma = args.nvol_bp * np.sqrt(args.years)
        pw, p, d = p_weighted_dv01_per100(bk, sigma, args.freq)
        out = pd.DataFrame({"conv_fwd_px": conv, "bpv_per_cf": d, "p_ctd": p},
                           index=bk.get("instrument_id", bk.index))
        print(out.round(4).to_string())
        i = int(np.argmin(conv))
        print(f"CTD {out.index[i]}  theoretical futures {conv[i]:.4f}  RoT DV01/100 {d[i]:.5f}  "
              f"OA {oa_dv01_per100(bk, args.freq):.5f}  P-weighted {pw:.5f}  (sigma {sigma:.1f}bp)")
        if args.fut_price is not None:
            print(f"market futures minus zero-option theoretical: {args.fut_price - conv[i]:+.4f} px (negative = option value priced in)")
    elif args.cmd == "contracts":
        print(f"{args.swap_notional / 1e6 * args.swap_dv01_per_mm / args.fut_dv01:.1f} contracts")
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
