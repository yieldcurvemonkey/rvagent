#!/usr/bin/env python3
"""Compounded-in-arrears RFR accrual, fixing conventions and fixing-risk ladder.

Conventions: rates in PERCENT (3.92 = 3.92%), notionals in currency, sensitivities per 1bp.
Functions take pandas/numpy objects; the CLI reads a canonical `rate_fixings` CSV/Parquet.

Methods (see SKILL.md): plain/payment_delay, obs_shift n, lookback n, lockout n.
Cash of the float leg = N * (prod_k (1 + r_k w_k / B) - 1), w_k = calendar days the rate is applied,
B = day-count basis (360 or 365). Annualised rate = cash / N * B / sum(w).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


def compound_rate(rates_pct, days, basis=360.0):
    """Compounded period rate in percent: [prod(1 + r_i d_i/B) - 1] * B / sum(d) * 100."""
    r = np.asarray(rates_pct, float) / 100.0
    d = np.asarray(days, float)
    return (np.prod(1.0 + r * d / basis) - 1.0) * basis / d.sum() * 100.0


def average_rate(rates_pct, days):
    """Arithmetic (SR1-style) day-weighted average, percent."""
    r, d = np.asarray(rates_pct, float), np.asarray(days, float)
    return float((r * d).sum() / d.sum())


def _calendar(start, end, n_back, holidays):
    """Business days around [start, end); returns (all_bd, i0, i1), accrual days = all_bd[i0:i1]."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    lo = start - pd.Timedelta(days=3 * n_back + 10)
    bd = pd.bdate_range(lo, end + pd.Timedelta(days=10), freq="C", holidays=list(holidays))
    i0, i1 = int(bd.searchsorted(start)), int(bd.searchsorted(end))
    if i0 >= len(bd) or bd[i0] != start:
        raise ValueError(f"start {start.date()} is not a business day: adjust the accrual start first")
    return bd, i0, i1


def accrual_map(start, end, method="plain", n=0, holidays=()):
    """Per accrual day: (source fixing date, weight days). Also returns the full BD index.

    plain / payment_delay: rate of the day itself.   obs_shift n: observation period shifted n BD
    earlier, weights = the observed days' own day counts.   lookback n: day i uses the rate of day
    i-n, weights from the unshifted calendar.   lockout n: the last n days reuse the rate of the day
    before them, so the locked rate carries n+1 days (book convention; check your confirm).
    """
    bd, i0, i1 = _calendar(start, end, n, holidays)
    end = pd.Timestamp(end)
    if method in ("plain", "payment_delay"):
        idx = [(j, j) for j in range(i0, i1)]
    elif method == "lookback":
        idx = [(j - n, j) for j in range(i0, i1)]
    elif method == "lockout":
        lock = i1 - 1 - n
        idx = [(j if j <= lock else lock, j) for j in range(i0, i1)]
    elif method == "obs_shift":
        idx = [(j - n, j - n) for j in range(i0, i1)]
    else:
        raise ValueError(f"unknown method {method!r}")
    rows = []
    for src, day in idx:
        w = (min(bd[day + 1], end) - bd[day]).days if method != "obs_shift" else (bd[day + 1] - bd[day]).days
        rows.append((bd[src], w))
    return pd.DataFrame(rows, columns=["source", "weight_days"]), bd


def period_rate(fix_pct: pd.Series, start, end, method="plain", n=0, basis=360.0, holidays=()):
    """Compounded period rate in percent. fix_pct indexed by fixing date (must cover all sources)."""
    m, _ = accrual_map(start, end, method, n, holidays)
    r = fix_pct.reindex(m["source"]).to_numpy(float)
    if np.isnan(r).any():
        raise ValueError("missing fixings: " + ", ".join(str(d.date()) for d in m["source"][np.isnan(r)]))
    return compound_rate(r, m["weight_days"], basis)


