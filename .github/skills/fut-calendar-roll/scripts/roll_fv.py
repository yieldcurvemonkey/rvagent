"""Bond-futures calendar roll toolkit: fair roll from forward CTD prices, calendar implied repo, BPV roll ratio,
funding sensitivity, positioning regression, and roll-adjusted (back-adjusted) generic series.

Conventions: prices per 100 face, decimal (never 32nds text); repo in percent, simple interest, ACT/360 by default;
roll = FRONT - BACK futures price (points; x32 for 32nds). Positive roll = front above back (positive carry).
Net basis b = forward clean CTD - CF*F, so the fair futures price is F = (forward clean - b)/CF and
fair roll = F_front_fair - F_back_fair. Calendar "rich" = market roll above fair roll (sell front, buy back).

CLI (canonical tables as csv or parquet in --dir):
  python roll_fv.py --selftest
  python roll_fv.py fair   --dir D --front FUT:ZN:2026-12 --back FUT:ZN:2027-03 --ctd-front BOND:A --ctd-back BOND:B
                           --date 2026-11-10 [--snap settle] [--delivery auto|first|last] [--repo-pct 4.0]
                           [--nb-front 0.0 --nb-back 0.0]   (model net basis = option value, points; default 0)
  python roll_fv.py stitch --dir D --generic FUT:ZN:1 [--snap settle] [--out adj.csv]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

T32 = 32.0


# ---------------------------------------------------------------- bond helpers (self-contained copy)
def _cpn_date(maturity: pd.Timestamp, months: int) -> pd.Timestamp:
    """Coupon date `months` before maturity; a month-end maturity pays on month-ends (30 Nov -> 31 May, not 30 May)."""
    c = maturity - pd.DateOffset(months=months)
    return c + pd.offsets.MonthEnd(0) if maturity.is_month_end else c


def _prev_next_coupon(maturity: pd.Timestamp, d: pd.Timestamp, freq: int = 2):
    step, k = 12 // freq, 0
    while _cpn_date(maturity, step * k) > d:
        k += 1
    if k == 0:
        raise ValueError("bond matured on or before date")
    return _cpn_date(maturity, step * k), _cpn_date(maturity, step * (k - 1))


def accrued(coupon_pct: float, maturity, d, freq: int = 2, day_count: str = "ACT/ACT ICMA") -> float:
    """Accrued per 100 at d. ACT/ACT ICMA and ACT/365F only; other day counts must be passed in by the caller."""
    maturity, d = pd.Timestamp(maturity), pd.Timestamp(d)
    prev, nxt = _prev_next_coupon(maturity, d, freq)
    if day_count == "ACT/ACT ICMA":
        return coupon_pct / freq * (d - prev).days / (nxt - prev).days
    if day_count == "ACT/365F":
        return coupon_pct * (d - prev).days / 365.0
    raise NotImplementedError(f"day count {day_count}: pass accrued explicitly")


def coupons_between(coupon_pct: float, maturity, start, end, freq: int = 2):
    """[(cash_per_100, days_from_coupon_to_end)] for coupons paid in (start, end]."""
    maturity, start, end = map(pd.Timestamp, (maturity, start, end))
    out, k, step = [], 0, 12 // freq
    while True:
        c = _cpn_date(maturity, step * k)
        if c <= start:
            break
        if c <= end:
            out.append((coupon_pct / freq, (end - c).days))
        k += 1
    return out


def forward_clean(clean, ai0, ai_t, repo_pct, days, coupons=(), day_basis=360.0):
    """Clean forward price at delivery: bond financed at term repo, intervening coupons reinvested at repo."""
    r = repo_pct / 100.0
    full = (clean + ai0) * (1 + r * days / day_basis)
    for cash, n2 in coupons:
        full -= cash * (1 + r * n2 / day_basis)
    return full - ai_t


# ---------------------------------------------------------------- roll fair value
def fut_fair(fwd_clean: float, cf: float, model_nb: float = 0.0) -> float:
    """Fair futures price = (forward clean CTD - model net basis) / CF. model_nb = option value (>= 0), 0 if ignored."""
    return (fwd_clean - model_nb) / cf


def fair_roll(fwd1, cf1, nb1, fwd2, cf2, nb2) -> float:
    """Fair roll (front - back) in points: FV(front) - FV(back)."""
    return fut_fair(fwd1, cf1, nb1) - fut_fair(fwd2, cf2, nb2)


def roll_parts(fwd1, cf1, nb1, fwd2, cf2, nb2) -> dict:
    """Split the fair roll into a carry/forward part (zero-option roll) and an option part."""
    carry = fwd1 / cf1 - fwd2 / cf2
    opt = -nb1 / cf1 + nb2 / cf2
    return dict(carry_part=carry, option_part=opt, fair_roll=carry + opt)


def calendar_irp(inv1: float, inv2: float, days: float, coupons=(), day_basis: float = 360.0) -> float:
    """Calendar implied repo, percent: buy the CTD at the front invoice price inv1 (= CF1*F1 + AI at d1), finance to d2,
    sell at the back invoice price inv2 (= CF2*F2 + AI at d2), plus coupons paid in between [(cash, days_to_d2)].
    Valid only for the SAME CTD in both months; with different CTDs use option-adjusted measures instead."""
    num = inv2 + sum(c for c, _ in coupons) - inv1
    den = (inv1 * days - sum(c * n2 for c, n2 in coupons)) / day_basis
    return 100.0 * num / den


def funding_sens(full_price: float, d_repo_bp: float, days: float, cf: float = 1.0, day_basis: float = 360.0) -> float:
    """Change in roll (points) for a parallel funding move over the d1->d2 gap: the back forward is financed longer,
    so d(roll) = -full_price * d_repo * days / day_basis / CF. 25bp, ~91d, price 100 -> about -0.0625 (-2/32)."""
    return -full_price * (d_repo_bp / 1e4) * days / day_basis / cf


def bpv_ratio(dv01_front: float, dv01_back: float, per: float = 1000.0) -> float:
    """BPV-neutral roll: back contracts per `per` front = PVBP_front / PVBP_back (usually < 1)."""
    return per * dv01_front / dv01_back


def fit_line(x, y) -> dict:
    """OLS y = a*x + b (e.g. roll richness in ticks vs normalised asset-manager share of OI). Returns slope,
    intercept, r2, resid (array) and n. Exclude extreme-vol cycles before fitting."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.ptp(x) == 0:
        raise ValueError("fit_line needs >= 3 finite points with varying x")
    a, b = np.polyfit(x, y, 1)
    res = y - (a * x + b)
    r2 = 1.0 - res.var() / y.var() if y.var() > 0 else np.nan
    return dict(slope=a, intercept=b, r2=r2, resid=res, n=len(x))


