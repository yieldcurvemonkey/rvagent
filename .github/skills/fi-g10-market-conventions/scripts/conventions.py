#!/usr/bin/env python3
"""Convention primitives for G10 rates: day-count fractions, business-day adjustment, compounded overnight
(RFR / OIS) period rates, SOFR-strip to OIS, bond accrued interest, UST 32nds quotes, US Treasury futures
conversion factors, implied repo, cash-settled AUD bond futures valuation, linker reference index.

Functions take plain dates / numbers / pandas objects. The CLI reads the canonical `rate_fixings` table.

  python conventions.py dcf 2016-06-01 2016-09-01
  python conventions.py compound --fixings rate_fixings.parquet --index USD-SOFR --start 2026-09-16 --end 2026-12-16 --basis 360
  python conventions.py px32 99-24+            # cash 32nds
  python conventions.py px32 97-187 --futures  # futures 32nds
  python conventions.py cf 8.875 16 0          # CF: coupon %, whole years, extra months (down to a quarter; --monthly for TU/3y/FV)
  python conventions.py --selftest
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas as pd

DAY_COUNTS = ("ACT/360", "ACT/365F", "30/360", "30E/360", "ACT/ACT ISDA", "1/1")


def _d(x) -> date:
    return pd.Timestamp(x).date()


def year_fraction(start, end, dc: str) -> float:
    """Day-count fraction. 30/360 = bond basis (end 31st -> 30th only if start day >= 30); 30E/360 = Eurobond basis
    (any 31st -> 30th). ACT/ACT ISDA splits by calendar year (/365 or /366)."""
    s, e = _d(start), _d(end)
    dc = dc.upper()
    if dc == "ACT/360":
        return (e - s).days / 360.0
    if dc in ("ACT/365F", "ACT/365"):
        return (e - s).days / 365.0
    if dc in ("30/360", "30E/360"):
        d1, d2 = min(s.day, 30), e.day
        if d2 == 31 and (dc == "30E/360" or d1 == 30):
            d2 = 30
        return (360 * (e.year - s.year) + 30 * (e.month - s.month) + (d2 - d1)) / 360.0
    if dc == "ACT/ACT ISDA":
        yf, cur = 0.0, s
        while cur < e:
            nxt = min(e, date(cur.year + 1, 1, 1))
            yf += (nxt - cur).days / (366.0 if pd.Timestamp(cur).is_leap_year else 365.0)
            cur = nxt
        return yf
    if dc == "1/1":
        return 1.0
    raise ValueError(f"unknown day count {dc!r}; use one of {DAY_COUNTS}")


def adjust(d, rule: str = "MF", holidays=frozenset()) -> date:
    """Business-day adjustment: F, MF, P, MP or U (unadjusted). Weekends are always non-business days."""
    d, hol = _d(d), {_d(h) for h in holidays}
    good = lambda x: x.weekday() < 5 and x not in hol  # noqa: E731
    rule = rule.upper()
    if rule == "U" or good(d):
        return d
    step = 1 if rule in ("F", "MF") else -1
    x = d
    while not good(x):
        x += timedelta(days=step)
    if rule in ("MF", "MP") and x.month != d.month:  # modified: never cross the month boundary
        x = d
        while not good(x):
            x -= timedelta(days=step)
    return x


def compounded_rate(rates_pct, day_weights, basis: int) -> float:
    """Daily-compounded overnight rate over a period, in pct: [prod(1 + r_i n_i / B) - 1] * B / sum(n_i).
    n_i = calendar days fixing i applies (Friday = 3 over a weekend). B = the index day-count basis: 360 for
    SOFR / ESTR / SARON, 365 for SONIA / TONA / CORRA (365F, no leap adjustment) / AONIA / NZIONA / NOWA."""
    rates_pct, day_weights = list(rates_pct), list(day_weights)
    if len(rates_pct) != len(day_weights):
        raise ValueError("rates and day weights differ in length")
    growth, days = 1.0, 0
    for r, n in zip(rates_pct, day_weights):
        if r != r:  # NaN fixing: never compound through a gap
            raise ValueError("NaN fixing in compounding window")
        growth *= 1.0 + float(r) / 100.0 * int(n) / basis
        days += int(n)
    if days == 0:
        raise ValueError("empty period")
    return (growth - 1.0) * basis / days * 100.0


def compound_from_fixings(fix: pd.DataFrame, start, end, basis: int) -> float:
    """Compound a published fixing series over [start, end). Each fixing applies until the next fixing date, so the
    fixing dates themselves define the business-day calendar. `fix` has columns fixing_date, rate_pct."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    f = fix.assign(fixing_date=pd.to_datetime(fix["fixing_date"])).sort_values("fixing_date")
    f = f[(f["fixing_date"] >= s) & (f["fixing_date"] < e)]
    if f.empty or f["fixing_date"].iloc[0] != s:
        raise ValueError(f"no fixing on period start {s.date()} (start must be a business day of the index)")
    nxt = f["fixing_date"].shift(-1).fillna(e)
    n = (nxt - f["fixing_date"]).dt.days
    if (n > 5).any():  # ponytail: crude gap check; a calendar-aware check needs the `calendars` table
        raise ValueError(f"gap > 5 calendar days in fixings near {f['fixing_date'][n > 5].iloc[0].date()}")
    return compounded_rate(f["rate_pct"], n, basis)