def fixing_ladder(fix_pct: pd.Series, start, end, method="plain", n=0, basis=360.0, holidays=(),
                  notional=1e6, pay_date=None, disc_rate_pct=None):
    """Risk per fixing date: cash per 1bp and the 'one-day-equivalent' notional of that fixing.

    dC/dr_s = N * sum_{k: src=s} (w_k/B) * prod / (1 + r_k w_k/B)   (discount factors held fixed)
    N_s    = dC/dr_s * v_pay / ((d_own_s/B) * v(m_s)), d_own_s = days from fixing date to next BD,
    v(t) = (1 + disc/B)^-(t - start).days (flat, default disc = mean fixing). Unit: currency.
    """
    m, bd = accrual_map(start, end, method, n, holidays)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    pay = pd.Timestamp(pay_date) if pay_date is not None else end
    r = fix_pct.reindex(m["source"]).to_numpy(float) / 100.0
    if np.isnan(r).any():
        raise ValueError("missing fixings for ladder")
    w = m["weight_days"].to_numpy(float)
    g = 1.0 + r * w / basis
    prod = g.prod()
    disc = (np.nanmean(r) if disc_rate_pct is None else disc_rate_pct / 100.0)
    v = lambda t: (1.0 + disc / basis) ** (-(pd.Timestamp(t) - start).days)  # noqa: E731
    d_k = notional * (w / basis) * prod / g  # cash per unit rate, per accrual day
    out = pd.DataFrame({"source": m["source"], "dC": d_k}).groupby("source", sort=True).sum()
    pos = bd.get_indexer(out.index)
    d_own = np.array([(bd[p + 1] - bd[p]).days for p in pos], float)
    nxt = bd[pos + 1]
    out["cash_per_bp"] = out["dC"] * 1e-4 * v(pay)
    out["equiv_notional"] = out["dC"] * v(pay) / ((d_own / basis) * np.array([v(t) for t in nxt]))
    out["d_own_days"] = d_own
    return out[["cash_per_bp", "equiv_notional", "d_own_days"]]


def fixing_ladder_asof(ladder: pd.DataFrame, asof):
    """Split ladder into fixed (<= asof) and still-open risk. Open cash/bp is the live reset risk."""
    open_ = ladder[ladder.index > pd.Timestamp(asof)]
    return {"open_cash_per_bp": float(open_["cash_per_bp"].sum()),
            "fixed_cash_per_bp": float(ladder["cash_per_bp"].sum() - open_["cash_per_bp"].sum()),
            "n_open": int(len(open_))}


def sr3_price(fix_pct: pd.Series, ref_start, ref_end, holidays=(), basis=360.0):
    """SR3-style price = 100 - compounded rate over [ref_start, ref_end) (plain method)."""
    return 100.0 - period_rate(fix_pct, ref_start, ref_end, "plain", 0, basis, holidays)


def contract_bp_value(fix_pct: pd.Series, ref_start, ref_end, asof, bp_value=25.0, basis=360.0, holidays=()):
    """Live value of 1bp (parallel bump of all still-unpublished daily fixings) of a compounded-RFR
    futures contract: bp_value * (B/D) * sum_open dC/dr_k  (N=1, no discounting). = bp_value with no
    fixings known, 0 when all known. fix_pct must hold every day (known + forward). asof = last published
    fixing date (a fixing is open if its source date is later)."""
    m, _ = accrual_map(ref_start, ref_end, "plain", 0, holidays)
    lad = fixing_ladder(fix_pct, ref_start, ref_end, "plain", 0, basis, holidays, 1.0, disc_rate_pct=0.0)
    open_ = lad[lad.index > pd.Timestamp(asof)]["cash_per_bp"].sum() * 1e4  # per unit rate
    return float(bp_value * basis / m["weight_days"].sum() * open_)


def futures_convexity_bp(sigma_bp: float, t_years: float, kind="compounded", beta: float | None = None):
    """Futures-minus-forward rate (bp), normal one-factor, constant drift (Tuckman & Serrat s12.6).

    term:       s^2 t^2/2 + s^2 t b/2                  (b = 0.25 for 3M)
    average:    ... + s^2 b^2/6                        (b = 1/12 for 1M)
    compounded: ... + s^2 b^2/3                        (b = 0.25 for 3M)
    t = years to START of the reference period; sigma_bp = normal short-rate vol, bp/yr.
    """
    b = beta if beta is not None else {"term": 0.25, "average": 1 / 12, "compounded": 0.25}[kind]
    s2 = (sigma_bp / 1e4) ** 2
    c = s2 * t_years**2 / 2 + s2 * t_years * b / 2
    if kind == "average":
        c += s2 * b**2 / 6
    elif kind == "compounded":
        c += s2 * b**2 / 3
    return c * 1e4


