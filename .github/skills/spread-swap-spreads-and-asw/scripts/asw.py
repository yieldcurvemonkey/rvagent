"""Asset-swap and swap-spread calculator.

Functions (prices per 100; spreads in bp; times in years ACT/365F from the as-of date):
  bond_cashflows      coupon schedule rolled back from maturity (regular coupons; run() handles ex-div)
  par_rate            par swap rate (%) from settlement to an arbitrary end date (front stub), on one curve
  par_par_asw         par/par ASW, bp on the float leg. + = bond cheap to swaps (govt_minus_swap)
  proceeds_asw        market-value / proceeds ASW = par_par * 100 / dirty
  zspread             parallel spread over the swap zero curve that reprices the bond. + = cheap
  bond_ytm            yield in the bond's own compounding (coupon frequency)
  matched_maturity    spread_mm = par swap to bond maturity - bond yield (swap_minus_govt, US quote)
  hedge_notional      DV01-neutral swap notional per bond notional
  tfp_zds             daily cross-section: spread_m = ZDS - TFP * moddur_m (+ residuals)
  dislocation_index   RMS of residual z-scores across tenors, 10d moving average

CLI: python asw.py --bonds bond_static.csv --quotes bond_quotes.csv --curve curve_zero.csv
                   --curve-id USD-SOFR --date 2026-11-10 [--fixed-freq 1 --float-freq 1 --dc ACT/360]
     Reads canonical tables (CSV or Parquet); writes swap_spreads-shaped rows to stdout or --out.
Curve is rebased to the bond's settle date (DF(t)/DF(settle)); only nominal coupon bonds are priced (bills, strips,
linkers, FRNs are skipped); static rows are taken point-in-time; accrued_px < 0 (ex-div) drops the next coupon; several
snaps on one date need --snap.
--selftest: bond priced off the curve has ASW = z = 0 (also through run() with settle lag, shuffled nodes, duplicate
static versions, ex-div accrued); S-G sign of spread_mm; par bond has spread_mm = 0; Genworth 4.90s Aug-23 at 98.70 on a flat 0.288% curve gives par/par
526.4 and proceeds 533.3 (Tuckman-Serrat); z-spread round trip; TFP/ZDS recovered from a synthetic cross-section;
2y hedge ratio 184.0/191.3.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq

DC_DIV = {"ACT/360": 360.0, "ACT/365F": 365.0}


# ---------- curve ----------
def df_interp(t, curve_t, curve_df):
    """Log-linear DF interpolation; flat zero-rate extrapolation beyond the last node."""
    t = np.atleast_1d(np.asarray(t, float))
    ct = np.concatenate([[0.0], np.asarray(curve_t, float)])
    lndf = np.concatenate([[0.0], np.log(np.asarray(curve_df, float))])
    out = np.interp(t, ct, lndf)
    hi = t > ct[-1]
    out[hi] = lndf[-1] / ct[-1] * t[hi]
    return np.exp(out)


def _yf(d0, d1):
    return (pd.Timestamp(d1) - pd.Timestamp(d0)).days / 365.0


def _schedule(settle, maturity, freq):
    """Payment dates rolled back from maturity every 12/freq months, strictly after settle; plus previous date."""
    settle, maturity = pd.Timestamp(settle), pd.Timestamp(maturity)
    m, dates, k = int(12 / freq), [maturity], 1
    while maturity - pd.DateOffset(months=m * k) > settle:  # roll from maturity, so month-end dates do not drift
        dates.append(maturity - pd.DateOffset(months=m * k))
        k += 1
    return maturity - pd.DateOffset(months=m * k), sorted(dates)


# ---------- bond ----------
def bond_cashflows(settle, maturity, coupon_pct, freq):
    """Times (yrs from settle), cash flows per 100, and accrued per 100 (simple ACT/ACT-period accrual)."""
    prev, dates = _schedule(settle, maturity, freq)
    t = np.array([_yf(settle, d) for d in dates])
    cf = np.full(len(dates), coupon_pct / freq)
    cf[-1] += 100.0
    period = (dates[0] - prev).days
    accrued = coupon_pct / freq * (pd.Timestamp(settle) - prev).days / period
    return t, cf, accrued


def pv_on_curve(t, cf, curve_t, curve_df, z_bp=0.0):
    return float(np.sum(cf * df_interp(t, curve_t, curve_df) * np.exp(-z_bp / 1e4 * np.asarray(t))))


def annuity(settle, end, freq, curve_t, curve_df, dc="ACT/360"):
    """sum tau_i * DF(t_i) for a leg from settle to end (front stub), tau on the leg's day count."""
    prev, dates = _schedule(settle, end, freq)
    starts = [pd.Timestamp(settle)] + dates[:-1]
    tau = np.array([(e - s).days / DC_DIV[dc] for s, e in zip(starts, dates)])
    t = np.array([_yf(settle, d) for d in dates])
    return float(np.sum(tau * df_interp(t, curve_t, curve_df)))