# ---------------------------------------------------------------- roll-adjusted generic series
def stitch(px: pd.DataFrame, held: pd.Series) -> pd.DataFrame:
    """Back-adjusted generic. px: date x instrument prices (same snap). held: date -> instrument the generic points to
    on that date (the roll_map). Day-t P&L is the change of the contract held on t between t-1 and t, so the roll is
    never booked as a return. held[t] is therefore decided at the t-1 close: build the roll rule from data up to t-1
    (shift OI/volume-based rules by one day) or the series has look-ahead. Columns: raw_px (jumps at rolls), gap (new - old price at t-1 on a roll date),
    pnl, adj_px (= cumulative pnl, shifted so the LAST value equals the raw last price),
    ratio_px (non-negative: cumprod of pnl / previous held price, scaled to start at the first raw price)."""
    px = px.sort_index()
    if len(px) < 2:
        raise ValueError("stitch needs >= 2 dates")
    held = held.reindex(px.index)
    if held.isna().any():
        raise ValueError("held (roll map) has no instrument for some dates")
    idx = list(px.index)
    raw, gap, pnl, prev_px = [], [np.nan], [np.nan], [np.nan]
    for i, t in enumerate(idx):
        raw.append(px.at[t, held[t]])
        if i == 0:
            continue
        s, new, old = idx[i - 1], held[t], held[idx[i - 1]]
        p0, p1 = px.at[s, new], px.at[t, new]
        if np.isnan(p0) or np.isnan(p1):
            raise ValueError(f"{new} has no price on {s.date()} or {t.date()}: cannot roll into it, do not invent")
        gap.append(p0 - px.at[s, old] if new != old else 0.0)
        pnl.append(p1 - p0)
        prev_px.append(p0)
    out = pd.DataFrame(dict(instrument=held.values, raw_px=raw, gap=gap, pnl=pnl, prev_px=prev_px), index=px.index)
    cum = out.pnl.fillna(0).cumsum()
    out["adj_px"] = cum + (out.raw_px.iloc[-1] - cum.iloc[-1])
    ratio = (1 + out.pnl.fillna(0) / out.prev_px.fillna(1)).cumprod()
    out["ratio_px"] = ratio * out.raw_px.iloc[0]
    return out.drop(columns="prev_px")


