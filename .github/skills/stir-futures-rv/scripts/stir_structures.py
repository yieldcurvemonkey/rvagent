"""STIR futures structures: spreads, flies, packs/bundles, strip->swap, SR1/SR3 hedges, residual z-scores.

Conventions (same as SKILL.md)
  price = 100 - rate. Rates in percent, outputs in bp.
  calendar_bp = 100*(r_far - r_near)            (longer minus shorter; positive = upward sloping)
  fly_bp      = 100*(2*r_belly - r_front - r_back) = 100*(P_front + P_back - 2*P_belly)
                positive = belly cheap (high rate). Exchange "buy fly" = long wings / short belly = PAY belly.
  roll_long_belly_bp = fly_bp[i] - fly_bp[i-1]: what a LONG-belly (receive) package earns over one quarter if
                the curve is static (structure at slot i becomes the structure now at slot i-1).

Usage
  python stir_structures.py --quotes stir_quotes.csv --root SR3 [--snap settle] [--asof YYYY-MM-DD]
         [--n 12] [--gap 1] [--window 65] [--skip-front 1]
  python stir_structures.py --selftest
Input table `stir_quotes`: date, snap, fut_id (FUT:<root>:<YYYY-MM>), price_px (csv or parquet).
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import sys

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ spreads, flies, costs
def calendar_bp(r_near, r_far):
    return 100.0 * (np.asarray(r_far, float) - np.asarray(r_near, float))


def fly_bp(r_front, r_belly, r_back):
    return 100.0 * (2.0 * np.asarray(r_belly, float) - np.asarray(r_front, float) - np.asarray(r_back, float))


def package_cost_bp(weights, half_spread_bp=0.25):
    """Round-trip cost in bp of the package spread S = sum(w_i * r_i). Package DV01 is one contract-BPV per bp
    of S whatever the weights, so cost = sum|w| * 2 * half_spread."""
    return float(np.abs(np.asarray(weights, float)).sum() * 2.0 * half_spread_bp)


def micro_flies(rates_pct):
    """rates_pct: consecutive quarterly contract rates, front first. Returns DataFrame indexed by belly slot
    (1-based; first fly has belly = 2nd contract) with fly_bp and roll_long_belly_bp (NaN for the first)."""
    r = np.asarray(rates_pct, float)
    f = fly_bp(r[:-2], r[1:-1], r[2:])
    out = pd.DataFrame({"belly_slot": np.arange(2, len(r)), "fly_bp": f})
    out["roll_long_belly_bp"] = out["fly_bp"] - out["fly_bp"].shift(1)
    return out.set_index("belly_slot")


# ------------------------------------------------------------------ packs / bundles / strip
def pack_yield(prices):
    """Compounded yield of a pack (4 contracts, 1y) from prices, as a fraction. Quarters standardised to 0.25y."""
    r = (100.0 - np.asarray(prices, float)) / 100.0
    return float(np.prod(1.0 + 0.25 * r) - 1.0)


def bundle_yield(prices):
    """Annualised yield of an N-year bundle (4N contracts): [prod(1 + 0.25*r)]^(1/N) - 1."""
    p = np.asarray(prices, float)
    n_years = len(p) / 4.0
    return float(np.prod(1.0 + 0.25 * (100.0 - p) / 100.0) ** (1.0 / n_years) - 1.0)


def strip_swap_rate(rates_pct, days=91.0):
    """Par fixed rate (act/360, both legs) of an IMM-dated SOFR swap bootstrapped from consecutive quarterly
    futures rates. days = reference-period length (scalar or list). Returns percent."""
    r = np.asarray(rates_pct, float) / 100.0
    d = np.broadcast_to(np.asarray(days, float), r.shape)
    cdf = np.cumprod(1.0 / (1.0 + r * d / 360.0))
    pv_float = np.sum(cdf * r * d / 360.0)
    return float(100.0 * pv_float / np.sum(cdf * d / 360.0))


def ho_lee_ca_bp(sigma_bp, t1, t2):
    """Ho-Lee futures-minus-forward adjustment CA = sigma^2*T1*T2/2 (normal short-rate vol sigma bp/yr; T1 start of
    the reference period = expiry for Euribor, T2 end of reference period, years). Returns bp (futures rate above
    forward). Full treatment: stir-convexity-adjustment."""
    s = sigma_bp / 1e4
    return float(1e4 * 0.5 * s * s * t1 * t2)


# ------------------------------------------------------------------ SR1 / SR3 relationships
def _days(a, b):
    return (b - a).days


def sr1_hedge_for_sr3(q0, q1, meeting_effective, late_month):
    """Meeting-neutral SR1 hedge per ONE SR3 (reference period [q0, q1), hike effective on `meeting_effective`).
    late_month=(year, month) is the SR1 month containing the meeting. Returns (n_early, n_late); the standard
    CME ICS uses 0.3/0.3 per SR3 (3+3 vs 10). Simple-interest sensitivities (compounding is a <1% correction)."""
    D = _days(q0, q1)
    s_l = 25.0                                   # USD per bp of level shift
    s_j = 25.0 * _days(max(meeting_effective, q0), q1) / D   # USD per bp jump on the effective date
    y, m = late_month
    n_m = calendar.monthrange(y, m)[1]
    post = min(n_m, _days(meeting_effective, dt.date(y, m, n_m)) + 1)
    if post <= 0:
        raise ValueError("meeting takes effect after the SR1 month: it cannot be hedged with that SR1")
    n_late = s_j / ((post / n_m) * 41.67)
    n_early = s_l / 41.67 - n_late
    return n_early, n_late


def fair_sr1_sr3_bp(level_bp, slope_bp, q0, q1, sr1_months):
    """Fair CME-convention ICS spread (avg SR1 price - SR3 price, bp) when daily SOFR starts the SR3 quarter at
    level_bp and drifts linearly by slope_bp over it (SR1 months inside the quarter, no Fed jump)."""
    D = _days(q0, q1)
    daily = lambda day: (level_bp + slope_bp * _days(q0, day) / D) / 1e4
    sr3 = (np.prod([1 + daily(q0 + dt.timedelta(i)) / 360.0 for i in range(D)]) - 1) * 360.0 / D
    sr1 = []
    for y, m in sr1_months:
        n = calendar.monthrange(y, m)[1]
        sr1.append(np.mean([daily(dt.date(y, m, k)) for k in range(1, n + 1)]))
    return float((sr3 - np.mean(sr1)) * 1e4)


# ------------------------------------------------------------------ meeting calendar vs fly
def meeting_weights(q_starts, q_ends, meeting_effective):
    """W[i, m] = share of contract i's reference days at the post-meeting-m rate."""
    W = np.zeros((len(q_starts), len(meeting_effective)))
    for i, (a, b) in enumerate(zip(q_starts, q_ends)):
        D = _days(a, b)
        for j, e in enumerate(meeting_effective):
            W[i, j] = max(0.0, min(1.0, _days(max(e, a), b) / D)) if e < b else 0.0
    return W


