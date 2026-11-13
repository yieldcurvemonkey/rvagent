#!/usr/bin/env python3
"""Skew and tail-hedge tools in the normal (Bachelier) model. Units: bp for rates/strikes/vols, years for time.

Prices are per unit annuity (PV01 = 1), in bp of the forward rate; multiply by the annuity PV01 for currency.
Everything is expressed as a strike OFFSET from the ATM forward (F = 0), because Bachelier prices depend only on K - F.

CLI:
  python skew_tools.py --selftest
  python skew_tools.py grid --vol-surface vol_surface.csv [--date YYYY-MM-DD] [--otm auto|25|50|100]
      -> payer skew, receiver skew, RR, smile and costless-payer-ladder breakeven width per expiry x tenor.
         Input: canonical `vol_surface` table (columns date, snap, index_id, product, expiry, tenor,
         strike_offset_bp, nvol_bp). CSV or Parquet.
"""
from __future__ import annotations

import argparse
import math
import re
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

SQRT_2PI = math.sqrt(2.0 * math.pi)
_trapz = getattr(np, "trapezoid", None) or np.trapz


# ----------------------------------------------------------------------------- pricing
def bachelier(k_off, sigma_bp, t_years, w=+1):
    """Normal-model option price per unit annuity, bp. k_off = K - F (bp); w=+1 payer (call on rate), -1 receiver.

    price = w(F-K)*Phi(d) + s*phi(d), s = sigma*sqrt(T), d = w(F-K)/s.  Payer minus receiver = F - K (parity).
    """
    s = np.asarray(sigma_bp, float) * math.sqrt(t_years)
    m = -w * np.asarray(k_off, float)  # w*(F-K)
    d = m / s
    return m * norm.cdf(d) + s * norm.pdf(d)


def bachelier_vega(k_off, sigma_bp, t_years):
    """Vega per 1bp of normal vol, per unit annuity (same for payer and receiver): sqrt(T)*phi(d)."""
    s = sigma_bp * math.sqrt(t_years)
    return math.sqrt(t_years) * norm.pdf(np.asarray(k_off, float) / s)


def bachelier_delta(k_off, sigma_bp, t_years, w=+1):
    """Delta wrt the forward rate (per unit annuity): payer Phi(d), receiver -Phi(-d), d = (F-K)/s."""
    d = -np.asarray(k_off, float) / (sigma_bp * math.sqrt(t_years))
    return norm.cdf(d) if w > 0 else -norm.cdf(-d)


def lognormal_to_normal_atm(f_pct, lnvol_pct, t_years):
    """ATM lognormal vol (% of F) -> normal vol (bp), exact equivalence of ATM prices. Short expiry ~ F*sigma_LN.

    Black ATM = F*(2Phi(v/2)-1), v = sigma_LN*sqrt(T); Bachelier ATM = sigma_N*sqrt(T/(2pi)); F in %, result in bp.
    """
    v = lnvol_pct / 100.0 * math.sqrt(t_years)
    return 100.0 * f_pct * (2.0 * norm.cdf(v / 2.0) - 1.0) * SQRT_2PI / math.sqrt(t_years)


def breakeven_prob(be_width_bp, nvol_bp, t_years):
    """Risk-neutral probability of finishing beyond the far breakeven: 1 - Phi(BE / (sigma*sqrt(T)))."""
    z = be_width_bp / (nvol_bp * math.sqrt(t_years))
    return z, float(1.0 - norm.cdf(z))


# ----------------------------------------------------------------------------- structures
def structure_cost(strikes, weights, vol_fn, t_years, w=+1):
    """Net premium (bp per unit annuity) of sum(weights_i * option(strikes_i)); vol_fn(k_off)->normal vol (bp)."""
    return float(sum(wt * bachelier(k, vol_fn(k), t_years, w) for k, wt in zip(strikes, weights)))


