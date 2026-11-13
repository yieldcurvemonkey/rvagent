"""Meeting-date implied policy path: what is priced in, per meeting, with hike/cut probabilities.

Conventions (same as SKILL.md): rates in percent, steps/cumulative in bp, probabilities 0..1.
step_bp(k)  = expected overnight rate after meeting k  minus  expected rate before it (bp)
cum_bp(k)   = expected overnight rate after meeting k  minus  current/stub rate (bp)
Positive = hike (receive-fixed loses). Dates are EFFECTIVE dates (the day the new rate applies).

Subcommands
  table  --rates meeting_rates.csv --base 3.88 [--size 25]
         csv columns: effective_date, rate_pct  (meeting-dated OIS rate for the period starting that date;
         the first row is the stub/current period if --base is omitted)
  fit    --quotes stir_quotes.csv --fut-static fut_static.csv --meetings cb_meetings.csv --cb FED
         --asof 2026-11-10 [--fixings rate_fixings.csv --index-id USD-SOFR] [--roots <comma list of fut_static.root>] [--snap settle] [--ridge 1e-6] [--horizon 183]
         Fits a step-function overnight forward (jumps on effective dates) to futures averaging windows by
         ridge least squares (Heitfield-Park style).  Tables: stir_quotes, fut_static, cb_meetings, rate_fixings.
  --selftest   known-answer checks, non-zero exit on failure.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------- probabilities
def step_probabilities(step_bp, size_bp=25.0):
    """Isolated per-meeting outcome probabilities from the priced step (Pulman/Aikin rule).

    step = k*size + frac*size  ->  P(|k+1| moves) = frac, P(|k| moves) = 1 - frac, same sign as step.
    Returns DataFrame: step_bp, n_low, p_low, n_high, p_high (n = signed number of size-bp moves),
    p_move = P(at least one move), exp_moves = step/size.  10bp priced with 25bp size = 40% of a move.
    Not a joint distribution: 50%/50% at two meetings usually means one move, timing uncertain.
    """
    s = np.asarray(step_bp, float)
    a = np.abs(s) / size_bp
    k = np.floor(a + 1e-12)
    frac = a - k
    sg = np.sign(s)
    return pd.DataFrame({"step_bp": s, "n_low": sg * k, "p_low": 1 - frac, "n_high": sg * (k + 1),
                         "p_high": frac, "p_move": np.where(k >= 1, 1.0, frac), "exp_moves": s / size_bp})


def expected_bp(dist, size_bp=25.0):
    """Probability-weighted bp from a subjective {n_moves: prob} distribution (fair value of a block of meetings)."""
    p = np.array(list(dist.values()), float)
    if abs(p.sum() - 1) > 1e-9:
        raise ValueError("probabilities must sum to 1")
    return float(sum(n * pr for n, pr in dist.items()) * size_bp)


# ----------------------------------------------------------------------------- meeting-dated OIS -> steps
def steps_from_period_rates(period_rates_pct, base_pct=None):
    """Meeting-dated OIS rates (one per period, period i starts at effective date i) -> step/cum in bp.

    base_pct = stub/current rate; if None the first period rate is the base and gets step 0.
    Approximation: the compounded period rate is treated as the period's overnight rate (error << 0.5bp
    below 1y; see fi-curve-construction for exact bootstrap).
    """
    r = np.asarray(period_rates_pct, float)
    base = r[0] if base_pct is None else float(base_pct)
    prev = np.concatenate([[base], r[:-1]])
    return pd.DataFrame({"rate_pct": r, "step_bp": 100 * (r - prev), "cum_bp": 100 * (r - base)})


def bootstrap_next_rate(R_pct, t0, t1, T1, r0_pct, basis=360.0):
    """Pulman (2007) recursion: overnight rate r1 after a meeting from a 1M-type OIS rate R.

    (1 + R (T1-t0)/D) = (1 + r0/D)^(t1-t0) * (1 + r1/D)^(T1-t1)   (t = day offsets from start, D = basis)
    r0 = rate in force until the meeting at t1, T1 = OIS maturity. Returns r1 in percent.
    """
    R, r0 = R_pct / 100.0, r0_pct / 100.0
    lhs = (1 + R * (T1 - t0) / basis) / (1 + r0 / basis) ** (t1 - t0)
    return 100.0 * basis * (lhs ** (1.0 / (T1 - t1)) - 1.0)


# ----------------------------------------------------------------------------- step-function fit
def _design(asof, eff, contracts, fixings):
    """Rows: contracts (start, end exclusive, rate_pct). Cols: theta0 then one jump per effective date.

    Average over calendar days; days <= asof use the (forward-filled) fixing, later days use the step path.
    Returns A (n x 1+K), b (known part), y (target).
    """
    A = np.zeros((len(contracts), 1 + len(eff)))
    b = np.zeros(len(contracts))
    fx = None
    if fixings is not None and len(fixings):
        fx = fixings.copy()
        fx.index = pd.to_datetime(fx.index)
        fx = fx[~fx.index.duplicated(keep="last")].sort_index()  # ffill needs a monotonic index
    for i, c in enumerate(contracts.itertuples()):
        days = pd.date_range(pd.Timestamp(c.start), pd.Timestamp(c.end) - pd.Timedelta(days=1))
        n = len(days)
        for d in days:
            if d <= asof:
                if fx is None:
                    raise ValueError(f"contract window {c.start}..{c.end} includes realised days: pass fixings")
                v = fx.reindex([d], method="ffill").iloc[0]
                if pd.isna(v):
                    raise ValueError(f"no fixing on or before {d.date()} (contract {c.start}..{c.end}): extend fixings history")
                b[i] += v / n
            else:
                A[i, 0] += 1.0 / n
                for k, e in enumerate(eff):
                    if d >= e:
                        A[i, 1 + k] += 1.0 / n
    return A, b, contracts["rate_pct"].to_numpy(float)


def fit_step_path(asof, effective_dates, contracts, fixings=None, ridge=1e-6, horizon_days=183, weights=None):
    """Fit theta0 + sum_k theta_k * 1{t >= eff_k} to contract averages. Returns (theta0_pct, table).

    ridge: L2 penalty on jumps (percent units): resolves under-identified jumps with the minimum-norm
    split across meetings sharing one contract window (a cheap stand-in for policy gradualism). Meetings with no post-meeting days
    in any contract are flagged identified=False and get 0.  Meetings > horizon_days ahead are dropped, and so are
    contracts that start beyond the horizon (Heitfield-Park: far meetings are unscheduled and far contracts thin).
    Windows are averaged arithmetically; for compounded contracts (3M RFR futures) this ignores the
    compounding gap ~ r^2 T/2 (3M window: ~0.1bp at 1%, ~3bp at 5%; 1M: ~1bp at 5%): net it off the 3M targets
    when it is comparable to the bid-offer.
    """
    asof = pd.Timestamp(asof)
    eff = [pd.Timestamp(e) for e in sorted(effective_dates)
           if asof < pd.Timestamp(e) <= asof + pd.Timedelta(days=horizon_days)]
    contracts = contracts[pd.to_datetime(contracts["start"]) <= asof + pd.Timedelta(days=horizon_days)].dropna(subset=["rate_pct"])
    # contracts starting beyond the horizon would be explained by unmodelled meetings and bias the level theta0
    if len(contracts) == 0:
        raise ValueError("no usable futures contracts (check as-of snap, reference-index filter, horizon)")
    A, b, y = _design(asof, eff, contracts, fixings)
    w = np.ones(len(y)) if weights is None else np.asarray(weights, float)
    K = len(eff)
    lam = np.sqrt(ridge) * np.ones(K)
    M = np.vstack([A * w[:, None], np.hstack([np.zeros((K, 1)), np.diag(lam)])])
    t = np.concatenate([(y - b) * w, np.zeros(K)])
    theta = np.linalg.lstsq(M, t, rcond=None)[0]
    ident = A[:, 1:].sum(axis=0) > 1e-12
    rate = theta[0] + np.cumsum(theta[1:])
    out = pd.DataFrame({"effective_date": eff, "step_bp": 100 * theta[1:], "rate_pct": rate,
                        "cum_bp": 100 * np.cumsum(theta[1:]), "identified": ident})
    out = pd.concat([out, step_probabilities(out["step_bp"].to_numpy())[["p_low", "n_low", "p_high", "n_high", "p_move"]]],
                    axis=1)
    resid = (A @ theta + b - y) * 100  # bp
    out.attrs["resid_bp"] = resid
    return float(theta[0]), out


# ----------------------------------------------------------------------------- selftest
def _selftest():
    ok = True

    def chk(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name, info)
        ok &= bool(cond)

    # 1. Pulman (2007) RBA 10-Apr-2007: policy 6.25; expected rates -> P(hike) 44,28,0,16,8,8 %
    exp = np.array([6.36, 6.43, 6.43, 6.47, 6.49, 6.51])
    steps = 100 * np.diff(np.concatenate([[6.25], exp]))
    p = step_probabilities(steps)["p_high"].to_numpy()
    chk("pulman_rba_probs", np.allclose(p, [0.44, 0.28, 0, 0.16, 0.08, 0.08], atol=1e-9), np.round(p, 3))
    s = step_probabilities([37.5, -10, 5.0])
    chk("prob_rules", np.allclose(s["p_high"], [0.5, 0.4, 0.2]) and s["n_high"].tolist() == [2, -1, 1]
        and s["n_low"].tolist() == [1, 0, 0], s["p_high"].tolist())
    # Aikin (2014) MPC-dated OIS, base 0.50: 7-Aug-14 0.524 -> ~10%, 5-Feb-15 0.700 -> 80%
    t = steps_from_period_rates([0.524, 0.700], base_pct=0.50)
    chk("aikin_cum_prob", np.allclose(t["cum_bp"] / 25, [0.096, 0.80]), (t["cum_bp"] / 25).round(3).tolist())
    chk("steps_from_period_rates", np.allclose(steps_from_period_rates([6.36, 6.43, 6.43], 6.25)["step_bp"], [11, 7, 0])
        and np.allclose(steps_from_period_rates([6.36, 6.43, 6.43], 6.25)["cum_bp"], [11, 18, 18]))
    chk("expected_bp_value", abs(expected_bp({0: 0.5, 1: 0.3, 2: 0.2}) - 17.5) < 1e-9)

    # 2. Pulman bootstrap: 30-day OIS, meeting after 10 days, r0 2.00% -> r1 2.25%; build R by explicit daily compounding
    r0, r1, D = 2.00, 2.25, 360.0
    R = (np.prod([1 + r0 / 100 / D] * 10 + [1 + r1 / 100 / D] * 20) - 1) * D / 30 * 100
    got = bootstrap_next_rate(R, 0, 10, 30, r0)
    chk("pulman_bootstrap", abs(got - r1) < 1e-9, round(got, 6))

    # 3. Tuckman & Serrat (2022) FF strip, 17-Jan-2022: rate after Mar meeting = Apr FF 0.355; after May meeting
    #    f_May = (31*0.450 - 4*0.355)/27 = 0.4641; after Jan = Feb FF 0.095
    cal = lambda m: (pd.Timestamp(2022, m, 1), pd.Timestamp(2022, m + 1, 1))
    ctr = pd.DataFrame([(*cal(m), v) for m, v in [(1, 0.0825), (2, 0.095), (4, 0.355), (5, 0.450)]],
                       columns=["start", "end", "rate_pct"])
    fx = pd.Series(0.08, index=pd.date_range("2021-12-01", "2022-01-17"))
    eff = ["2022-01-27", "2022-03-17", "2022-05-05"]
    th0, tab = fit_step_path("2022-01-17", eff, ctr, fx, ridge=1e-12)
    r = tab["rate_pct"].to_numpy()
    chk("tuckman_path", np.allclose(r, [0.095, 0.355, (31 * 0.450 - 4 * 0.355) / 27], atol=1e-6), np.round(r, 5))
    chk("tuckman_jan_prob", abs(tab["cum_bp"].iloc[0] / 25 - 0.06) < 0.01, round(tab["cum_bp"].iloc[0] / 25, 4))

    # 4. Citi (Sep 2019) FF closed form: dDec = -FF_Nov + 31/29 FF_Jan - 2/29 FF_Feb  (FOMC 11-Dec eff 12-Dec, 29-Jan eff 30-Jan)
    nov, dec_, jan_ = 1.55, -0.25, -0.25
    ffn = nov
    ffj = (29 / 31) * (nov + dec_) + (2 / 31) * (nov + dec_ + jan_)
    ffe = nov + dec_ + jan_
    c2 = pd.DataFrame([(pd.Timestamp(2019, 11, 1), pd.Timestamp(2019, 12, 1), ffn),
                       (pd.Timestamp(2020, 1, 1), pd.Timestamp(2020, 2, 1), ffj),
                       (pd.Timestamp(2020, 2, 1), pd.Timestamp(2020, 3, 1), ffe)], columns=["start", "end", "rate_pct"])
    th0, t2 = fit_step_path("2019-10-31", ["2019-12-12", "2020-01-30"], c2, None, ridge=1e-12)
    closed = -ffn + (31 / 29) * ffj - (2 / 29) * ffe
    chk("citi_ff_closed_form", abs(t2["step_bp"].iloc[0] / 100 - closed) < 1e-6 and abs(closed - dec_) < 1e-9,
        (round(t2["step_bp"].iloc[0] / 100, 6), round(closed, 6)))

    # 5. Round trip on a random path: brute-force daily generator vs design matrix; overdetermined with noise-free data
    rng = np.random.default_rng(7)
    eff5 = pd.to_datetime(["2026-12-10", "2027-01-28", "2027-03-18", "2027-05-06"])
    jumps = np.array([-0.25, 0.0, -0.25, -0.25])
    base = 3.60
    days = pd.date_range("2026-11-11", "2027-06-30")
    f = pd.Series(base + np.array([jumps[eff5 <= d].sum() for d in days]), index=days)
    wins = [(pd.Timestamp(2026, 11, 11), pd.Timestamp(2026, 12, 1))] + \
           [(pd.Timestamp(2026 + (m > 12), (m - 1) % 12 + 1, 1), pd.Timestamp(2026 + (m + 1 > 12), m % 12 + 1, 1)) for m in range(12, 18)]
    c5 = pd.DataFrame([(s, e, f[s:e - pd.Timedelta(days=1)].mean()) for s, e in wins], columns=["start", "end", "rate_pct"])
    th0, t5 = fit_step_path("2026-11-10", eff5, c5, None, ridge=1e-10, horizon_days=240)
    chk("roundtrip_jumps", np.allclose(t5["step_bp"] / 100, jumps, atol=1e-4) and abs(th0 - base) < 1e-4,
        np.round(t5["step_bp"].to_numpy(), 3))
    # meeting after every contract window -> flagged unidentified, jump 0
    _, t7 = fit_step_path("2026-11-10", ["2026-12-10", "2027-03-18", "2027-09-01"], c5.iloc[:2], None)
    chk("unidentified_flag", t7["identified"].tolist() == [True, False] and len(t7) == 2 and abs(t7["step_bp"].iloc[1]) < 1e-6,
        t7["identified"].tolist())
    # 6. edge cases: far-dated contract (beyond horizon) must not move the near path; unsorted fixings ok; missing fixings raise
    far = pd.concat([c5, pd.DataFrame([(pd.Timestamp(2028, 1, 1), pd.Timestamp(2028, 2, 1), 9.0)], columns=c5.columns)])
    _, t6 = fit_step_path("2026-11-10", eff5, far, None, ridge=1e-10, horizon_days=240)
    chk("far_contract_dropped", np.allclose(t6["step_bp"], t5["step_bp"], atol=1e-6))
    d10 = pd.Timestamp("2022-01-10")
    fxs = pd.concat([pd.Series([9.99], index=[d10]), fx.drop(d10), pd.Series([0.08], index=[d10])])  # unsorted, stale duplicate first
    _, ts = fit_step_path("2022-01-17", eff, ctr, fxs, ridge=1e-12)  # duplicated, unsorted index must not break or bias the fit
    chk("dup_unsorted_fixings", np.allclose(ts["rate_pct"], tab["rate_pct"]))
    for name, fn, msg in [("missing_fixings_raise", lambda: fit_step_path("2022-01-17", eff, ctr, fx.loc["2022-01-10":], ridge=1e-12), "no fixing"),
                          ("empty_contracts_raise", lambda: fit_step_path("2022-01-17", eff, ctr.iloc[:0], fx), "no usable")]:
        try:
            fn()
            chk(name, False)
        except ValueError as e:
            chk(name, msg in str(e), str(e)[:40])
    return ok


def _main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("table")
    t.add_argument("--rates", required=True)
    t.add_argument("--base", type=float)
    t.add_argument("--size", type=float, default=25.0)
    f = sub.add_parser("fit")
    for a in ("--quotes", "--fut-static", "--meetings", "--cb", "--asof"):
        f.add_argument(a, required=True)
    f.add_argument("--fixings")
    f.add_argument("--index-id")
    f.add_argument("--roots", default="")
    f.add_argument("--snap", default="settle")
    f.add_argument("--ridge", type=float, default=1e-6)
    f.add_argument("--horizon", type=int, default=183, help="max days ahead for meetings/contract starts")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if _selftest() else 1)
    rd = lambda p: pd.read_parquet(p) if str(p).endswith(".parquet") else pd.read_csv(p)
    if a.cmd == "table":
        d = rd(a.rates)
        out = steps_from_period_rates(d["rate_pct"], a.base)
        out.insert(0, "effective_date", d["effective_date"])
        out = pd.concat([out, step_probabilities(out["step_bp"], a.size)[["p_low", "n_low", "p_high", "n_high"]]], axis=1)
        print(out.round(3).to_string(index=False))
    elif a.cmd == "fit":
        asof = pd.Timestamp(a.asof)
        q, fs, mt = rd(a.quotes), rd(a.fut_static), rd(a.meetings)
        mt = mt[mt["cb"] == a.cb]
        if "scheduled" in mt:  # unscheduled moves are outcomes, not known in advance
            mt = mt[mt["scheduled"].astype(bool)]
        if "valid_from" in mt:  # schedule as published at as-of (no look-ahead on later moved/cancelled meetings)
            mt = mt[pd.to_datetime(mt["valid_from"]) <= asof]
        if "valid_to" in mt:
            mt = mt[mt["valid_to"].isna() | (pd.to_datetime(mt["valid_to"]) > asof)]
        md = pd.to_datetime(mt["meeting_date"])
        eff = (pd.to_datetime(mt["effective_date"]) if "effective_date" in mt else pd.Series(pd.NaT, index=mt.index))
        if eff.isna().any():
            print("warning: effective_date missing for some meetings, using meeting_date + 1 day (wrong for BoE/ECB/BoJ: fill the column)",
                  file=sys.stderr)
        eff = eff.fillna(md + pd.Timedelta(days=1))
        if mt.empty:
            sys.exit(f"no scheduled meetings for cb={a.cb} valid at {asof.date()}")
        ccy = mt["ccy"].iloc[0]
        q = q[(pd.to_datetime(q["date"]) == asof) & (q["snap"] == a.snap)]
        fs = fs[(fs["ccy"] == ccy) & fs["ref_start_date"].notna()]
        if a.index_id and "ref_index_id" in fs:  # one reference index per fit (e.g. SOFR, not EFFR, futures)
            fs = fs[fs["ref_index_id"] == a.index_id]
        if a.roots:
            fs = fs[fs["root"].isin(a.roots.split(","))]
        m = q.merge(fs, on="fut_id")
        c = pd.DataFrame({"start": pd.to_datetime(m["ref_start_date"]), "end": pd.to_datetime(m["ref_end_date"]),
                          "rate_pct": 100 - m["price_px"]}).sort_values("start")
        c = c[c["end"] > asof + pd.Timedelta(days=1)]
        fx = None
        if a.fixings:
            x = rd(a.fixings)
            x = x[x["index_id"] == a.index_id]
            pub = pd.to_datetime(x["pub_ts_utc"], utc=True).dt.tz_localize(None)
            x = x[pub < asof + pd.Timedelta(days=1)]  # published by the end of as-of day (as-of day's own fixing is not)
            x = x.assign(_pub=pub).sort_values("_pub").drop_duplicates("fixing_date", keep="last").sort_values("fixing_date")
            fx = pd.Series(x["rate_pct"].to_numpy(), index=pd.to_datetime(x["fixing_date"]))
        th0, tab = fit_step_path(asof, eff, c, fx, a.ridge, horizon_days=a.horizon)
        print(f"overnight rate after as-of (theta0): {th0:.4f}%   max |resid| {np.abs(tab.attrs['resid_bp']).max():.2f}bp")
        print(tab.round(3).to_string(index=False))
    else:
        ap.print_help()


if __name__ == "__main__":
    _main()
