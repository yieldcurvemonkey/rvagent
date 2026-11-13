#!/usr/bin/env python3
"""CTD scenario analysis for physically delivered bond futures.

Computes, for one futures contract and one date:
  * forward clean price / conversion factor (CF) for every deliverable (repo-financed forward to delivery),
  * the CTD under parallel and slope shifts of the forward yield curve, and the switch (crossover) points,
  * a probability-weighted scenario table: P(CTD), delivery option value (DOV), model net basis per bond
    (theoretical delivery option value, TDOV), probability-weighted futures DV01/CF, fair futures price,
  * wildcard option value by backward induction (post-close normal price moves).

Conventions: yields in percent (pct), shifts and vols in bp, prices per 100 face (decimal, never 32nds),
DV01 in price points per bp per 100 face. Futures-side numbers are per 100 of futures price.
Models the SWITCH + TIMING (single delivery date) option only; end-of-month and new-issue options are not modelled.

CLI (canonical tables, see data-contract-and-adapters):
  python ctd_scenarios.py --fut-id FUT:ZN:2026-12 --date 2026-11-10 --fut-static fut_static.csv \
      --fut-basket fut_basket.csv --bond-static bond_static.csv --bond-quotes bond_quotes.csv \
      --repo-pct 4.0 --level-nvol-bp 100 --slope-sd-bp 3 [--fut-quotes fut_quotes.csv] [--delivery first|last|YYYY-MM-DD]
  python ctd_scenarios.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm


# --------------------------------------------------------------------------- bond maths
def bond_state(date, maturity, cpn_pct, freq):
    """(n coupons left incl. next, w = fraction of period to next coupon, accrued per 100). Coupon on `date` is paid."""
    date, maturity = pd.Timestamp(date), pd.Timestamp(maturity)
    m = 12 // freq
    k = 0
    nxt = maturity
    while maturity - pd.DateOffset(months=m * (k + 1)) > date:
        k += 1
        nxt = maturity - pd.DateOffset(months=m * k)
    prev = maturity - pd.DateOffset(months=m * (k + 1))
    w = (nxt - date).days / (nxt - prev).days
    return k + 1, w, cpn_pct / freq * (1.0 - w)


def clean_from_yield(y_pct, cpn_pct, freq, n, w):
    """Clean price per 100 at yield(s) y_pct (street convention, periodic compounding, linear accrual)."""
    y = np.asarray(y_pct, dtype=float) / 100.0 / freq
    c = cpn_pct / freq
    k = np.arange(n)
    dirty = (c * (1.0 + y[..., None]) ** -(w + k)).sum(-1) + 100.0 * (1.0 + y) ** -(w + n - 1)
    return dirty - c * (1.0 - w)


def yield_from_clean(px, cpn_pct, freq, n, w):
    return brentq(lambda y: float(clean_from_yield(y, cpn_pct, freq, n, w)) - px, -5.0, 40.0, xtol=1e-12)


def ust_cf(cpn_pct, years, months, notional_pct=6.0):
    """CME-style CF for semiannual bonds: whole years `years` plus `months` (0..11) to maturity from the first day of
    the delivery month, months rounded DOWN to a quarter. Exchange-published CFs always take precedence."""
    z = (months // 3) * 3
    v = z if z < 7 else z - 6
    n2 = 2 * years if z < 7 else 2 * years + 1
    r = 1.0 + notional_pct / 200.0
    disc = r ** -n2
    c = cpn_pct / 100.0
    a = r ** (-v / 6.0)
    b = c / 2.0 * (6 - v) / 6.0
    return a * (c / 2.0 + disc + c / (notional_pct / 100.0) * (1.0 - disc)) - b


def forward_clean(clean_px, cpn_pct, freq, maturity, settle, delivery, repo_pct, basis=360.0):
    """Repo-financed forward clean price at delivery (coupons reinvested at repo). basis = repo day-count denominator:
    360 (USD, EUR, CHF, SEK, NOK), 365 (GBP, JPY, CAD, AUD, NZD)."""
    settle, delivery = pd.Timestamp(settle), pd.Timestamp(delivery)
    n, w, acc = bond_state(settle, maturity, cpn_pct, freq)
    r = repo_pct / 100.0
    fwd = (clean_px + acc) * (1.0 + r * (delivery - settle).days / basis)
    m = 12 // freq
    for j in range(n):
        cd = pd.Timestamp(maturity) - pd.DateOffset(months=m * (n - 1 - j))
        if settle < cd <= delivery:
            fwd -= cpn_pct / freq * (1.0 + r * (delivery - cd).days / basis)
    nd, wd, accd = bond_state(delivery, maturity, cpn_pct, freq)
    return fwd - accd


# --------------------------------------------------------------------------- basket and scenarios
def build_basket(df, settle, delivery, repo_pct, repo_basis=360.0):
    """df columns: instrument_id, coupon_pct, coupon_freq, maturity_date, conversion_factor, clean_px.
    Optional: repo_pct (per-bond, special), beta (yield beta to the level shift, default 1)."""
    rows = []
    for r in df.itertuples(index=False):
        rp = getattr(r, "repo_pct", np.nan)
        rp = repo_pct if pd.isna(rp) else rp
        beta = getattr(r, "beta", np.nan)
        f = int(r.coupon_freq) if pd.notna(r.coupon_freq) and r.coupon_freq else 2
        fc = forward_clean(r.clean_px, r.coupon_pct, f, r.maturity_date, settle, delivery, rp, repo_basis)
        nd, wd, _ = bond_state(delivery, r.maturity_date, r.coupon_pct, f)
        y = yield_from_clean(fc, r.coupon_pct, f, nd, wd)
        dv01 = float((clean_from_yield(y - 0.005, r.coupon_pct, f, nd, wd) -
                      clean_from_yield(y + 0.005, r.coupon_pct, f, nd, wd)))  # +-0.5bp => per 1bp
        rows.append(dict(instrument_id=r.instrument_id, cpn=r.coupon_pct, freq=f, n=nd, w=wd, cf=r.conversion_factor,
                         fwd_clean=fc, fwd_y=y, dv01=dv01, beta=1.0 if pd.isna(beta) else beta,
                         mat_yrs=(pd.Timestamp(r.maturity_date) - pd.Timestamp(delivery)).days / 365.25))
    b = pd.DataFrame(rows)
    b["fwd_conv"] = b.fwd_clean / b.cf
    b["dv01_cf"] = b.dv01 / b.cf
    return b


def scenario_conv(b, level_bp, slope_bp):
    """Converted prices (clean price at delivery / CF), shape (scenarios, bonds).
    Bond i yield shift = beta_i*level + slope*(pos_i - 0.5), pos = 0 (shortest) .. 1 (longest) by maturity, so slope =
    change in (longest - shortest) yield in bp and the basket's mean slope-shift is zero at the mid maturity."""
    level_bp, slope_bp = np.atleast_1d(level_bp).astype(float), np.atleast_1d(slope_bp).astype(float)
    span = b.mat_yrs.max() - b.mat_yrs.min()
    pos = ((b.mat_yrs - b.mat_yrs.min()) / span).to_numpy() if span > 0 else np.full(len(b), 0.5)
    out = np.empty((len(level_bp), len(b)))
    for i, r in enumerate(b.itertuples(index=False)):
        dy = (r.beta * level_bp + slope_bp * (pos[i] - 0.5)) / 100.0
        out[:, i] = clean_from_yield(r.fwd_y + dy, r.cpn, r.freq, r.n, r.w) / r.cf
    return out