# ---------------------------------------------------------------- canonical-table front end
def _read(path: Path) -> pd.DataFrame:
    for ext, fn in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
        p = path.with_suffix(ext)
        if p.exists():
            return fn(p)
    raise FileNotFoundError(f"{path}.csv|.parquet")


def _leg(t: dict, fut_id, bond_id, date, snap, delivery, repo_pct, settle) -> dict:
    fs = t["fut_static"][t["fut_static"].fut_id == fut_id].iloc[0]
    fq = t["fut_quotes"]
    fut_px = float(fq[(fq.fut_id == fut_id) & (fq.date == date) & (fq.snap == snap)].price_px.iloc[0])
    bk = t["fut_basket"]
    cf = float(bk[(bk.fut_id == fut_id) & (bk.instrument_id == bond_id)].conversion_factor.iloc[0])
    st = t["bond_static"].sort_values("valid_from").drop_duplicates("instrument_id", keep="last")
    b = st[st.instrument_id == bond_id].iloc[0]
    q = t["bond_quotes"]
    clean = float(q[(q.instrument_id == bond_id) & (q.date == date) & (q.snap == snap)].clean_px.iloc[0])
    dlv = pd.Timestamp(fs.first_delivery_date if delivery == "first" else fs.last_delivery_date)
    f = int(b.coupon_freq)
    ai0, ait = accrued(b.coupon_pct, b.maturity_date, settle, f), accrued(b.coupon_pct, b.maturity_date, dlv, f)
    cps = coupons_between(b.coupon_pct, b.maturity_date, settle, dlv, f)
    rr = t["repo_rates"]
    rr = rr[(rr.date == date) & (rr.snap == snap) & (rr.term == dlv.strftime("%Y-%m-%d"))]
    own = rr[rr.collateral == bond_id].rate_pct
    gc = rr[~rr.collateral.str.startswith("BOND:")].rate_pct
    rp = repo_pct if repo_pct is not None else (own.iloc[0] if len(own) else (gc.mean() if len(gc) else np.nan))
    if pd.isna(rp):
        raise ValueError(f"no term repo to {dlv.date()} for {bond_id}: supply --repo-pct or ask the data adapter")
    days = (dlv - settle).days
    fwd = forward_clean(clean, ai0, ait, rp, days, cps)
    return dict(fut_id=fut_id, bond=bond_id, fut_px=fut_px, cf=cf, clean=clean, delivery=dlv, repo_pct=rp, days=days,
                fwd_clean=fwd, ai_t=ait, coupons=cps, carry=(clean - cf * fut_px) - (fwd - cf * fut_px))


