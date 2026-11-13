"""Treasury-style bond-futures basis toolkit: CBOT conversion factor, gross basis, carry, net basis (BNOC),
implied repo rate (IRR), CTD by max IRR, and hedge sizing.

Conventions: prices per 100 face, decimal (never 32nds text); rates in percent; days are calendar days;
repo accrues simple, ACT/360 by default (pass day_basis=365 for GBP/CAD/AUD-style repo).
Sign: gross_basis = clean - CF*F; net_basis = forward_clean - CF*F; carry = gross_basis - net_basis
(positive carry = coupon accrual exceeds repo cost). IRR in percent.

CLI:
  python basis.py --selftest
  python basis.py --fut-id FUT:ZN:2026-12 --date 2026-11-10 --snap settle --dir <folder with canonical csv/parquet>
     (reads bond_static, bond_quotes, fut_static, fut_basket, fut_quotes, repo_rates; optional --repo-pct GC override)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

T32 = 32.0  # prices -> 32nds


# ---------------------------------------------------------------- conversion factor
def _whole_months(d0: pd.Timestamp, d1: pd.Timestamp) -> int:
    return (d1.year - d0.year) * 12 + d1.month - d0.month - (1 if d1.day < d0.day else 0)


def cbot_cf(coupon_pct: float, maturity, delivery_month_start, contract: str = "10y", notional_pct: float = 6.0) -> float:
    """CBOT/CME conversion factor, rounded to 4dp. contract: 'bond'/'10y' (term rounded DOWN to the quarter)
    or '5y'/'2y' (rounded down to the month). Term = first day of delivery month -> maturity (first call if callable).
    Verify against the exchange-published factor: this only predicts it."""
    m = _whole_months(pd.Timestamp(delivery_month_start), pd.Timestamp(maturity))
    n, z = divmod(m, 12)
    quarterly = contract.lower() in ("bond", "10y")
    if quarterly:
        z = z // 3 * 3
    v = z if z < 7 else (3 if quarterly else z - 6)
    cpn, r = coupon_pct / 100.0, 1.0 + notional_pct / 200.0  # r = 1.03 for 6%
    a = r ** (-v / 6.0)
    b = cpn / 2.0 * (6 - v) / 6.0
    c = r ** (-2 * n) if z < 7 else r ** (-(2 * n + 1))
    d = cpn / (notional_pct / 100.0) * (1.0 - c)
    return round(a * (cpn / 2.0 + c + d) - b, 4)


# ---------------------------------------------------------------- accrued / coupons
def _prev_next_coupon(maturity: pd.Timestamp, d: pd.Timestamp, freq: int = 2):
    step, k = 12 // freq, 0
    while maturity - pd.DateOffset(months=step * k) > d:
        k += 1
    if k == 0:
        raise ValueError("bond matured on or before date")
    return maturity - pd.DateOffset(months=step * k), maturity - pd.DateOffset(months=step * (k - 1))


def accrued(coupon_pct: float, maturity, d, freq: int = 2, day_count: str = "ACT/ACT ICMA") -> float:
    """Accrued per 100 at date d. Supports ACT/ACT ICMA (UST, gilt, Bund, OAT) and ACT/365F (JGB, CAD).
    Other conventions (30/360, JGB simple ACT/365) must be supplied by the caller."""
    maturity, d = pd.Timestamp(maturity), pd.Timestamp(d)
    prev, nxt = _prev_next_coupon(maturity, d, freq)
    if day_count == "ACT/ACT ICMA":
        return coupon_pct / freq * (d - prev).days / (nxt - prev).days
    if day_count in ("ACT/365F", "ACT/365"):
        return coupon_pct * (d - prev).days / 365.0
    raise NotImplementedError(f"day count {day_count}: pass accrued explicitly")


def coupons_between(coupon_pct: float, maturity, settle, delivery, freq: int = 2):
    """[(cash_per_100, days_from_coupon_to_delivery)] for coupons paid in (settle, delivery]."""
    maturity, settle, delivery = map(pd.Timestamp, (maturity, settle, delivery))
    out, k, step = [], 0, 12 // freq
    while True:
        c = maturity - pd.DateOffset(months=step * k)
        if c <= settle:
            break
        if c <= delivery:
            out.append((coupon_pct / freq, (delivery - c).days))
        k += 1
    return out


# ---------------------------------------------------------------- basis core
def forward_clean(clean, ai0, ai_t, repo_pct, days, coupons=(), day_basis=360.0):
    """Clean forward price to delivery by bond + term repo; coupons reinvested at repo to delivery."""
    r = repo_pct / 100.0
    full = (clean + ai0) * (1 + r * days / day_basis)
    for cash, n2 in coupons:
        full -= cash * (1 + r * n2 / day_basis)
    return full - ai_t


def implied_repo(clean, ai0, ai_t, cf, fut, days, coupons=(), day_basis=360.0):
    """IRR in percent: repo rate r such that forward_full(r) = CF*F + AI_T (cash-and-carry, CTD certain)."""
    purchase, invoice = clean + ai0, cf * fut + ai_t
    if days <= 0:
        return float("nan")  # delivery on/before settlement: IRR undefined
    num = invoice + sum(c for c, _ in coupons) - purchase
    den = (purchase * days - sum(c * n2 for c, n2 in coupons)) / day_basis
    return 100.0 * num / den


def basis_metrics(clean, ai0, ai_t, cf, fut, repo_pct, days, coupons=(), day_basis=360.0) -> dict:
    gb = clean - cf * fut
    fwd = forward_clean(clean, ai0, ai_t, repo_pct, days, coupons, day_basis)
    nb = fwd - cf * fut
    return dict(gross_basis=gb, net_basis=nb, carry=gb - nb, fwd_clean=fwd,
                irr_pct=implied_repo(clean, ai0, ai_t, cf, fut, days, coupons, day_basis))


def ctd_table(basket: pd.DataFrame, fut_px: float, settle, delivery, repo_pct=None, day_basis=360.0) -> pd.DataFrame:
    """Basis sheet for one futures price. basket columns: instrument_id, coupon_pct, maturity_date, clean_px,
    conversion_factor; optional coupon_freq (default 2), repo_pct (bond's own term repo to delivery, else GC `repo_pct`).
    Sorted best CTD first: highest (IRR - own repo), which equals highest IRR when no bond is special."""
    settle, delivery = pd.Timestamp(settle), pd.Timestamp(delivery)
    days = (delivery - settle).days
    rows = []
    for b in basket.itertuples(index=False):
        f = int(getattr(b, "coupon_freq", 2) or 2)
        own = getattr(b, "repo_pct", np.nan)
        rp = repo_pct if pd.isna(own) else own
        if rp is None or pd.isna(rp):
            raise ValueError("no repo rate for %s: supply it, do not assume" % b.instrument_id)
        dc = getattr(b, "day_count", None)
        dc = dc if isinstance(dc, str) else "ACT/ACT ICMA"  # canonical bond_static.day_count; unsupported ones raise
        ai0 = accrued(b.coupon_pct, b.maturity_date, settle, f, dc)
        ait = accrued(b.coupon_pct, b.maturity_date, delivery, f, dc)
        cps = coupons_between(b.coupon_pct, b.maturity_date, settle, delivery, f)
        m = basis_metrics(b.clean_px, ai0, ait, b.conversion_factor, fut_px, rp, days, cps, day_basis)
        rows.append(dict(instrument_id=b.instrument_id, repo_pct=rp, **m))
    t = pd.DataFrame(rows)
    t["gb_32nds"], t["nb_32nds"] = t.gross_basis * T32, t.net_basis * T32
    t["irr_minus_repo_bp"] = (t.irr_pct - t.repo_pct) * 100.0
    t = t.sort_values("irr_minus_repo_bp", ascending=False, na_position="last").reset_index(drop=True)
    t["is_ctd"] = (t.index == 0) & t.irr_minus_repo_bp.notna()  # NaN legs (bad quote) are never CTD
    return t


# ---------------------------------------------------------------- hedge sizing
def contracts_cf(face: float, cf: float, contract_size: float = 100_000.0) -> float:
    """CF-weighted contracts per face: locks IRR on a CTD basis (a futures DV01 hedge does not)."""
    return face * cf / contract_size


def tailed(contracts: float, repo_pct: float, days: float, day_basis: float = 360.0) -> float:
    """Tail: reduce contracts by the PV factor to horizon (daily variation margin earns interest)."""
    return contracts / (1 + repo_pct / 100.0 * days / day_basis)


def dv01_contracts(bond_dv01_ccy: float, ctd_fwd_dv01_per_100k_ccy: float, cf: float, contract_size: float = 100_000.0) -> float:
    """Contracts to DV01-hedge a bond. Futures DV01 per contract = CTD forward DV01 (per contract_size face) / CF.
    Equals CF-weighting only for the CTD itself; for any other bond it is the curve-aware answer."""
    return bond_dv01_ccy / (ctd_fwd_dv01_per_100k_ccy * contract_size / 100_000.0 / cf)


# ---------------------------------------------------------------- canonical-table front end
def _read(path: Path) -> pd.DataFrame:
    for ext, fn in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
        p = path.with_suffix(ext)
        if p.exists():
            return fn(p)
    raise FileNotFoundError(f"{path}.csv|.parquet")


def from_canonical(d: Path, fut_id: str, date, snap="settle", delivery="auto", repo_pct=None) -> pd.DataFrame:
    date = pd.Timestamp(date)
    st, bq, fs, fb, fq, rr = (_read(d / n) for n in
                              ("bond_static", "bond_quotes", "fut_static", "fut_basket", "fut_quotes", "repo_rates"))
    fs = fs[fs.fut_id == fut_id]
    fq["date"], bq["date"] = pd.to_datetime(fq["date"]), pd.to_datetime(bq["date"])
    fp = fq[(fq.fut_id == fut_id) & (fq.date == date) & (fq.snap == snap)].price_px.dropna()
    if fs.empty or fp.empty:
        raise ValueError(f"no fut_static / fut_quotes row for {fut_id} on {date.date()} snap={snap} - ask the data adapter")
    fs, fut_px = fs.iloc[0], float(fp.iloc[0])
    day_basis = 365.0 if fs.ccy in ("GBP", "JPY", "CAD", "AUD", "NZD") else 360.0
    fb = fb[(fb.fut_id == fut_id) & (pd.to_datetime(fb.eligible_from) <= date)
            & (fb.eligible_to.isna() | (pd.to_datetime(fb.eligible_to) > date))]
    st = st.sort_values("valid_from").drop_duplicates("instrument_id", keep="last")
    q = bq[(bq.date == date) & (bq.snap == snap)]
    bk = fb.merge(st, on="instrument_id").merge(q, on="instrument_id")
    if bk.empty:
        raise ValueError("empty basket: missing bond_static / bond_quotes / fut_basket rows - ask the data adapter")
    if "settle_date" in bk and bk.settle_date.notna().all():
        settle = pd.Timestamp(bk.settle_date.iloc[0])
    else:  # ponytail: weekend-only calendar; pass bond_quotes.settle_date to be exact
        settle = date + pd.offsets.BDay(int(bk.settle_days.iloc[0]))
    bk["maturity_date"] = pd.to_datetime(bk["maturity_date"])

    def one(dlv):
        dd = pd.Timestamp(dlv).strftime("%Y-%m-%d")
        b = bk.copy()
        own = rr[(pd.to_datetime(rr.date) == date) & (rr.snap == snap) & (rr.term == dd) & (rr.ccy == fs.ccy)]
        b["repo_pct"] = b.instrument_id.map(own[own.collateral.str.startswith("BOND:")].groupby("collateral").rate_pct.mean())
        gc = repo_pct if repo_pct is not None else (own[~own.collateral.str.startswith("BOND:")].rate_pct.mean()
                                                    if (~own.collateral.str.startswith("BOND:")).any() else None)
        return ctd_table(b, fut_px, settle, dlv, gc, day_basis)

    first, last = fs.first_delivery_date, fs.last_delivery_date
    if delivery == "auto":  # positive carry -> price to last delivery day, negative -> first
        t = one(last)
        return t if t.loc[0, "carry"] > 0 else one(first)
    return one({"first": first, "last": last}.get(delivery, delivery))


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    bad = []

    def chk(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.6f} want {want:.6f}")
        if not ok:
            bad.append(name)

    # 1) CBOT CF vs published values (Burghardt App. A; CME Understanding Treasury Futures)
    chk("CF 4-7/8 2/15/12 Jun04", cbot_cf(4.875, "2012-02-15", "2004-06-01"), 0.9328, 5e-5)
    chk("CF 3-5/8 5/15/13 Jun04", cbot_cf(3.625, "2013-05-15", "2004-06-01"), 0.8401, 5e-5)
    chk("CF 2.375 8/15/24 Dec17 TY", cbot_cf(2.375, "2024-08-15", "2017-12-01"), 0.8072, 5e-5)
    chk("CF 1.875 8/15/24 Dec17 TY", cbot_cf(1.875, "2024-08-15", "2017-12-01"), 0.7807, 5e-5)
    chk("CF 7.5 11/15/16 Jun01", cbot_cf(7.5, "2016-11-15", "2001-06-01"), 1.1484, 5e-5)
    chk("CF 8-7/8 8/15/17 Jun01 bond", cbot_cf(8.875, "2017-08-15", "2001-06-01", "bond"), 1.2931, 5e-5)
    chk("CF par bond at notional = 1", cbot_cf(6.0, "2030-06-01", "2024-06-01"), 1.0, 1e-9)

    # 2) Burghardt Ch.1: 7-1/4 8/15/22, clean 119.875, 4/6/01 -> 6/29/01 (84d), repo 4.54%, F 103.9375, CF 1.1481
    mat, s, dl = "2022-08-15", "2001-04-06", "2001-06-29"
    ai0, ait = accrued(7.25, mat, s), accrued(7.25, mat, dl)
    chk("AI settle", ai0, 1.0014, 1e-4)
    chk("AI delivery", ait, 2.683702, 1e-5)
    m = basis_metrics(119.875, ai0, ait, 1.1481, 103.9375, 4.54, 84, coupons_between(7.25, mat, s, dl))
    chk("carry per 100", m["carry"], 0.401836, 2e-4)
    chk("IRR %", m["irr_pct"], 4.03, 5e-3)
    chk("GB 7.5 11/16 (32nds)", (120.625 - 1.1484 * 103.9375) * T32, 40.4, 0.05)

    # 3) Tuckman Ch.11: TYU1 CTD 2.875 5/15/28, 14 May 2021, F=131-17+, CF .8338, 136d, repo .015%
    fut, cf = 131 + 17.5 / 32, 0.8338
    fwd = forward_clean(110.77344, 0.01562, 1.07813, 0.015, 136)
    chk("TYU1 forward clean", fwd, 109.71721, 5e-5)
    chk("TYU1 GB", 110.77344 - cf * fut, 1.0896, 5e-4)
    chk("TYU1 NB", fwd - cf * fut, 0.0334, 5e-4)
    chk("TYU1 IRR % (book: -0.065)", implied_repo(110.77344, 0.01562, 1.07813, cf, fut, 136), -0.065, 2e-3)

    # 4) Analytic identities: NB=0 -> IRR=repo (with and without an intervening coupon); IRR = repo - NB/dirty*360/n
    for cps in ((), ((1.8125, 40),)):
        f0 = forward_clean(101.0, 1.2, 0.3, 3.7, 90, cps)  # clean fwd; choose F so CF*F = fwd -> NB = 0
        chk(f"IRR=repo at NB=0 (coupons={len(cps)})", implied_repo(101.0, 1.2, 0.3, 0.8, f0 / 0.8, 90, cps), 3.7, 1e-9)
    mm = basis_metrics(101.0, 1.2, 0.3, 0.8, 125.0, 3.7, 90)
    chk("IRR = repo - NB/dirty*360/n", mm["irr_pct"], 3.7 - 100 * mm["net_basis"] / 102.2 * 360 / 90, 1e-9)

    # 5) CTD = max IRR, hedge arithmetic
    bk = pd.DataFrame(dict(instrument_id=["A", "B"], coupon_pct=[3.0, 3.0], maturity_date=["2031-02-15", "2031-02-15"],
                           clean_px=[100.0, 100.0], conversion_factor=[0.80, 0.80]))
    fut_fair = forward_clean(100.0, accrued(3, "2031-02-15", "2026-11-12"), accrued(3, "2031-02-15", "2026-12-31"),
                             3.7, 49) / 0.80
    t = ctd_table(bk.assign(clean_px=[100.0, 100.5]), fut_fair, "2026-11-12", "2026-12-31", 3.7)
    chk("CTD is the cheaper bond (A=0, B>0 NB)", float(t.instrument_id.iloc[0] == "A"), 1.0, 0)
    chk("CTD IRR = repo", t.irr_pct.iloc[0], 3.7, 1e-9)
    chk("contracts $10mm CF .8072", contracts_cf(10e6, 0.8072), 80.72, 1e-9)
    chk("tail", tailed(10000 * 0.8006, 1.10, 116), 7978, 1)
    chk("DV01 hedge 10mm May-27 (CME: 108.3)", dv01_contracts(8558, 63.78, 0.8072), 108.31, 0.01)
    # 6) edge cases and the canonical-table front end (Tuckman TYU1 case, own repo beats GC, delivery auto -> last day)
    chk("IRR undefined when days<=0", float(np.isnan(implied_repo(100, 0, 0, 1, 100, 0))), 1.0, 0)
    chk("ACT/365F accrued", accrued(1.0, "2030-01-15", "2025-04-15", 2, "ACT/365F"), 1.0 * 90 / 365, 1e-12)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d, bid, fid = Path(td), "BOND:X", "FUT:ZN:2021-09"
        pd.DataFrame(dict(instrument_id=[bid], valid_from=["2020-01-01"], coupon_pct=[2.875], coupon_freq=[2], day_count=["ACT/ACT ICMA"],
                          maturity_date=["2028-05-15"], settle_days=[1])).to_csv(d / "bond_static.csv", index=False)
        pd.DataFrame(dict(date=["2021-05-14"], snap=["settle"], instrument_id=[bid], clean_px=[110.77344],
                          settle_date=["2021-05-17"])).to_csv(d / "bond_quotes.csv", index=False)
        pd.DataFrame(dict(fut_id=[fid], ccy=["USD"], first_delivery_date=["2021-09-01"], last_delivery_date=["2021-09-30"])
                     ).to_csv(d / "fut_static.csv", index=False)
        pd.DataFrame(dict(fut_id=[fid], instrument_id=[bid], conversion_factor=[0.8338], eligible_from=["2021-03-01"],
                          eligible_to=[np.nan])).to_csv(d / "fut_basket.csv", index=False)
        pd.DataFrame(dict(date=["2021-05-14"], snap=["settle"], fut_id=[fid], price_px=[fut])).to_csv(d / "fut_quotes.csv", index=False)
        pd.DataFrame(dict(date=["2021-05-14"] * 2, snap=["settle"] * 2, ccy=["USD"] * 2, collateral=["GC_US", bid],
                          term=["2021-09-30"] * 2, rate_pct=[0.50, 0.015])).to_csv(d / "repo_rates.csv", index=False)
        r = from_canonical(d, fid, "2021-05-14")
        chk("front end NB (32nds, book 1.1)", float(r.nb_32nds.iloc[0]), 1.07, 0.02)
        chk("front end IRR % (book -0.065)", float(r.irr_pct.iloc[0]), -0.065, 2e-3)
    print("SELFTEST", "FAILED: " + ", ".join(bad) if bad else "PASSED")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fut-id")
    ap.add_argument("--date")
    ap.add_argument("--snap", default="settle")
    ap.add_argument("--dir", help="folder holding the canonical tables as csv or parquet")
    ap.add_argument("--delivery", default="auto", help="auto | first | last | YYYY-MM-DD")
    ap.add_argument("--repo-pct", type=float, help="GC term repo override; otherwise repo_rates is used")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.fut_id and a.date and a.dir):
        ap.error("--fut-id, --date and --dir are required (or --selftest)")
    t = from_canonical(Path(a.dir), a.fut_id, a.date, a.snap, a.delivery, a.repo_pct)
    cols = ["instrument_id", "gb_32nds", "carry", "nb_32nds", "irr_pct", "repo_pct", "irr_minus_repo_bp", "is_ctd"]
    print(t[cols].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
