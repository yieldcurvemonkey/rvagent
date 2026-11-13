"""Futures-vs-forward convexity adjustment (CA): Ho-Lee / Hull-White fair values, pack CA, CA-implied vol, gamma sizing.

Units: sigma in bp per year (normal vol), times in years, CA in bp.  Work in decimals internally (1bp = 1e-4).

Library:  ho_lee_ca_bp, hull_white_ca_bp, pack_model_ca_bp, implied_vol_bp, pack_ca_bp, par_from_forwards, par_from_dfs,
          gamma_ca_bp, tail_factor, screen
CLI:      python -I convexity_adj.py --selftest
          python -I convexity_adj.py --screen packs.csv [--form T1sq] [--window 63]
  packs.csv columns: date, pack_id, t1_first_years, ca_bp, sigma_cap_bp   (one row per date and pack; t1_first_years =
  ACT/365 years from `date` to the first contract's reference start; ca_bp = pack rate - matched forward swap, bp)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

BP = 1e-4
_trapz = getattr(np, "trapezoid", None) or np.trapz
FORMS = ("T1sq", "T1T2", "simple")
# T1sq   : sigma^2 * T1^2 / 2           Ho-Lee zero-accrual limit; reproduces the sell-side pack screens
# T1T2   : sigma^2 * T1 * T2 / 2        Hull textbook (continuously compounded forward rate)
# simple : sigma^2*(T2^2 - tau^2/3)/2   Ho-Lee, SR3-style compounded/simple rate, exact Gaussian (F -> 0)


def imm_date(year: int, month: int) -> date:
    """Third Wednesday of the month (IMM date)."""
    d = date(year, month, 1)
    first_wed = d + timedelta(days=(2 - d.weekday()) % 7)
    return first_wed + timedelta(days=14)


def t1_years(asof: date, ref_start: date) -> float:
    return (ref_start - asof).days / 365.0


def ho_lee_ca_bp(sigma_bp, T1, tau: float = 0.25, form: str = "T1sq"):
    """Futures rate minus forward rate in bp, one-factor normal Ho-Lee. Vectorised over sigma_bp / T1."""
    s, T1 = np.asarray(sigma_bp, float), np.asarray(T1, float)
    T2 = T1 + tau
    if form == "T1sq":
        w = T1 ** 2
    elif form == "T1T2":
        w = T1 * T2
    elif form == "simple":
        w = T2 ** 2 - tau ** 2 / 3.0
    else:
        raise ValueError(f"form must be one of {FORMS}")
    return 0.5 * s ** 2 * w * BP  # (s*BP)^2 /BP  = s^2 * BP


def _B(a, t):
    return t if a < 1e-5 else (1.0 - np.exp(-a * t)) / a


def hull_white_ca_bp(sigma_bp, a, T1, tau: float = 0.25, form: str = "simple", fwd: float = 0.0):
    """Hull-White 1F CA in bp (mean reversion a, 1/yr). a -> 0 recovers Ho-Lee.
    form='bsic'  : Hull continuous-compounding formula (-> sigma^2*T1*T2/2 as a->0)
    form='simple': simple-rate TERM futures (Euribor-style, fixed in advance), Henrard gamma: (exp(lnG)-1)(1+tau*fwd)/tau, fwd decimal.
    At a=0 this is Citi's printed form (Fwd+1/D)*[exp(s^2*T*D*(D+T/2))-1]. The compounded-in-arrears SR3 payoff adds s^2*tau^2/3
    (see ho_lee_ca_bp form='simple'); that term is < 0.1bp for packs, so the two are interchangeable at pack level."""
    s = np.asarray(sigma_bp, float) * BP
    T1 = np.asarray(T1, float)
    T2 = T1 + tau
    if form == "bsic":
        if a < 1e-5:
            return 0.5 * s ** 2 * T1 * T2 / BP
        b = _B(a, tau)
        return b / tau * (b * (1 - np.exp(-2 * a * T1)) + 2 * a * _B(a, T1) ** 2) * s ** 2 / (4 * a) / BP
    if form != "simple":
        raise ValueError("form must be 'simple' or 'bsic'")
    if a < 1e-5:
        lng = s ** 2 * tau * T1 * (T1 / 2 + tau)
    else:
        lng = s ** 2 * _B(a, tau) / a * ((1 - np.exp(-a * T1)) / a
                                         - (np.exp(-a * tau) - np.exp(-a * (T1 + T2))) / (2 * a))
    return (np.expm1(lng)) * (1 + tau * fwd) / tau / BP


def pack_model_ca_bp(sigma_bp, t1_first, n: int = 4, step: float = 0.25, form: str = "T1sq", a: float = 0.0):
    """Model CA of an n-contract pack = mean of per-contract CAs (contract i starts t1_first + i*step)."""
    t = np.asarray(t1_first, float)[..., None] + step * np.arange(n)
    if a > 0:
        return np.mean(hull_white_ca_bp(np.asarray(sigma_bp, float)[..., None], a, t, step), axis=-1)
    return np.mean(ho_lee_ca_bp(np.asarray(sigma_bp, float)[..., None], t, step, form), axis=-1)


def implied_vol_bp(ca_bp, t1_first, n: int = 4, step: float = 0.25, form: str = "T1sq", a: float = 0.0):
    """CA-implied normal vol: the sigma at which the model pack CA equals the observed CA. Scalar inputs.
    CA scales as sigma^2 for every model here, so inversion is closed form: sigma = sqrt(CA / CA(1bp))."""
    if ca_bp < 0:
        return float("nan")  # negative CA violates no-arbitrage sign: stale data, do not invert
    unit = float(pack_model_ca_bp(1.0, t1_first, n, step, form, a))  # CA per (1bp vol)^2, scales as sigma^2
    return float(np.sqrt(ca_bp / unit))


def pack_ca_bp(pack_rates_pct, matched_par_pct) -> float:
    """CA = pack rate (mean of the leg rates = 100 - price) minus the matched quarterly/quarterly forward swap par rate, bp."""
    return 100.0 * (float(np.mean(pack_rates_pct)) - float(matched_par_pct))


def par_from_forwards(fwd_pct, dcf=0.25):
    """Par rate of a swap whose fixed and floating legs both pay on the same grid: DF-weighted mean of the forwards."""
    f = np.asarray(fwd_pct, float) / 100.0
    d = np.broadcast_to(np.asarray(dcf, float), f.shape)
    df = np.cumprod(1.0 / (1.0 + f * d))
    return 100.0 * float((df * f * d).sum() / (df * d).sum())


def par_from_dfs(df_nodes, dcf=0.25):
    """Matched quarterly/quarterly OIS forward-swap par rate (%) from discount factors at the window start and the n quarter
    ends: df_nodes = [DF(T0), DF(T1), ..., DF(Tn)]; par = (DF(T0) - DF(Tn)) / sum(d_i * DF(Ti)). Use this when the stored
    par curve has annual fixed legs (an annual leg adds ~3q^2/8 compounding bias that is NOT convexity)."""
    d = np.asarray(df_nodes, float)
    return 100.0 * float((d[0] - d[-1]) / (np.sum(dcf * d[1:])))


def gamma_ca_bp(gamma_ccy_per_bp2, sigma_bp, horizon_years, dv01_ccy_per_bp, decay_to_zero_years=None, n=2000):
    """Expected hedging P&L of a delta-hedged IRS-vs-futures package, in bp of futures: integral of 0.5*Gamma(t)*sigma^2 dt / DV01.
    gamma_ccy_per_bp2: delta change per 1bp (ccy/bp per bp). decay_to_zero_years: gamma falls linearly to 0 at that time
    (None = constant gamma, which overstates)."""
    if decay_to_zero_years is not None and decay_to_zero_years <= 0:
        raise ValueError("decay_to_zero_years must be > 0")
    t = np.linspace(0.0, horizon_years, n)
    g = np.full_like(t, gamma_ccy_per_bp2) if decay_to_zero_years is None else \
        gamma_ccy_per_bp2 * np.clip(1 - t / decay_to_zero_years, 0, None)
    return float(0.5 * sigma_bp ** 2 * _trapz(g, t) / dv01_ccy_per_bp)


def tail_factor(r0_pct, days_in_hedge_to_expiry, basis=360.0):
    """Futures hedge tail: N_tailed = N / (1 + R0 * D / basis). Returns the multiplier."""
    return 1.0 / (1.0 + r0_pct / 100.0 * days_in_hedge_to_expiry / basis)


def screen(df: pd.DataFrame, form: str = "T1sq", window: int = 63) -> pd.DataFrame:
    """Per-pack CA monitor: model CA (Ho-Lee on cap vol), CA - model, CA-implied vol / cap vol, z-scores over `window` rows."""
    out = df.sort_values(["pack_id", "date"]).copy()
    out["model_bp"] = [float(pack_model_ca_bp(s, t, form=form)) for s, t in zip(out.sigma_cap_bp, out.t1_first_years)]
    out["vs_model_bp"] = out.ca_bp - out.model_bp
    out["implied_vol_bp"] = [implied_vol_bp(c, t, form=form) for c, t in zip(out.ca_bp, out.t1_first_years)]
    out["impl_over_cap"] = out.implied_vol_bp / out.sigma_cap_bp
    g = out.groupby("pack_id")
    for col in ("ca_bp", "vs_model_bp"):
        m, s = g[col].transform(lambda x: x.rolling(window).mean()), g[col].transform(lambda x: x.rolling(window).std())
        out[f"{col}_z"] = (out[col] - m) / s
    return out


# ----------------------------------------------------------------------------------------------------- selftest
def _selftest() -> int:
    from scipy.integrate import quad
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.6g} want {want:.6g} (tol {tol:g})")
        if not ok:
            fails.append(name)

    # 1. Hull textbook: sigma=1.2%, T1=8, T2=8.25 -> 0.5*0.012^2*8*8.25 = 47.52bp
    check("Hull Ho-Lee 47.52bp", float(ho_lee_ca_bp(120.0, 8.0, 0.25, "T1T2")), 47.52, 1e-9)
    # 2. exact Gaussian check of the 'simple' (compounded) Ho-Lee form by independent numerical covariance:
    #    ln E_B[exp(Y)] - ln fwd ratio = Cov(X_Te, Y), Y = int_Ts^Te r, X_T = int_0^T r; rate CA = Cov/tau for F->0, small sigma
    s, Ts, tau = 1e-4 * 100.0, 3.0, 0.25
    Te = Ts + tau
    cov = quad(lambda u: (Te - u) * ((Te - u) - max(Ts - u, 0.0)), 0, Ts, points=[Ts])[0] \
        + quad(lambda u: (Te - u) ** 2, Ts, Te)[0]
    check("simple Ho-Lee vs numerical Gaussian covariance (bp)", float(ho_lee_ca_bp(100.0, Ts, tau, "simple")),
          s ** 2 * cov / tau / BP, 1e-9)
    # 3. Hull-White: a->0 limit recovers Ho-Lee in both forms
    check("HW bsic a=1e-4 ~ T1T2", float(hull_white_ca_bp(100, 1e-4, 3.0, 0.25, "bsic")), float(ho_lee_ca_bp(100, 3.0, 0.25, "T1T2")), 0.01)
    check("HW simple a->0 = Ho-Lee exact", float(hull_white_ca_bp(100, 1e-4, 3.0, 0.25, "simple")),
          float(hull_white_ca_bp(100, 0.0, 3.0, 0.25, "simple")), 0.01)
    # HW 'simple' integrates to T1 only (term-rate futures); Ho-Lee 'simple' is compounded-in-arrears: gap = s^2*tau^2/3
    check("Ho-Lee simple - HW simple(a=0) = s^2 tau^2/3 (bp)", float(ho_lee_ca_bp(100, 3.0, 0.25, "simple"))
          - float(hull_white_ca_bp(100, 0.0, 3.0, 0.25, "simple")), 100.0 ** 2 * 0.25 ** 2 / 3 * BP, 1e-3)
    # published anchors: Ametrano & Bianchetti, EUR 11-Dec-2012, HW1F a=3%, sigma=35.26bp: Z4 .30 Z5 .60 Z6 1.00 U7 1.36bp
    a12 = date(2012, 12, 11)
    for lab, (yy, mm), want in (("Z4", (2014, 12), 0.30), ("Z6", (2016, 12), 1.00), ("U7", (2017, 9), 1.36)):
        check(f"HW simple EUR {lab} (published {want})", float(hull_white_ca_bp(35.26, 0.03, t1_years(a12, imm_date(yy, mm)))), want, 0.01)
    check("HW bsic EUR U7 differs from published (discriminates form)", float(hull_white_ca_bp(35.26, 0.03, t1_years(a12, imm_date(2017, 9)), form="bsic") < 1.33), 1.0, 0)
    # HW 'bsic' (continuously compounded forward) vs independent HJM drift integral: E[f(T1,u)] - f(0,u) averaged over (T1,T2)
    for T1b in (3.0, 5.0):
        sb, ab = 100.0 * BP, 0.03
        Bf = lambda x: (1 - np.exp(-ab * x)) / ab
        drift = lambda u: quad(lambda t: sb * sb * np.exp(-ab * (u - t)) * Bf(u - t), 0, T1b)[0]
        check(f"HW bsic closed form vs HJM integral T1={T1b:g} (bp)", float(hull_white_ca_bp(100.0, ab, T1b, 0.25, "bsic")),
              quad(drift, T1b, T1b + 0.25)[0] / 0.25 / BP, 1e-6)
    # Tuckman-Serrat Table 12.12, sigma=80bp, term-rate row: 0.4 / 1.4 / 8.4 / 32.8 at t = 1/2/5/10
    for tt, want in ((1, 0.4), (2, 1.4), (5, 8.4), (10, 32.8)):
        check(f"Tuckman T1T2 t={tt}", float(ho_lee_ca_bp(80.0, tt, 0.25, "T1T2")), want, 0.05)
    # 4. HW closed form vs numerical integral of Henrard's gamma exponent
    a, s2, T1, tau = 0.05, 0.01, 4.0, 0.25
    T2 = T1 + tau
    lng = quad(lambda u: s2 * _B(a, T2 - u) * s2 * np.exp(-a * (T1 - u)) * _B(a, tau), 0, T1)[0]
    check("HW simple closed form vs quad (bp)", float(hull_white_ca_bp(100.0, a, T1, tau, "simple")),
          np.expm1(lng) / tau / BP, 1e-6)
    # 5. mean reversion lowers the CA (same form: HW simple vs its own a=0 limit)
    if not (hull_white_ca_bp(100, 0.05, 5.0) < hull_white_ca_bp(100, 0.0, 5.0)):
        fails.append("HW<HoLee")
        print("FAIL HW < Ho-Lee")
    # 6. Published reproduction: Blues H6-Z6 on 16-Feb-2023, CA 13.09bp -> CA-implied vol 147.6bp (published)
    asof = date(2023, 2, 16)
    t1 = t1_years(asof, imm_date(2026, 3))
    check("implied vol Blues H6-Z6 (published 147.6)", implied_vol_bp(13.09, t1, form="T1sq"), 147.6, 0.8)
    #    and Golds H7-Z7: CA 21.24 -> 146.1
    check("implied vol Golds H7-Z7 (published 146.1)", implied_vol_bp(21.24, t1_years(asof, imm_date(2027, 3))), 146.1, 0.8)
    # 7. implied-vol / model round trip
    v = implied_vol_bp(9.44, t1)
    check("round trip", float(pack_model_ca_bp(v, t1)), 9.44, 1e-9)
    # 8. gamma sizing example: 0.5*(140*sqrt(2))^2*12.2 = 239,120 USD / 25,000 = 9.57bp (constant gamma)
    check("gamma constant 9.57bp", gamma_ca_bp(12.2, 140.0, 2.0, 25000.0), 0.5 * 140 ** 2 * 2 * 12.2 / 25000, 1e-3)
    check("gamma decay lowers CA", float(gamma_ca_bp(12.2, 140.0, 2.0, 25000.0, 2.35) < 9.0), 1.0, 0)
    # 9. par vs mean forwards: exact on a flat curve; DF tilt on a sloped curve is small and negative here
    check("flat curve par = mean fwd", par_from_forwards([3.0] * 4), 3.0, 1e-9)
    check("sloped control residual (bp)", 100 * (3.5 - par_from_forwards([3.0, 3.33, 3.67, 4.0])), 0.38, 0.02)
    # 9b. par from DFs agrees with par from the forwards those DFs imply
    f = np.array([3.0, 3.33, 3.67, 4.0]) / 100
    dfs = np.concatenate([[1.0], np.cumprod(1 / (1 + f * 0.25))])
    check("par_from_dfs = par_from_forwards", par_from_dfs(dfs), par_from_forwards(f * 100), 1e-9)
    # 10. tail: 10.89 contracts at R0=0.65%, 250 days -> 10.84 (Tuckman-Serrat 2022 Table 12.8)
    check("tail 10.84", 10.89 * tail_factor(0.65, 250), 10.84, 0.005)
    # 11. screen on synthetic data with a known planted dislocation
    d = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=200).repeat(1), "pack_id": "B", "t1_first_years": 3.0,
                      "sigma_cap_bp": 100.0})
    d["ca_bp"] = float(pack_model_ca_bp(100.0, 3.0)) + np.where(np.arange(200) == 199, 4.0, 0.0)
    r = screen(d)
    check("screen planted +4bp vs model", float(r.vs_model_bp.iloc[-1]), 4.0, 1e-9)
    # 12. pack CA sign/units: pack mean 3.25%, matched par 3.20% -> +5bp (futures above forward); negative CA is not inverted
    check("pack_ca_bp +5bp", pack_ca_bp([3.10, 3.20, 3.30, 3.40], 3.20), 5.0, 1e-9)
    check("implied_vol_bp negative CA -> NaN", float(np.isnan(implied_vol_bp(-0.5, 3.0))), 1.0, 0)
    # 13. rolling z-score on a ramp 0..199: last value vs its 63-row window (ddof=1 std) = 31/sqrt(63*64/12)
    ramp = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=200), "pack_id": "B", "t1_first_years": 3.0,
                         "sigma_cap_bp": 100.0, "ca_bp": np.arange(200, dtype=float) + 5.0})
    check("screen 63d z of ramp", float(screen(ramp).ca_bp_z.iloc[-1]), 31 / np.sqrt(63 * 64 / 12), 1e-9)
    check("screen short history -> NaN z", float(np.isnan(screen(ramp.head(10)).ca_bp_z.iloc[-1])), 1.0, 0)
    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "PASSED")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--screen", help="CSV/Parquet of pack CA observations (see module doc)")
    ap.add_argument("--form", default="T1sq", choices=FORMS)
    ap.add_argument("--window", type=int, default=63)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.screen:
        df = pd.read_parquet(a.screen) if a.screen.endswith(".parquet") else pd.read_csv(a.screen, parse_dates=["date"])
        print(screen(df, a.form, a.window).tail(20).to_string(index=False))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