def costless_gap(vol_fn, t_years, kind="ladder", w=+1, k0=0.0, max_gap=None):
    """Gap D (bp) making the structure free. Payer: strikes ride up from k0 (offset from ATMF); receiver: down.

    kind='ladder': (1,-1,-1) at k0, k0+D, k0+2D  -> far breakeven width = 3D from k0
    kind='1x2'   : (1,-2)    at k0, k0+D         -> far breakeven width = 2D from k0
    Returns D, or nan if no root inside max_gap (e.g. the vol grid does not reach that far).
    vol_fn may return nan outside its support; that makes the cost nan and the solve returns nan.
    """
    n, wts = (3, (1, -1, -1)) if kind == "ladder" else (2, (1, -2))
    sgn = 1.0 if w > 0 else -1.0
    hi = max_gap if max_gap is not None else 20.0 * max(float(vol_fn(k0)), 1.0) * math.sqrt(t_years)

    def f(d):
        return structure_cost([k0 + sgn * i * d for i in range(n)], wts, vol_fn, t_years, w)

    lo = 1e-6
    flo, fhi = f(lo), f(hi)
    if not (np.isfinite(flo) and np.isfinite(fhi)) or flo * fhi > 0:
        return float("nan")
    return float(brentq(f, lo, hi, xtol=1e-9))


def vega_neutral_straddle(n_rr, vega_payer, vega_receiver, vega_straddle):
    """Straddle notional that zeroes the vega of a long-payer / short-receiver risk reversal of notional n_rr.

    net = n_rr*(vega_payer - vega_receiver) + n_str*vega_straddle = 0  ->  n_str = -n_rr*(vp - vr)/vs.
    Positive result = buy straddle. Vegas per unit notional, same units.
    """
    return -n_rr * (vega_payer - vega_receiver) / vega_straddle


def swap_delta_hedge(n_payer, d_payer, n_receiver, d_receiver, n_straddle, d_straddle, dv01_swap):
    """Swap notional that zeroes rate-delta. Positive N_swap = PAY fixed (short duration).

    Deltas here are RATE deltas (d value / d rate, payer positive, receiver negative) - the opposite sign to the
    duration-convention DV01 used elsewhere (DV01 > 0 = long duration). Notionals are signed (short = negative).
    dv01_swap = rate-delta of a pay-fixed swap per unit notional (positive number).
    Returns N_swap = -(sum N_i*delta_i)/dv01_swap.
    """
    return -(n_payer * d_payer + n_receiver * d_receiver + n_straddle * d_straddle) / dv01_swap


# ----------------------------------------------------------------------------- skew metrics
def make_vol_fn(offsets, vols):
    """Linear interpolation of the smile in strike offset; nan outside the quoted range (no extrapolation)."""
    o = np.asarray(offsets, float)
    v = np.asarray(vols, float)
    i = np.argsort(o)
    o, v = o[i], v[i]

    def fn(k):
        k = float(k)
        return float(np.interp(k, o, v)) if o[0] <= k <= o[-1] else float("nan")

    return fn


def otm_distance(expiry_years, rule="auto"):
    """Citi-style OTM distance: 25bp out to 3m, 50bp for 6m-2y, 100bp for 3y+. A number overrides the rule."""
    if rule != "auto":
        return float(rule)
    return 25.0 if expiry_years <= 0.26 else (50.0 if expiry_years <= 2.01 else 100.0)


def tenor_years(s):
    m = re.fullmatch(r"(\d+)([DWMY])", str(s).strip().upper())
    if not m:
        raise ValueError(f"bad tenor {s!r}")
    return int(m.group(1)) * {"D": 1 / 365, "W": 7 / 365, "M": 1 / 12, "Y": 1}[m.group(2)]


def skew_row(offsets, vols, t_years, otm="auto", ladder=True):
    """One smile -> dict(atm, d, payer_skew, receiver_skew, rr, smile, be_width). RR = payer vol - receiver vol."""
    fn = make_vol_fn(offsets, vols)
    d = otm_distance(t_years, otm)
    atm, vp, vr = fn(0.0), fn(d), fn(-d)
    out = dict(atm=atm, d=d, payer_skew=vp - atm, receiver_skew=vr - atm, rr=vp - vr, smile=0.5 * (vp + vr) - atm)
    out["be_width"] = float("nan")
    if ladder and np.isfinite(atm):
        gap = costless_gap(fn, t_years, "ladder", +1, 0.0, max_gap=(max(offsets) / 2.0) if max(offsets) > 0 else None)
        out["be_width"] = 3.0 * gap
    return out