def fair_from_canonical(d: Path, front, back, ctd_front, ctd_back, date, snap="settle", delivery="auto",
                        repo_pct=None, nb_front=0.0, nb_back=0.0) -> dict:
    date = pd.Timestamp(date)
    t = {n: _read(d / n) for n in ("bond_static", "bond_quotes", "fut_static", "fut_basket", "fut_quotes", "repo_rates")}
    for n in ("fut_quotes", "bond_quotes", "repo_rates"):
        t[n]["date"] = pd.to_datetime(t[n]["date"])
    t["bond_static"]["maturity_date"] = pd.to_datetime(t["bond_static"]["maturity_date"])
    q = t["bond_quotes"]
    q = q[(q.instrument_id == ctd_front) & (q.date == date) & (q.snap == snap)]
    if q.empty:
        raise ValueError(f"no bond_quotes row for {ctd_front} on {date.date()} {snap}")
    settle = pd.Timestamp(q.settle_date.iloc[0]) if "settle_date" in q and q.settle_date.notna().all() else \
        date + pd.offsets.BDay(1)  # ponytail: weekend-only calendar; pass bond_quotes.settle_date to be exact
    if delivery == "auto":
        delivery = "last" if _leg(t, front, ctd_front, date, snap, "last", repo_pct, settle)["carry"] > 0 else "first"
    a = _leg(t, front, ctd_front, date, snap, delivery, repo_pct, settle)
    b = _leg(t, back, ctd_back, date, snap, delivery, repo_pct, settle)
    mk = a["fut_px"] - b["fut_px"]
    parts = roll_parts(a["fwd_clean"], a["cf"], nb_front, b["fwd_clean"], b["cf"], nb_back)
    res = dict(date=str(date.date()), delivery_rule=delivery, market_roll_32nds=mk * T32,
               fair_roll_32nds=parts["fair_roll"] * T32, carry_part_32nds=parts["carry_part"] * T32,
               option_part_32nds=parts["option_part"] * T32,
               rich_cheap_32nds=(mk - parts["fair_roll"]) * T32,
               view="calendar RICH (sell front, buy back)" if mk > parts["fair_roll"] else "calendar CHEAP (buy front, sell back)",
               same_ctd=ctd_front == ctd_back)
    if res["same_ctd"]:
        i1, i2 = a["cf"] * a["fut_px"] + a["ai_t"], b["cf"] * b["fut_px"] + b["ai_t"]
        gap = (b["delivery"] - a["delivery"]).days
        st = t["bond_static"].drop_duplicates("instrument_id", keep="last").set_index("instrument_id").loc[ctd_front]
        cps = coupons_between(st.coupon_pct, st.maturity_date, a["delivery"], b["delivery"], int(st.coupon_freq))
        res["calendar_irp_pct"] = calendar_irp(i1, i2, gap, cps)
        # forward repo d1->d2 implied by the two spot-start term repos (simple interest): compare IRP with THIS
        res["fwd_repo_pct"] = 100.0 * ((1 + b["repo_pct"] / 100 * b["days"] / 360) /
                                       (1 + a["repo_pct"] / 100 * a["days"] / 360) - 1) * 360 / gap
    return res