def ois_from_future_strip(prices, days_per_period, basis: int = 360) -> float:
    """Par OIS rate (pct) from a contiguous strip of 3M compounded-RFR futures (SR3-style, 100 - rate).
    DF_i = 1 / (1 + R_i d_i / B), CDF = running product; fixed = PV(float) * B / sum(CDF_i d_i). Same day count on
    both legs and no payment delay (the CME worked example)."""
    prices, days_per_period = list(prices), list(days_per_period)
    if len(prices) != len(days_per_period) or any(p != p for p in prices):
        raise ValueError("strip needs equal-length, NaN-free prices and day counts")
    cdf, pv_float, annuity = 1.0, 0.0, 0.0
    for p, d in zip(prices, days_per_period):
        r = (100.0 - float(p)) / 100.0
        cdf /= 1.0 + r * d / basis
        pv_float += cdf * r * d / basis
        annuity += cdf * d
    return pv_float * basis / annuity * 100.0


def compounding_equivalent(rate_pct: float, from_freq: int, to_freq: int) -> float:
    """Quote the same effective annual growth at another compounding frequency (pct)."""
    g = (1 + rate_pct / 100.0 / from_freq) ** from_freq
    return (g ** (1.0 / to_freq) - 1.0) * to_freq * 100.0


def bill_discount_to_simple(disc_pct: float, days: int, basis: int = 360) -> float:
    """Bill discount rate -> money-market simple yield (pct, same basis). P = 100 (1 - d t); y = (100/P - 1)/t."""
    t = days / basis
    return (1.0 / (1.0 - disc_pct / 100.0 * t) - 1.0) / t * 100.0


def accrued(coupon_pct: float, freq: int, last_cpn, next_cpn, settle, dc: str = "ACT/ACT ICMA") -> float:
    """Accrued interest per 100 face. ACT/ACT ICMA: (c/f) * days / days_in_period (UST, gilts, Bunds, OATs, BTPs).
    ACT/365F: c * days / 365 (Canada). Anything else: c * year_fraction(last_cpn, settle, dc) (e.g. 30E/360)."""
    days = (_d(settle) - _d(last_cpn)).days
    if not _d(last_cpn) <= _d(settle) <= _d(next_cpn):
        raise ValueError("settle must lie in [last_cpn, next_cpn]; ex-dividend (negative accrued) is not handled")
    if dc.upper() == "ACT/ACT ICMA":
        return coupon_pct / freq * days / (_d(next_cpn) - _d(last_cpn)).days
    if dc.upper() == "ACT/365F":
        return coupon_pct * days / 365.0
    return coupon_pct * year_fraction(last_cpn, settle, dc)


_FUT_FRAC = {"0": 0.0, "1": 0.125, "2": 0.25, "3": 0.375, "5": 0.5, "6": 0.625, "7": 0.75, "8": 0.875}