def par_rate(settle, end, freq, curve_t, curve_df, dc="ACT/360"):
    """Par rate (%) of a spot-starting swap to `end`, single-curve: (1 - DF(T)) / annuity."""
    dfT = df_interp([_yf(settle, end)], curve_t, curve_df)[0]
    return 100.0 * (1.0 - dfT) / annuity(settle, end, freq, curve_t, curve_df, dc)


def par_par_asw(dirty_px, t, cf, curve_t, curve_df, float_annuity):
    """bp over the float index on 100 notional: (PV of bond cash flows on swap curve - dirty) / (100 * A_float)."""
    return 1e4 * (pv_on_curve(t, cf, curve_t, curve_df) - dirty_px) / (100.0 * float_annuity)


def proceeds_asw(par_par_bp, dirty_px):
    return par_par_bp * 100.0 / dirty_px


def zspread(dirty_px, t, cf, curve_t, curve_df):
    """Continuously compounded parallel spread (bp) over the swap zero curve. + = bond cheap."""
    return brentq(lambda z: pv_on_curve(t, cf, curve_t, curve_df, z) - dirty_px, -5000, 5000, xtol=1e-10)


def bond_ytm(dirty_px, t, cf, freq):
    f = lambda y: float(np.sum(cf / (1 + y / freq) ** (freq * np.asarray(t)))) - dirty_px
    return 100.0 * brentq(f, -0.5, 1.0, xtol=1e-14)


def matched_maturity(ytm_pct, par_swap_pct):
    """spread_mm in bp, US quote: swap minus govt (negative = Treasury cheap to swaps)."""
    return 100.0 * (par_swap_pct - ytm_pct)


def hedge_notional(bond_dv01_per_mn, swap_dv01_per_mn):
    """Swap notional per 1 of bond notional for a DV01-neutral package."""
    return bond_dv01_per_mn / swap_dv01_per_mn