def stitch_from_canonical(d: Path, generic: str, snap="settle") -> pd.DataFrame:
    rm, fq = _read(d / "roll_map"), _read(d / "fut_quotes")
    rm["date"], fq["date"] = pd.to_datetime(rm["date"]), pd.to_datetime(fq["date"])
    rm = rm[rm.generic_id == generic].set_index("date").sort_index()
    px = fq[fq.snap == snap].pivot(index="date", columns="fut_id", values="price_px")
    px = px.loc[px.index.intersection(rm.index)]
    out = stitch(px, rm.instrument_id)
    out["roll_rule"] = rm.roll_rule.reindex(out.index).values
    return out


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    bad = []

    def chk(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(("ok   " if ok else "FAIL ") + f"{name}: got {got:.6f} want {want:.6f}")
        if not ok:
            bad.append(name)

    # 1. Burghardt 2005 (4 Apr 2001): CTD 105-02.5, theoretical June basis 13.8/32, CF 0.9904 -> FV 105-21.2
    f = fut_fair(105 + 2.5 / 32, 0.9904, 13.8 / 32)
    chk("futures FV 105-21.2 (32nds past 105)", (f - 105) * 32, 21.2, 0.06)
    # 2. zero-coupon, CF 1, no options: roll = -P*r*dt/360 exactly (carry is negative = financing cost)
    P, r, d1, d2 = 100.0, 4.0, 90, 181
    f1, f2 = forward_clean(P, 0, 0, r, d1), forward_clean(P, 0, 0, r, d2)
    chk("zero-coupon fair roll", fair_roll(f1, 1, 0, f2, 1, 0), -100 * 0.04 * (d2 - d1) / 360, 1e-9)
    # 3. funding sensitivity: +25bp over ~a quarter on a ~100 price = -0.0625 points = -2/32 (JPM, Aug 2026)
    chk("funding +25bp -> roll (points)", funding_sens(100, 25, 90), -0.0625, 1e-9)
    # re-price the roll with repo +25bp: change must equal the closed form (zero-coupon, CF 1)
    g1, g2 = forward_clean(P, 0, 0, r + .25, d1), forward_clean(P, 0, 0, r + .25, d2)
    chk("repriced vs closed form", fair_roll(g1, 1, 0, g2, 1, 0) - fair_roll(f1, 1, 0, f2, 1, 0),
        funding_sens(100, 25, d2 - d1), 1e-9)
    # 4. calendar IRP of a roll priced at fair value equals the repo (chained forwards, one coupon in between)
    full1, c, n2, dd, rr = 101.3, 2.0, 40, 91, 4.2
    full2 = full1 * (1 + rr / 100 * dd / 360) - c * (1 + rr / 100 * n2 / 360)
    chk("calendar IRP == repo at fair", calendar_irp(full1, full2, dd, [(c, n2)]), rr, 1e-9)
    # 5. BPV roll ratios from the JPM Aug-2026 DV01 table (back per 1000 front)
    chk("HR WN", bpv_ratio(173.53, 175.28), 990, 1.0)
    chk("HR UXY", bpv_ratio(85.83, 87.80), 977, 1.0)
    chk("HR TU", bpv_ratio(36.88, 42.25), 872.5, 1.0)
    # 6. Citi 2015 basket mismatch: DV01 166 (USH5) vs 252 (USM5) -> 34.1% fewer June contracts
    chk("equal-DV01 roll saves", 1 - 166 / 252, 0.341, 5e-4)
    # 7. regression recovers a known line (Citi May-2019 FV fit used as a synthetic truth)
    x = np.linspace(0.1, 0.9, 12)
    fl = fit_line(x, -17.517 * x + 2.5885)
    chk("fit slope", fl["slope"], -17.517, 1e-9)
    chk("fit intercept", fl["intercept"], 2.5885, 1e-9)
    chk("fit r2", fl["r2"], 1.0, 1e-9)
    # 8. stitch: calendar constant at +2 (A = B + 2), A held to day 3 then B: adjusted series must equal B throughout
    dates = pd.bdate_range("2026-01-05", periods=8)
    A = pd.Series([100, 101, 100.5, 102, 103, 104, 103.5, 105.0], index=dates)
    B = A - 2.0
    held = pd.Series(["A"] * 4 + ["B"] * 4, index=dates)
    s = stitch(pd.DataFrame({"A": A, "B": B}), held)
    chk("stitch adj == B path", float(np.abs(s.adj_px - B).max()), 0.0, 1e-12)
    chk("gap at roll", float(s.gap.iloc[4]), -2.0, 1e-12)
    chk("raw jump at roll", float(s.raw_px.iloc[4] - s.raw_px.iloc[3]), 103 - 2 - 102, 1e-12)  # raw has a 2pt hole
    chk("pnl at roll = true B move", float(s.pnl.iloc[4]), float(B.iloc[4] - B.iloc[3]), 1e-12)
    # 9. end-to-end through canonical tables: market roll set at fair => richness 0; +1 tick on the front => +1.0 tick
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        mat, cpn, cf1, cf2, rp = "2036-08-15", 4.0, 0.80, 0.80, 4.0
        settle, dt = pd.Timestamp("2026-11-10"), pd.Timestamp("2026-11-09")
        d1, d2 = pd.Timestamp("2026-12-31"), pd.Timestamp("2027-03-31")
        clean = 98.5
        ai0 = accrued(cpn, mat, settle)
        fw = [forward_clean(clean, ai0, accrued(cpn, mat, x), rp, (x - settle).days,
                            coupons_between(cpn, mat, settle, x)) for x in (d1, d2)]
        fa, fb = fw[0] / cf1, fw[1] / cf2
        irp = []
        for bump in (0.0, 1 / 32):
            pd.DataFrame([dict(fut_id="FUT:X:2026-12", first_delivery_date="2026-12-01", last_delivery_date=str(d1.date())),
                          dict(fut_id="FUT:X:2027-03", first_delivery_date="2027-03-01", last_delivery_date=str(d2.date()))]
                         ).to_csv(d / "fut_static.csv", index=False)
            pd.DataFrame([dict(fut_id="FUT:X:2026-12", instrument_id="BOND:A", conversion_factor=cf1),
                          dict(fut_id="FUT:X:2027-03", instrument_id="BOND:A", conversion_factor=cf2)]
                         ).to_csv(d / "fut_basket.csv", index=False)
            pd.DataFrame([dict(date=str(dt.date()), snap="settle", fut_id="FUT:X:2026-12", price_px=fa + bump),
                          dict(date=str(dt.date()), snap="settle", fut_id="FUT:X:2027-03", price_px=fb)]
                         ).to_csv(d / "fut_quotes.csv", index=False)
            pd.DataFrame([dict(instrument_id="BOND:A", valid_from="2026-01-01", coupon_pct=cpn, coupon_freq=2,
                               maturity_date=mat)]).to_csv(d / "bond_static.csv", index=False)
            pd.DataFrame([dict(date=str(dt.date()), snap="settle", instrument_id="BOND:A", clean_px=clean,
                               settle_date=str(settle.date()))]).to_csv(d / "bond_quotes.csv", index=False)
            pd.DataFrame([dict(date=str(dt.date()), snap="settle", ccy="USD", collateral="GC_US", term=str(x.date()),
                               rate_pct=rp) for x in (d1, d2)]).to_csv(d / "repo_rates.csv", index=False)
            res = fair_from_canonical(d, "FUT:X:2026-12", "FUT:X:2027-03", "BOND:A", "BOND:A", dt, delivery="last")
            chk(f"canonical richness (bump {bump * 32:.0f} tick)", res["rich_cheap_32nds"], bump * 32, 1e-6)
            irp.append(res["calendar_irp_pct"])
        # at fair, IRP is the forward repo d1->d2: ~repo/(1+repo*t1) = 3.98 here, not the 4.00 spot-start repo
        chk("calendar IRP at fair ~ forward repo", irp[0], 3.978, 0.01)
        chk("reported fwd repo = 3.978 (not the 4.00 spot-start repo)", res["fwd_repo_pct"], 3.978, 0.002)
        # one tick richer front (invoice +CF/32) lowers the long-calendar IRP by that amount / financed carry base = ~0.10 pct
        chk("IRP drop for +1 tick on front", irp[0] - irp[1], cf1 * (1 / 32) / ((100.0092 * 90 - 2 * 44) / 360) * 100, 0.003)
    # option part: back net basis 3/32 above front at CF 0.80 widens the roll by (3/32)/0.80 (worked example in SKILL.md)
    rp_ = roll_parts(100.0, 0.8, 0.0, 99.9, 0.8, 3 / 32)
    chk("option part = +3.75/32", rp_["option_part"] * 32, 3.75, 1e-9)
    chk("parts sum to fair roll", rp_["carry_part"] + rp_["option_part"] - fair_roll(100.0, 0.8, 0.0, 99.9, 0.8, 3 / 32), 0.0, 1e-12)
    # 10. month-end maturity pays month-end coupons: 30-Nov-2033 bond on 15-Dec-2026: prev 30 Nov, next 31 May = 182 days
    chk("EOM coupon accrual", accrued(4.0, "2033-11-30", "2026-12-15"), 2.0 * 15 / 182, 1e-12)
    try:
        fit_line([1.0, 2.0], [1.0, 2.0])
        bad.append("fit_line short input not rejected")
    except ValueError:
        print("ok   fit_line rejects n<3")
    print("SELFTEST", "FAILED: " + ", ".join(bad) if bad else "PASSED")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fair")
    f.add_argument("--dir", required=True)
    f.add_argument("--front", required=True)
    f.add_argument("--back", required=True)
    f.add_argument("--ctd-front", required=True)
    f.add_argument("--ctd-back", required=True)
    f.add_argument("--date", required=True)
    f.add_argument("--snap", default="settle")
    f.add_argument("--delivery", default="auto", choices=["auto", "first", "last"])
    f.add_argument("--repo-pct", type=float)
    f.add_argument("--nb-front", type=float, default=0.0)
    f.add_argument("--nb-back", type=float, default=0.0)
    s = sub.add_parser("stitch")
    s.add_argument("--dir", required=True)
    s.add_argument("--generic", required=True)
    s.add_argument("--snap", default="settle")
    s.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "fair":
        r = fair_from_canonical(Path(a.dir), a.front, a.back, a.ctd_front, a.ctd_back, a.date, a.snap, a.delivery,
                                a.repo_pct, a.nb_front, a.nb_back)
        for k, v in r.items():
            print(f"{k:22s} {v:.4f}" if isinstance(v, float) else f"{k:22s} {v}")
        return 0
    if a.cmd == "stitch":
        o = stitch_from_canonical(Path(a.dir), a.generic, a.snap)
        (o.to_csv(a.out) if a.out else print(o.to_string()))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