def grid(level_sd_bp, slope_sd_bp=0.0, n_level=801, n_slope=41, width=5.0):
    """Midpoint-rule normal grid: level (and optionally independent slope). Returns level, slope, weights (sum 1)."""
    zl = np.linspace(-width, width, n_level)
    wl = norm.pdf(zl)
    wl /= wl.sum()
    if slope_sd_bp <= 0:
        return zl * level_sd_bp, np.zeros(n_level), wl
    zs = np.linspace(-width, width, n_slope)
    ws = norm.pdf(zs)
    ws /= ws.sum()
    L, S = np.meshgrid(zl, zs, indexing="ij")
    return (L * level_sd_bp).ravel(), (S * slope_sd_bp).ravel(), np.outer(wl, ws).ravel()


def option_stats(conv, w, fwd_conv, cf, adjust=True):
    """Probability-weighted CTD analysis. adjust=True adds (forward - mean simulated converted price) per bond so each
    bond's expected converted price equals its forward (removes the convexity drift of the shock distribution).
    Returns dict: p_ctd (per bond), f_fair (E[min conv]), dov (min fwd conv - f_fair), tdov (per bond, model net basis)."""
    conv = np.asarray(conv, dtype=float)
    fwd_conv, cf = np.asarray(fwd_conv, dtype=float), np.asarray(cf, dtype=float)
    if adjust:
        conv = conv + (fwd_conv - (w[:, None] * conv).sum(0))
    mn = conv.min(1)
    p = np.bincount(conv.argmin(1), weights=w, minlength=conv.shape[1])
    f_fair = float((w * mn).sum())
    return dict(p_ctd=p, f_fair=f_fair, dov=float(fwd_conv.min() - f_fair),
                tdov=cf * (w[:, None] * (conv - mn[:, None])).sum(0))


