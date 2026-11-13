#!/usr/bin/env python3
"""Callable / structured issuance -> swapped vega supply -> hedge points -> straddle equivalents.

Functions (pandas / numpy in, numbers / pandas out):
  annuity               flat-rate forward annuity A(start, tenor), years of PV01 per unit notional.
  straddle_vega         normal-model ATMF straddle vega per 1bp of normal vol: 2 * N * A * sqrt(T) * phi(0) * 1e-4.
  is_swapped            issuer-type rule: financial / government / ssa swapped, non-financial not (override column).
  deal_vega             vega supplied per deal = notional / 100mn * vega_per_100mn, zero if not swapped.
  monthly_supply        gross, swapped gross and vega by announce month.
  bucket_supply         allocate deal vega to liquid hedge points with a structure -> {point: weight} map.
  straddle_equivalents  bucket vega -> notional of ATMF straddles carrying the same vega.
  expected_redemptions  sum(call_prob * notional) * efficiency (empirical haircut on raw Bermudan odds).
  dealer_short_european stock vega * (1 - hedge-fund share) * hedge ratio, split by hedge mix.

Conventions: notional = initial (issue) notional in deal currency; vega in currency per 1bp normal vol;
rates in pct; hedge points written <expiry>y<tail>y, e.g. 10y20y. Per-deal vega should come from a Bermudan
pricer at the announcement-date par strike. The two built-in anchors (30NC1, 30NC6) are one source's
early-2017 estimates and only fit order-of-magnitude work.

Deal log columns (canonical table `callable_issuance`): announce_date, notional_ccy, structure (e.g. 30NC5),
issuer_type (financial | government | ssa | non_financial); optional swapped (bool), vega_per_100mn_ccy.

CLI:
  python vega_supply.py --deals deals.csv [--vega-table vt.csv] [--hedge-map hm.csv] [--rate-pct 4.0]
      vt.csv columns: structure, vega_per_100mn_ccy      hm.csv columns: structure, hedge_point, weight
  python vega_supply.py --selftest
"""
from __future__ import annotations

import argparse
import math
import re
import sys

import numpy as np
import pandas as pd

PHI0 = 1.0 / math.sqrt(2.0 * math.pi)
SWAPPED_TYPES = {"financial", "government", "ssa"}
# $ normal vega per 100mn initial notional, zero-coupon 30y callables (Citi, Long Live Formosa, Jan 2017 rates).
ANCHOR_VEGA = {"30NC1": 145e3, "30NC6": 270e3}
# Hedge mixes. Short lockouts: "some combination of 1y30y and 10y20y" (Citi, Jan 2017; 50/50 is our default).
# Longer lockouts: Citi's Mar 2019 bucketing of the outstanding stock (average structure printed as "4NC30").
SHORT_LOCKOUT_MAP = {"1y30y": 0.5, "10y20y": 0.5}
LONG_LOCKOUT_MAP = {"5y25y": 0.35, "10y20y": 0.35, "20y10y": 0.30}


def parse_structure(s: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*NC\s*(\d+)\s*", str(s), re.I)
    if not m:
        raise ValueError(f"structure '{s}' is not <final>NC<lockout>, e.g. 30NC5")
    return int(m.group(1)), int(m.group(2))


def parse_point(p: str) -> tuple[float, float]:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)y(\d+(?:\.\d+)?)y\s*", str(p), re.I)
    if not m:
        raise ValueError(f"hedge point '{p}' is not <expiry>y<tail>y, e.g. 10y20y")
    return float(m.group(1)), float(m.group(2))


def annuity(start_y: float, tenor_y: float, rate_pct: float, freq: int = 1) -> float:
    """Forward annuity on a flat curve, periodic compounding: sum_k (1/freq) * (1 + r/freq)^-(start*freq + k)."""
    r = rate_pct / 100.0 / freq
    n = int(round(tenor_y * freq))
    if n < 1:
        raise ValueError(f"tenor {tenor_y}y has no {freq}x/yr payments; use a tenor of at least {1 / freq}y")
    k = np.arange(1, n + 1) + start_y * freq
    return float(np.sum((1.0 + r) ** -k) / freq)


