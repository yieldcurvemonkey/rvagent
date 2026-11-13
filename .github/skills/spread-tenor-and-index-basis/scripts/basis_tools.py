"""Tenor / index basis tools: sign conversions, RFR compounding, basis-swap fair spread and DV01, monitor.

Conventions (same as SKILL.md)
  * Basis = spread in bp added to leg_a against leg_b flat (canonical `basis_swaps.spread_bp`).
  * Realised overnight basis = secured minus unsecured, e.g. SOFR - EFFR, in bp (positive = tighter funding).
  * Futures price spread (1M SOFR price - 30d FF price) = FF - SOFR in rate terms: OPPOSITE sign to the realised basis.
  * Basis DV01 is the PV change per +1bp in the MARKET spread, for the party who RECEIVES leg_a + contract spread.
    It is negative (that party loses when the market spread widens): dPV/ds = -N * annuity(leg_a) * 1e-4.

Usage
  python basis_tools.py --basis basis_swaps.csv [--basis-type tenor] [--snap eod_ldn] [--window 252] [--out ranked.csv]
  python basis_tools.py --selftest
Input table `basis_swaps`: date, snap, basis_type, ccy, leg_a, leg_b, start, tenor, spread_bp (csv or parquet).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- sign conversions
def realised_from_futures_prices(price_a, price_b):
    """Realised basis in bp = rate_a - rate_b from two futures prices (price = 100 - rate).

    price_a = 1M SOFR future, price_b = 30-day FF future (same month) gives SOFR - EFFR in bp.
    (100-rate_a) - (100-rate_b) = rate_b - rate_a, so the PRICE spread a-b is the negative of the realised basis.
    """
    return (np.asarray(price_b, float) - np.asarray(price_a, float)) * 100.0


# ---------------------------------------------------------------- compounding
def compound_period_rate(rates_pct, ndays, year_basis):
    """Annualised compounded rate (pct) over the period: [prod(1 + r_i*n_i/B) - 1] * B / sum(n_i).

    rates_pct: daily fixings applied; ndays: calendar days each fixing applies (3 for a Friday fixing).
    year_basis B is REQUIRED: 360 for SOFR/estr/SARON/SWESTR (ACT/360), 365 for SONIA/TONA/CORRA/AONIA/NOWA (ACT/365F).
    """
    r = np.asarray(rates_pct, float) / 100.0
    n = np.asarray(ndays, float)
    return (np.prod(1.0 + r * n / year_basis) - 1.0) * year_basis / n.sum() * 100.0


# ---------------------------------------------------------------- basis swap pricing
def sbs_mid_spread_bp(fwd_a_pct, dcf_a, df_a, fwd_b_pct, dcf_b, df_b):
    """Fair (par) spread in bp on leg a, vs leg b flat: PV = 0.

    Party receiving (leg_a + Z) and paying leg_b:  PV = sum d_a (r_a + Z) v_a - sum d_b r_b v_b = 0
    => Z = (sum d_b r_b v_b - sum d_a r_a v_a) / sum d_a v_a. Positive when leg b's index is the higher one.
    fwd_*: simple forward rate per period (pct), dcf_*: accrual fractions, df_*: discount factors at payment.
    Both legs must be projected off their own curves; this function just prices given forwards.
    """
    ra, da, va = (np.asarray(x, float) for x in (fwd_a_pct, dcf_a, df_a))
    rb, db, vb = (np.asarray(x, float) for x in (fwd_b_pct, dcf_b, df_b))
    num = (db * rb * vb).sum() - (da * ra * va).sum()
    return num / (da * va).sum() * 100.0  # pct -> bp


def sbs_pv(z_contract_bp, fwd_a_pct, dcf_a, df_a, fwd_b_pct, dcf_b, df_b, notional=1.0):
    """PV to the receiver of (leg_a + z_contract) and payer of leg_b (spread-receiver)."""
    ra, da, va = (np.asarray(x, float) for x in (fwd_a_pct, dcf_a, df_a))
    rb, db, vb = (np.asarray(x, float) for x in (fwd_b_pct, dcf_b, df_b))
    leg_a = (da * (ra / 100.0 + z_contract_bp / 1e4) * va).sum()
    leg_b = (db * rb / 100.0 * vb).sum()
    return notional * (leg_a - leg_b)


def basis_dv01(dcf_a, df_a, notional=1.0):
    """PV change per +1bp of the MARKET spread for the spread-receiver: -N * sum(d_a v_a) * 1e-4 (negative)."""
    return -notional * float((np.asarray(dcf_a, float) * np.asarray(df_a, float)).sum()) * 1e-4


def convert_spread_bp(z_bp, annuity_from, annuity_to):
    """MAGNITUDE of the equivalent spread on the other leg: same PV needs |z_from|*A_from = |z_to|*A_to.

    The sign flips when the spread moves to the other leg: spread on leg_a of z == spread on leg_b of -z*A_a/A_b.
    """
    return z_bp * annuity_from / annuity_to


def rfr_ibor_two_curve(c_pct, x_bp, df_q, acc_q, df_ann, acc_ann):
    """Identity c*sum(acc_ann*d) + d_T = 1 + x*sum(acc_q*d), d = RFR discount factors (Tuckman & Serrat A13.2).

    c: fixed rate of an annual-fixed vs quarterly-IBOR swap (pct); x: RFR+x vs IBOR basis (bp).
    Returns (lhs, rhs, x_solved_bp). x_solved is the basis implied by c; lhs == rhs when x == x_solved.
    """
    df_q, acc_q = np.asarray(df_q, float), np.asarray(acc_q, float)
    df_ann, acc_ann = np.asarray(df_ann, float), np.asarray(acc_ann, float)
    lhs = c_pct / 100.0 * (acc_ann * df_ann).sum() + df_q[-1]
    rhs = 1.0 + x_bp / 1e4 * (acc_q * df_q).sum()
    x_solved = (lhs - 1.0) / (acc_q * df_q).sum() * 1e4
    return lhs, rhs, x_solved


# ---------------------------------------------------------------- statistics
def ar1_half_life(x):
    """Half-life (in observations) from AR(1) on levels; nan if not mean-reverting (phi outside (0,1)).

    OLS phi is biased low in short samples (~250 obs), so the half-life is biased short; treat as indicative.
    """
    x = np.asarray(pd.Series(x).dropna(), float)
    if len(x) < 20:
        return np.nan
    y, z = x[1:], x[:-1]
    zc = z - z.mean()
    if (zc**2).sum() == 0:
        return np.nan
    phi = float((zc * (y - y.mean())).sum() / (zc**2).sum())
    return float(-np.log(2.0) / np.log(phi)) if 0.0 < phi < 1.0 else np.nan


def residual_vs_driver(y, x, window=252):
    """Fit y = a + b*x on the window BEFORE the last point; return beta, last residual, residual sigma, z.

    Positive residual = basis wide vs the driver. Sigma is the in-sample residual std (ddof=2). Series are aligned on their
    index (dates) when both are pandas Series, by position for arrays. Levels regression: check residual stationarity.
    """
    d = pd.concat([pd.Series(y), pd.Series(x)], axis=1).dropna()
    h, last = d.iloc[-window - 1:-1], d.iloc[-1]
    if len(h) < 20:
        return {"beta": np.nan, "resid": np.nan, "sigma": np.nan, "z": np.nan}
    b, a = np.polyfit(h.iloc[:, 1].to_numpy(), h.iloc[:, 0].to_numpy(), 1)
    res = h.iloc[:, 0].to_numpy() - (a + b * h.iloc[:, 1].to_numpy())
    sig = float(res.std(ddof=2))
    r = float(last.iloc[0] - (a + b * last.iloc[1]))
    return {"beta": float(b), "resid": r, "sigma": sig, "z": r / sig if sig > 0 else np.nan}


def monitor(basis: pd.DataFrame, window=252, basis_type=None, snap=None):
    """Rank every basis series by |z| of the latest level vs the trailing window BEFORE it (latest point excluded
    from mean/sd/percentile/half-life, so a jump does not dilute its own z). One snap per series."""
    b = basis.copy()
    b["date"] = pd.to_datetime(b["date"])
    if basis_type:
        b = b[b["basis_type"] == basis_type]
    if snap:
        b = b[b["snap"] == snap]
    keys = ["basis_type", "ccy", "leg_a", "leg_b", "start", "tenor"]
    rows = []
    for k, g in b.groupby(keys):
        if g["snap"].nunique() > 1:
            raise ValueError(f"mixed snaps in series {k}: pass --snap")
        s = g.sort_values("date").set_index("date")["spread_bp"].dropna()
        s = s[~s.index.duplicated(keep="last")]
        h = s.iloc[-window - 1:-1]
        if len(h) < 20:
            continue
        sd = h.std(ddof=1)
        rows.append(dict(zip(keys, k)) | {
            "date": s.index[-1].date(), "n": len(h), "level_bp": s.iloc[-1],
            "chg_5d_bp": s.iloc[-1] - s.iloc[-6] if len(s) > 5 else np.nan,
            "mean_bp": h.mean(), "sd_bp": sd, "z": (s.iloc[-1] - h.mean()) / sd if sd > 0 else np.nan,
            "pctile": float((h <= s.iloc[-1]).mean() * 100.0), "half_life_obs": ar1_half_life(h)})
    out = pd.DataFrame(rows)
    return out.reindex(out["z"].abs().sort_values(ascending=False).index) if len(out) else out


# ---------------------------------------------------------------- selftest
def _selftest():
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name, info)
        ok &= bool(cond)

    # 1. futures price spread has the opposite sign to the realised basis (SOFR 4.00, FF 3.90 -> +10bp realised)
    sr1, zq = 100 - 4.00, 100 - 3.90
    check("futures sign flip", abs(realised_from_futures_prices(sr1, zq) - 10.0) < 1e-9
          and abs((sr1 - zq) * 100 + 10.0) < 1e-9)
    # 2. compounding: published worked examples (Thu 2.00, Fri 2.10 x3 days, Mon 2.15 -> 2.0902%; 12/13/14 -> 13.0046%)
    c1 = compound_period_rate([2.0, 2.1, 2.15], [1, 3, 1], 365.0)
    c2 = compound_period_rate([12, 13, 14], [1, 1, 1], 365.0)
    c3 = compound_period_rate([5.0] * 90, [1] * 90, 360.0)  # ACT/360 constant 5% over a quarter: gap ~ r^2*T/2 = 3.1bp
    check("compounding", abs(c1 - 2.0902) < 5e-4 and abs(c2 - 13.0046) < 5e-4 and abs(c3 - 5.0310) < 5e-4,
          f"{c1:.4f} {c2:.4f} {c3:.4f}")
    # 3. flat-curve 3s6s: 3M fwd 2.00, 6M fwd 2.10, 5y, DF = 1 -> 10bp exactly; spread on 6M leg is the same on flat DFs
    na, nb = 20, 10
    z = sbs_mid_spread_bp([2.0] * na, [0.25] * na, [1.0] * na, [2.1] * nb, [0.5] * nb, [1.0] * nb)
    check("sbs mid flat", abs(z - 10.0) < 1e-9, f"{z:.6f}")
    # 4. non-flat DFs: PV at the mid spread is zero; DV01 sign by repricing (bump leg_b index +1bp -> PV falls by |DV01|)
    ta, tb = np.arange(1, na + 1) * 0.25, np.arange(1, nb + 1) * 0.5
    dfa, dfb = np.exp(-0.03 * ta), np.exp(-0.03 * tb)
    args = ([2.0] * na, [0.25] * na, dfa, [2.1] * nb, [0.5] * nb, dfb)
    zm = sbs_mid_spread_bp(*args)
    pv0 = sbs_pv(zm, *args, notional=1e8)
    args_up = ([2.0] * na, [0.25] * na, dfa, [2.11] * nb, [0.5] * nb, dfb)
    pv1 = sbs_pv(zm, *args_up, notional=1e8)
    z_up = sbs_mid_spread_bp(*args_up)
    dv = basis_dv01([0.25] * na, dfa, 1e8)
    check("sbs pv at mid = 0", abs(pv0) < 1e-6, f"{pv0:.2e}")
    check("basis dv01 sign and size", dv < 0 and abs((pv1 - pv0) - dv * (z_up - zm)) < 1e-3 * abs(dv),
          f"dPV={pv1 - pv0:.1f} vs dv01*dz={dv * (z_up - zm):.1f} (dv01={dv:.1f}/bp)")
    check("flat annuity dv01 = -50000/bp", abs(basis_dv01([0.25] * 20, [1.0] * 20, 1e8) + 50000.0) < 1e-6)
    check("spread conversion", abs(convert_spread_bp(10.0, 4.0, 5.0) - 8.0) < 1e-12)
    # 5. EUR eSTR vs 3m Euribor, 2y, published discount factors: c = 0.078% -> x ~ 13.8bp, both legs ~ 100.28
    dq = [1.0014099, 1.0028134, 1.0038902, 1.0044606, 1.0042784, 1.0035455, 1.0024888, 1.0012201]
    acc = 365.0 / 360.0
    lhs, rhs, xs = rfr_ibor_two_curve(0.078, 13.8, dq, [acc / 4] * 8, [dq[3], dq[7]], [acc] * 2)
    check("two-curve identity (published case)", abs(xs - 13.8) < 0.3 and abs(lhs * 100 - 100.281) < 0.01
          and abs(rhs * 100 - 100.281) < 0.01, f"x={xs:.2f}bp lhs={lhs * 100:.3f} rhs={rhs * 100:.3f}")
    # 6. AR(1) half-life, phi = 0.9 -> ln2/-ln0.9 = 6.58
    rng = np.random.default_rng(7)
    e = rng.normal(size=40000)
    x = np.zeros_like(e)
    for i in range(1, len(e)):
        x[i] = 0.9 * x[i - 1] + e[i]
    hl = ar1_half_life(x)
    check("half-life", abs(hl - 6.58) / 6.58 < 0.1, f"{hl:.2f}")
    # 7. residual vs driver: y = 3x + 1 +- 0.1, last point 1.0 above the line
    xs_ = np.linspace(0, 5, 300)
    ys_ = 3 * xs_ + 1 + 0.1 * np.where(np.arange(300) % 2 == 0, 1, -1)
    ys_[-1] += 1.0
    r = residual_vs_driver(ys_, xs_, window=250)
    check("residual vs driver", abs(r["beta"] - 3) < 0.05 and abs(r["resid"] - 1.0) < 0.2 and r["z"] > 5, str(r))
    # last point must not enter its own fit: short window, big outlier at the high-leverage end
    ys2 = 3 * xs_ + 1 + 0.1 * np.where(np.arange(300) % 2 == 0, 1, -1)
    ys2[-1] += 5.0
    r2 = residual_vs_driver(ys2, xs_, window=30)
    check("residual excludes last point", abs(r2["resid"] - 5.0) < 0.2, str(r2))
    # 8. monitor: constant-level series plus one jump has large positive z, and mixed snaps are rejected
    dates = pd.bdate_range("2025-01-01", periods=120)
    lv = np.r_[np.tile([5.0, 5.2], 59), 5.0, 9.0]
    df = pd.DataFrame({"date": dates, "snap": "eod_ldn", "basis_type": "tenor", "ccy": "EUR", "leg_a": "EUR-EURIBOR-3M",
                       "leg_b": "EUR-EURIBOR-6M", "start": "0D", "tenor": "5Y", "spread_bp": lv})
    m = monitor(df)
    # baseline = 119 alternating 5.0/5.2 obs (mean 5.1, sd 0.1), latest 9.0 -> z ~ 39 (a baseline incl. the jump gives ~10)
    check("monitor z", len(m) == 1 and 30 < m["z"].iloc[0] < 45, str(m[["level_bp", "z"]].to_dict("records")))
    df2 = pd.concat([df, df.assign(snap="settle")])
    try:
        monitor(df2)
        check("monitor rejects mixed snaps", False)
    except ValueError:
        check("monitor rejects mixed snaps", True)
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--basis", help="basis_swaps table (csv or parquet)")
    p.add_argument("--basis-type", choices=["tenor", "index", "xccy"])
    p.add_argument("--snap")
    p.add_argument("--window", type=int, default=252)
    p.add_argument("--out")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.basis:
        p.error("--basis or --selftest required")
    df = pd.read_parquet(a.basis) if a.basis.endswith(".parquet") else pd.read_csv(a.basis)
    if "data_ok" in df.columns:
        df = df[df["data_ok"].fillna(True).astype(bool)]
    out = monitor(df, a.window, a.basis_type, a.snap)
    if a.out:
        out.to_csv(a.out, index=False)
    print(out.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