# ---------- curve-of-spreads signals ----------
def tfp_zds(spreads_bp, moddur):
    """One date: OLS spread_m = a + b*moddur_m. Returns ZDS = a, TFP = -b (bp/yr of duration), residuals."""
    x, y = np.asarray(moddur, float), np.asarray(spreads_bp, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:  # short / NaN-ridden cross-section: no fit
        return np.nan, np.nan, np.full(len(y), np.nan)
    b, a = np.polyfit(x[ok], y[ok], 1)
    return a, -b, y - (a + b * x)


def dislocation_index(resid_z: pd.DataFrame, ma=10):
    """BofA-style DI: 10d MA of sqrt(mean_i z_i^2) across tenors (columns)."""
    return np.sqrt((resid_z ** 2).mean(axis=1)).rolling(ma).mean()


# ---------- CLI ----------
def _read(p):
    return pd.read_parquet(p) if str(p).endswith(".parquet") else pd.read_csv(p)


def rebase_curve(ct, cdf, ts):
    """Re-express a curve (times from as-of) at settle ts: DF_s(t) = DF(t) / DF(ts), times t - ts, nodes after ts only."""
    ct, cdf = np.asarray(ct, float), np.asarray(cdf, float)
    d_s = df_interp([ts], ct, cdf)[0]
    keep = ct > ts + 1e-9
    return ct[keep] - ts, cdf[keep] / d_s


def run(bonds, quotes, curve, curve_id, date, fixed_freq=1, float_freq=1, dc="ACT/360", snap=None):
    """Canonical tables in, swap_spreads-shaped rows out. Nominal coupon bonds only; one snap; curve rebased to settle."""
    asof = pd.Timestamp(date)
    c = curve[(curve.curve_id == curve_id) & (pd.to_datetime(curve.date) == asof)]
    if snap and "snap" in c:
        c = c[c.snap == snap]
    if c.empty:
        raise SystemExit(f"no curve_zero rows for {curve_id} on {date}")
    c = c.assign(_nd=pd.to_datetime(c.node_date)).sort_values("_nd")
    ct0 = np.array([_yf(asof, d) for d in c._nd])
    cdf0 = c.discount_factor.to_numpy(float)
    b = bonds.copy()  # point-in-time static: the version valid on `date`, latest valid_from wins
    if "valid_from" in b:
        b = b[pd.to_datetime(b.valid_from) <= asof]
        if "valid_to" in b:
            b = b[b.valid_to.isna() | (pd.to_datetime(b.valid_to) > asof)]
        b = b.sort_values("valid_from").drop_duplicates("instrument_id", keep="last")
    if "bond_type" in b:
        b = b[b.bond_type == "nominal"]  # linkers/FRNs/bills/strips need their own treatment (see SKILL.md)
    b = b[b.coupon_freq > 0]
    q = quotes[pd.to_datetime(quotes.date) == asof]
    if snap and "snap" in q:
        q = q[q.snap == snap]
    if not snap and (("snap" in c and c.snap.nunique() > 1) or ("snap" in q and q.snap.nunique() > 1)):
        raise SystemExit("several snaps on this date: pass --snap (never mix snaps)")
    q = q.merge(b.drop(columns=[x for x in ("date", "snap", "settle_date") if x in b]), on="instrument_id", how="inner")
    rows = []
    for _, r in q.iterrows():
        settle = pd.Timestamp(r["settle_date"]) if pd.notna(r.get("settle_date", np.nan)) else asof
        if pd.Timestamp(r.maturity_date) <= settle + pd.Timedelta(days=30):
            continue
        ts = _yf(asof, settle)
        ct, cdf = rebase_curve(ct0, cdf0, ts)
        t, cf, acc = bond_cashflows(settle, r.maturity_date, r.coupon_pct, int(r.coupon_freq))
        a_q = r.get("accrued_px", np.nan)
        if pd.isna(a_q) and pd.notna(r.get("dirty_px", np.nan)) and pd.notna(r.get("clean_px", np.nan)):
            a_q = r.dirty_px - r.clean_px
        if pd.notna(a_q) and a_q < 0:  # ex-dividend (gilts): the next coupon belongs to the seller
            cf[0] -= r.coupon_pct / int(r.coupon_freq)
        if pd.notna(r.get("dirty_px", np.nan)):
            dirty = r.dirty_px
        elif pd.notna(r.get("accrued_px", np.nan)):
            dirty = r.clean_px + r.accrued_px  # honours negative gilt ex-div accrued
        else:
            dirty = r.clean_px + acc
        if not (np.isfinite(dirty) and dirty > 0):  # missing / bad price: skip, never invent
            continue
        a_flt = annuity(settle, r.maturity_date, float_freq, ct, cdf, dc)
        pp = par_par_asw(dirty, t, cf, ct, cdf, a_flt)
        ytm = bond_ytm(dirty, t, cf, int(r.coupon_freq))
        mm = matched_maturity(ytm, par_rate(settle, r.maturity_date, fixed_freq, ct, cdf, dc))
        out = {"asw_parpar": (pp, "govt_minus_swap"), "asw_proceeds": (proceeds_asw(pp, dirty), "govt_minus_swap"),
               "zspread": (zspread(dirty, t, cf, ct, cdf), "govt_minus_swap"), "spread_mm": (mm, "swap_minus_govt")}
        for m, (v, sgn) in out.items():
            rows.append(dict(date=asof.date(), snap=r.get("snap", ""), ccy=r.get("ccy", ""), curve_id=curve_id,
                             measure=m, ref=r.instrument_id, value_bp=round(v, 3), sign_convention=sgn,
                             source="asw.py"))
    return pd.DataFrame(rows)


# ---------- selftest ----------
def selftest():
    ok = True

    def chk(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'ok ' if good else 'FAIL'} {name}: got {got:.6f} want {want:.6f}")

    asof = pd.Timestamp("2026-11-10")
    ct = np.array([0.5, 1, 2, 3, 5, 7, 10, 20, 30])
    zr = np.array([3.6, 3.55, 3.5, 3.55, 3.7, 3.85, 4.0, 4.3, 4.4]) / 100
    cdf = np.exp(-zr * ct)
    mat = pd.Timestamp("2033-08-15")
    t, cf, acc = bond_cashflows(asof, mat, 4.5, 2)
    fair = pv_on_curve(t, cf, ct, cdf)
    a_flt = annuity(asof, mat, 1, ct, cdf)
    chk("par/par ASW of a bond priced on the curve", par_par_asw(fair, t, cf, ct, cdf, a_flt), 0.0, 1e-9)
    chk("z-spread of a bond priced on the curve", zspread(fair, t, cf, ct, cdf), 0.0, 1e-6)
    dP = -1.25  # bond 1.25 points cheaper -> ASW = 1.25 / (100 * A_float) in bp
    chk("par/par ASW after price shift", par_par_asw(fair + dP, t, cf, ct, cdf, a_flt), 1e4 * 1.25 / (100 * a_flt), 1e-9)
    chk("z-spread sign (cheaper bond -> positive z)", float(zspread(fair + dP, t, cf, ct, cdf) > 0), 1.0, 0)
    # par bond: annual coupon = par swap rate, ACT/365F both legs -> priced at 100, yield = par, spread_mm = 0
    m5 = pd.Timestamp("2031-11-10")
    p = par_rate(asof, m5, 1, ct, cdf, "ACT/365F")
    prev, dates = _schedule(asof, m5, 1)
    starts = [asof] + dates[:-1]
    tb = np.array([_yf(asof, d) for d in dates])
    cfb = np.array([p * (e - s).days / 365.0 for s, e in zip(starts, dates)])
    cfb[-1] += 100
    chk("par bond prices at 100 on the curve", pv_on_curve(tb, cfb, ct, cdf), 100.0, 1e-9)
    # tolerance 0.01bp: leap-year accruals (366/365) vs yield compounding on ACT/365F time
    chk("matched-maturity spread of a par bond", matched_maturity(bond_ytm(100.0, tb, cfb, 1), p), 0.0, 1e-2)
    chk("proceeds ASW, Genworth (Tuckman-Serrat)", proceeds_asw(526.4, 98.70), 533.3, 0.05)
    chk("matched-maturity sign, S-G (JPM 2y: swap 4.083, UST 4.232)", matched_maturity(4.232, 4.083), -14.9, 1e-9)
    chk("month-end roll does not drift (31 Aug maturity, semi-annual)", float(_schedule("2027-03-10", "2033-08-31", 2)[1][0].day), 31.0, 0)
    chk("TFP/ZDS with <3 points returns NaN", float(np.isnan(tfp_zds([-10.0, np.nan, -20.0], [2.0, 5.0, np.nan])[1])), 1.0, 0)
    zds, tfp, res = tfp_zds(-8.2 - 4.2 * np.array([1.9, 2.8, 4.5, 6.2, 8.3, 13.8, 17.5]),
                            [1.9, 2.8, 4.5, 6.2, 8.3, 13.8, 17.5])
    chk("ZDS recovered", zds, -8.2, 1e-9)
    chk("TFP recovered", tfp, 4.2, 1e-9)
    chk("2y widener hedge ratio (JPM, Aug 2026)", hedge_notional(184.0, 191.3), 0.962, 5e-4)
    z = pd.DataFrame({"2y": [1.0] * 10, "5y": [-1.0] * 10, "10y": [2.0] * 10, "30y": [0.0] * 10})
    chk("dislocation index", float(dislocation_index(z).iloc[-1]), float(np.sqrt(1.5)), 1e-12)
    # independent: Genworth 4.90s Aug-2023 at 98.70 on a flat 0.288% semi-annual curve -> par/par 526.4, proceeds 533.3
    tg = np.array([0.5, 1.0, 1.5, 2.0])
    dfg = (1 + 0.00288 / 2) ** (-2 * tg)
    cfg = np.array([2.45, 2.45, 2.45, 102.45])
    ppg = par_par_asw(98.70, tg, cfg, tg, dfg, float(np.sum(0.5 * dfg)))
    chk("par/par ASW, Genworth (Tuckman-Serrat)", ppg, 526.4, 0.05)
    chk("proceeds ASW from computed par/par", proceeds_asw(ppg, 98.70), 533.3, 0.1)
    tf = np.array([1.0, 2.0, 3.0])  # independent of pv_on_curve: flat 3.5% curve + 25bp spread, priced by hand
    cff = np.array([5.0, 5.0, 105.0])
    pz = float(np.sum(cff * np.exp(-(0.035 + 0.0025) * tf)))
    chk("z-spread vs hand-priced bond at +25bp", zspread(pz, tf, cff, tf, np.exp(-0.035 * tf)), 25.0, 1e-6)
    # run(): settle after as-of, shuffled nodes, two static versions, bill + linker rows must be ignored
    zf = 0.035
    nodes = pd.to_datetime(["2027-11-10", "2029-11-10", "2031-11-10", "2036-11-10", "2046-11-10"])[[3, 0, 4, 2, 1]]
    cur = pd.DataFrame(dict(date="2026-11-10", snap="eod_ny", curve_id="USD-SOFR", node_date=nodes,
                            discount_factor=[np.exp(-zf * _yf("2026-11-10", n)) for n in nodes]))
    stl = pd.Timestamp("2026-11-11")
    tt, cc, ac = bond_cashflows(stl, "2033-05-15", 4.0, 2)
    fair_dirty = float(np.sum(cc * np.exp(-zf * tt)))  # flat curve: DF_rebased(t from settle) = exp(-z t), analytic
    st = pd.DataFrame(dict(instrument_id=["B1", "B1", "BILL", "TIPS"], valid_from=["2020-01-01", "2026-01-01", "2020-01-01", "2020-01-01"],
                           valid_to=[None, None, None, None], ccy="USD", bond_type=["nominal", "nominal", "bill", "linker"],
                           coupon_pct=[4.0, 4.0, 0.0, 1.0], coupon_freq=[2, 2, 0, 2],
                           maturity_date=["2033-05-15", "2033-05-15", "2027-01-15", "2033-01-15"]))
    qu = pd.DataFrame(dict(date="2026-11-10", snap="eod_ny", instrument_id=["B1", "BILL", "TIPS"],
                           clean_px=[fair_dirty - ac, 98.0, 101.0], accrued_px=[ac, 0.0, 0.0], settle_date="2026-11-11"))
    res = run(st, qu, cur, "USD-SOFR", "2026-11-10", snap="eod_ny")
    chk("run(): rows only for the nominal coupon bond", float(len(res)), 4.0, 0)
    chk("run(): par/par ASW of on-curve bond with settle lag", float(res[res.measure == "asw_parpar"].value_bp.iloc[0]), 0.0, 1e-6)
    chk("run(): z-spread of on-curve bond with settle lag", float(res[res.measure == "zspread"].value_bp.iloc[0]), 0.0, 1e-6)
    # ex-dividend: next coupon (15 Nov, 4 days after settle) belongs to the seller; accrued is negative; ASW must still be 0
    t0 = float(tt[0])
    fair_ex = fair_dirty - 2.0 * np.exp(-zf * t0)
    acc_ex = ac - 2.0
    st2 = pd.concat([st, st.iloc[[0]].assign(instrument_id="GILT", valid_from="2020-01-01")], ignore_index=True)
    qx = pd.concat([qu, pd.DataFrame(dict(date="2026-11-10", snap="eod_ny", instrument_id=["GILT"], clean_px=[fair_ex - acc_ex],
                                          accrued_px=[acc_ex], settle_date="2026-11-11"))], ignore_index=True)
    rx = run(st2, qx, cur, "USD-SOFR", "2026-11-10", snap="eod_ny")
    chk("run(): ex-div bond priced off the curve has par/par ASW 0", float(rx[(rx.measure == "asw_parpar") & (rx.ref == "GILT")].value_bp.iloc[0]), 0.0, 1e-6)
    chk("run(): ex-div bond priced off the curve has z-spread 0", float(rx[(rx.measure == "zspread") & (rx.ref == "GILT")].value_bp.iloc[0]), 0.0, 1e-6)
    sg = dict(zip(res.measure, res.sign_convention))
    chk("run(): sign tags (asw/z govt_minus_swap, spread_mm swap_minus_govt)",
        float(sg["asw_parpar"] == sg["asw_proceeds"] == sg["zspread"] == "govt_minus_swap" and sg["spread_mm"] == "swap_minus_govt"), 1.0, 0)
    qu.loc[0, "clean_px"] -= 1.0
    cheap = run(st, qu, cur, "USD-SOFR", "2026-11-10", snap="eod_ny")
    chk("run(): cheaper bond -> positive ASW (govt_minus_swap)", float(cheap[cheap.measure == "asw_parpar"].value_bp.iloc[0] > 15), 1.0, 0)
    chk("run(): cheaper bond -> spread_mm more negative (swap_minus_govt)",
        float(cheap[cheap.measure == "spread_mm"].value_bp.iloc[0] < res[res.measure == "spread_mm"].value_bp.iloc[0] - 10), 1.0, 0)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--bonds"), ap.add_argument("--quotes"), ap.add_argument("--curve")
    ap.add_argument("--curve-id", default="USD-SOFR")
    ap.add_argument("--date")
    ap.add_argument("--fixed-freq", type=int, default=1)
    ap.add_argument("--float-freq", type=int, default=1)
    ap.add_argument("--dc", default="ACT/360", choices=sorted(DC_DIV))
    ap.add_argument("--snap")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not (a.bonds and a.quotes and a.curve and a.date):
        ap.error("--bonds, --quotes, --curve and --date are required (or --selftest)")
    res = run(_read(a.bonds), _read(a.quotes), _read(a.curve), a.curve_id, a.date, a.fixed_freq, a.float_freq, a.dc, a.snap)
    if a.out:
        res.to_csv(a.out, index=False)
    else:
        print(res.to_string(index=False))


if __name__ == "__main__":
    main()