def straddle_vega(expiry_y: float, tenor_y: float, rate_pct: float, notional: float = 1.0, freq: int = 1) -> float:
    """ATMF straddle vega per 1bp normal vol (Bachelier): 2 * N * A * sqrt(T) * phi(0) * 1e-4."""
    a = annuity(expiry_y, tenor_y, rate_pct, freq)
    return 2.0 * notional * a * math.sqrt(expiry_y) * PHI0 * 1e-4


def bachelier_straddle(fwd_pct, strike_pct, nvol_bp, expiry_y, annuity_y, notional=1.0) -> float:
    """Payer + receiver premium, normal model. Used to check straddle_vega by finite difference."""
    s = nvol_bp / 1e4 * math.sqrt(expiry_y)
    d = (fwd_pct - strike_pct) / 100.0 / s
    pdf = math.exp(-0.5 * d * d) * PHI0
    cdf = 0.5 * (1.0 + math.erf(d / math.sqrt(2.0)))
    x = (fwd_pct - strike_pct) / 100.0
    payer = x * cdf + s * pdf
    receiver = payer - x                                   # put-call parity on the forward
    return notional * annuity_y * (payer + receiver)


def is_swapped(deals: pd.DataFrame) -> pd.Series:
    rule = deals["issuer_type"].astype(str).str.lower().isin(SWAPPED_TYPES)
    if "swapped" in deals:                                 # CSV text: "true"/"false"/blank; never bool("false")
        txt = deals["swapped"].astype(str).str.strip().str.lower()
        override = txt.map({"true": True, "1": True, "1.0": True, "yes": True,
                            "false": False, "0": False, "0.0": False, "no": False})
        rule = override.where(override.notna(), rule).astype(bool)
    return rule


def deal_vega(deals: pd.DataFrame, vega_table: dict | None = None) -> pd.Series:
    table = {k.upper(): v for k, v in {**ANCHOR_VEGA, **(vega_table or {})}.items()}
    per = deals["structure"].astype(str).str.upper().str.replace(" ", "").map(table)
    if "vega_per_100mn_ccy" in deals:
        per = deals["vega_per_100mn_ccy"].where(deals["vega_per_100mn_ccy"].notna(), per)
    if deals["notional_ccy"].isna().any():
        raise ValueError("deal log has blank notional_ccy rows; fix them before aggregating")
    sw = is_swapped(deals)
    missing = sorted(set(deals.loc[per.isna() & sw, "structure"].astype(str)))
    if missing:
        raise ValueError(f"no vega for structures {missing}: add vega_per_100mn_ccy (Bermudan pricer) or --vega-table")
    return deals["notional_ccy"].astype(float) / 1e8 * per.fillna(0.0).astype(float) * sw


def monthly_supply(deals: pd.DataFrame, vega: pd.Series) -> pd.DataFrame:
    month = pd.to_datetime(deals["announce_date"]).dt.to_period("M")
    sw = is_swapped(deals)
    out = pd.DataFrame({"gross_ccy": deals["notional_ccy"].astype(float),
                        "swapped_gross_ccy": deals["notional_ccy"].astype(float) * sw,
                        "vega_ccy_per_bp": vega}).groupby(month).sum()
    out["vega_per_bn_swapped"] = out["vega_ccy_per_bp"] / (out["swapped_gross_ccy"] / 1e9)
    return out


def _default_map(structure: str) -> dict:
    final, lockout = parse_structure(structure)
    if final != 30:                                        # default maps are 30y-coterminal
        raise ValueError(f"no default hedge map for {structure}: pass --hedge-map (defaults cover 30y finals only)")
    return SHORT_LOCKOUT_MAP if lockout <= 2 else LONG_LOCKOUT_MAP


