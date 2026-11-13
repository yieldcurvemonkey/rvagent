"""OIS/RFR curve construction: par-swap bootstrap (log-linear DF) and meeting-date step curve fitted to
OIS and SOFR-style futures quotes.

Usage:
    python bootstrap.py --selftest
    python bootstrap.py par  --par curve_par.csv --date 2026-11-10 --curve-id USD-SOFR [--start-date 2026-11-12] [--snap eod_ny] [--basis ACT/360] [--out nodes.csv]
    python bootstrap.py step --quotes q.csv --as-of 2026-11-10 --steps 2026-12-10,2027-01-28 [--fixings fix.csv] [--lam 1e-6] [--out steps.csv]
      q.csv columns: kind (ois|sr3|sr1), start, end, value  (ois: rate in pct; sr3/sr1: price = 100 - rate)
      fix.csv columns: date, rate_pct (published overnight fixings; REQUIRED when a contract period started before --as-of)

Conventions (all rates in PERCENT, spreads in bp, DFs are plain numbers):
  * Curve starts at `as_of` (= spot/effective start; pass the T+2 date yourself), DF(as_of) = 1.
  * Interpolation: log-linear DF in calendar days = piecewise-flat overnight forwards. Beyond the last node the
    last forward is extended flat.
  * par(): single payment at maturity if <= 12M, else annual payments counted back from maturity (so 18M pays at 6M
    and 18M). Dates are NOT business-day adjusted and there is no payment lag. # ponytail: add a calendar and
    payment-lag if you must match a CCP to the cent; the model shape is unchanged.
  * Step curve: one overnight rate per period between `step_dates` (use central-bank EFFECTIVE dates); weekdays
    only, Friday's rate accrues 3 days (no holiday calendar). SR3 = ISDA-compounded rate ACT/360 over the reference
    quarter, SR1 = arithmetic average over calendar days of the month, OIS = compounded rate ACT/360, single payment.
Requires numpy, pandas, scipy.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares


# ---------------------------------------------------------------- dates / day counts
def dcf(d0, d1, basis: str = "ACT/360") -> float:
    d0, d1 = pd.Timestamp(d0), pd.Timestamp(d1)
    if basis == "ACT/360":
        return (d1 - d0).days / 360.0
    if basis == "ACT/365F":
        return (d1 - d0).days / 365.0
    if basis == "30/360":
        a, b = min(d0.day, 30), d1.day
        if a == 30:
            b = min(b, 30)
        return (360 * (d1.year - d0.year) + 30 * (d1.month - d0.month) + (b - a)) / 360.0
    raise ValueError(f"unknown day count {basis}")


def parse_tenor(t: str) -> int:
    """'6M' -> 6, '10Y' -> 120 (months). Only M and Y tenors are bootstrapped."""
    t = t.strip().upper()
    if t.endswith("Y"):
        return int(round(float(t[:-1]) * 12))
    if t.endswith("M"):
        m = float(t[:-1])
        if m != int(m):
            raise ValueError(f"tenor {t!r}: fractional months not supported")
        return int(m)
    raise ValueError(f"tenor {t!r}: only M/Y tenors are supported")


def pay_dates(as_of, months: int, freq_months: int = 12):
    """Payment dates counted back from maturity in steps of `freq_months`; single payment if months <= freq."""
    as_of = pd.Timestamp(as_of)
    mat = as_of + pd.DateOffset(months=months)
    out, k = [], 0
    while True:
        d = mat - pd.DateOffset(months=k * freq_months)
        if d <= as_of:
            break
        out.append(d)
        k += 1
    return sorted(out)


# ---------------------------------------------------------------- discount curve
class DFCurve:
    """Log-linear DF curve on calendar days from as_of."""

    def __init__(self, as_of, dates, dfs):
        self.as_of = pd.Timestamp(as_of)
        t = np.array([(pd.Timestamp(d) - self.as_of).days for d in dates], float)
        lnd = np.log(np.asarray(dfs, float))
        o = np.argsort(t)
        t, lnd = t[o], lnd[o]
        if t[0] > 0:
            t, lnd = np.r_[0.0, t], np.r_[0.0, lnd]
        self.t, self.lnd = t, lnd

    def df(self, d) -> float:
        x = (pd.Timestamp(d) - self.as_of).days
        if x > self.t[-1]:  # flat last forward
            if len(self.t) < 2:
                return float(np.exp(self.lnd[-1]))
            slope = (self.lnd[-1] - self.lnd[-2]) / (self.t[-1] - self.t[-2])
            return float(np.exp(self.lnd[-1] + slope * (x - self.t[-1])))
        return float(np.exp(np.interp(x, self.t, self.lnd)))

    def fwd(self, d0, d1, basis: str = "ACT/360") -> float:
        """Simple forward rate d0->d1 in percent."""
        return 100.0 * (self.df(d0) / self.df(d1) - 1.0) / dcf(d0, d1, basis)


def par_rate(curve: DFCurve, months: int, basis: str = "ACT/360", freq_months: int = 12) -> float:
    """Par fixed rate (percent) of a spot-starting OIS read off `curve`: (1 - DF_T) / sum(tau_j DF_j)."""
    ds = pay_dates(curve.as_of, months, freq_months)
    prev, ann = curve.as_of, 0.0
    for d in ds:
        ann += dcf(prev, d, basis) * curve.df(d)
        prev = d
    return 100.0 * (1.0 - curve.df(ds[-1])) / ann


def bootstrap_par(as_of, tenors_months, par_pct, basis: str = "ACT/360", freq_months: int = 12) -> DFCurve:
    """Bootstrap spot-starting par OIS rates (percent) to a log-linear DF curve; reprices every input.
    Intermediate coupon dates between nodes are interpolated, so sparse tenors (e.g. 5Y, 7Y) work: each maturity's
    DF is found with a 1-D root solve."""
    if len(tenors_months) != len(par_pct) or len(tenors_months) == 0:
        raise ValueError("tenors and par rates must be non-empty and the same length")
    if len(set(tenors_months)) != len(tenors_months):
        raise ValueError("duplicate tenors (e.g. 12M and 1Y): one quote per maturity")
    if not np.all(np.isfinite(np.asarray(par_pct, float))):
        raise ValueError("NaN/inf par rate: drop the row or fix the data; never fill it")
    order = np.argsort(tenors_months)
    ms = [int(tenors_months[i]) for i in order]
    rs = [float(par_pct[i]) / 100.0 for i in order]
    dates, dfs = [pd.Timestamp(as_of)], [1.0]
    for m, r in zip(ms, rs):
        ds = pay_dates(as_of, m, freq_months)
        taus, prev = [], pd.Timestamp(as_of)
        for d in ds:
            taus.append(dcf(prev, d, basis))
            prev = d

        def resid(x, ds=ds, taus=taus, r=r):
            c = DFCurve(as_of, dates + [ds[-1]], dfs + [np.exp(x)])
            return r * sum(tau * c.df(d) for tau, d in zip(taus, ds)) + np.exp(x) - 1.0

        x = brentq(resid, -8.0, 2.0, xtol=1e-15, rtol=1e-14)
        dates.append(ds[-1])
        dfs.append(float(np.exp(x)))
    return DFCurve(as_of, dates, dfs)


def nodes_frame(curve: DFCurve, date, curve_id: str, snap: str, tenors: list[str] | None = None) -> pd.DataFrame:
    """`curve_zero`-shaped rows (cc zero ACT/365F)."""
    t, lnd = curve.t[1:], curve.lnd[1:]
    nd = [curve.as_of + pd.Timedelta(days=int(x)) for x in t]
    return pd.DataFrame({
        "date": pd.Timestamp(date).date(), "snap": snap, "curve_id": curve_id,
        "node_date": [d.date() for d in nd], "tenor": tenors if tenors else "",
        "discount_factor": np.exp(lnd), "zero_rate_pct": -100.0 * lnd / (t / 365.0),
        "interpolation": "log_linear_df", "source": "bootstrap.py"})


# ---------------------------------------------------------------- meeting-date step curve
class StepCurve:
    """Piecewise-constant overnight rate between `step_dates` (first must equal as_of)."""

    def __init__(self, as_of, step_dates, rates_pct, fixings: dict | None = None):
        self.as_of = pd.Timestamp(as_of)
        self.steps = pd.DatetimeIndex([pd.Timestamp(d) for d in step_dates])
        assert self.steps[0] == self.as_of, "step_dates[0] must be as_of"
        self.rates = np.asarray(rates_pct, float)
        self.fixings = {pd.Timestamp(k): float(v) for k, v in (fixings or {}).items()}

    def _rate_on(self, d: pd.Timestamp) -> float:
        if d < self.as_of:
            if d not in self.fixings:
                raise KeyError(f"missing fixing for {d.date()} (pass fixings for in-period contracts)")
            return self.fixings[d]
        return float(self.rates[np.searchsorted(self.steps, d, side="right") - 1])

    def _legs(self, start, end):
        """[(rate, calendar days it accrues)] for business days; weekends/holidays accrue to the prior weekday."""
        out: dict[pd.Timestamp, int] = {}
        for d in pd.date_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1)):
            rd = d
            while rd.weekday() >= 5:
                rd -= pd.Timedelta(days=1)
            out[rd] = out.get(rd, 0) + 1
        return [(self._rate_on(rd), n) for rd, n in out.items()]

    def compounded_pct(self, start, end) -> float:
        """ISDA-compounded ACT/360 rate over [start, end): [prod(1 + r_i n_i/360) - 1] * 360 / D."""
        legs, D = self._legs(start, end), (pd.Timestamp(end) - pd.Timestamp(start)).days
        g = np.prod([1.0 + r / 100.0 * n / 360.0 for r, n in legs])
        return 100.0 * (g - 1.0) * 360.0 / D

    def average_pct(self, start, end) -> float:
        """Arithmetic average over calendar days (SR1 / Fed-funds-futures style)."""
        legs = self._legs(start, end)
        return sum(r * n for r, n in legs) / sum(n for _, n in legs)

    def quote_rate(self, kind: str, start, end) -> float:
        return self.average_pct(start, end) if kind == "sr1" else self.compounded_pct(start, end)


def fit_step(as_of, step_dates, quotes: pd.DataFrame, lam: float = 1e-6, fixings: dict | None = None):
    """Least-squares fit of step heights (percent) to quotes (kind, start, end, value).
    Residuals are in bp. The objective is sum(resid_bp^2) + lam * sum(jump_bp^2) over consecutive steps (sum-of-squares
    form, NOT the CME/Heitfield-Park root-sum-square form, so lam is not comparable with their lambda). Use a tiny lam
    (1e-6) only to resolve under-identified steps; raise it to damp noisy back contracts and inspect the residuals.
    Returns (StepCurve, residuals_bp)."""
    bad = set(quotes["kind"]) - {"ois", "sr1", "sr3"}
    if bad:
        raise ValueError(f"unknown quote kind(s) {sorted(bad)}: use ois, sr1 or sr3")
    if quotes[["start", "end", "value"]].isna().any().any():
        raise ValueError("NaN in quotes: drop the row, never fill it")
    sd = [pd.Timestamp(as_of)] + sorted({pd.Timestamp(d) for d in step_dates if pd.Timestamp(d) > pd.Timestamp(as_of)})
    mk = np.array([v if k == "ois" else 100.0 - v for k, v in zip(quotes["kind"], quotes["value"])], float)

    def resid(p):
        c = StepCurve(as_of, sd, p, fixings)
        m = [c.quote_rate(k, s, e) for k, s, e in zip(quotes["kind"], quotes["start"], quotes["end"])]
        r = 100.0 * (np.asarray(m) - mk)
        return np.r_[r, np.sqrt(lam) * 100.0 * np.diff(p)] if lam > 0 else r

    sol = least_squares(resid, np.full(len(sd), mk.mean()), xtol=1e-14, ftol=1e-14, gtol=1e-14)
    c = StepCurve(as_of, sd, sol.x, fixings)
    return c, resid(sol.x)[: len(mk)]


# ---------------------------------------------------------------- futures strip -> IMM OIS rate
def strip_ois_rate(prices, days, basis: int = 360) -> float:
    """Fixed rate (percent) of an IMM-dated OIS replicated by a strip of 3M futures (CME method):
    DF_i = 1/(1 + R_i d_i/basis), R_i = 100 - price_i, CDF = cumulative product, fixed = PV_float / annuity."""
    R = 100.0 - np.asarray(prices, float)
    d = np.asarray(days, float)
    cdf = np.cumprod(1.0 / (1.0 + R / 100.0 * d / basis))
    return 100.0 * float(np.sum(cdf * R / 100.0 * d / basis) / np.sum(cdf * d / basis))


# ---------------------------------------------------------------- selftest
def _selftest() -> None:
    ok = True

    def chk(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name}: got {got:.8g} want {want:.8g} tol {tol:g}")

    # 1. annual 30/360 bootstrap against a published table (USD swaps 5-Jun-2020: 0.307/0.299/0.346% ->
    #    DF 0.996939 / 0.994047 / 0.989687, 1y1y forward 0.291%, 2y1y 0.441%)
    c = bootstrap_par("2020-06-05", [12, 24, 36], [0.307, 0.299, 0.346], basis="30/360")
    for m, want in ((12, 0.996939), (24, 0.994047), (36, 0.989687)):
        chk(f"DF {m}M", c.df(c.as_of + pd.DateOffset(months=m)), want, 6e-7)
    a, b, d3 = (c.as_of + pd.DateOffset(months=m) for m in (12, 24, 36))
    chk("fwd 1y1y 30/360 %", 100 * (c.df(a) / c.df(b) - 1), 0.291, 6e-4)
    chk("fwd 2y1y 30/360 %", 100 * (c.df(b) / c.df(d3) - 1), 0.441, 6e-4)

    # 1b. default ACT/360 path with 184/365-day accruals and an 18M front stub: published SOFR OIS bootstrap
    #     (14-May-2021: 0.0340/0.0460/0.0670/0.1120% -> DF 0.999826/0.999534/0.998979/0.997732)
    c = bootstrap_par("2021-05-18", [6, 12, 18, 24], [0.0340, 0.0460, 0.0670, 0.1120])
    for m, want in ((6, 0.999826), (12, 0.999534), (18, 0.998979), (24, 0.997732)):
        chk(f"ACT/360 DF {m}M", c.df(c.as_of + pd.DateOffset(months=m)), want, 6e-7)

    # 2. ACT/360 round trip with a sparse set incl. 18M (front-stub schedule) and 5Y/10Y (interpolated coupons)
    ten = [3, 6, 12, 18, 24, 60, 120]
    par = [3.60, 3.50, 3.40, 3.35, 3.30, 3.45, 3.80]
    c = bootstrap_par("2026-11-12", ten, par)
    for m, p in zip(ten, par):
        chk(f"reprice {m}M", par_rate(c, m), p, 1e-9)

    # 3. CME strip example (Apr 2025): 8 IMM SOFR futures, 91-day periods -> 3.3304%
    px = [95.895, 96.290, 96.605, 96.815, 96.940, 96.985, 96.965, 96.910]
    chk("IMM OIS from strip %", strip_ois_rate(px, [91] * 8), 3.3304, 5e-4)

    # 4. Step-curve futures maths against Huggins-Schaller numbers: 25bp hike effective 5-May-2022
    #    (decision 4-May): SR1 May moves 25*27/31 = 21.77bp; Mar-22 SR3 (16-Mar..15-Jun) moves 11.3bp.
    asof, hike = "2022-02-25", "2022-05-05"
    sd = [asof, hike]
    base, up = StepCurve(asof, sd, [0.05, 0.05]), StepCurve(asof, sd, [0.05, 0.30])
    chk("SR1 May hike bp", 100 * (up.average_pct("2022-05-01", "2022-06-01") - base.average_pct("2022-05-01", "2022-06-01")),
        25 * 27 / 31, 1e-9)
    chk("SR3 Mar22 hike bp", 100 * (up.compounded_pct("2022-03-16", "2022-06-15") - base.compounded_pct("2022-03-16", "2022-06-15")),
        11.3, 0.1)
    # weekends: Friday accrues 3 days -> 1 week at 5% compounds to (1+.05/360)^4*(1+3*.05/360)... check vs hand value
    w = StepCurve("2022-01-03", ["2022-01-03"], [5.0]).compounded_pct("2022-01-03", "2022-01-10")
    hand = 100 * ((1 + .05 / 360) ** 4 * (1 + .05 * 3 / 360) - 1) * 360 / 7
    chk("weekend accrual", w, hand, 1e-9)

    # 5. recover a known step path from OIS + SR1 + SR3 quotes (exactly determined AND over-determined with lam=0)
    asof = "2026-11-10"
    steps = [asof, "2026-12-10", "2027-01-28", "2027-03-18", "2027-04-29"]
    true = [3.75, 3.50, 3.50, 3.25, 3.00]
    tc = StepCurve(asof, steps, true)
    rows = [("ois", asof, "2027-01-11"), ("ois", asof, "2027-02-10"), ("ois", asof, "2027-04-12"),
            ("ois", asof, "2027-06-10"), ("sr1", "2027-02-01", "2027-03-01"), ("sr1", "2027-04-01", "2027-05-01"),
            ("sr3", "2027-03-17", "2027-06-16")]
    q = pd.DataFrame(rows, columns=["kind", "start", "end"])
    q["value"] = [tc.quote_rate(k, s, e) if k == "ois" else 100 - tc.quote_rate(k, s, e) for k, s, e in rows]
    fit, res = fit_step(asof, steps, q, lam=0.0)
    chk("max |resid| bp", float(np.max(np.abs(res))), 0.0, 1e-6)
    chk("max |step err| bp", float(np.max(np.abs(100 * (fit.rates - np.array(true))))), 0.0, 1e-5)

    # 6. in-period SR3 with known fixings: the SKILL.md stub formula must recover the ACT/360 compounded rate of the
    #    unknown window (5% flat overnight compounds to ~5.02% over 72 days)
    asof = pd.Timestamp("2022-04-04")
    fx = {d: 4.0 for d in pd.date_range("2022-03-16", "2022-04-03")}
    cur = StepCurve(asof, [asof], [5.0], fx)
    R = cur.compounded_pct("2022-03-16", "2022-06-15")
    known = np.prod([1 + r / 36000 * n for r, n in cur._legs("2022-03-16", asof)])
    n_known = (asof - pd.Timestamp("2022-03-16")).days
    d_tot, d_unk = 91, 91 - n_known
    chk("in-period stub R_unknown %", ((R * d_tot / 36000 + 1) / known - 1) * 36000 / d_unk,
        cur.compounded_pct(asof, "2022-06-15"), 1e-9)

    # 6b. jump penalty: step 1 is constrained by no quote, so lam > 0 must set it equal to step 2 (no jump)
    q = pd.DataFrame([("sr1", "2026-02-02", "2026-03-02", 97.0), ("sr1", "2026-04-01", "2026-05-01", 96.0)],
                     columns=["kind", "start", "end", "value"])
    fit, _ = fit_step("2026-01-05", ["2026-02-02", "2026-04-01"], q, lam=1e-6)
    chk("penalty pulls unconstrained step to neighbour (bp)", 100 * (fit.rates[0] - fit.rates[1]), 0.0, 1e-4)

    # 7. bad data must raise, not be filled
    for bad in (lambda: bootstrap_par("2026-01-01", [12, 24], [3.0, float("nan")]),
                lambda: bootstrap_par("2026-01-01", [12, 12], [3.0, 3.1]),
                lambda: fit_step("2026-01-01", ["2026-02-01"], pd.DataFrame({"kind": ["xx"], "start": ["2026-01-01"], "end": ["2026-02-01"], "value": [3.0]}))):
        try:
            bad()
            ok = False
            print("FAIL bad input accepted")
        except ValueError:
            print("PASS bad input rejected")

    if not ok:
        print("SELFTEST FAILED")
        sys.exit(1)
    print("SELFTEST OK")


# ---------------------------------------------------------------- CLI
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("par", help="bootstrap canonical curve_par rows to curve_zero-style nodes")
    p.add_argument("--par", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--start-date", default=None, help="spot/effective date = DF 1 (default --date; pass T+2 for USD/EUR/CHF...)")
    p.add_argument("--curve-id", required=True)
    p.add_argument("--snap", default=None)
    p.add_argument("--basis", default="ACT/360")
    p.add_argument("--out")
    s = sub.add_parser("step", help="fit a meeting-date step curve to OIS/SR1/SR3 quotes")
    s.add_argument("--quotes", required=True)
    s.add_argument("--as-of", required=True)
    s.add_argument("--steps", required=True, help="comma-separated effective dates")
    s.add_argument("--lam", type=float, default=1e-6)
    s.add_argument("--fixings", default=None)
    s.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return
    if a.cmd == "par":
        df = pd.read_parquet(a.par) if a.par.endswith(".parquet") else pd.read_csv(a.par)
        df = df[(df["curve_id"] == a.curve_id) & (df["date"].astype(str).str[:10] == a.date) & (df["start"] == "0D")]
        if a.snap:
            df = df[df["snap"] == a.snap]
        if df["snap"].nunique() > 1:
            sys.exit("several snaps present: pass --snap (never mix snaps in one curve)")
        ok = df["tenor"].astype(str).str.upper().str.fullmatch(r"\d+(\.\d+)?[MY]")
        if (~ok).any():
            print(f"skipping non-M/Y tenors: {sorted(df.loc[~ok, 'tenor'].astype(str).unique())}", file=sys.stderr)
        df = df[ok]
        if df.empty:
            sys.exit("no spot-start (start=0D) M/Y rows for that date/curve_id/snap")
        df = df.assign(m=df["tenor"].map(parse_tenor)).sort_values("m")
        start = a.start_date or a.date
        c = bootstrap_par(start, df["m"].tolist(), df["par_rate_pct"].tolist(), basis=a.basis)
        if start != a.date:
            print(f"note: curve is spot-start from {start} (DF=1 there); the `date` column is the start date. Add the "
                  f"{a.date}->{start} O/N-T/N stub before using it as a trade-date curve.", file=sys.stderr)
        out = nodes_frame(c, start, a.curve_id, df["snap"].iloc[0], df["tenor"].tolist())
    elif a.cmd == "step":
        q = pd.read_csv(a.quotes)
        fx = None
        if a.fixings:
            f = pd.read_csv(a.fixings)
            fx = dict(zip(pd.to_datetime(f["date"]), f["rate_pct"]))
        c, res = fit_step(a.as_of, a.steps.split(","), q, lam=a.lam, fixings=fx)
        out = pd.DataFrame({"step_date": c.steps.date, "rate_pct": c.rates})
        out["step_bp"] = out["rate_pct"].diff().mul(100)
        print(f"max |residual| = {np.abs(res).max():.4f} bp", file=sys.stderr)
    else:
        ap.print_help()
        return
    if a.out:
        out.to_csv(a.out, index=False)
    else:
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