def calendar_tilted_fly_bp(r_front, r_belly, r_back, m_front, m_belly, m_back, max_tilt=0.35, min_dm=0.5):
    """Fly whose wing split follows the effective meeting counts M (row sums of W): zero if the curve is linear
    in M. weights (-(1-t), 2, -(1+t)), t = ((Mb-Mf)-(Mk-Mb))/(Mk-Mf), |t| <= max_tilt; sum of weights = 0."""
    dm = max(m_back - m_front, min_dm)
    t = float(np.clip(((m_belly - m_front) - (m_back - m_belly)) / dm, -max_tilt, max_tilt))
    return 100.0 * (2.0 * r_belly - (1.0 - t) * r_front - (1.0 + t) * r_back)


def ff_decompose(ff_nov, ff_dec, ff_jan, ff_feb, dec_pre=11, jan_pre=29, n_dec=31, n_jan=31):
    """Split monthly FF-futures averages (rates, pct or bp) into FOMC steps and a year-end premium.
    Nov = base (no meeting). Dec meeting is effective after `dec_pre` days of Dec, Jan meeting after `jan_pre`
    days of Jan; YE = excess average over the post-Dec-meeting days of Dec vs the early-Jan days.
    Returns dict(d_dec, d_jan, ye). Solves the exact linear system (Feb = Nov + d_dec + d_jan)."""
    fd, fj = (n_dec - dec_pre) / n_dec, (n_jan - jan_pre) / n_jan
    # unknowns x = (d_dec, d_jan, ye); rows: Dec, Jan, Feb minus Nov
    A = np.array([[fd, 0.0, fd], [1.0, fj, 0.0], [1.0, 1.0, 0.0]])
    b = np.array([ff_dec - ff_nov, ff_jan - ff_nov, ff_feb - ff_nov], float)
    x = np.linalg.solve(A, b)
    return {"d_dec": float(x[0]), "d_jan": float(x[1]), "ye": float(x[2])}