def _selftest():
    ok = True

    def chk(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name}: got {got:.6f} want {want:.6f} (tol {tol})")

    # 1. Darbyshire: 1% and 2% O/N, Act/365F, 2 days -> 1.5000274%
    chk("2-day compounding", compound_rate([1, 2], [1, 1], 365), 1.5000274, 1e-6)
    # 2. Credit Suisse 1w OIS: breakeven 0.1286%, Friday carries 3 days
    chk("1w OIS breakeven", compound_rate([.12, .13, .14, .13, .10], [1, 1, 3, 1, 1], 360), 0.1286, 5e-5)
    # 3. Huggins & Schaller Table 3.2: 1y constant SOFR 3% -> ~3.05%, 5% -> ~5.13%
    chk("1y const 5%", compound_rate([5] * 365, [1] * 365, 360), 5.13, 6e-3)
    chk("1y const 3%", compound_rate([3] * 365, [1] * 365, 360), 3.05, 6e-3)
    # 4. Tuckman & Serrat SR3 Jun-22: 42d @0.51 then 56d @0.76 over 98d -> 0.653%
    chk("SR3 Jun-22", compound_rate([.51, .76], [42, 56], 360), 0.653, 6e-4)
    # 5. Convexity table (sigma 80bp): compounded 3M at t=1,10y -> 0.4, 32.8bp; avg 1M t=5 -> 8.1
    chk("convexity t=1", futures_convexity_bp(80, 1), 0.4, 0.05)
    chk("convexity t=10", futures_convexity_bp(80, 10), 32.8, 0.05)
    chk("convexity avg t=5", futures_convexity_bp(80, 5, "average"), 8.1, 0.05)
    # 6. Darbyshire Table 8.4 fixing notionals: 3-10 Feb 2022, 1mm, all rates 4.03%, Act/360, pay at end
    hol = []
    fx = pd.Series(4.03, index=pd.bdate_range("2022-01-20", "2022-02-28"))
    tab = {
        ("plain", 0): {"2022-02-03": 1_000_000, "2022-02-04": 1_000_112, "2022-02-07": 1_000_447,
                       "2022-02-08": 1_000_559, "2022-02-09": 1_000_671},
        ("obs_shift", 3): {"2022-01-31": 999_665, "2022-02-01": 999_776, "2022-02-02": 999_888,
                           "2022-02-03": 1_000_000, "2022-02-04": 1_000_112},
        ("lockout", 2): {"2022-02-03": 1_000_000, "2022-02-04": 1_000_112, "2022-02-07": 3_001_342},
        ("lookback", 3): {"2022-01-31": 999_665, "2022-02-01": 2_998_658, "2022-02-02": 999_888,
                          "2022-02-03": 1_000_000, "2022-02-04": 333_445},
    }
    for (meth, n), want in tab.items():
        lad = fixing_ladder(fx, "2022-02-03", "2022-02-10", meth, n, 360, hol, 1e6, disc_rate_pct=4.03)
        for d, v in want.items():
            chk(f"Table 8.4 {meth}{n} {d}", lad.loc[pd.Timestamp(d), "equiv_notional"], v, 2.5)
    # 7. ladder vs brute-force bump of the compounded cash (independent check of the derivative)
    rng = np.random.default_rng(1)
    fx2 = pd.Series(4 + rng.normal(0, 0.2, len(fx)), index=fx.index)
    lad = fixing_ladder(fx2, "2022-02-03", "2022-02-10", "lookback", 3, 360, hol, 1e6, disc_rate_pct=0.0)
    d0 = pd.Timestamp("2022-02-01")
    up = fx2.copy(); up[d0] += 0.01
    m, _ = accrual_map("2022-02-03", "2022-02-10", "lookback", 3, hol)
    cash = lambda s: 1e6 * (np.prod(1 + s.reindex(m["source"]).to_numpy() / 100 * m["weight_days"] / 360) - 1)  # noqa: E731
    chk("bump vs analytic cash/bp", cash(up) - cash(fx2), lad.loc[d0, "cash_per_bp"], 1e-3)
    # 8. SR1 vs SR3 gap at constant 5% over 91 days is about 3bp
    gap = (compound_rate([5] * 91, [1] * 91) - average_rate([5] * 91, [1] * 91)) * 100
    chk("SR3-SR1 gap bp", gap, 3.2, 0.3)
    # 9. front-contract bp value: 25 with nothing fixed, ~25*fraction open mid-period, 0 when all fixed
    ref = pd.Series(4.0, index=pd.bdate_range("2022-02-01", "2022-07-15"))
    a, b = "2022-03-16", "2022-06-15"
    chk("bp value none fixed", contract_bp_value(ref, a, b, "2022-03-15"), 25.0, 0.4)
    chk("bp value all fixed", contract_bp_value(ref, a, b, "2022-06-15"), 0.0, 1e-9)
    chk("bp value ~half fixed", contract_bp_value(ref, a, b, "2022-04-29"), 25 * 44 / 91, 0.4)  # Fri 29-Apr fixing covers the weekend; 44 days open
    # exact check: bump every open fixing by 1bp and reprice (SR3 rate in percent -> bp, x USD 25)
    for asof in ("2022-03-15", "2022-04-29"):
        ub = ref.copy(); ub[ub.index > pd.Timestamp(asof)] += 0.01
        bump = 25.0 * 100.0 * (period_rate(ub, a, b) - period_rate(ref, a, b))
        chk(f"bp value vs bump {asof}", contract_bp_value(ref, a, b, asof), bump, 5e-3)
    # a non-business-day accrual start must be refused, not silently shifted
    try:
        accrual_map("2022-03-19", "2022-03-25"); chk("weekend start refused", 0, 1, 0)
    except ValueError:
        chk("weekend start refused", 1, 1, 0)
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def _load(path):
    df = pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)
    return df


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fixings", help="canonical rate_fixings CSV/Parquet")
    ap.add_argument("--index", help="index_id, e.g. USD-SOFR")
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--method", default="plain", choices=["plain", "payment_delay", "obs_shift", "lookback", "lockout"])
    ap.add_argument("--n", type=int, default=0, help="shift / lookback / lockout business days")
    ap.add_argument("--basis", type=float, default=360.0)
    ap.add_argument("--notional", type=float, default=1e8)
    ap.add_argument("--asof", help="last published fixing date; later days use --fwd-pct")
    ap.add_argument("--fwd-pct", type=float, help="flat forward for days after --asof")
    ap.add_argument("--calendars", help="canonical calendars CSV/Parquet"); ap.add_argument("--calendar-id")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not (a.fixings and a.index and a.start and a.end):
        ap.error("need --fixings --index --start --end (or --selftest)")
    f = _load(a.fixings)
    f = f[f.index_id == a.index].copy()
    f["fixing_date"] = pd.to_datetime(f["fixing_date"])
    if "pub_ts_utc" in f:  # latest vintage per date
        f = f.sort_values("pub_ts_utc").drop_duplicates("fixing_date", keep="last")
    s = f.set_index("fixing_date")["rate_pct"].sort_index()
    hol = ()
    if a.calendars and a.calendar_id:
        c = _load(a.calendars)
        hol = pd.to_datetime(c[(c.calendar_id == a.calendar_id) & (~c.is_business_day.astype(bool))].cal_date)
    if a.fwd_pct is not None:
        full = pd.bdate_range(s.index.min(), pd.Timestamp(a.end) + pd.Timedelta(days=10), freq="C", holidays=list(hol))
        cut = pd.Timestamp(a.asof) if a.asof else s.index.max()
        s = s.reindex(full)
        s[s.index > cut] = a.fwd_pct
    R = period_rate(s, a.start, a.end, a.method, a.n, a.basis, hol)
    lad = fixing_ladder(s, a.start, a.end, a.method, a.n, a.basis, hol, a.notional)
    print(f"compounded rate {R:.5f}%  ({a.method} {a.n})")
    print(lad.round(2).to_string())
    if a.asof:
        print(fixing_ladder_asof(lad, a.asof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