def bucket_supply(deals: pd.DataFrame, vega: pd.Series, hedge_map: dict | None = None) -> pd.Series:
    """hedge_map: {structure: {hedge_point: weight}}; weights per structure must sum to 1."""
    hedge_map = {k.upper(): v for k, v in (hedge_map or {}).items()}
    acc: dict[str, float] = {}
    for s, v in zip(deals["structure"].astype(str), vega):
        if v == 0:                                         # unswapped: no vega, structure may be exotic
            continue
        m = hedge_map.get(s.upper().replace(" ", "")) or _default_map(s)
        if abs(sum(m.values()) - 1.0) > 1e-9:
            raise ValueError(f"hedge weights for {s} sum to {sum(m.values())}, not 1")
        for p, w in m.items():
            acc[p] = acc.get(p, 0.0) + v * w
    return pd.Series(acc, name="vega_ccy_per_bp").sort_index()


def straddle_equivalents(bucket: pd.Series, rate_pct: float) -> pd.DataFrame:
    per_mn = pd.Series({p: straddle_vega(*parse_point(p), rate_pct, 1e6) for p in bucket.index})
    return pd.DataFrame({"vega_ccy_per_bp": bucket, "straddle_vega_per_1mn": per_mn,
                         "straddle_notional_eq_mn": bucket / per_mn})


def expected_redemptions(notional, call_prob, efficiency: float = 1.0) -> float:
    return float(np.sum(np.asarray(notional, float) * np.asarray(call_prob, float)) * efficiency)


def dealer_short_european(stock_vega: float, hf_share: float = 0.15, hedge_ratio: float = 0.85,
                          mix: dict | None = None) -> pd.Series:
    short = stock_vega * (1.0 - hf_share) * hedge_ratio
    return pd.Series({p: short * w for p, w in (mix or LONG_LOCKOUT_MAP).items()})