def skew_grid(vs: pd.DataFrame, otm="auto", ladder=True) -> pd.DataFrame:
    """Canonical vol_surface rows -> one skew row per (date, snap, index_id, product, expiry, fwd_start, tenor)."""
    keys = [c for c in ("date", "snap", "index_id", "product", "expiry", "fwd_start", "tenor") if c in vs.columns]
    rows = []
    for key, g in vs.groupby(keys, sort=True):
        g = g.dropna(subset=["nvol_bp"])
        if g["strike_offset_bp"].nunique() < 3 or 0.0 not in set(g["strike_offset_bp"]):
            continue
        r = skew_row(g["strike_offset_bp"], g["nvol_bp"], tenor_years(dict(zip(keys, key))["expiry"]), otm, ladder)
        rows.append({**dict(zip(keys, key)), **r})
    return pd.DataFrame(rows)


def ladder_residual_z(be_width, atm_vol, fwd, window=63):
    """Rolling z of the BE-width residual after regressing out ATM vol and forward level (no look-ahead).

    For each t >= window: OLS on rows [t-window, t) of be ~ 1 + atm + fwd, residual at t over the in-window residual sd.
    Non-finite rows (e.g. NaN BE widths where the strike grid was too short) are dropped from the window; z[t] is NaN
    if fewer than 80% of the window rows are usable. z[t] uses data up to close t: trade it no earlier than t+1.
    Default 63 = 3 months of business days (BofA reads the 3m z of the de-directionalised BE width).
    """
    y = np.asarray(be_width, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(atm_vol, float), np.asarray(fwd, float)])
    z = np.full(len(y), np.nan)
    for t in range(window, len(y)):
        Xw, yw = X[t - window:t], y[t - window:t]
        ok = np.isfinite(Xw).all(axis=1) & np.isfinite(yw)
        if ok.sum() < 0.8 * window or not (np.isfinite(X[t]).all() and np.isfinite(y[t])):
            continue
        Xw, yw = Xw[ok], yw[ok]
        beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
        sd = np.std(yw - Xw @ beta, ddof=3)  # 3 fitted parameters
        if sd > 0:
            z[t] = (y[t] - X[t] @ beta) / sd
    return z


# ----------------------------------------------------------------------------- selftest
def _quad_price(k_off, sigma, t, w):
    """Independent check: integrate the payoff against the normal density on a fine grid."""
    s = sigma * math.sqrt(t)
    x = np.linspace(-12 * s, 12 * s, 400001)  # terminal rate minus F
    pay = np.maximum(w * (x - k_off), 0.0)
    return float(_trapz(pay * norm.pdf(x / s) / s, x))