# ------------------------------------------------------------------ monitors
def regression_monitor(y, x, window=252):
    """Regress y on x over the trailing window. Returns dict(beta, alpha, resid, z) for the LAST observation;
    z = resid / std(window residuals). Use y=spread, x=its longer leg (negative resid = too flat), or y=fly,
    x=belly (negative resid = belly rich).
    Level regression: a corroborating monitor, not a stationarity test."""
    y = pd.Series(y).astype(float).iloc[-window:]
    x = pd.Series(x).astype(float).iloc[-window:]
    ok = y.notna() & x.notna()
    y, x = y[ok].to_numpy(), x[ok].to_numpy()
    if len(y) < 10 or np.ptp(x) == 0:      # too short / constant regressor
        return {"beta": np.nan, "alpha": np.nan, "resid": np.nan, "z": np.nan}
    b, a = np.polyfit(x, y, 1)
    res = y - (a + b * x)
    sd = res.std(ddof=2)
    return {"beta": float(b), "alpha": float(a), "resid": float(res[-1]), "z": float(res[-1] / sd) if sd > 0 else np.nan}


def screen_flies(quotes, root, snap="settle", asof=None, n=12, gap=1, window=65, skip_front=1):
    """Fixed-contract fly screen on the quarterly strip of `root` from a stir_quotes frame.
    skip_front: number of nearest live contracts dropped (the in-period / expiring front is sticky; 0 keeps it).
    Uses only data up to `asof` (default: last date); no forward information enters z, roll or vol."""
    q = quotes.copy()
    parts = q["fut_id"].str.split(":", expand=True)
    q = q[(parts[1] == root) & (q["snap"] == snap)]
    if q.empty:                                        # (assign onto an empty frame would resurrect rows)
        return pd.DataFrame()
    q = q.assign(cm=parts.loc[q.index, 2])
    q = q[q["cm"].str[5:7].isin(["03", "06", "09", "12"])]
    if q.empty:
        return pd.DataFrame()
    px = q.pivot(index="date", columns="cm", values="price_px")
    px.index = pd.to_datetime(px.index)
    px = px.sort_index()
    asof = pd.Timestamp(asof) if asof is not None else px.index[-1]
    prior = px.index[px.index <= asof]
    if len(prior) == 0:
        return pd.DataFrame()
    asof = prior[-1]                                   # last available date on or before asof
    live = [c for c in px.columns if pd.notna(px.loc[asof, c])][skip_front:skip_front + n]
    r = 100.0 - px[live]
    rows = []
    for i in range(0, len(live) - 2 * gap):
        a, b, c = live[i], live[i + gap], live[i + 2 * gap]
        f = pd.Series(fly_bp(r[a], r[b], r[c]), index=r.index).loc[:asof].dropna()
        if len(f) < max(20, window // 2):
            continue
        w = f.iloc[-window:]
        z = (f.iloc[-1] - w.mean()) / w.std(ddof=1)
        prev = pd.Series(fly_bp(r[live[i - 1]], r[a], r[b]), index=r.index).loc[:asof].iloc[-1] if i > 0 and gap == 1 else np.nan
        roll = f.iloc[-1] - prev
        vol = f.diff().iloc[-20:].std(ddof=1) * np.sqrt(252)
        d = np.sign(z)
        rows.append({"front": a, "belly": b, "back": c, "fly_bp": f.iloc[-1], "z": z, "roll_long_belly_bp": roll,
                     "fade_roll_bp": d * roll, "vol20_ann_bp": vol, "fade_roll_over_vol": d * roll / vol if vol > 0 else np.nan})
    out = pd.DataFrame(rows)
    if len(out):
        out["actionable"] = (out["z"].abs() >= 2.0) & (out["fade_roll_over_vol"] >= 0.3)
    return out


# ------------------------------------------------------------------ selftest
def selftest():
    ok = True

    def check(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {name}: got {got:.5f} want {want:.5f} (tol {tol})")

    # 1. Microfly levels and roll from a published Euribor strip (prices -> rates)
    px = [96.44, 96.70, 96.94, 97.135, 97.285, 97.39, 97.46, 97.50, 97.525, 97.545, 97.55, 97.56]
    mf = micro_flies(100.0 - np.array(px))
    # source quotes price-space microfly (2*belly - wings) = -fly_bp: 2nd +2.0, 3rd +4.5, 11th -0.5
    check("microfly 2nd (rate sign)", mf.loc[2, "fly_bp"], -2.0, 1e-9)
    check("microfly 3rd", mf.loc[3, "fly_bp"], -4.5, 1e-9)
    check("microfly 11th", mf.loc[11, "fly_bp"], 0.5, 1e-9)
    check("long-belly roll 8th (+1.5)", mf.loc[8, "roll_long_belly_bp"], 1.5, 1e-9)
    check("long-belly roll 11th (+2.0)", mf.loc[11, "roll_long_belly_bp"], 2.0, 1e-9)
    check("long-belly roll 3rd (-2.5)", mf.loc[3, "roll_long_belly_bp"], -2.5, 1e-9)
    # 2. pack / bundle yields (published example)
    p4 = [97.490, 97.310, 97.210, 97.160]
    check("pack yield %", 100 * pack_yield(p4), 2.735, 5e-4)
    check("2y bundle yield %", 100 * bundle_yield(p4 + [97.10, 97.00, 96.90, 96.87]), 2.901, 5e-4)
    # 3. 2y IMM swap from the SOFR strip (published bootstrap: 3.3304%)
    y = [4.105, 3.710, 3.395, 3.185, 3.060, 3.015, 3.035, 3.090]
    check("strip -> 2y IMM swap %", strip_swap_rate(y, 91), 3.3304, 1e-4)
    check("flat strip -> swap = strip rate", strip_swap_rate([4.0] * 8, 91), 4.0, 1e-9)
    # 4. FOMC-neutral SR1 hedge per 10 SR3 (published: 2.9 Apr + 3.1 May for a 4-May-2022 meeting)
    ne, nl = sr1_hedge_for_sr3(dt.date(2022, 3, 16), dt.date(2022, 6, 15), dt.date(2022, 5, 5), (2022, 5))
    check("SR1 early per 10 SR3", 10 * ne, 2.9, 0.03)
    check("SR1 late per 10 SR3", 10 * nl, 3.1, 0.03)
    # 5. fair SR1-SR3 ICS spread (published table, Sep-22 SR3): level/slope -> bp
    q0, q1, mm = dt.date(2022, 9, 21), dt.date(2022, 12, 21), [(2022, 10), (2022, 11)]
    for lvl, sl, want in [(0, 25, 1.33), (0, 50, 2.67), (100, -50, -2.59), (100, 0, 0.12), (500, 0, 3.11), (500, 50, 6.09)]:
        check(f"fair ICS level {lvl} slope {sl}", fair_sr1_sr3_bp(lvl, sl, q0, q1, mm), want, 0.07)
    # 6. Ho-Lee CA analytic: 100bp vol, T1=2, T2=2.25 -> 2.25bp
    check("Ho-Lee CA", ho_lee_ca_bp(100, 2.0, 2.25), 2.25, 1e-9)
    # 7. package cost: (1,-2,1) fly = 4 contracts * 0.5bp = 2bp
    check("fly round-trip cost", package_cost_bp([1, -2, 1]), 2.0, 1e-12)
    # 8. calendar tilt: curve linear in meeting count => tilted fly 0 while plain fly != 0
    M = np.array([0.0, 1.0, 4.0]); r = 3.0 + 0.10 * M
    check("plain fly on uneven meetings", fly_bp(r[0], r[1], r[2]), 100 * (2 * r[1] - r[0] - r[2]), 1e-9)
    check("tilted fly == 0", calendar_tilted_fly_bp(r[0], r[1], r[2], *M, max_tilt=1.0), 0.0, 1e-9)
    W = meeting_weights([dt.date(2026, 1, 1)], [dt.date(2026, 4, 1)], [dt.date(2026, 2, 1), dt.date(2026, 5, 1)])
    check("meeting weight (59/90 days post)", W[0, 0], 59 / 90, 1e-12)
    # 8b. FF decomposition recovers a known (step, step, year-end) triple
    N, dD, dJ, YE = 1.55, -0.25, -0.25, 0.07
    ffD = (11 / 31) * N + (20 / 31) * (N + dD + YE); ffJ = (29 / 31) * (N + dD) + (2 / 31) * (N + dD + dJ)
    dec = ff_decompose(N, ffD, ffJ, N + dD + dJ)
    check("FF decompose ye", dec["ye"], YE, 1e-12); check("FF decompose d_dec", dec["d_dec"], dD, 1e-12)
    check("FF decompose d_jan", dec["d_jan"], dJ, 1e-12)
    # 9. regression monitor recovers beta and flags an injected outlier
    rng = np.random.default_rng(0)
    x = np.cumsum(rng.normal(size=300)); yv = 0.5 * x + rng.normal(scale=0.2, size=300); yv[-1] += 1.5
    mon = regression_monitor(yv, x, 250)
    check("monitor beta", mon["beta"], 0.5, 0.03)
    check("monitor z flags outlier (>5)", float(mon["z"] > 5), 1.0, 0)
    # 10. fly screen: planted +10bp kink in the belly (5th contract) on the last day, gently sloped noisy curve
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2026-01-05", periods=120)
    cms = [f"2027-{m:02d}" for m in (3, 6, 9, 12)] + [f"2028-{m:02d}" for m in (3, 6, 9, 12)]
    base = 3.0 + 0.05 * np.arange(len(cms))
    rates = base + np.cumsum(rng.normal(0, 0.01, (len(dates), 1)), axis=0) + rng.normal(0, 0.003, (len(dates), len(cms)))
    rates[-1, 4] += 0.10                                   # contract index 4 (belly of fly 3-4-5) +10bp
    qd = pd.DataFrame([{"date": d, "snap": "settle", "fut_id": f"FUT:SR3:{c}", "price_px": 100 - rates[i, j]}
                       for i, d in enumerate(dates) for j, c in enumerate(cms)])
    scr = screen_flies(qd, "SR3", asof=dates[-1] + pd.Timedelta(days=2), n=8, skip_front=0)   # asof off-index
    row = scr[scr["belly"] == "2028-03"].iloc[0]
    check("screen z of planted kink (>4)", float(row["z"] > 4.0), 1.0, 0)
    check("screen roll = fly[i]-fly[i-1]", row["roll_long_belly_bp"],
          100 * (2 * rates[-1, 4] - rates[-1, 3] - rates[-1, 5]) - 100 * (2 * rates[-1, 3] - rates[-1, 2] - rates[-1, 4]), 1e-9)
    check("fade_roll = sign(z)*roll (z>0: belly cheap, receive belly earns the roll)", row["fade_roll_bp"], np.sign(row["z"]) * row["roll_long_belly_bp"], 1e-12)
    check("skip_front drops first contract", float(screen_flies(qd, "SR3", n=8, skip_front=1)["front"].iloc[0] == "2027-06"), 1.0, 0)
    check("unknown root -> empty", float(len(screen_flies(qd, "ZZ")) == 0), 1.0, 0)
    check("regression monitor short history -> NaN", float(np.isnan(regression_monitor([1, 2, 3], [1, 2, 3])["z"])), 1.0, 0)
    try:
        sr1_hedge_for_sr3(dt.date(2022, 3, 16), dt.date(2022, 6, 15), dt.date(2022, 6, 2), (2022, 5))
        check("meeting after SR1 month raises", 0.0, 1.0, 0)
    except ValueError:
        check("meeting after SR1 month raises", 1.0, 1.0, 0)
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quotes"); ap.add_argument("--root", default="SR3"); ap.add_argument("--snap", default="settle")
    ap.add_argument("--asof"); ap.add_argument("--n", type=int, default=12); ap.add_argument("--gap", type=int, default=1)
    ap.add_argument("--window", type=int, default=65); ap.add_argument("--skip-front", type=int, default=1)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 1
    if not a.quotes:
        ap.error("--quotes required (or --selftest)")
    q = pd.read_parquet(a.quotes) if a.quotes.endswith(".parquet") else pd.read_csv(a.quotes)
    out = screen_flies(q, a.root, a.snap, a.asof, a.n, a.gap, a.window, a.skip_front)
    with pd.option_context("display.width", 200, "display.float_format", "{:.2f}".format):
        print(out.reindex(out["z"].abs().sort_values(ascending=False).index).to_string(index=False) if len(out) else "no data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