def ctd_by_shift(b, shifts_bp, slope_bp=0.0):
    conv = scenario_conv(b, np.asarray(shifts_bp, float), np.full(len(np.atleast_1d(shifts_bp)), slope_bp))
    return b.instrument_id.to_numpy()[conv.argmin(1)]


def switch_points(b, lo=-150.0, hi=150.0, step=5.0, slope_bp=0.0, tol=1e-3):
    """Parallel-shift crossovers of the CTD (bp of shift to the forward yield curve). List of (shift_bp, from, to)."""
    xs = np.arange(lo, hi + step / 2, step)
    ids = ctd_by_shift(b, xs, slope_bp)
    out = []
    for i in range(len(xs) - 1):
        if ids[i] != ids[i + 1]:
            a, c = xs[i], xs[i + 1]
            while c - a > tol:
                m = 0.5 * (a + c)
                if ctd_by_shift(b, [m], slope_bp)[0] == ids[i]:
                    a = m
                else:
                    c = m
            out.append((float(round(0.5 * (a + c), 3)), str(ids[i]), str(ids[i + 1])))
    return out


def analyse(b, level_sd_bp, slope_sd_bp=0.0, fut_px=None):
    """Full table. fut_px (market futures price) adds market net basis and OA basis (= market NB - TDOV)."""
    lv, sl, w = grid(level_sd_bp, slope_sd_bp)
    st = option_stats(scenario_conv(b, lv, sl), w, b.fwd_conv.to_numpy(), b.cf.to_numpy())
    t = b[["instrument_id", "cpn", "cf", "fwd_clean", "fwd_y", "dv01", "dv01_cf"]].copy()
    t["p_ctd"] = st["p_ctd"]
    t["tdov_px"] = st["tdov"]  # model net basis per bond, price points
    t.attrs.update(f_fair=st["f_fair"], dov=st["dov"], fut_dv01=float((st["p_ctd"] * b.dv01_cf).sum()),
                   current_ctd=b.instrument_id[b.fwd_conv.idxmin()])
    if fut_px is not None:
        t["nb_px"] = b.fwd_clean - b.cf * fut_px
        t["oab_px"] = t.nb_px - t.tdov_px
        t.attrs["fut_rich_px"] = fut_px - st["f_fair"]  # > 0: futures rich vs model (basis cheap)
    return t


# --------------------------------------------------------------------------- wildcard option
def wildcard_exercise_threshold(cf, gross_basis_px):
    """Post-close price move x (points per 100 face) beyond which delivering today beats waiting:
    (1/cf - 1) * x > GB  ->  x* = GB * cf / (1 - cf). cf < 1: x* > 0 is a rise needed; cf > 1: x* < 0 is a fall needed."""
    return gross_basis_px * cf / (1.0 - cf)


def wildcard_value(cf, sigma_px, carry_px_per_day, n_days, sigma_mult=None):
    """Wildcard value per 100 face delivered (= futures points per contract) by backward induction.
    k = 1/cf - 1 (tail per unit delivered; |k| is used so CF > 1, where a post-close FALL pays, is symmetric); x ~ N(0, sigma^2) is the post-close price move (points);
    W_i = V_{i+1} + g; V_i = k*s*phi(W_i/(k*s)) + Phi(W_i/(k*s)) * W_i; value = V_1 - V_1(k=0) (so carry is not
    double counted). sigma_mult: optional per-day multipliers (e.g. 2 on FOMC days). Last day: V_{N+1} = 0."""
    mult = np.ones(n_days) if sigma_mult is None else np.asarray(sigma_mult, float)

    def run(k):
        v = 0.0
        for i in range(n_days - 1, -1, -1):
            wv, s = v + carry_px_per_day, sigma_px * mult[i] * abs(k)
            v = wv if s <= 0 else s * norm.pdf(wv / s) + norm.cdf(wv / s) * wv
        return v

    return run(1.0 / cf - 1.0) - run(0.0)


