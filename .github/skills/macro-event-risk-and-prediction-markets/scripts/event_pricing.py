#!/usr/bin/env python3
"""Event-risk pricing helpers: prediction-market ladders -> PMF, event-day vol, surprise beta, calibration.

Conventions: rates/vols in bp unless stated; prediction prices are probabilities on 0..1 (Yes pays 1).
Functions take numpy/pandas objects. CLI reads the canonical `events_probs` table (CSV/Parquet).

  python event_pricing.py pmf --file events_probs.csv --event-id FED-2026-12-09 --date 2026-11-10 --venue <venue>
  python event_pricing.py eventvol --sig-short 25 --short-years 0.0833 --sig-long 69 --long-years 0.1667 --days 21
  python event_pricing.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

TRADING_DAYS = 252.0


# ---------------------------------------------------------------- prediction-market ladder -> PMF
def repair_survival(strikes, prices):
    """Middle-out no-arbitrage repair of 'above K' prices (must be non-increasing in K).

    Centre = strike priced closest to 0.49. Sweep left: a lower strike priced below its
    centre-ward neighbour is raised to it. Sweep right: a higher strike priced above its
    centre-ward neighbour is lowered to it. Returns (sorted strikes, repaired prices).
    """
    k = np.asarray(strikes, float)
    p = np.asarray(prices, float)
    ok = ~(np.isnan(k) | np.isnan(p))
    k, p = k[ok], p[ok]
    o = np.argsort(k)
    k, p = k[o], p[o].copy()
    if len(k) == 0:
        return k, p
    c = int(np.argmin(np.abs(p - 0.49)))
    for i in range(c - 1, -1, -1):
        p[i] = max(p[i], p[i + 1])
    for i in range(c + 1, len(p)):
        p[i] = min(p[i], p[i - 1])
    return k, p


def survival_to_pmf(strikes, surv, normalise=True, tails=False):
    """PMF over buckets from S(K)=P(X>K). Bucket i = (K_i, K_{i+1}], mass S_i - S_{i+1}; optional
    open tails (<=K_0 mass 1-S_0, >K_last mass S_last) with tails=True.

    Yes is quoted 1c..99c, so interior masses sum to at most 0.98 (S_0 - S_last); with normalise=True
    they are divided by their sum. Zero buckets sitting inside non-zero, more extreme buckets (stale tails)
    are moved to the end of the distribution before normalising (step (a) of the repair).
    Returns DataFrame[label, upper, mass] where `upper` is the bucket's upper strike (inf for the tail).
    """
    k = np.asarray(strikes, float)
    s = np.asarray(surv, float)
    if tails:  # add open tails (<=K_0, >K_last); the interior-only default matches a 1c..99c ladder
        mass = np.concatenate([[1.0 - s[0]], s[:-1] - s[1:], [s[-1]]])
        upper = np.concatenate([k, [np.inf]])
        lo = np.concatenate([[-np.inf], k])
    else:
        mass, upper, lo = s[:-1] - s[1:], k[1:], k[:-1]
    # bubble up: interior zero buckets (non-zero mass on both sides) are moved to the far end,
    # i.e. the non-zero masses are compacted toward the first non-zero bucket; labels stay fixed.
    nz = np.flatnonzero(mass > 1e-12)
    if len(nz) > 1:
        a, b = nz[0], nz[-1]
        seg = mass[a:b + 1]
        packed = np.concatenate([seg[seg > 1e-12], np.zeros((seg <= 1e-12).sum())])
        mass = mass.copy()
        mass[a:b + 1] = packed
    if normalise:
        if mass.sum() <= 0:
            raise ValueError("ladder has no probability mass between its first and last strike")
        mass = mass / mass.sum()
    return pd.DataFrame({"lower": lo, "upper": upper, "mass": mass})


def pmf_moments(pmf: pd.DataFrame, step=None):
    """mean/median/mode of a bucketed PMF. For step-valued outcomes (Fed moves in 25bp steps) the
    outcome of bucket (lower, upper] is `upper`; open upper tail uses upper_prev + step; the lower
    tail is dropped from the outcome support (assigned to the first finite strike)."""
    up = pmf["upper"].to_numpy(float).copy()
    fin = up[np.isfinite(up)]
    if step is None:
        step = float(np.median(np.diff(fin))) if len(fin) > 1 else 1.0
    if not np.isfinite(up[-1]):
        up[-1] = fin[-1] + step
    m = pmf["mass"].to_numpy(float)
    mean = float((m * up).sum())
    cdf = np.cumsum(m)
    median = float(up[int(np.searchsorted(cdf, 0.5))])
    mode = float(up[int(np.argmax(m))])
    return {"mean": mean, "median": median, "mode": mode}


def stale_filter(df: pd.DataFrame, asof, max_age_days=60, date_col="date", strike_col="threshold_pct",
                 price_col="prob"):
    """Last traded price per strike as of `asof`; drop strikes whose last trade is > max_age_days old.
    Expects non-stale rows to be those with is_stale False (price traded that day)."""
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col])
    d = d[d[date_col] <= pd.Timestamp(asof)].dropna(subset=[strike_col, price_col])
    if "is_stale" in d:
        traded = d[~d["is_stale"].eq(True)]  # NaN counts as traded
    else:
        traded = d
    last = traded.sort_values(date_col).groupby(strike_col).tail(1)
    age = (pd.Timestamp(asof) - last[date_col]).dt.days
    return last[age <= max_age_days][[strike_col, price_col]].rename(columns={strike_col: "strike", price_col: "price"})


# ---------------------------------------------------------------- option-implied event vol
def event_day_weight(sig_short, days_short, sig_long, normal_days_long):
    """Implied event weight X (in 'normal-day' units) from two expiries straddling the event.

    n = sig_short / sqrt(days_short) is the vol per unit event weight; the long expiry has
    `normal_days_long` ordinary days (all of them, including those of the short expiry) plus the event:
    sig_long^2 = n^2 (normal_days_long + X). Returns (n, X, event_day_vol = n*sqrt(X)).
    Vols are expiry-TOTAL vols in bp (annualised vol * sqrt(days/252)), not annualised vols.
    """
    n = sig_short / np.sqrt(days_short)
    x = (sig_long / n) ** 2 - normal_days_long
    return float(n), float(x), float(n * np.sqrt(max(x, 0.0)))


def forward_vol(t, sig_t, f, sig_f):
    """Forward vol over (f, t] from annualised normal vols: sqrt((t*sig_t^2 - f*sig_f^2)/(t - f))."""
    return float(np.sqrt((t * sig_t**2 - f * sig_f**2) / (t - f)))


def event_day_vol(fwd_vol_annual, window_years, n_days, base_vol_annual, tdays=TRADING_DAYS):
    """Attribute all excess variance of a window to one event day.
    total var = fwd^2 * window_years = (n_days-1) * (base/sqrt(tdays))^2 + event^2. Returns event-day bp vol."""
    total = fwd_vol_annual**2 * window_years
    normal = (n_days - 1) * base_vol_annual**2 / tdays
    return float(np.sqrt(max(total - normal, 0.0)))


# ---------------------------------------------------------------- probabilities, EV, edge
def two_outcome_prob(implied_move_bp, step_bp=25.0):
    """Meeting-implied move (bp, vs current rate; sign gives the direction, hike or cut) -> P(a move of one
    step in that direction), assuming only {0, step} outcomes."""
    return float(np.clip(abs(implied_move_bp) / step_bp, 0.0, 1.0))


def contract_edge(p_own, ask, fee=0.0):
    """Expected profit per 1.00 payout from buying Yes at `ask` plus `fee` (all in probability units)."""
    return float(p_own - (ask + fee))


def scenario_ev(probs, payoffs):
    """Probability-weighted payoff; probs must sum to 1 (+-1e-6). Returns (EV, std)."""
    p = np.asarray(probs, float)
    x = np.asarray(payoffs, float)
    if abs(p.sum() - 1) > 1e-6:
        raise ValueError("scenario probabilities must sum to 1")
    ev = float((p * x).sum())
    return ev, float(np.sqrt((p * (x - ev) ** 2).sum()))


# ---------------------------------------------------------------- surprise beta, triggers, calibration
def surprise_z(actual: pd.Series, consensus: pd.Series, window=24, min_periods=8):
    """Surprise = actual - consensus; z = surprise / rolling std of surprises (history only: shifted by 1)."""
    s = actual - consensus
    sd = s.rolling(window, min_periods=min_periods).std().shift(1)
    return s / sd


def surprise_beta(dy_bp: pd.Series, z: pd.Series):
    """OLS slope (bp per 1 z) of on-day yield change on surprise z, with intercept. Returns (beta, alpha, r2)."""
    d = pd.concat([dy_bp, z], axis=1).dropna()
    x, y = d.iloc[:, 1].to_numpy(), d.iloc[:, 0].to_numpy()
    if len(d) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan"), float("nan"), float("nan")
    b, a = np.polyfit(x, y, 1)
    r2 = 1 - ((y - (a + b * x)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return float(b), float(a), float(r2)


def sigma_trigger(dy_bp: pd.Series, lookback=21, k=2.0):
    """+1 (yield up) / -1 (yield down) where the day's change in yield (bp) is >= k x the std of the previous
    `lookback` daily changes (today excluded), else 0 (also 0 while the history is too short)."""
    sd = dy_bp.rolling(lookback, min_periods=lookback).std().shift(1)
    return np.sign(dy_bp).where(dy_bp.abs() >= k * sd, 0.0)


def calibration(prob, outcome, bins=10):
    """Brier score, mean gap (mean outcome - mean prob; Shafer-Vovk calibration check) and reliability table."""
    p = np.asarray(prob, float)
    y = np.asarray(outcome, float)
    ok = ~(np.isnan(p) | np.isnan(y))
    p, y = p[ok], y[ok]
    brier = float(((p - y) ** 2).mean())
    cut = np.clip((p * bins).astype(int), 0, bins - 1)
    rows = [(b / bins, int((cut == b).sum()), float(p[cut == b].mean()), float(y[cut == b].mean()))
            for b in range(bins) if (cut == b).any()]
    tab = pd.DataFrame(rows, columns=["bin_lo", "n", "mean_prob", "freq"])
    return brier, float(y.mean() - p.mean()), tab


def calibration_z(prob, outcome):
    """z-statistic of the mean gap under H0 'every forecast is calibrated' (outcome_i ~ Bernoulli(p_i), independent):
    z = sum(y - p) / sqrt(sum p(1-p)). |z| > 2 rejects calibration; needs many events (a single mid-range p is untestable)."""
    p = np.asarray(prob, float)
    y = np.asarray(outcome, float)
    ok = ~(np.isnan(p) | np.isnan(y))
    p, y = p[ok], y[ok]
    v = (p * (1 - p)).sum()
    return float((y - p).sum() / np.sqrt(v)) if v > 0 else float("nan")


# ---------------------------------------------------------------- CLI
def _cmd_pmf(a):
    df = pd.read_parquet(a.file) if a.file.endswith(".parquet") else pd.read_csv(a.file, parse_dates=["date"])
    df = df[df["event_id"] == a.event_id]
    if a.venue:
        df = df[df["venue"] == a.venue]
    lad = stale_filter(df, a.date)
    k, s = repair_survival(lad["strike"], lad["price"])
    pmf = survival_to_pmf(k, s)
    print(pmf.to_string(index=False))
    print(pmf_moments(pmf, step=a.step))


def _cmd_eventvol(a):
    f = forward_vol(a.long_years, a.sig_long, a.short_years, a.sig_short)
    ev = event_day_vol(f, a.long_years - a.short_years, a.days, a.sig_short)
    print(f"forward vol {f:.1f}bp/yr ; event-day vol {ev:.2f}bp ; base day {a.sig_short / np.sqrt(TRADING_DAYS):.2f}bp")


def selftest():
    bad = []

    def chk(name, got, exp, tol):
        ok = abs(got - exp) <= tol
        print(("ok   " if ok else "FAIL ") + f"{name}: got {got:.4f} expected {exp:.4f}")
        if not ok:
            bad.append(name)

    # 1. middle-out repair: 4.75% priced above 4.50% gets pulled down; centre kept
    k, p = repair_survival([4.0, 4.25, 4.5, 4.75], [0.50, 0.20, 0.04, 0.06])
    chk("repair monotone", float(np.all(np.diff(p) <= 1e-12)), 1.0, 0)
    chk("repair 4.75", p[3], 0.04, 1e-12)
    # 1b. left sweep: lower strike priced below its centre-ward neighbour is raised
    _, pl = repair_survival([3.5, 3.75, 4.0, 4.25], [0.90, 0.30, 0.50, 0.10])
    chk("repair left sweep", pl[1], 0.50, 1e-12)
    # 2. PMF: S(4.25)=20c, S(4.50)=4c -> bucket (4.25,4.50] mass 16c before normalisation
    pm = survival_to_pmf([4.0, 4.25, 4.5], [0.60, 0.20, 0.04], normalise=False)  # buckets 4.25: .40, 4.50: .16
    chk("bucket mass 4.50", float(pm.loc[pm.upper == 4.5, "mass"].iloc[0]), 0.16, 1e-12)
    chk("interior mass = S0 - Slast", float(pm.mass.sum()), 0.56, 1e-12)
    # 2b. bubble-up: 4.75 bucket zero inside non-zero tails (stale) -> masses compacted inward
    pb = survival_to_pmf([4.0, 4.25, 4.5, 4.75, 5.0], [0.60, 0.20, 0.02, 0.02, 0.01], normalise=False)  # zero bucket at 4.75
    chk("bubble-up fills 4.75", float(pb.loc[pb.upper == 4.75, "mass"].iloc[0]), 0.01, 1e-12)
    chk("bubble-up empties last", float(pb["mass"].iloc[-1]), 0.0, 1e-12)
    # 3. normalisation to 98c ladder: masses (excluding implicit tails) sum 0.98 -> /0.98
    pn = survival_to_pmf([4.0, 4.25, 4.5], [0.99, 0.20, 0.01], normalise=True)
    chk("normalised sum", float(pn.mass.sum()), 1.0, 1e-12)
    chk("normalised 4.25 bucket", float(pn.loc[pn.upper == 4.25, "mass"].iloc[0]), 0.79 / 0.98, 1e-12)
    # 3b. hand-repair example in SKILL.md: 0.97/0.60/0.20/0.04/0.06 -> 39.8/43.0/17.2/0 %
    kk, sr = repair_survival([3.5, 3.75, 4.0, 4.25, 4.5], [0.97, 0.60, 0.20, 0.04, 0.06])
    pr = survival_to_pmf(kk, sr)
    chk("hand repair 4.50 lowered", sr[4], 0.04, 1e-12)
    chk("hand repair 3.75 bucket", float(pr.mass.iloc[0]), 0.37 / 0.93, 1e-12)
    chk("hand repair 4.00 bucket", float(pr.mass.iloc[1]), 0.40 / 0.93, 1e-12)
    # 3c. stale filter: strike last traded 70d before asof is dropped; carried-forward (is_stale) rows do not count as trades
    sf = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-03-01", "2026-03-10", "2026-03-11"]),
                       "threshold_pct": [4.0, 4.25, 4.25, 4.25], "prob": [0.5, 0.3, 0.31, 0.35],
                       "is_stale": [False, False, False, True]})
    st = stale_filter(sf, "2026-03-11")
    chk("stale drops old strike", float(len(st)), 1.0, 0)
    chk("stale uses last real trade", float(st.price.iloc[0]), 0.31, 1e-12)
    # 4. moments of a symmetric PMF: mean=median=mode
    sym = pd.DataFrame({"lower": [3.5, 3.75, 4.0], "upper": [3.75, 4.0, 4.25], "mass": [0.25, 0.5, 0.25]})
    mo = pmf_moments(sym, step=0.25)
    chk("sym mean", mo["mean"], 4.0, 1e-12)
    chk("sym median", mo["median"], 4.0, 1e-12)
    chk("sym mode", mo["mode"], 4.0, 1e-12)
    # 4b. skewed PMF: mean 3.9625, median 4.0 (cdf .4,.75,1), mode 3.75
    sk = pmf_moments(pd.DataFrame({"lower": [3.5, 3.75, 4.0], "upper": [3.75, 4.0, 4.25], "mass": [0.4, 0.35, 0.25]}), step=0.25)
    chk("skew mean", sk["mean"], 3.9625, 1e-12)
    chk("skew median", sk["median"], 4.0, 1e-12)
    chk("skew mode", sk["mode"], 3.75, 1e-12)
    # 5. Brexit forward vol and event-day vol (Darbyshire 2022 Ex 20.7): 94bp, 26.2bp
    f = forward_vol(2 / 12, 69.0, 1 / 12, 25.0)
    chk("brexit fwd vol", f, 94.3, 0.1)
    chk("brexit event-day vol", event_day_vol(94.0, 1 / 12, 21, 25.0), 26.21, 0.05)
    chk("base day vol", 25 / np.sqrt(252), 1.57, 0.01)
    # 6. event weight: 10bp total over 5 days, 20bp total over 10 days (9 normal + event): n=4.472, X=(20/n)^2-9=11
    n, x, evv = event_day_weight(10.0, 5, 20.0, 9)
    chk("event weight X", x, 11.0, 1e-9)
    chk("event-day vol", evv, 4.4721 * np.sqrt(11), 1e-3)
    # 7. surprise beta recovers known slope on noiseless data
    rng = np.random.default_rng(0)
    z = pd.Series(rng.normal(size=60))
    dy = 3.0 * z + 0.5
    b, a, r2 = surprise_beta(dy, z)
    chk("beta", b, 3.0, 1e-9)
    chk("alpha", a, 0.5, 1e-9)
    # 7b. r2 and slope on noisy data: x=1..4, y=[1,3,2,4] -> b=0.8, r2=0.64
    b2, _, r22 = surprise_beta(pd.Series([1.0, 3.0, 2.0, 4.0]), pd.Series([1.0, 2.0, 3.0, 4.0]))
    chk("beta noisy", b2, 0.8, 1e-12)
    chk("r2 noisy", r22, 0.64, 1e-12)
    # 8. sigma trigger fires on a 3-sd jump and not on noise
    base = pd.Series(np.tile([1.0, -1.0], 15))
    base.iloc[25] = 2.1  # 2.05 sd of the PRIOR 21 days (sd 1.024) but < 2 sd if today were in the window (1.10): checks no look-ahead
    tr = sigma_trigger(base, lookback=21, k=2.0)
    chk("trigger fires", float(tr.iloc[25]), 1.0, 0)
    chk("trigger quiet", float(tr.iloc[24]), 0.0, 0)
    chk("trigger sign", float(sigma_trigger(-base, lookback=21, k=2.0).iloc[25]), -1.0, 0)
    chk("trigger short history", float(tr.iloc[10]), 0.0, 0)
    # 8b. surprise z uses only earlier surprises: z_t = s_t / std(s_{t-w..t-1})
    act = pd.Series(np.arange(12, dtype=float) ** 1.5)
    cons = pd.Series(np.zeros(12))
    zz = surprise_z(act, cons, window=8, min_periods=8)
    chk("surprise z", float(zz.iloc[10]), float(act.iloc[10] / act.iloc[2:10].std()), 1e-12)
    chk("surprise z needs history", float(np.isnan(zz.iloc[7])), 1.0, 0)
    # 9. calibration: perfectly calibrated deterministic set has mean gap 0; Brier of p=0.5 is 0.25
    br, gap, _ = calibration([0.5] * 10, [1, 0] * 5)
    chk("brier", br, 0.25, 1e-12)
    chk("gap", gap, 0.0, 1e-12)
    br2, gap2, _ = calibration([0.9] * 10, [1] * 8 + [0] * 2)  # overconfident: Brier (8*.01+2*.81)/10, gap -0.1
    chk("brier 2", br2, 0.17, 1e-12)
    chk("gap 2", gap2, -0.1, 1e-12)
    chk("calibration z", calibration_z([0.5] * 100, [1] * 60 + [0] * 40), 2.0, 1e-12)  # 10 / sqrt(25)
    # 10. EV and edge
    ev, _ = scenario_ev([0.3, 0.7], [-10.0, 4.0])
    chk("scenario EV", ev, -0.2, 1e-12)
    chk("scenario std", scenario_ev([0.5, 0.5], [-10.0, 10.0])[1], 10.0, 1e-12)
    chk("edge", contract_edge(0.40, 0.34, 0.01), 0.05, 1e-12)
    chk("two-outcome prob", two_outcome_prob(6.25), 0.25, 1e-12)
    chk("two-outcome prob cut", two_outcome_prob(-6.25), 0.25, 1e-12)
    if bad:
        print("SELFTEST FAILED:", bad)
        return 1
    print("SELFTEST PASSED")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("pmf", help="events_probs ladder -> repaired PMF and moments")
    p.add_argument("--file", required=True)
    p.add_argument("--event-id", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--step", type=float, default=0.25)
    p.add_argument("--venue", help="prediction venue to keep (events_probs.venue); omit only if the file has one venue")
    e = sub.add_parser("eventvol", help="event-day vol from two expiries (annualised bp vols)")
    e.add_argument("--sig-short", type=float, required=True, help="vol of the pre-event expiry, bp/yr")
    e.add_argument("--short-years", type=float, required=True)
    e.add_argument("--sig-long", type=float, required=True, help="vol of the expiry containing the event, bp/yr")
    e.add_argument("--long-years", type=float, required=True)
    e.add_argument("--days", type=int, required=True, help="business days in the forward window")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "pmf":
        _cmd_pmf(a)
    elif a.cmd == "eventvol":
        _cmd_eventvol(a)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