def _selftest() -> None:
    ok = True

    def check(label, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {label}: got {got:,.4f} want {want:,.4f} (tol {tol})")

    # 1. annuity at zero rate = tenor; straddle vega closed form at r = 0 for $1bn 10y10y.
    check("annuity(0, 10, 0%)", annuity(0, 10, 0.0), 10.0, 1e-12)
    check("annuity(10, 10, 2.6%) closed form", annuity(10, 10, 2.6), (1.026 ** -10 - 1.026 ** -20) / 0.026, 1e-9)
    want = 2 * 1e9 * 10 * math.sqrt(10) * PHI0 * 1e-4
    check("10y10y straddle vega $1bn at r=0", straddle_vega(10, 10, 0.0, 1e9), want, 1e-6)
    # 2. vega formula vs finite difference of an independent Bachelier price (ATMF, 2.6%, 70bp vol).
    a, h = annuity(10, 10, 2.6), 0.01
    fd = (bachelier_straddle(2.6, 2.6, 70 + h, 10, a, 1e8) - bachelier_straddle(2.6, 2.6, 70 - h, 10, a, 1e8)) / (2 * h)
    check("vega vs finite difference ($100mn)", straddle_vega(10, 10, 2.6, 1e8), fd, 1e-3)
    # 3. Citi Jan 2017 beta-weighted switch: 1 unit vega 2y30y vs 0.8 unit 2y10y -> about $53mn vs $100mn.
    n30 = straddle_vega(2, 10, 2.6, 1e8) / 0.8 / straddle_vega(2, 30, 2.6, 1.0)
    check("2y30y notional vs $100mn 2y10y ($mn)", n30 / 1e6, 53.0, 1.0)
    # 4. Straddle-equivalent conversion lands inside the range Citi's two conversions imply ($1.55-1.84mn per $bn).
    check("10y10y vega per $bn at 2.6% ($mn)", straddle_vega(10, 10, 2.6, 1e9) / 1e6, 1.70, 0.15)
    # 5. Aggregation with a known answer: non-financial deal is not swapped.
    deals = pd.DataFrame({"announce_date": ["2017-01-05", "2017-01-20", "2017-02-03"],
                          "notional_ccy": [1e8, 1e8, 1e8], "structure": ["30NC1", "30NC6", "30NC6"],
                          "issuer_type": ["financial", "financial", "non_financial"]})
    v = deal_vega(deals)
    check("total swapped vega", v.sum(), 415e3, 1e-6)
    b = bucket_supply(deals, v, {"30NC6": {"10y20y": 0.5, "10y10y": 0.5}})
    check("bucket 10y20y", b["10y20y"], 0.5 * 145e3 + 0.5 * 270e3, 1e-6)
    check("bucket 1y30y", b["1y30y"], 72.5e3, 1e-6)
    m = monthly_supply(deals, v)
    check("Jan vega per $bn swapped", m.iloc[0]["vega_per_bn_swapped"], 2.075e6, 1e-3)
    unswapped = pd.DataFrame({"notional_ccy": [1e8], "structure": ["30NC5"], "issuer_type": ["non_financial"]})
    check("unswapped deal needs no vega input", deal_vega(unswapped).sum(), 0.0, 0.0)
    exotic = pd.DataFrame({"notional_ccy": [1e8], "structure": ["PRDC"], "issuer_type": ["non_financial"]})
    check("unswapped exotic skipped in buckets", bucket_supply(exotic, deal_vega(exotic)).sum(), 0.0, 0.0)
    # 5b. swapped override as CSV text: "false" on a financial kills it, "true" on a non-financial counts, blank = rule.
    ov = pd.DataFrame({"notional_ccy": [1e8] * 3, "structure": ["30NC1"] * 3,
                       "issuer_type": ["financial", "non_financial", "financial"], "swapped": ["false", "true", None]})
    check("swapped override (text)", deal_vega(ov).sum(), 2 * 145e3, 1e-6)
    # 6. Redemptions and the Citi Mar 2019 dealer chain (366 * 0.85 * 0.85 = about 265).
    check("expected redemptions", expected_redemptions([100, 200], [0.5, 0.25], 0.5), 50.0, 1e-12)
    try:
        annuity(1, 0.4, 3.0)
        check("annuity rejects tenor < 1 period", 1.0, 0.0, 0.0)
    except ValueError:
        pass
    try:
        bucket_supply(pd.DataFrame({"structure": ["25NC5"]}), pd.Series([1.0]))
        check("25NC5 has no default hedge map", 1.0, 0.0, 0.0)
    except ValueError:
        pass
    check("dealer short European vega", dealer_short_european(366.0).sum(), 264.435, 1e-9)
    if not ok:
        sys.exit("selftest FAILED")
    print("selftest passed")


def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith(".parquet") else pd.read_csv(path)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--deals", help="deal log CSV/Parquet")
    ap.add_argument("--vega-table", help="CSV: structure, vega_per_100mn_ccy")
    ap.add_argument("--hedge-map", help="CSV: structure, hedge_point, weight")
    ap.add_argument("--rate-pct", type=float, default=4.0, help="flat rate for straddle annuities (default 4.0)")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return
    if not a.deals:
        ap.error("--deals is required (or --selftest)")
    deals = _read(a.deals)
    if "deal_id" in deals:  # canonical callable_issuance has one row per vintage: supply uses the announcement row
        deals = deals.sort_values("pub_ts_utc", kind="stable") if "pub_ts_utc" in deals else deals
        deals = deals.drop_duplicates("deal_id", keep="first")
    vt = None
    if a.vega_table:
        t = _read(a.vega_table)
        vt = dict(zip(t["structure"], t["vega_per_100mn_ccy"]))
    hm = None
    if a.hedge_map:
        t = _read(a.hedge_map)
        hm = {s: dict(zip(g["hedge_point"], g["weight"])) for s, g in t.groupby("structure")}
    try:
        v = deal_vega(deals, vt)
        buckets = straddle_equivalents(bucket_supply(deals, v, hm), a.rate_pct)
    except ValueError as e:
        sys.exit(str(e))
    pd.set_option("display.width", 160)
    print("Monthly supply (vega in ccy per 1bp normal vol)")
    print(monthly_supply(deals, v).round(0).to_string())
    print(f"\nHedge-point vega and ATMF straddle equivalents (flat {a.rate_pct}% annuities)")
    print(buckets.round(2).to_string())


if __name__ == "__main__":
    main()