def px32(quote: str, futures: bool = False) -> float:
    """UST price in 32nds to decimal. Cash: '+' = 1/64, third digit = eighths of a 32nd (99-245 = 99 + 24/32 + 5/256).
    Futures: the third digit is a truncated decimal of a 32nd: 2 = .25, 5 = .5, 7 = .75 (the 1/4-of-32nd ticks of
    TU/FV); 1, 3, 6, 8 = .125, .375, .625, .875 (the 1/8-of-32nd TU tick). Cash 97-186 = futures 97-187."""
    q = quote.strip()
    whole, frac = q.split("-") if "-" in q else (q, "0")
    plus = frac.endswith("+")
    frac = frac.rstrip("+")
    t32 = float(frac[:2] or 0)
    if len(frac) > 2:
        if not futures and int(frac[2]) > 7:
            raise ValueError(f"cash third digit counts eighths of a 32nd (0-7): {quote!r}")
        t32 += _FUT_FRAC[frac[2]] if futures else int(frac[2]) / 8.0
    if plus:
        t32 += 0.5
    if t32 >= 32:
        raise ValueError(f"bad 32nds quote {quote!r}")
    return float(whole) + t32 / 32.0


def ust_conversion_factor(coupon_pct: float, years: int, months: int, monthly: bool = False) -> float:
    """US Treasury futures conversion factor: price per 1 of the bond at a 6% yield. `years`, `months` = remaining life
    from the first day of the delivery month. Months are rounded DOWN to a whole quarter (z = 0, 3, 6, 9) for TY, Ultra 10y,
    US and Ultra bond; pass monthly=True for TU, 3-year and FV, which round down to the whole month (z = 0..11, v = z - 6
    when z >= 7)."""
    if not 0 <= months <= 11:
        raise ValueError("months must be 0..11 (carry whole years in `years`)")
    c, z = coupon_pct / 100.0, (months if monthly else (months // 3) * 3)
    v = z if z < 7 else (z - 6 if monthly else 3)
    a = 1.0 / 1.03 ** (v / 6.0)
    b = c / 2.0 * (6 - v) / 6.0
    cp = 1.0 / 1.03 ** (2 * years) if z < 7 else 1.0 / 1.03 ** (2 * years + 1)
    return a * (c / 2.0 + cp + c / 0.06 * (1.0 - cp)) - b


def implied_repo(purchase_dirty: float, invoice: float, days: int, basis: int = 360) -> float:
    """Implied repo rate in pct, no coupon in the period: (invoice / purchase - 1) * basis / days. Both dirty."""
    return (invoice / purchase_dirty - 1.0) * basis / days * 100.0


def au_bond_future_value(price: float, coupon: float = 6.0, n_half_years: int = 20) -> float:
    """ASX cash-settled Treasury bond future contract value in A$: price = 100 - yield; n = 20 (10y), 6 (3y).
    1000 * [ (c/2)(1 - v^n)/i + 100 v^n ], i = yield/200, v = 1/(1+i). Tick value depends on the yield level."""
    i = (100.0 - price) / 200.0
    v = 1.0 / (1.0 + i)
    return 1000.0 * (coupon / 2.0 * (1.0 - v**n_half_years) / i + 100.0 * v**n_half_years)


def linker_ref_index(cpi_m3: float, cpi_m2: float, day: int, days_in_month: int) -> float:
    """Canadian-model reference index with a 3-month lag, interpolated by day of month:
    RV = CPI(m-3) + (day - 1) / ND * (CPI(m-2) - CPI(m-3)). (US TIPS, OATei, DBRei, BTPei...)"""
    return cpi_m3 + (day - 1) / days_in_month * (cpi_m2 - cpi_m3)


def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def _latest_vintage(df: pd.DataFrame, asof=None) -> pd.DataFrame:
    """Keep one row per fixing_date: final print if flagged, else the latest publication. `asof` (UTC timestamp) drops
    vintages published later, so a historical signal never sees a print it could not have had."""
    if asof is not None and "pub_ts_utc" in df:
        df = df[pd.to_datetime(df["pub_ts_utc"], utc=True) <= pd.Timestamp(asof, tz="UTC")]
    keys = [c for c in ("is_final", "pub_ts_utc") if c in df]
    return (df.sort_values(keys) if keys else df).drop_duplicates("fixing_date", keep="last")


def selftest() -> int:
    checks = []

    def ok(name, got, want, tol):
        checks.append((name, abs(got - want) <= tol, got, want))

    # Darbyshire, PTIRD 3rd ed. Ex 2.3: 1-Jun-16 to 1-Sep-16
    ok("ACT/ACT ISDA 92/366", year_fraction("2016-06-01", "2016-09-01", "ACT/ACT ISDA"), 0.251366120, 1e-9)
    ok("30/360 90/360", year_fraction("2016-06-01", "2016-09-01", "30/360"), 0.25, 1e-12)
    ok("ACT/365F 92/365", year_fraction("2016-06-01", "2016-09-01", "ACT/365F"), 0.252054795, 1e-9)
    # Tuckman & Serrat: 1 Jun to 15 Aug = 75 actual days, 74 on 30/360
    ok("30/360 74 days", year_fraction("2021-06-01", "2021-08-15", "30/360") * 360, 74, 1e-9)
    # 30/360 and 30E/360 differ on a 31st end date when the start is not the 30th/31st
    ok("30/360 end-31 kept", year_fraction("2021-01-15", "2021-03-31", "30/360") * 360, 76, 1e-9)
    ok("30E/360 end-31 cut", year_fraction("2021-01-15", "2021-03-31", "30E/360") * 360, 75, 1e-9)
    ok("30/360 start-30 cuts end-31", year_fraction("2021-01-30", "2021-03-31", "30/360") * 360, 60, 1e-9)
    # Credit Suisse Basis Points (2010): USD FF OIS 6-Jan-10..13-Jan-10 breakeven 0.1286%
    fx = pd.DataFrame({"fixing_date": ["2010-01-06", "2010-01-07", "2010-01-08", "2010-01-11", "2010-01-12"],
                       "rate_pct": [0.12, 0.13, 0.14, 0.13, 0.10]})
    ok("FF OIS 1w breakeven", compound_from_fixings(fx, "2010-01-06", "2010-01-13", 360), 0.1286, 5e-5)
    # Darbyshire PTIRD Ex 3.4: Thu 2.00, Fri 2.10 (3 days), Mon 2.15, ACT/365F -> 2.0902%
    ok("SONIA-style Ex 3.4", compounded_rate([2.00, 2.10, 2.15], [1, 3, 1], 365), 2.0902, 5e-5)
    # Tuckman & Serrat Ch.12: SR3 Jun-22, 42 days at 0.51% then 56 at 0.76% -> 0.653%
    ok("SR3 Jun-22", compounded_rate([0.51] * 42 + [0.76] * 56, [1] * 98, 360), 0.653, 5e-4)
    # Darbyshire Coding IR: daily fixings 12/13/14% -> 13.0046% compounded (365 basis, 1 day each)
    ok("compound 12/13/14", compounded_rate([12, 13, 14], [1, 1, 1], 365), 13.0046, 5e-4)
    # CME (Rogerson 2025): 8 SOFR futures of 91 days -> 2y IMM OIS 3.3304%
    strip = [95.895, 96.290, 96.605, 96.815, 96.940, 96.985, 96.965, 96.910]
    ok("CME 2y IMM OIS from SR3 strip", ois_from_future_strip(strip, [91] * 8), 3.3304, 5e-5)
    # Tuckman & Serrat Ch.2: 2% annual = 1.9901% semi = 1.9819% monthly
    ok("2% annual -> semi", compounding_equivalent(2.0, 1, 2), 1.9901, 5e-5)
    ok("2% annual -> monthly", compounding_equivalent(2.0, 1, 12), 1.9819, 5e-5)
    # Duering Ch.13: 12% monthly compounded = 12.68% effective
    ok("12% monthly effective", compounding_equivalent(12.0, 12, 1), 12.6825, 5e-4)
    # bill identity: 5% discount over 91 days is 5.0636% simple (360)
    ok("bill disc -> simple", bill_discount_to_simple(5.0, 91), 5.0636, 5e-4)
    # Modified following: Sun 30-Nov-14 -> F Mon 1-Dec, MF Fri 28-Nov (Darbyshire PTIRD)
    checks.append(("MF month-end", adjust("2014-11-30", "MF") == date(2014, 11, 28), adjust("2014-11-30", "MF"), "2014-11-28"))
    checks.append(("F month-end", adjust("2014-11-30", "F") == date(2014, 12, 1), adjust("2014-11-30", "F"), "2014-12-01"))
    # London 2021: 25-Dec + 1d F with substitute days 27/28-Dec -> 29-Dec (Darbyshire, Coding Interest Rates)
    got = adjust(date(2021, 12, 26), "F", {"2021-12-27", "2021-12-28"})
    checks.append(("London substitute days", got == date(2021, 12, 29), got, "2021-12-29"))
    # Tuckman & Serrat Ch.1: UST 0.625s 8/15/30 settle 17-May-21 -> AI 0.15711
    ok("UST accrued", accrued(0.625, 2, "2021-02-15", "2021-08-15", "2021-05-17"), 0.15711, 5e-6)
    # Darbyshire, Coding IR: 5% gilt settle 15-Apr-22 -> 1.43646409; Canada ACT/365F -> 1.42465753
    ok("gilt accrued", accrued(5, 2, "2022-01-01", "2022-07-01", "2022-04-15"), 1.43646409, 1e-8)
    ok("Canada accrued", accrued(5, 2, "2022-01-01", "2022-07-01", "2022-04-15", "ACT/365F"), 1.42465753, 1e-8)
    # 32nds (Duering Ch.16; CME Understanding Treasury Futures)
    ok("99-24+", px32("99-24+"), 99.765625, 1e-12)
    ok("99-245", px32("99-245"), 99.76953125, 1e-12)
    ok("97-18", px32("97-18"), 97.5625, 1e-12)
    ok("cash 97-186 = fut 97-187", px32("97-187", futures=True), px32("97-186"), 1e-12)
    ok("cash 97-18+ = fut 97-185", px32("97-185", futures=True), px32("97-18+"), 1e-12)
    ok("TU 1/8-of-32nd futures digit 1", px32("97-181", futures=True), 97 + 18 / 32 + 0.125 / 32, 1e-12)
    # Burghardt et al. 2005: 8-7/8s of 8/15/17 -> 16y0m -> CF 1.2931 ; 7.5s of 11/15/16 -> 15y3m -> CF 1.1484
    ok("CF 8-7/8 16y0m", ust_conversion_factor(8.875, 16, 0), 1.2931, 5e-5)
    ok("CF 7.5 15y3m", ust_conversion_factor(7.5, 15, 3), 1.1484, 5e-5)
    ok("CF at 6% coupon = 1", ust_conversion_factor(6.0, 10, 0), 1.0, 1e-12)
    # CF by definition: clean price at 6% semi-annual yield, first coupon in (6 - z) months, accrued deducted
    for z in (0, 3, 6, 9):
        cpn, yrs = 4.25, 7
        nxt = (6 - z) % 6 or 6                       # months to next coupon
        first = nxt / 6.0                            # periods to next coupon
        ncf = 2 * yrs + {0: 0, 3: 1, 6: 1, 9: 2}[z]  # coupons remaining
        pv = sum(cpn / 2 / 1.03 ** (first + k) for k in range(ncf)) + 100 / 1.03 ** (first + ncf - 1)
        brute = (pv - cpn / 2 * (1 - first)) / 100
        ok(f"CF by definition z={z}", ust_conversion_factor(cpn, yrs, z), brute, 1e-9)
    # TYU1 (14 May 2021, Tuckman & Serrat Table 11.8): 2.875s of 5/15/28 -> CF .8338 ; 1.125s 2/15/31 -> .6577
    ok("CF TYU1 CTD", ust_conversion_factor(2.875, 6, 6), 0.8338, 5e-5)
    ok("CF 1.125s 2031", ust_conversion_factor(1.125, 9, 3), 0.6577, 5e-5)
    # Burghardt: Sep-2001 contract CF of the 7.5s of 11/15/16 (15y0m) = 1.1470 (book table); 7.25s of 8/15/22 Jun-01 -> 1.1481
    ok("CF 7.5 15y0m", ust_conversion_factor(7.5, 15, 0), 1.1470, 5e-5)
    ok("CF 7.25 21y0m", ust_conversion_factor(7.25, 21, 0), 1.1481, 5e-5)
    # 2y/3y/5y round to the month: monthly CF must equal the by-definition price for every z = 0..11
    for z in range(12):
        cpn, yrs = 3.5, 4
        life = 12 * yrs + z
        first = ((life - 1) % 6 + 1) / 6.0              # periods to the next coupon
        ncf = -(-life // 6)                              # coupons remaining
        pv = sum(cpn / 2 / 1.03 ** (first + k) for k in range(ncf)) + 100 / 1.03 ** (first + ncf - 1)
        ok(f"CF monthly z={z}", ust_conversion_factor(cpn, yrs, z, monthly=True), (pv - cpn / 2 * (1 - first)) / 100, 1e-9)
    # Burghardt App A (CBOT): 4-7/8s of 2/15/12 for Jun-04 (7y 8m15d -> 7y6m) = 0.9328 ; 3-5/8s of 5/15/13 (8y 11m15d -> 8y9m) = 0.8401
    ok("CF 4.875 7y6m", ust_conversion_factor(4.875, 7, 6), 0.9328, 5e-5)
    ok("CF 3.625 8y9m", ust_conversion_factor(3.625, 8, 9), 0.8401, 5e-5)
    # Burghardt: gross basis 120.6250 - 103.9375 * 1.1484 = 1.2632 (7.5s of 11/15/16, Jun-01)
    ok("gross basis", px32("120-20") - px32("103-30") * 1.1484, 1.2632, 5e-5)
    # Burghardt Ch.1 IRR: 7.25s of 8/15/22, clean 119.875 + AI 1.0014 = 120.8764; delivery 84 days on at CF 1.1481, AI 2.683702
    ok("implied repo", implied_repo(120.8764, 103.9375 * 1.1481 + 2.683702, 84), 4.03, 5e-3)
    # Burghardt Exh 9.5 / ASX pricing guide: 6% 10y at 95.00 -> A$107,794.58 (book prints ...795.58); 3y at 95.505
    ok("ASX 10y value", au_bond_future_value(95.0), 107794.58, 0.01)
    ok("ASX 10y tick DV01", (au_bond_future_value(95.01) - au_bond_future_value(94.99)) / 2, 81.63, 0.01)
    ok("ASX 3y value", au_bond_future_value(95.505, 6.0, 6), 104180.10, 0.02)
    # BofA linker primer 2025: OATei ref value 22-Jul-25, index ratio 1.36681; US CPI ref 22-Jul-25 = 321.23423
    rv = linker_ref_index(128.16, 128.08, 22, 31)
    ok("OATei ref value", rv, 128.10581, 5e-6)
    ok("OATei index ratio", rv / 93.72591, 1.36681, 5e-6)
    ok("TIPS ref index", linker_ref_index(320.795, 321.44339, 22, 31), 321.23423, 5e-5)

    bad = [c for c in checks if not c[1]]
    for name, passed, got, want in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}: got {got}, want {want}")
    print(f"{len(checks) - len(bad)}/{len(checks)} checks passed")
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    a = sub.add_parser("dcf", help="year fraction under every supported day count")
    a.add_argument("start")
    a.add_argument("end")
    c = sub.add_parser("compound", help="compounded RFR rate from the canonical rate_fixings table")
    c.add_argument("--fixings", required=True, help="rate_fixings CSV/Parquet (index_id, fixing_date, rate_pct, ...)")
    c.add_argument("--index", required=True, help="index_id, e.g. USD-SOFR")
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True, help="exclusive")
    c.add_argument("--basis", type=int, required=True, choices=(360, 365))
    c.add_argument("--asof", help="UTC timestamp: ignore fixings published after it (no look-ahead)")
    x = sub.add_parser("px32", help="32nds quote to decimal")
    x.add_argument("quote")
    x.add_argument("--futures", action="store_true")
    f = sub.add_parser("cf", help="US Treasury futures conversion factor (6% yield)")
    f.add_argument("coupon_pct", type=float)
    f.add_argument("years", type=int)
    f.add_argument("months", type=int)
    f.add_argument("--monthly", action="store_true", help="round to the month (TU, 3-year, FV) instead of the quarter")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.cmd == "dcf":
        for dc in DAY_COUNTS:
            print(f"{dc:13s} {year_fraction(args.start, args.end, dc):.9f}")
    elif args.cmd == "compound":
        df = _read(args.fixings)
        df = _latest_vintage(df[df["index_id"] == args.index], args.asof)
        r = compound_from_fixings(df, args.start, args.end, args.basis)
        print(f"{args.index} compounded {args.start}..{args.end} (ACT/{args.basis}): {r:.6f} %")
    elif args.cmd == "px32":
        print(f"{px32(args.quote, args.futures):.10f}")
    elif args.cmd == "cf":
        print(f"{ust_conversion_factor(args.coupon_pct, args.years, args.months, args.monthly):.4f}")
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