def selftest() -> int:
    ok = True

    def chk(name, cond, detail=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
        ok &= bool(cond)

    # 1. published numerical example: 5Y30Y payer, F=1.325%, K=1.5%, vol 52bp -> 38.16bp
    p = float(bachelier(17.5, 52.0, 5.0, +1))
    chk("Darbyshire 5Y30Y payer 38.16bp", abs(p - 38.16) < 0.05, f"{p:.3f}")
    # 2. parity payer - receiver = F - K
    pr, rc = float(bachelier(17.5, 52.0, 5.0, +1)), float(bachelier(17.5, 52.0, 5.0, -1))
    chk("put-call parity", abs((pr - rc) - (-17.5)) < 1e-9, f"{pr - rc:.6f}")
    # 3. ATM closed form
    chk("ATM = sigma*sqrt(T/2pi)", abs(float(bachelier(0, 80.0, 2.0)) - 80 * math.sqrt(2 / (2 * math.pi))) < 1e-9)
    # 4. independent quadrature
    for k, w in [(0, 1), (35, 1), (-35, -1), (80, 1)]:
        q, b = _quad_price(k, 90.0, 1.5, w), float(bachelier(k, 90.0, 1.5, w))
        chk(f"quadrature k={k} w={w}", abs(q - b) < 1e-3 * max(b, 1), f"{q:.4f} vs {b:.4f}")
    # 5. vega and delta vs finite differences
    h = 1e-4
    fd = (float(bachelier(25, 100 + h, 1.0)) - float(bachelier(25, 100 - h, 1.0))) / (2 * h)
    chk("vega finite-difference", abs(fd - float(bachelier_vega(25, 100.0, 1.0))) < 1e-6)
    fd = -(float(bachelier(25 + h, 100, 1.0)) - float(bachelier(25 - h, 100, 1.0))) / (2 * h)  # d/dF = -d/dK
    chk("payer delta finite-difference", abs(fd - float(bachelier_delta(25, 100.0, 1.0))) < 1e-6)
    fd = -(float(bachelier(25 + h, 100, 1.0, -1)) - float(bachelier(25 - h, 100, 1.0, -1))) / (2 * h)
    chk("receiver delta finite-difference (negative)", abs(fd - float(bachelier_delta(25, 100.0, 1.0, -1))) < 1e-6
        and fd < 0, f"{fd:.5f}")
    chk("payer delta - receiver delta = 1 (parity)",
        abs(float(bachelier_delta(40, 90.0, 2.0, 1) - bachelier_delta(40, 90.0, 2.0, -1)) - 1.0) < 1e-12)
    # 6. ATM lognormal -> normal: 15.68% at 2%, 1y -> ~31.33bp (Darbyshire 1Y10Y example)
    n = lognormal_to_normal_atm(2.0, 15.68, 1.0)
    chk("log->normal ATM 31.33bp", abs(n - 31.33) < 0.03, f"{n:.3f}")
    # 7. BE probability: 127bp BE vs 110bp 1y vol -> z 1.155, 12.4%
    z, pr_ = breakeven_prob(127.0, 110.0, 1.0)
    chk("BE z=1.155, p=12.4%", abs(z - 1.155) < 0.001 and abs(pr_ - 0.124) < 0.001, f"{z:.4f} {pr_:.4f}")
    # 8. costless ladder / 1x2 under a flat smile: cost ~0 at the root, BE width = 3D, 1x2 BE = 2D
    flat = lambda k: 110.0
    for kind, n_ in (("ladder", 3), ("1x2", 2)):
        d = costless_gap(flat, 1.0, kind)
        wts = (1, -1, -1) if kind == "ladder" else (1, -2)
        indep = sum(wt * _quad_price(i * d, 110.0, 1.0, +1) for i, wt in enumerate(wts))
        chk(f"costless {kind} cost=0 (independent quadrature)", abs(indep) < 1e-3, f"D={d:.2f}bp cost={indep:.2e}")
    # 9. skew richer in the wings -> wider costless gap (BofA: BE width widens as skew richens)
    d_flat = costless_gap(flat, 1.0, "ladder")
    rich = lambda k: 110.0 + 0.05 * max(k, 0.0)  # payer-side smile steepening, +5bp vol per 100bp OTM
    d_rich = costless_gap(rich, 1.0, "ladder")
    chk("richer payer skew widens ladder gap", d_rich > d_flat + 1.0, f"{d_flat:.1f} -> {d_rich:.1f}")
    # mirror: receiver ladder under a payer-skewed smile is tighter than payer ladder
    d_rcv = costless_gap(rich, 1.0, "ladder", w=-1)
    chk("payer-skewed smile: payer gap > receiver gap", d_rich > d_rcv, f"{d_rich:.1f} vs {d_rcv:.1f}")
    # 10. grid on a synthetic surface with KNOWN skew: vol = 100 + 0.04*k  (RR at +/-50 = 4bp)
    offs = np.arange(-300, 301, 25)
    vs = pd.DataFrame({"date": "2026-01-02", "snap": "eod", "index_id": "X", "product": "swaption", "expiry": "1Y",
                       "fwd_start": "0D", "tenor": "10Y", "strike_offset_bp": offs, "nvol_bp": 100 + 0.04 * offs})
    g = skew_grid(vs).iloc[0]
    chk("grid RR/skews known", abs(g.rr - 4.0) < 1e-9 and abs(g.payer_skew - 2.0) < 1e-9
        and abs(g.receiver_skew + 2.0) < 1e-9 and abs(g.smile) < 1e-9, f"d={g.d} rr={g.rr:.3f}")
    chk("grid BE width finite and > 0", np.isfinite(g.be_width) and g.be_width > 0, f"{g.be_width:.1f}")
    # BE width = 3 x costless gap (ladder strikes at 0, D, 2D; payoff dies at 3D); flat smile: D = 0.3407*sigma*sqrt(T)
    chk("BE width = 3 x gap (flat smile 0.3407 s sqrt T)",
        abs(skew_row([-300, 0, 300], [100, 100, 100], 1.0)["be_width"] - 3 * 0.34072 * 100) < 0.05)
    # 11. vega-neutral sizing: residual vega must vanish; symmetric strikes around ATMF need no straddle
    vp = float(bachelier_vega(50, 100, 0.25)); vr = float(bachelier_vega(-50, 100, 0.25))
    chk("symmetric RR needs no straddle", abs(vega_neutral_straddle(100, vp, vr, 2 * float(bachelier_vega(0, 100, .25)))) < 1e-12)
    vp2, vr2 = float(bachelier_vega(30, 100, 0.25)), float(bachelier_vega(-70, 100, 0.25))  # asymmetric
    vs_ = 2 * float(bachelier_vega(0, 100, 0.25))
    ns = vega_neutral_straddle(100, vp2, vr2, vs_)
    chk("vega neutral after sizing", abs(100 * (vp2 - vr2) + ns * vs_) < 1e-9 and ns != 0, f"n_str={ns:.2f}")
    # delta hedge: result offsets option deltas
    dp, dr, da = (float(bachelier_delta(50, 100, .25, 1)), float(bachelier_delta(-50, 100, .25, -1)),
                  float(bachelier_delta(0, 100, .25, 1) + bachelier_delta(0, 100, .25, -1)))
    ns2 = swap_delta_hedge(100, dp, -100, dr, ns, da, 1.0)
    chk("delta neutral after swap", abs(100 * dp - 100 * dr + ns * da + ns2 * 1.0) < 1e-9)
    # 12. residual z: synthetic BE = 20 + 0.5*atm + 0.1*fwd + noise, last point shocked +6 sd
    rng = np.random.default_rng(7)
    n_ = 400
    atm, fwd = 100 + np.cumsum(rng.normal(0, 1, n_)), 300 + np.cumsum(rng.normal(0, 3, n_))
    be = 20 + 0.5 * atm + 0.1 * fwd + rng.normal(0, 2.0, n_)
    be[-1] += 12.0
    zz = ladder_residual_z(be, atm, fwd, 63)
    chk("residual z flags +6sd shock", zz[-1] > 4.0 and abs(np.nanmean(zz[:-1])) < 0.2 and np.nanstd(zz[:-1]) < 1.3,
        f"z_last={zz[-1]:.2f} mean={np.nanmean(zz[:-1]):.2f} sd={np.nanstd(zz[:-1]):.2f}")
    # independent check of the last residual z (out-of-sample point, window excludes t) and truncation invariance
    t = n_ - 1
    Xi = np.column_stack([np.ones(63), atm[t - 63:t], fwd[t - 63:t]])
    b_, *_ = np.linalg.lstsq(Xi, be[t - 63:t], rcond=None)
    z_ref = (be[t] - np.array([1, atm[t], fwd[t]]) @ b_) / np.std(be[t - 63:t] - Xi @ b_, ddof=3)
    chk("residual z matches independent out-of-sample calc", abs(zz[-1] - z_ref) < 1e-9, f"{zz[-1]:.4f} vs {z_ref:.4f}")
    zt = ladder_residual_z(be[:300], atm[:300], fwd[:300], 63)
    chk("residual z has no look-ahead (truncation invariant)", np.allclose(zt[63:], zz[63:300], equal_nan=True))
    be_n = be.copy(); be_n[330:340] = np.nan  # a gap of NaN BE widths must not blank the whole window
    zn = ladder_residual_z(be_n, atm, fwd, 63)
    chk("residual z tolerates NaN gaps", np.isfinite(zn[345]) and np.isnan(zn[335]) and np.isfinite(zn[-1]))
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("grid", help="skew table from a canonical vol_surface file")
    g.add_argument("--vol-surface", required=True)
    g.add_argument("--date", default=None)
    g.add_argument("--otm", default="auto", help="auto (25/50/100bp by expiry) or a number of bp")
    g.add_argument("--no-ladder", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd != "grid":
        ap.print_help()
        return 2
    vs = pd.read_parquet(a.vol_surface) if a.vol_surface.endswith(".parquet") else pd.read_csv(a.vol_surface)
    if a.date:
        vs = vs[vs["date"].astype(str) == a.date]
    out = skew_grid(vs, a.otm, not a.no_ladder)
    print(out.round(2).to_string(index=False) if len(out) else "no complete smiles found (need >= 3 strikes incl. ATM)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
