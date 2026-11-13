#!/usr/bin/env python3
"""Conditional curve trades: Bachelier pricing, zero-cost strike, vol-weighted curve, pick-ups, ladders.

Units: rates/strikes in pct, spreads/vols/premiums in bp, annuity A in years, T in years.
Premium (bp of notional) = A * bachelier_price_bp.  Curve = long tail minus short tail.
Terminal payoff of a conditional steepener with both options ITM = (curve - K), K = K_long - K_short
(a flattener = K - curve).  Notionals are DV01-neutral: N_short = N_long * A_long / A_short.

CLI: python conditional_curve.py solve --vol-surface vol_surface.csv --date 2026-11-10 --index-id USD-SOFR \
        --expiry 1Y --short-tail 2Y --long-tail 10Y --structure bear-steepener [--curve-par curve_par.csv]
     python conditional_curve.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np

SQ2PI = math.sqrt(2.0 * math.pi)


def _phi(d):
    return math.exp(-0.5 * d * d) / SQ2PI


def _Phi(d):
    return 0.5 * math.erfc(-d / math.sqrt(2.0))


def bachelier(kind: str, F_pct: float, K_pct: float, vol_bp: float, T: float, A: float = 1.0) -> float:
    """Premium in bp of notional of a payer ('payer') or receiver ('receiver'), normal vol in bp/yr."""
    s = vol_bp * math.sqrt(T)                    # bp std-dev of the forward at expiry
    m = (F_pct - K_pct) * 100.0                  # forward minus strike, bp
    if s <= 0:
        return A * max(m if kind == "payer" else -m, 0.0)
    d = m / s
    if kind == "payer":
        return A * (m * _Phi(d) + s * _phi(d))
    return A * (-m * _Phi(-d) + s * _phi(d))


def delta(kind: str, F_pct, K_pct, vol_bp, T) -> float:
    """Rate delta per unit annuity: payer in (0,1), receiver in (-1,0) (so DV01 = -delta x A x 1bp for a long payer)."""
    s = vol_bp * math.sqrt(T)
    m = (F_pct - K_pct) * 100.0
    if s <= 0:
        return float(m > 0) if kind == "payer" else -float(m < 0)
    d = m / s
    return _Phi(d) if kind == "payer" else -_Phi(-d)


def vega(F_pct, K_pct, vol_bp, T, A=1.0) -> float:
    """Premium bp per 1bp of normal vol."""
    s = vol_bp * math.sqrt(T)
    return 0.0 if s <= 0 else A * math.sqrt(T) * _phi((F_pct - K_pct) * 100.0 / s)


# structure -> (kind, long-tail option is bought?)
STRUCT = {
    "bear-steepener": ("payer", True, "steepener"),
    "bear-flattener": ("payer", False, "flattener"),
    "bull-steepener": ("receiver", False, "steepener"),
    "bull-flattener": ("receiver", True, "flattener"),
}


def zero_cost_conditional(structure, F_S, F_L, vol_S, vol_L, A_S, A_L, T, vol_fn_S=None, vol_fn_L=None):
    """Strike-shift (JPM method A) zero-premium conditional curve trade.

    The leg with the larger DV01-matched ATMF premium is struck OTM (payer above / receiver below the
    forward) until premiums are equal; the other leg stays ATMF.  vol_fn_*(offset_bp) -> vol_bp lets a
    skewed surface re-vol the shifted strike (offset = strike - forward, bp); default flat vol.
    Notional: long tail 100, short tail 100*A_L/A_S.  Returns a dict (strikes pct, bp quantities).
    net_delta_annuity is in RATE-delta sign (long payer > 0), i.e. DV01 sign is the opposite; vega in bp premium per bp vol.
    """
    from scipy.optimize import brentq
    if T <= 0 or min(vol_S, vol_L, A_S, A_L) <= 0:
        raise ValueError("T, vols and annuities must be positive")
    kind, long_bought, side = STRUCT[structure]
    sgn = 1.0 if kind == "payer" else -1.0
    N = {"L": 1.0, "S": A_L / A_S}
    F = {"S": F_S, "L": F_L}
    A = {"S": A_S, "L": A_L}
    vf = {"S": vol_fn_S or (lambda o, v=vol_S: v), "L": vol_fn_L or (lambda o, v=vol_L: v)}

    def prem(leg, x):  # premium of leg struck x bp OTM, per 100 of long notional (bp)
        off = sgn * x
        return N[leg] * bachelier(kind, F[leg], F[leg] + off / 100.0, vf[leg](off), T, A[leg])

    atm = {k: prem(k, 0.0) for k in "SL"}
    exp = "S" if atm["S"] > atm["L"] else "L"
    cheap = "L" if exp == "S" else "S"
    x = 0.0
    if atm[exp] - atm[cheap] > 1e-12:
        x = brentq(lambda z: prem(exp, z) - atm[cheap], 0.0, 5000.0, xtol=1e-9)
    off = {"S": 0.0, "L": 0.0}
    off[exp] = sgn * x
    K = {k: F[k] + off[k] / 100.0 for k in "SL"}
    fwd_curve = (F_L - F_S) * 100.0
    k_curve = (K["L"] - K["S"]) * 100.0
    bought = "L" if long_bought else "S"
    pos = {"L": 1.0 if bought == "L" else -1.0, "S": 1.0 if bought == "S" else -1.0}
    vols = {k: vf[k](off[k]) for k in "SL"}
    dlt = sum(pos[k] * N[k] * A[k] * delta(kind, F[k], K[k], vols[k], T) for k in "SL")
    vg = sum(pos[k] * N[k] * vega(F[k], K[k], vols[k], T, A[k]) for k in "SL")
    return dict(structure=structure, expensive_leg=exp, shift_bp=x, strike_short_pct=K["S"], strike_long_pct=K["L"],
                notional_long=100.0, notional_short=100.0 * N["S"], premium_bp=atm[cheap],
                fwd_curve_bp=fwd_curve, strike_curve_bp=k_curve,
                vol_pickup_bp=(fwd_curve - k_curve) if side == "steepener" else (k_curve - fwd_curve),
                net_delta_annuity=dlt, net_vega_bp_per_bp=vg)


def vol_weighted(vol_S, vol_L, A_S, A_L, F_S, F_L):
    """JPM method B: both ATMF, long-tail notional scaled by W = vol_S/vol_L; exposure W*Y_L - Y_S.
    W < 1 when the long tail is the rich leg (JPM: cut its notional); W > 1 when the short tail is rich (the same
    premium match, expressed by scaling the cheap leg up)."""
    W = vol_S / vol_L
    return dict(weight=W, notional_long=100.0 * W, notional_short=100.0 * A_L / A_S,
                entry_level_bp=(W * F_L - F_S) * 100.0, implied_directionality=1.0 - W)


def pickups(spot_bp, fwd_bp, strike_bp, side):
    """Citi screen: steepener curve = S-F, vol = F-K; flattener curve = F-S, vol = K-F; total = sum."""
    sgn = 1.0 if side == "steepener" else -1.0
    c, v = sgn * (spot_bp - fwd_bp), sgn * (fwd_bp - strike_bp)
    return dict(curve=c, vol=v, total=c + v)


def package_payoff(legs, y_pct):
    """Terminal payoff (pct) of option legs [(kind, strike_pct, signed_weight)] at yields y_pct (array)."""
    y = np.asarray(y_pct, float)
    out = np.zeros_like(y)
    for kind, k, w in legs:
        out += w * (np.maximum(y - k, 0.0) if kind == "payer" else np.maximum(k - y, 0.0))
    return out


def carry_to_premium(roll_bp, premium_bp):
    """Bassman three-to-one screen: roll-down / premium; both in the same DV01 scaling."""
    return roll_bp / premium_bp


def spread_vol(vol_a, vol_b, rho):
    """Normal vol of A-B: sqrt(a^2 + b^2 - 2 rho a b)."""
    return math.sqrt(max(vol_a ** 2 + vol_b ** 2 - 2.0 * rho * vol_a * vol_b, 0.0))


def implied_corr(vol_a, vol_b, vol_spread):
    return (vol_a ** 2 + vol_b ** 2 - vol_spread ** 2) / (2.0 * vol_a * vol_b)


def breakeven_move(daily_carry_bp, gamma_bp):
    """Daily move (bp) whose convexity gain 0.5*gamma*m^2 offsets negative daily carry; 0 if carry >= 0 (long-convexity
    flattener: lower BE/RV is better).  For a short-convexity position with positive carry (forward steepener) pass
    -carry: BE is then the move at which convexity losses eat the carry and BE/RV > 1 is the cushion."""
    return 0.0 if daily_carry_bp >= 0 else math.sqrt(2.0 * -daily_carry_bp / gamma_bp)


def delivered_directionality(y_long, y_short):
    """Beta of curve changes (long - short) on long-yield changes (levels differenced); compare 1 - vol_S/vol_L."""
    dl, ds = np.diff(np.asarray(y_long, float)), np.diff(np.asarray(y_short, float))
    ok = np.isfinite(dl) & np.isfinite(ds)       # a NaN gap drops both adjacent differences, never bridges them
    if ok.sum() < 30:
        return float("nan")                      # too short for a stable beta
    return float(np.polyfit(dl[ok], (dl - ds)[ok], 1)[0])


def _annuity(f_pct, n_years, freq=1):
    f = max(f_pct / 100.0, 1e-6)
    return (1 - (1 + f / freq) ** (-n_years * freq)) / f   # flat-yield approximation of the swap annuity


def _tenor_years(t):
    t = str(t).upper()
    return float(t[:-1]) / {"M": 12.0, "Y": 1.0, "W": 52.0, "D": 365.0}[t[-1]]


def _cli_solve(a):
    import pandas as pd
    v = pd.read_csv(a.vol_surface)
    v = v[(v["date"] == a.date) & (v["index_id"] == a.index_id) & (v["expiry"] == a.expiry)
          & (v["product"] == "swaption") & (v["fwd_start"] == "0D")]
    if a.snap:
        v = v[v["snap"] == a.snap]
    elif v["snap"].nunique() > 1:
        sys.exit("several snaps in vol_surface for this date: pass --snap (never mix snaps)")
    T = _tenor_years(a.expiry)
    leg = {}
    for key, tn in (("S", a.short_tail), ("L", a.long_tail)):
        g = v[v["tenor"] == tn].sort_values("strike_offset_bp")
        if g.empty or not (g["strike_offset_bp"] == 0).any():
            sys.exit(f"missing ATMF vol for {a.expiry}x{tn}: ask the data adapter, do not invent")
        atm = g[g["strike_offset_bp"] == 0].iloc[0]
        if pd.isna(atm.get("atm_fwd_pct")):
            sys.exit(f"missing atm_fwd_pct for {a.expiry}x{tn}")
        xs, vs = g["strike_offset_bp"].to_numpy(float), g["nvol_bp"].to_numpy(float)
        leg[key] = (float(atm["atm_fwd_pct"]), float(atm["nvol_bp"]), (lambda o, xs=xs, vs=vs: float(np.interp(o, xs, vs))),
                    _annuity(float(atm["atm_fwd_pct"]), _tenor_years(tn), a.freq))
    r = zero_cost_conditional(a.structure, leg["S"][0], leg["L"][0], leg["S"][1], leg["L"][1],
                              leg["S"][3], leg["L"][3], T, leg["S"][2], leg["L"][2])
    if a.curve_par:
        c = pd.read_csv(a.curve_par)
        c = c[(c["date"] == a.date) & (c["start"] == "0D")]
        if a.snap:
            c = c[c["snap"] == a.snap]
        elif c["snap"].nunique() > 1:
            sys.exit("several snaps in curve_par for this date: pass --snap (never mix snaps)")
        if a.index_id in set(c["curve_id"]):
            c = c[c["curve_id"] == a.index_id].set_index("tenor")["par_rate_pct"]
            if a.short_tail in c.index and a.long_tail in c.index:
                spot = (c[a.long_tail] - c[a.short_tail]) * 100.0
                r["spot_curve_bp"] = float(spot)
                r.update({"pickup_" + k: x for k, x in pickups(spot, r["fwd_curve_bp"], r["strike_curve_bp"],
                                                               STRUCT[a.structure][2]).items()})
    for k, x in r.items():
        print(f"{k}: {x:.4f}" if isinstance(x, float) else f"{k}: {x}")


def selftest():
    bad = []

    def ok(name, cond, info=""):
        if not cond:
            bad.append(f"{name} {info}")

    # 1. Bachelier: ATMF closed form, parity, and quadrature of the payoff under N(F, sigma^2 T)
    p = bachelier("payer", 2.0, 2.0, 80.0, 1.0, 1.0)
    ok("atmf", abs(p - 80.0 * math.sqrt(1 / (2 * math.pi))) < 1e-9, p)
    pay, rec = bachelier("payer", 2.0, 2.3, 70.0, 0.5, 6.0), bachelier("receiver", 2.0, 2.3, 70.0, 0.5, 6.0)
    ok("parity", abs((pay - rec) - 6.0 * (2.0 - 2.3) * 100.0) < 1e-9, (pay, rec))
    z = np.linspace(-9, 9, 400001)
    s = 70.0 * math.sqrt(0.5)
    num = (getattr(np, "trapezoid", None) or np.trapz)(np.maximum(200.0 + s * z - 230.0, 0.0) * np.exp(-z * z / 2) / SQ2PI, z) * 6.0
    ok("quadrature", abs(num - pay) < 1e-4, (num, pay))
    # 1b. delta/vega against finite differences of the premium; receiver payoff; degenerate (zero-vol) limits
    h = 1e-4
    for kd in ("payer", "receiver"):
        nd = (bachelier(kd, 2.0 + h, 2.3, 70.0, 0.5) - bachelier(kd, 2.0 - h, 2.3, 70.0, 0.5)) / (2 * h * 100.0)
        ok("delta " + kd, abs(nd - delta(kd, 2.0, 2.3, 70.0, 0.5)) < 1e-6, nd)
    nv = (bachelier("payer", 2.0, 2.3, 70.001, 0.5) - bachelier("payer", 2.0, 2.3, 69.999, 0.5)) / 0.002
    ok("vega", abs(nv - vega(2.0, 2.3, 70.0, 0.5)) < 1e-6, nv)
    ok("zero-vol limit", abs(bachelier("payer", 2.3, 2.0, 0.0, 1.0) - 30.0) < 1e-12 and delta("receiver", 2.0, 2.3, 0.0, 1.0) == -1.0)
    ok("receiver payoff", np.allclose(package_payoff([("receiver", 3.0, 1)], [2.0, 3.0, 4.0]), [1.0, 0.0, 0.0]))
    # 2. Equal vols/annuities -> no shift, strike curve = forward curve
    r = zero_cost_conditional("bear-steepener", 2.0, 3.0, 90.0, 90.0, 1.9, 1.9, 1.0)
    ok("equal vols", abs(r["shift_bp"]) < 1e-9 and abs(r["vol_pickup_bp"]) < 1e-9, r)
    # 3. Zero cost really nets to zero, shifted leg is OTM, and pickup sign per structure (BofA: left vol rich)
    for st in STRUCT:
        r = zero_cost_conditional(st, 3.8, 4.0, 132.0, 110.0, 1.9, 7.8, 1.0)
        kind, _, side = STRUCT[st]
        K_S, K_L = r["strike_short_pct"], r["strike_long_pct"]
        pS = r["notional_short"] / 100.0 * bachelier(kind, 3.8, K_S, 132.0, 1.0, 1.9)
        pL = bachelier(kind, 4.0, K_L, 110.0, 1.0, 7.8)
        ok("zero cost " + st, abs(pS - pL) < 1e-6, (pS, pL))
        ok("short leg shifted " + st, r["expensive_leg"] == "S" and r["shift_bp"] > 1.0, r)
        ok("OTM direction " + st, (K_S > 3.8) if kind == "payer" else (K_S < 3.8), r)
        # short-tail vol rich: steepener picks up for bear steepener / bull flattener only
        gain = {"bear-steepener": 1, "bull-flattener": 1, "bear-flattener": -1, "bull-steepener": -1}[st]
        ok("pickup sign " + st, gain * r["vol_pickup_bp"] > 1.0, r["vol_pickup_bp"])
        ok("payoff consistent " + st, abs(r["strike_curve_bp"] - (K_L - K_S) * 100.0) < 1e-9)
    # 3b. skewed surface: shifted strike is re-volled and the package still nets to zero premium
    skew = lambda o: 132.0 + 0.1 * o
    r = zero_cost_conditional("bear-steepener", 3.8, 4.0, 132.0, 110.0, 1.9, 7.8, 1.0, vol_fn_S=skew)
    pS = r["notional_short"] / 100.0 * bachelier("payer", 3.8, r["strike_short_pct"], skew(r["shift_bp"]), 1.0, 1.9)
    ok("skew zero cost", abs(pS - bachelier("payer", 4.0, r["strike_long_pct"], 110.0, 1.0, 7.8)) < 1e-6 and r["shift_bp"] > 1.0, r)
    # 4. JPM EUR 3s20s example: strike shift ~23bp (printed), weighted ratio 0.39 / entry 53bp
    r = zero_cost_conditional("bear-steepener", -0.10, 1.10, 25.0, 63.4, 3.01, 17.9, 0.25)
    ok("JPM shift", r["expensive_leg"] == "L" and 17.0 < r["shift_bp"] < 26.0, r["shift_bp"])
    ok("JPM notional", abs(r["notional_short"] - 595.0) < 2.0, r["notional_short"])
    w = vol_weighted(25.0, 63.4, 3.01, 17.9, -0.10, 1.10)
    ok("JPM weighted", abs(w["weight"] - 0.39) < 0.01 and abs(w["entry_level_bp"] - 53.0) < 1.5, w)
    ok("implied directionality 61%", abs(w["implied_directionality"] - 0.61) < 0.01, w)
    # 5. Citi 1y 2s10s printed numbers (spot -102.3, fwd -23.3, strike -57.6): vol 34.3, total -44.7 (rounding 0.15)
    pu = pickups(-102.3, -23.3, -57.6, "steepener")
    ok("Citi pickups", abs(pu["curve"] + 78.9) < 0.15 and abs(pu["vol"] - 34.3) < 1e-9 and abs(pu["total"] + 44.7) < 0.15, pu)
    pu = pickups(18.1, 10.0, 3.1, "steepener")
    ok("Citi 1s2s", abs(pu["total"] - 15.0) < 0.1, pu)
    ok("flattener mirror", pickups(5, 3, 1, "flattener")["total"] == -pickups(5, 3, 1, "steepener")["total"])
    # 6. Bassman payer ladder: long 4.85, short 5.60, short 6.90 -> cap 0.75 at 5.60..6.90, zero at 7.65
    lad = [("payer", 4.85, 1), ("payer", 5.60, -1), ("payer", 6.90, -1)]
    pf = package_payoff(lad, [4.0, 5.6, 6.9, 7.65, 9.0])
    ok("ladder", np.allclose(pf, [0, 0.75, 0.75, 0.0, -1.35]), pf)
    # 7. Three-to-one rule (Bassman 2014: 82 * 1.97 / 56 = 2.88; 2010: 132/47 = 2.8)
    ok("3:1", abs(carry_to_premium(82 * 1.97, 56) - 2.88) < 0.01 and abs(carry_to_premium(132, 47) - 2.81) < 0.01)
    # 8. Spread vol / implied correlation round trip; limiting cases
    ok("spread vol", abs(spread_vol(80, 80, 1.0)) < 1e-9 and abs(spread_vol(60, 80, 0.0) - 100.0) < 1e-9)
    ok("implied corr", abs(implied_corr(60, 80, spread_vol(60, 80, 0.35)) - 0.35) < 1e-12)
    # 9. Break-even: carry -0.25bp/day, gamma 0.5 -> 1bp move; carry >= 0 -> 0
    ok("BE", abs(breakeven_move(-0.25, 0.5) - 1.0) < 1e-12 and breakeven_move(0.1, 0.5) == 0.0)
    # 10. Directionality: short yield = 0.7 * long yield + noise => curve beta on long ~ 0.3 = 1 - vol ratio
    rng = np.random.default_rng(7)
    yl = np.cumsum(rng.normal(0, 5, 4000))
    ys = 0.7 * yl + np.cumsum(rng.normal(0, 0.5, 4000))
    ok("directionality", abs(delivered_directionality(yl, ys) - 0.3) < 0.03, delivered_directionality(yl, ys))
    ok("directionality short history -> nan", math.isnan(delivered_directionality(yl[:10], ys[:10])))
    yl2, ys2 = yl.copy(), ys.copy()
    ys2[100] = np.nan
    ok("directionality NaN gap", abs(delivered_directionality(yl2, ys2) - 0.3) < 0.03)
    if bad:
        print("SELFTEST FAILED:\n  " + "\n  ".join(bad))
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("solve", help="zero-cost strike for a conditional curve trade from canonical vol_surface rows")
    s.add_argument("--vol-surface", required=True)
    s.add_argument("--curve-par")
    s.add_argument("--date", required=True)
    s.add_argument("--snap")
    s.add_argument("--index-id", required=True)
    s.add_argument("--expiry", required=True)
    s.add_argument("--short-tail", required=True)
    s.add_argument("--long-tail", required=True)
    s.add_argument("--structure", required=True, choices=sorted(STRUCT))
    s.add_argument("--freq", type=int, default=1, help="fixed-leg payments/yr for the flat-yield annuity (default 1)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "solve":
        return _cli_solve(a) or 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
