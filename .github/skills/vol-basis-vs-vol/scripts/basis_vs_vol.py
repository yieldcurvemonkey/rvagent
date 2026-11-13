#!/usr/bin/env python3
"""Basis-as-option vs swaption / futures-option vol: pricing, cost per gamma, option-adjusted basis, Board ratio.

Units: yields/shifts in bp; vols are NORMAL (bp per year); T in years; basis/option values in price points per 100
face (any consistent price unit works as long as slope and net basis share it); annuity = 1 (it cancels in ratios).
Conventions: the reference yield shift x is the move of the forward yield of the CTD-sector bond (bp, +ve = sell-off).
A call-type leg pays slope * max(x - k, 0), a put-type leg pays slope * max(k - x, 0), slope = price pts per bp.

CLI:  python basis_vs_vol.py --selftest | ratio | cpg | conditional | oab   (see --help of each)
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np

SQRT2PI = math.sqrt(2.0 * math.pi)


def _phi(u):
    return math.exp(-0.5 * u * u) / SQRT2PI


def _Phi(u):
    return 0.5 * (1.0 + math.erf(u / math.sqrt(2.0)))


# ----------------------------------------------------------------------------- normal (Bachelier) building blocks
def normal_option(sigma_bp, T, strike_bp=0.0, side="call"):
    """Undiscounted normal option on a shift x ~ N(0, sigma^2 T) paying max(x-k,0) (call) or max(k-x,0) (put).
    Returns (value_bp, gamma_per_bp, d) with gamma = d(delta)/dx = phi(d)/s, s = sigma*sqrt(T); d = (0-k)/s for a call."""
    s = sigma_bp * math.sqrt(T)
    if s <= 0:
        intrinsic = max(-strike_bp, 0.0) if side == "call" else max(strike_bp, 0.0)
        return intrinsic, 0.0, math.inf
    d = (-strike_bp) / s if side == "call" else strike_bp / s
    return s * (_phi(d) + d * _Phi(d)), _phi(d) / s, d


def basis_value(legs, sigma_bp, T):
    """Expected net-basis option value: sum of legs (slope_px_per_bp, strike_bp, 'call'|'put')."""
    return sum(sl * normal_option(sigma_bp, T, k, sd)[0] for sl, k, sd in legs)


def basis_gamma(legs, sigma_bp, T):
    """Analytic gamma (px per bp^2) of the basis legs; never bump across the kink."""
    return sum(sl * normal_option(sigma_bp, T, k, sd)[1] for sl, k, sd in legs)


def implied_switch_vol(nb_px, legs, T, lo=1.0, hi=3000.0):
    """Normal vol at which the model option value equals the market net basis. None if outside [lo, hi] value range.
    Read it as a diagnostic only: net basis also contains financing, squeeze and flow noise (see SKILL.md)."""
    if not (math.isfinite(nb_px) and T > 0):
        return None
    f = lambda s: basis_value(legs, s, T) - nb_px
    if f(lo) > 0 or f(hi) < 0:
        return None
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------------------- cost per gamma
def cost_per_gamma_richness(nb_px, legs, sigma_swn_bp, T):
    """Swaption cost per unit gamma / basis cost per unit gamma, like-for-like strikes (a swaption struck at each leg's
    switch point, same vol). cpg = value/gamma, in bp^2. >1 -> basis is the cheaper gamma (buy basis), <1 -> dearer.
    Fair (basis priced at the swaption vol) gives exactly 1. An ATMF swaption has cpg = sigma^2*T."""
    g_b = basis_gamma(legs, sigma_swn_bp, T)
    if g_b <= 0:
        return None
    cpg_b = nb_px / g_b
    v_s = sum(abs(sl) * normal_option(sigma_swn_bp, T, k, sd)[0] for sl, k, sd in legs)
    g_s = sum(abs(sl) * normal_option(sigma_swn_bp, T, k, sd)[1] for sl, k, sd in legs)
    return (v_s / g_s) / cpg_b


# ----------------------------------------------------------------------------- option-adjusted basis
def atmf_cpg_richness(nb_px, legs, sigma_swn_bp, T):
    """ATMF swaption cpg (sigma^2 T) / basis cpg (NB / gamma_basis). Biased > 1 for an OTM basis: read it next to
    cost_per_gamma_richness (same strike)."""
    g = basis_gamma(legs, sigma_swn_bp, T)
    return None if g <= 0 else sigma_swn_bp ** 2 * T / (nb_px / g)


def oab(nb, tdov):
    """OAB = NB - TDOV (same unit). >0 basis rich / futures cheap; <0 basis cheap / futures rich."""
    return nb - tdov


def futures_rich_by(oab_val, cf):
    """Market futures minus model futures = -OAB / CF (same unit as OAB). Positive = futures rich."""
    return -oab_val / cf


def oa_irr_pct(irr_pct, option_px, dirty_px, n_days, basis=360.0):
    """Option-adjusted implied repo (%) = IRR + option / dirty * basis/n (as a percent). Compare with term repo."""
    return irr_pct + option_px / dirty_px * basis / n_days * 100.0


def irr_from_repo_pct(repo_pct, bnoc_px, dirty_px, n_days, basis=360.0):
    """IRR = term repo - BNOC / dirty * basis/n (identity, % units)."""
    return repo_pct - bnoc_px / dirty_px * basis / n_days * 100.0


def grid_expectation(cells, p_rows, p_cols):
    """Probability-weighted BNOC over a slope (rows) x level (cols) grid."""
    c = np.asarray(cells, float)
    return float(np.asarray(p_rows) @ c @ np.asarray(p_cols))


# ----------------------------------------------------------------------------- Board vs CTD-matched swaption
def swaption_strike_pct(board_strike_yield_pct, invoice_spread_bp):
    """Strike map: swaption strike = futures-option strike yield + invoice spread (swap - govt, bp)."""
    return board_strike_yield_pct + invoice_spread_bp / 100.0


def conditional_notional_mn(n_contracts, face_per_contract, fut_dv01, swap_dv01):
    """Swaption notional (mn) DV01-matched to n futures contracts: n * face * fut_dv01 / swap_dv01. DV01s share a unit."""
    return n_contracts * face_per_contract * fut_dv01 / swap_dv01 / 1e6


def pickup_bp(invoice_spread_bp, costless_strike_spread_bp):
    """Printed-row convention: pick-up = invoice spread - costless strike spread. Positive: puts vs payers -> Board put
    rich; calls vs receivers -> Board call cheap (derived from strikes; matches printed vol ratios). The source's prose
    has the opposite subtraction order; recompute from raw numbers."""
    return invoice_spread_bp - costless_strike_spread_bp


def fut_px_to_bp(dpx, dv01_px_per_bp):
    """Futures price change -> yield-equivalent change in bp (price up = yield down)."""
    return -np.asarray(dpx, float) / dv01_px_per_bp


def realised_ratio(d_fut_bp, d_swap_bp, window=21):
    """Latest realised vol ratio futures/swap over `window` daily changes (both bp, same dates)."""
    a, b = np.asarray(d_fut_bp, float), np.asarray(d_swap_bp, float)
    m = np.isfinite(a) & np.isfinite(b)  # pairwise-complete, then the latest `window` pairs
    a, b = a[m][-window:], b[m][-window:]
    if len(a) < 3 or b.std(ddof=1) == 0:
        return float("nan")  # short history: no ratio rather than a wrong one
    return float(a.std(ddof=1) / b.std(ddof=1))


def board_signal(board_nvol_bp, swn_nvol_bp, realised=None, band=0.05):
    """Implied Board/swaption ratio vs the realised futures/swap ratio. gap = implied - realised.
    'board_rich' if gap > band, 'board_cheap' if gap < -band (band is a working default, not a source value)."""
    r = board_nvol_bp / swn_nvol_bp
    if realised is None or not math.isfinite(realised) or not math.isfinite(r):
        return {"ratio": r, "realised": None, "gap": None, "signal": "no_realised_ratio"}
    gap = r - realised
    sig = "board_rich" if gap > band else "board_cheap" if gap < -band else "neutral"
    return {"ratio": r, "realised": realised, "gap": gap, "signal": sig}


# ----------------------------------------------------------------------------- self-test (known answers)
def _selftest():
    bad = []

    def check(name, ok, info=""):
        print(("PASS " if ok else "FAIL ") + name + (f"  [{info}]" if info else ""))
        if not ok:
            bad.append(name)

    # 1. ATM normal call = sigma*sqrt(T)/sqrt(2 pi); sigma=100, T=1 -> 39.8942
    v, g, d = normal_option(100, 1.0, 0.0, "call")
    check("ATM call value", abs(v - 39.894228) < 1e-5, f"{v:.6f}")
    check("ATM gamma = 1/(sigma sqrt(2 pi T))", abs(g - 1 / (100 * SQRT2PI)) < 1e-12)
    # 2. put-call: call - put = -k (forward 0)
    c = normal_option(80, 0.5, 15, "call")[0]
    p = normal_option(80, 0.5, 15, "put")[0]
    check("put-call parity", abs((c - p) - (0 - 15)) < 1e-9, f"{c - p:.6f}")
    # 3. independent numeric integration of an OTM leg payoff (not the closed form)
    s = 70 * math.sqrt(0.25)
    x = np.linspace(-12 * s, 12 * s, 400001)
    pdf = np.exp(-0.5 * (x / s) ** 2) / (s * SQRT2PI)
    num = float((getattr(np, "trapezoid", None) or np.trapz)(0.03 * np.maximum(x - 40, 0) * pdf, x))
    ana = basis_value([(0.03, 40, "call")], 70, 0.25)
    check("closed form vs numeric integral", abs(num - ana) < 1e-6, f"{num:.8f} vs {ana:.8f}")
    # 4. implied vol round trip on a strangle (put-like + call-like leg)
    legs = [(0.02, 35, "call"), (0.015, -30, "put")]
    iv = implied_switch_vol(basis_value(legs, 91.0, 0.25), legs, 0.25)
    check("implied switch vol round trip", iv is not None and abs(iv - 91.0) < 1e-6, f"{iv}")
    # 5. cost per gamma: fair basis -> 1, half price -> 2; ATMF swaption cpg = sigma^2 T
    fair = basis_value(legs, 80, 0.25)
    check("cpg richness fair = 1", abs(cost_per_gamma_richness(fair, legs, 80, 0.25) - 1) < 1e-9)
    check("cpg richness half price = 2", abs(cost_per_gamma_richness(fair / 2, legs, 80, 0.25) - 2) < 1e-9)
    atm = [(1.0, 0.0, "call")]
    check("ATMF richness = 1 for ATM fair basis", abs(atmf_cpg_richness(basis_value(atm, 80, 0.25), atm, 80, 0.25) - 1) < 1e-9)
    u = 0.75  # OTM leg u sd away: ATMF richness = 1/(1 - u Phi(-u)/phi(u)), hand formula
    leg1 = [(0.0125, u * 80 * 0.5, "call")]
    exp = 1 / (1 - u * _Phi(-u) / _phi(u))
    check("ATMF richness OTM bias", abs(atmf_cpg_richness(basis_value(leg1, 80, 0.25), leg1, 80, 0.25) - exp) < 1e-9, f"{exp:.4f}")
    v0, g0, _ = normal_option(80, 0.25, 0.0, "call")
    check("ATMF cpg = sigma^2 T", abs(v0 / g0 - 80 ** 2 * 0.25) < 1e-9, f"{v0 / g0:.4f}")
    # 6. Burghardt OAB example (Treasury Bond Basis, 4 Apr 2001): NB 4.5, TDOV 8.0, CF 1.1936
    o = oab(4.5, 8.0)
    check("OAB = -3.5/32", abs(o + 3.5) < 1e-12)
    check("futures rich by 2.93 ticks", abs(futures_rich_by(o, 1.1936) - 2.9323) < 1e-3, f"{futures_rich_by(o, 1.1936):.4f}")
    # 7. Burghardt grid expectation 7.41/32
    cells = [[20, 2, 20], [25, 1, 15], [30, 3, 10]]
    e = grid_expectation(cells, [0.16, 0.68, 0.16], [0.16, 0.68, 0.16])
    check("expected BNOC grid = 7.41", abs(e - 7.4064) < 1e-4, f"{e:.4f}")
    # 8. IRR identity: repo 3.00%, BNOC 0.5 pt on dirty 100, 60 days -> IRR 0.0%; OA IRR returns repo
    irr = irr_from_repo_pct(3.0, 0.5, 100.0, 60)
    check("IRR identity", abs(irr - 0.0) < 1e-12, f"{irr}")
    check("OA IRR = repo", abs(oa_irr_pct(irr, 0.5, 100.0, 60) - 3.0) < 1e-12)
    # 9. Citi conditional-spread printed rows (Rates Vol Lab, 2017 and 2018 and 2026)
    check("TYH7 notional 120.3mn", abs(conditional_notional_mn(1000, 100000, 7.53, 6.26) - 120.3) < 0.05)
    check("FVM7 notional ~119.1mn", abs(conditional_notional_mn(1000, 100000, 4.77, 4.01) - 119.1) < 0.2)
    check("FVK8 pick-up +0.8", abs(pickup_bp(11.6, 10.8) - 0.8) < 1e-9)
    check("TYX6 pick-up +2.6", abs(pickup_bp(-38.4, -41.0) - 2.6) < 1e-9)
    check("TYM3 pick-up -5.2", abs(pickup_bp(-29.8, -24.6) + 5.2) < 1e-9)
    check("strike map FVK8", abs(swaption_strike_pct(2.74, 11.6) - 2.856) < 1e-9)
    # 10. Board ratio vs realised (TYH7, Citi, Jan/May 2017): 87.4/81.8 = 1.07 vs realised 0.97 -> rich
    sg = board_signal(87.4, 81.8, realised=0.97)
    check("board_signal rich", sg["signal"] == "board_rich" and abs(sg["ratio"] - 1.0685) < 1e-3, str(sg))
    # 11. realised ratio on constructed data with known scale (futures 1.5x swap)
    rng = np.random.default_rng(0)
    sw = rng.standard_normal(400)
    check("realised ratio = 1.5", abs(realised_ratio(1.5 * sw, sw, 400) - 1.5) < 1e-12)
    check("realised ratio NaN-safe / short history", abs(realised_ratio([np.nan, 3.0, 6.0, 9.0], [1.0, 2.0, 4.0, 6.0], 21) - 1.5) < 1e-12
          and math.isnan(realised_ratio([1.0, 2.0], [1.0, 2.0])))
    check("board_signal NaN realised -> no signal", board_signal(90, 80, realised=float("nan"))["signal"] == "no_realised_ratio")
    check("implied vol NaN guard", implied_switch_vol(float("nan"), legs, 0.25) is None)
    check("fut_px_to_bp sign", fut_px_to_bp([0.05], 0.05)[0] == -1.0)
    return 0 if not bad else 1


# ----------------------------------------------------------------------------- CLI on canonical tables
def _cmd_ratio(a):
    import pandas as pd
    rd = lambda p: pd.read_parquet(p) if str(p).endswith(".parquet") else pd.read_csv(p)
    q = rd(a.opt_quotes)
    d0 = pd.Timestamp(a.date)
    q = q[(pd.to_datetime(q["date"]) == d0) & (q["opt_id"] == a.opt_id)]
    s = rd(a.vol_surface)
    s = s[(pd.to_datetime(s["date"]) == d0) & (s["index_id"] == a.index_id) & (s["product"] == "swaption") &
          (s["expiry"] == a.expiry) & (s["tenor"] == a.tenor) & (s["strike_offset_bp"] == a.strike_offset_bp)]
    if q.empty or s.empty or q["nvol_bp"].isna().all():
        sys.exit("no matching Board quote or swaption vol row (check date, ids, expiry, tenor, strike offset)")
    if len(q) > 1 or len(s) > 1:  # several snaps / duplicate rows: the caller must pick one snap type first
        sys.exit("ambiguous: %d Board rows, %d swaption rows; filter to one snap per series" % (len(q), len(s)))
    out = board_signal(float(q["nvol_bp"].iloc[0]), float(s["nvol_bp"].iloc[0]), a.realised_ratio, a.band)
    print(json.dumps(out))


def _cmd_cpg(a):
    legs = json.loads(a.legs)  # [[slope_px_per_bp, strike_bp, "call"|"put"], ...]
    legs = [(float(x), float(k), sd) for x, k, sd in legs]
    out = {"model_value_px": basis_value(legs, a.swaption_nvol_bp, a.T),
           "atmf_cpg_richness": atmf_cpg_richness(a.net_basis_px, legs, a.swaption_nvol_bp, a.T),
           "implied_switch_nvol_bp": implied_switch_vol(a.net_basis_px, legs, a.T),
           "cpg_richness": cost_per_gamma_richness(a.net_basis_px, legs, a.swaption_nvol_bp, a.T)}
    print(json.dumps(out))


def _cmd_cond(a):
    print(json.dumps({"swaption_notional_mn": conditional_notional_mn(a.contracts, a.face, a.fut_dv01, a.swap_dv01),
                      "pickup_bp": pickup_bp(a.invoice_bp, a.costless_spread_bp)}))


def _cmd_oab(a):
    o = oab(a.net_basis, a.tdov)
    print(json.dumps({"oab": o, "futures_rich_by": futures_rich_by(o, a.cf)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true", help="check known-answer cases; exit 1 on failure")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("ratio", help="Board ATM nvol / CTD-matched swaption nvol from opt_quotes + vol_surface CSV")
    r.add_argument("--opt-quotes", required=True); r.add_argument("--vol-surface", required=True)
    r.add_argument("--date", required=True); r.add_argument("--opt-id", required=True)
    r.add_argument("--index-id", required=True); r.add_argument("--expiry", required=True)
    r.add_argument("--tenor", required=True, help="CTD-matched swap tail, e.g. 7Y")
    r.add_argument("--strike-offset-bp", type=float, default=0.0)
    r.add_argument("--realised-ratio", type=float, default=None); r.add_argument("--band", type=float, default=0.05)
    r.set_defaults(fn=_cmd_ratio)
    c = sub.add_parser("cpg", help="implied switch vol and cost-per-gamma richness for a basis described by legs")
    c.add_argument("--legs", required=True, help='JSON [[slope_px_per_bp, strike_bp, "call"|"put"], ...]')
    c.add_argument("--net-basis-px", type=float, required=True); c.add_argument("--swaption-nvol-bp", type=float, required=True)
    c.add_argument("--T", type=float, required=True, help="years to the last trading day"); c.set_defaults(fn=_cmd_cpg)
    d = sub.add_parser("conditional", help="DV01-matched swaption notional and pick-up")
    d.add_argument("--contracts", type=float, default=1000); d.add_argument("--face", type=float, default=100000)
    d.add_argument("--fut-dv01", type=float, required=True); d.add_argument("--swap-dv01", type=float, required=True)
    d.add_argument("--invoice-bp", type=float, required=True); d.add_argument("--costless-spread-bp", type=float, required=True)
    d.set_defaults(fn=_cmd_cond)
    o = sub.add_parser("oab"); o.add_argument("--net-basis", type=float, required=True)
    o.add_argument("--tdov", type=float, required=True); o.add_argument("--cf", type=float, required=True)
    o.set_defaults(fn=_cmd_oab)
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.cmd:
        p.error("give a subcommand or --selftest")
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