# --------------------------------------------------------------------------- CLI from canonical tables
def _active(df, d, lo="valid_from", hi="valid_to"):
    d = pd.Timestamp(d)
    m = df[lo].le(d) if lo in df else True
    if hi in df:
        m = m & (df[hi].isna() | df[hi].gt(d))
    return df[m]


def run_from_tables(fut_id, date, fut_static, fut_basket, bond_static, bond_quotes, repo_pct, level_nvol_bp,
                    slope_sd_bp=0.0, delivery="last", fut_quotes=None, settle_date=None, repo_basis=360.0):
    fs = fut_static[fut_static.fut_id == fut_id].iloc[0]
    deliv = {"first": fs.first_delivery_date, "last": fs.last_delivery_date}.get(delivery, delivery)
    deliv = pd.Timestamp(deliv)
    fb = fut_basket[fut_basket.fut_id == fut_id]
    fb = _active(fb, date, "eligible_from", "eligible_to")
    bs = _active(bond_static, date).drop_duplicates("instrument_id", keep="last")
    bq = bond_quotes[pd.to_datetime(bond_quotes.date) == pd.Timestamp(date)].drop_duplicates("instrument_id", keep="last")  # one snap per bond
    df = fb.merge(bs, on="instrument_id").merge(bq[["instrument_id", "clean_px"]], on="instrument_id")
    df["maturity_date"] = pd.to_datetime(df["maturity_date"])
    n0 = len(df)
    df = df.dropna(subset=["conversion_factor", "clean_px"])  # never invent a CF or a price
    if df.empty:
        raise ValueError(f"no deliverable with both a conversion factor and a clean price on {date} for {fut_id}")
    if len(df) < n0:
        print(f"WARNING: dropped {n0 - len(df)} basket bond(s) missing CF or price", file=sys.stderr)
    settle = pd.Timestamp(settle_date) if settle_date else pd.Timestamp(date) + pd.offsets.BDay(1)
    b = build_basket(df, settle, deliv, repo_pct, repo_basis)
    T = max((pd.Timestamp(fs.last_trade_date) - pd.Timestamp(date)).days, 1) / 365.0
    fpx = None
    if fut_quotes is not None:
        q = fut_quotes[(fut_quotes.fut_id == fut_id) & (pd.to_datetime(fut_quotes.date) == pd.Timestamp(date))]
        fpx = float(q.price_px.iloc[0]) if len(q) else None
    t = analyse(b, level_nvol_bp * math.sqrt(T), slope_sd_bp, fpx)
    return t, switch_points(b), b


# --------------------------------------------------------------------------- selftest
def _selftest():
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info else ""))
        ok &= bool(cond)

    # 1. CF known answers: a 6% bond has CF 1 (z=0, z=6); 8% 10y at 6% = 114.8775/100
    check("CF 6% 10y z=0 == 1", abs(ust_cf(6, 10, 0) - 1.0) < 1e-12)
    check("CF 6% 10y z=6 == 1", abs(ust_cf(6, 10, 6) - 1.0) < 1e-12)
    check("CF 8% 10y == 1.14877", abs(ust_cf(8, 10, 0) - 1.14877) < 5e-5, f"{ust_cf(8, 10, 0):.5f}")

    # 2. zero-coupon pair: CF = price at 6% => converted price ((1.03)/(1+y/2))^(2n); exact crossover at y = 6%
    d0 = pd.Timestamp("2026-06-15")
    zdf = pd.DataFrame(dict(instrument_id=["Z5", "Z10"], coupon_pct=[0.0, 0.0], coupon_freq=[2, 2],
                            maturity_date=pd.to_datetime(["2031-06-15", "2036-06-15"]),
                            conversion_factor=[1.03 ** -10, 1.03 ** -20]))
    y0 = 5.5
    zdf["clean_px"] = [100 / (1 + y0 / 200) ** 10, 100 / (1 + y0 / 200) ** 20]
    zb = build_basket(zdf, d0, d0, 0.0)
    sp = switch_points(zb)
    check("zero-coupon crossover at +50bp (6.00%)", len(sp) == 1 and abs(sp[0][0] - 50.0) < 0.01 and sp[0][2] == "Z10",
          str(sp))
    check("rally -> shorter bond CTD, sell-off -> longer", list(ctd_by_shift(zb, [-100, 100])) == ["Z5", "Z10"])

    # 3. probability: forward yield 6.5%, level sd 50bp -> P(longer is CTD) = P(y > 6%) = Phi(1)
    zdf["clean_px"] = [100 / (1 + 6.5 / 200) ** 10, 100 / (1 + 6.5 / 200) ** 20]
    zb2 = build_basket(zdf, d0, d0, 0.0)
    lv, sl, w = grid(50.0)
    st = option_stats(scenario_conv(zb2, lv, sl), w, zb2.fwd_conv.to_numpy(), zb2.cf.to_numpy(), adjust=False)
    check("P(long CTD) == Phi(1)", abs(st["p_ctd"][1] - norm.cdf(1.0)) < 0.01, f"{st['p_ctd'][1]:.4f}")
    tiny = analyse(zb2, 0.01)
    check("sigma->0: DOV -> 0 and current CTD certain", tiny.attrs["dov"] < 1e-6 and tiny.p_ctd.max() > 0.999)
    big = analyse(zb2, 50.0)
    check("DOV > 0 with vol and model NB of CTD > 0", big.attrs["dov"] > 0 and big.tdov_px.min() >= -1e-9,
          f"{big.attrs['dov']:.4f}")

    # 4. DOV analytic: converted prices a - k1 s, a - k2 s, s~N(0,sd): DOV = (k2 - k1) sd / sqrt(2 pi)
    sd, k1, k2 = 40.0, -0.05, 0.08
    lv, _, w = grid(sd)
    conv = 100.0 - np.outer(lv, [k1, k2])
    got = option_stats(conv, w, np.array([100.0, 100.0]), np.ones(2))["dov"]
    exp = (k2 - k1) * sd / math.sqrt(2 * math.pi)
    check("DOV == (k2-k1)*sd/sqrt(2pi)", abs(got - exp) / exp < 0.01, f"{got:.5f} vs {exp:.5f}")

    # 5. wildcard: N=1, g=0 -> k*s/sqrt(2pi); N=1 with carry -> Bachelier call struck at carry on k*x; k=0 -> 0
    cf, s, g = 0.8, 0.03, 0.002
    k = 1 / cf - 1
    v0 = wildcard_value(cf, s, 0.0, 1)
    check("wildcard N=1 g=0 == k s/sqrt(2pi)", abs(v0 - k * s / math.sqrt(2 * math.pi)) < 1e-12, f"{v0:.6f}")
    d = g / (k * s)
    bach = k * s * (norm.pdf(d) - d * norm.cdf(-d))
    check("wildcard N=1 with carry == Bachelier call", abs(wildcard_value(cf, s, g, 1) - bach) < 1e-12)
    check("wildcard CF=1 -> 0", wildcard_value(1.0, s, g, 5) == 0.0)
    check("wildcard rises with days", wildcard_value(cf, s, 0.0, 10) > wildcard_value(cf, s, 0.0, 1))
    # BofA example: CF 0.7342, GB 5/32 -> threshold 0.4316; 1pt rally exceeds it (deliver, net profit)
    thr = wildcard_exercise_threshold(0.7342, 5 / 32)
    check("wildcard threshold WNU5 example", abs(thr - 0.4316) < 1e-3 and 1.0 > thr, f"{thr:.4f}")

    # 6. coupon basket at flat 6%: below 6% the lowest-duration bond is CTD, above it the highest
    d1 = pd.Timestamp("2026-06-15")
    mats = ["2033-12-15", "2036-06-15", "2046-06-15"]
    cpns = [6.5, 3.0, 4.0]
    rows = []
    for i, (m, c) in enumerate(zip(mats, cpns)):
        yrs = (pd.Timestamp(m).year - 2026) + (pd.Timestamp(m).month - 6) / 12
        yy, mm = int(yrs), int(round((yrs - int(yrs)) * 12))
        n, wv, _ = bond_state(d1, m, c, 2)
        rows.append(dict(instrument_id=f"B{i}", coupon_pct=c, coupon_freq=2, maturity_date=pd.Timestamp(m),
                         conversion_factor=ust_cf(c, yy, mm), clean_px=float(clean_from_yield(6.0, c, 2, n, wv))))
    cb = build_basket(pd.DataFrame(rows), d1, d1, 0.0)
    dur = cb.dv01 / cb.fwd_clean  # modified-duration ordering at the forward yield
    lo, hi_ = list(ctd_by_shift(cb, [-150, 150]))
    check("coupon basket: rally -> lowest duration, sell-off -> highest",
          lo == f"B{int(dur.idxmin())}" and hi_ == f"B{int(dur.idxmax())}", f"{lo},{hi_}")
    check("CF-adjusted DV01 jump: P-weighted fut DV01 between min and max",
          cb.dv01_cf.min() <= analyse(cb, 60.0).attrs["fut_dv01"] <= cb.dv01_cf.max())

    # 6b. known-answer checks on forward, scenario map, aggregation and OAB (each pins one formula)
    p0, d_s, d_d = pd.Timestamp("2026-06-15"), pd.Timestamp("2026-06-15"), pd.Timestamp("2026-09-13")  # 90 days
    check("zero-coupon forward ACT/360", abs(forward_clean(95.0, 0.0, 2, "2031-06-15", d_s, d_d, 4.0) - 95.0 * 1.01) < 1e-12)
    check("repo basis 365", abs(forward_clean(95.0, 0.0, 2, "2031-06-15", d_s, d_d, 4.0, 365.0) - 95.0 * (1 + .04 * 90 / 365)) < 1e-12)
    st_, dl_ = pd.Timestamp("2026-07-15"), pd.Timestamp("2026-10-15")  # coupon 15 Aug falls inside the window
    acc_s = 2.0 * (1 - 31 / 181)
    acc_d = 2.0 * (1 - 123 / 184)
    want = (100 + acc_s) * (1 + .04 * 92 / 360) - 2.0 * (1 + .04 * 61 / 360) - acc_d
    check("coupon reinvested at repo and AI removed", abs(forward_clean(100.0, 4.0, 2, "2036-08-15", st_, dl_, 4.0) - want) < 1e-9,
          f"{forward_clean(100.0, 4.0, 2, '2036-08-15', st_, dl_, 4.0):.6f} vs {want:.6f}")
    sc = scenario_conv(zb, [0.0], [10.0])[0]  # slope +10bp: longest +5bp, shortest -5bp
    check("slope sign: longest yield up, shortest down", abs(sc[1] - 100 * 1.03 ** 20 / (1 + 5.55 / 200) ** 20) < 1e-9 and
          abs(sc[0] - 100 * 1.03 ** 10 / (1 + 5.45 / 200) ** 10) < 1e-9, str(sc))
    lv_, sl_, w_ = grid(60.0, 3.0)
    cv = scenario_conv(cb, lv_, sl_)
    adj = option_stats(cv, w_, cb.fwd_conv.to_numpy(), cb.cf.to_numpy())
    mean_adj = (w_[:, None] * (cv + (cb.fwd_conv.to_numpy() - (w_[:, None] * cv).sum(0)))).sum(0)
    check("mean adjustment: E[a_i] == forward a_i", np.allclose(mean_adj, cb.fwd_conv.to_numpy()))
    check("TDOV_i == CF_i (fwd a_i - E[min a])", np.allclose(adj["tdov"], cb.cf.to_numpy() * (cb.fwd_conv.to_numpy() - adj["f_fair"])))
    an = analyse(cb, 60.0, 3.0, fut_px=adj["f_fair"])
    check("OAB == 0 at model-fair futures; fut_rich == 0", np.allclose(an.oab_px, 0.0, atol=1e-9) and abs(an.attrs["fut_rich_px"]) < 1e-12)
    check("OAB = NB - TDOV (sign)", np.allclose(an.nb_px, cb.fwd_clean - cb.cf * adj["f_fair"]) and np.allclose(an.nb_px - an.tdov_px, an.oab_px))
    check("dv01_cf == dv01 / cf", np.allclose(cb.dv01_cf, cb.dv01 / cb.cf))
    check("sigma->0: futures DV01 == CTD dv01/CF (CF != 1)", abs(tiny.attrs["fut_dv01"] - zb2.dv01_cf[zb2.fwd_conv.idxmin()]) < 1e-6)
    check("wildcard symmetric in CF<1 / CF>1 (k = +/-0.2)", abs(wildcard_value(1 / 1.2, s, g, 5) - wildcard_value(1 / 0.8, s, g, 5)) < 1e-12 and
          wildcard_value(1.25, s, g, 5) > 0)

    # 7. CLI path through canonical tables
    fut_static = pd.DataFrame(dict(fut_id=["FUT:ZB:2026-12"], first_delivery_date=["2026-12-01"],
                                   last_delivery_date=["2026-12-31"], last_trade_date=["2026-12-21"]))
    fb = pd.DataFrame(dict(fut_id="FUT:ZB:2026-12", instrument_id=[f"B{i}" for i in range(3)],
                           conversion_factor=cb.cf, eligible_from="2020-01-01", eligible_to=None))
    bst = pd.DataFrame(dict(instrument_id=[f"B{i}" for i in range(3)], valid_from=pd.Timestamp("2020-01-01"),
                            valid_to=pd.NaT, coupon_pct=cpns, coupon_freq=2, maturity_date=pd.to_datetime(mats)))
    bqt = pd.DataFrame(dict(date="2026-06-12", instrument_id=[f"B{i}" for i in range(3)],
                            clean_px=[r["clean_px"] for r in rows]))
    for tb in (fb, bst):
        for c in ("eligible_from", "eligible_to", "valid_from", "valid_to"):
            if c in tb:
                tb[c] = pd.to_datetime(tb[c])
    t, sps, _ = run_from_tables("FUT:ZB:2026-12", "2026-06-12", fut_static, fb, bst, bqt, 4.0, 100.0, 3.0)
    check("CLI table: P(CTD) sums to 1", abs(t.p_ctd.sum() - 1.0) < 1e-9 and t.attrs["dov"] >= 0)
    print(t.round(4).to_string(index=False))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fut-id")
    ap.add_argument("--date")
    ap.add_argument("--fut-static")
    ap.add_argument("--fut-basket")
    ap.add_argument("--bond-static")
    ap.add_argument("--bond-quotes")
    ap.add_argument("--fut-quotes")
    ap.add_argument("--repo-pct", type=float, help="term repo to delivery, pct (GC default for every bond)")
    ap.add_argument("--level-nvol-bp", type=float, help="annual normal yield vol (bp/yr) from futures options")
    ap.add_argument("--slope-sd-bp", type=float, default=0.0, help="sd of (longest - shortest) yield change to LTD, bp")
    ap.add_argument("--delivery", default="last", help="first | last | YYYY-MM-DD (pricing date for the forward)")
    ap.add_argument("--settle-date")
    ap.add_argument("--repo-basis", type=float, default=360.0, help="repo day-count denominator: 360 (USD/EUR/CHF/SEK/NOK) or 365 (GBP/JPY/CAD/AUD/NZD)")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    need = ["fut_id", "date", "fut_static", "fut_basket", "bond_static", "bond_quotes", "repo_pct", "level_nvol_bp"]
    if any(getattr(a, k) is None for k in need):
        ap.error("need --fut-id --date --fut-static --fut-basket --bond-static --bond-quotes --repo-pct --level-nvol-bp")

    def rd(p):
        if p is None:
            return None
        return pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(
            p, parse_dates=[c for c in pd.read_csv(p, nrows=0).columns
                            if c.endswith("_date") or c in ("date", "valid_from", "valid_to")])

    t, sps, _ = run_from_tables(a.fut_id, a.date, rd(a.fut_static), rd(a.fut_basket), rd(a.bond_static),
                                rd(a.bond_quotes), a.repo_pct, a.level_nvol_bp, a.slope_sd_bp, a.delivery,
                                rd(a.fut_quotes), a.settle_date, a.repo_basis)
    print(t.round(4).to_string(index=False))
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.attrs.items()})
    print("parallel switch points (bp, from, to):", sps)
    if a.out:
        t.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
