r"""Cross-market government-bond RV helpers: FX-hedged yield pickup, USD ASW of a basis-swapped foreign bond,
DV01 hedge notionals, pair carry, rolling beta/R2/z to an anchor market, and the expanding-window PCA-residual
"dislocation index" used to screen EGB spreads to Germany.

Conventions (rates in pct in/out of the pct functions, spreads in bp):
    spread A-B = yield(A) - yield(B)           positive = A cheap / higher yield than B
    fx "home per foreign" = units of HOME currency per 1 unit of FOREIGN currency (EURUSD quote, USD home, EUR foreign)
    hedged pickup (bp) = [y_foreign + (F/S - 1) * basis/days * 100 - y_home] * 100
        F, S = forward and spot in home-per-foreign; investor buys foreign bond, sells foreign ccy forward.
        F/S - 1 < 0 (foreign ccy at forward discount, i.e. foreign rates above home) = hedge COST.
    rate-differential form (same number, no forward points):
        pickup (bp) = (y_foreign - r_foreign) - (y_home - r_home) + basis_bp
        r = money-market rate for the hedge tenor; basis_bp = cross-currency basis as the spread on the HOME-currency
        leg against the FOREIGN-currency leg flat (flip the sign if the table quotes it on the other leg)
    USD ASW (foreign bond) = (ASW_foreign - CCBS) / CF,  CF = BPV_USD / BPV_foreign
        ASW_foreign = govt_minus_swap (bond yield - swap rate; positive = bond cheap to swaps), on the CCBS foreign-leg index
    yields: the quotes in curve_par are in each curve's own compounding (UST semi-annual, Bund annual, JGB simple). Convert
        to one basis before differencing (semi vs annual is ~y^2/4, about 5bp at 4.5%): see to_annual / --home-freq
    hedge notional of leg B = -notional_A * DV01_A * fx_b_per_a / DV01_B   (DV01 per unit face in own currency;
        fx_b_per_a converts leg A's currency into leg B's currency)
    PCA residual: positive = spread cheap (actual - fitted), negative = rich.

CLI (canonical tables from data-contract-and-adapters, CSV or Parquet):
    python cross_market_spreads.py pickup --curve-par curve_par.csv --fx-rates fx_rates.csv \
        --home-curve USD-GOVT-US --foreign-curve EUR-GOVT-DE --tenor 10Y --pair EURUSD
    python cross_market_spreads.py beta --curve-par curve_par.csv --local EUR-GOVT-DE --anchor USD-GOVT-US \
        --tenor 10Y --freq W-WED --window 52
    python cross_market_spreads.py dislocation --curve-par curve_par.csv --base-curve EUR-GOVT-DE \
        --curves EUR-GOVT-FR,EUR-GOVT-IT,EUR-GOVT-ES --tenors 2Y,5Y,10Y,30Y --npc 3 --min-obs 250
    python cross_market_spreads.py --selftest
Look-ahead: beta/resid and dislocation values at date t use data through t (today's close is in the fit); trade at t+1
    (shift the signal by one bar) and never backfill the window.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------------------------- FX-hedged carry
def home_per_foreign(pair: str, outright: float, home: str, foreign: str) -> float:
    """Convert a BASEQUOTE outright (QUOTE per 1 BASE) to home-per-foreign. pair must be home+foreign in some order."""
    base, quote = pair[:3], pair[3:]
    if (base, quote) == (foreign, home):
        return float(outright)
    if (base, quote) == (home, foreign):
        return 1.0 / float(outright)
    raise ValueError(f"pair {pair} does not link home {home} and foreign {foreign}")


def hedge_carry_pct(spot_hpf: float, fwd_hpf: float, days: float, basis: float = 365.0) -> float:
    """Annualised hedge carry in pct for a rolling forward hedge of `days` (negative = hedge cost)."""
    return (fwd_hpf / spot_hpf - 1.0) * basis / days * 100.0


def hedged_pickup_bp(y_foreign_pct: float, y_home_pct: float, spot_hpf: float, fwd_hpf: float, days: float,
                     basis: float = 365.0) -> float:
    """FX-hedged yield pickup of the foreign bond over the home bond, bp. Simple (non-compounded) annualisation; `basis` is
    the day-count denominator (360 or 365). 365 vs 360 alone moves the carry by 1.4% of itself (about 4bp on a 300bp
    differential), so match the yields' convention and compare like with like. NOT the xccy basis."""
    return (y_foreign_pct + hedge_carry_pct(spot_hpf, fwd_hpf, days, basis) - y_home_pct) * 100.0


def to_annual(y_pct: float, freq: int) -> float:
    """Yield in pct quoted with `freq` compounding periods a year (2 = UST/gilt/JGB street, 1 = EGB annual) -> annual pct.
    Use before differencing yields quoted on different bases (4.5% semi = 4.5506% annual)."""
    return ((1.0 + y_pct / 100.0 / freq) ** freq - 1.0) * 100.0


def hedged_pickup_rates_bp(y_foreign_pct: float, r_foreign_pct: float, y_home_pct: float, r_home_pct: float,
                           basis_bp: float = 0.0) -> float:
    """Rate-differential form: (y_f - r_f) - (y_h - r_h) + basis, bp. r = money-market rate for the hedge tenor
    (same day count as the yields); basis_bp = xccy basis on the HOME leg vs the foreign leg flat."""
    return ((y_foreign_pct - r_foreign_pct) - (y_home_pct - r_home_pct)) * 100.0 + basis_bp


def usd_asw_foreign_bp(swap_spread_foreign_bp: float, ccbs_bp: float, bpv_usd: float, bpv_foreign: float) -> float:
    """USD ASW (over USD reference rate) of a basis-swapped foreign par bond: (ASW_foreign - CCBS) / CF.
    ASW_foreign must be on the same reference rate as the CCBS foreign leg (add the index basis first if not).
    CCBS is the spread on the foreign leg vs USD flat (negative = 'wider')."""
    return (swap_spread_foreign_bp - ccbs_bp) / (bpv_usd / bpv_foreign)


def dv01_hedge_notional(notional_a: float, dv01_a: float, dv01_b: float, fx_b_per_a: float = 1.0) -> float:
    """Face of leg B (in B's currency; negative = short when A is long) that zeroes net DV01 in one currency.
    dv01_* = currency per bp per unit face, each in its own currency; fx_b_per_a = B-currency units per 1 A-currency."""
    return -notional_a * dv01_a * fx_b_per_a / dv01_b


def pair_carry_bp(y_long_pct: float, cash_long_pct: float, dur_long: float,
                  y_short_pct: float, cash_short_pct: float, dur_short: float) -> float:
    """Duration-weighted carry of a long-bond / short-bond pair, each leg financed in its own currency, bp p.a.
    = (y_long - cash_long) - (dur_long/dur_short) * (y_short - cash_short); slide omitted."""
    w = dur_long / dur_short
    return ((y_long_pct - cash_long_pct) - w * (y_short_pct - cash_short_pct)) * 100.0


# ----------------------------------------------------------------------------------------------- betas and z-scores
def rolling_beta(y: pd.Series, x: pd.Series, window: int) -> pd.DataFrame:
    """Rolling OLS of y on x (with intercept): beta, r2, last residual, resid_z = residual / rolling resid sd.
    Feed CHANGES (weekly, mid-week close) for betas; feed LEVELS only for a fair-value residual (levels residuals are
    autocorrelated: R2 and z are overstated, test the residual for stationarity before trusting z).
    resid/resid_z are IN-SAMPLE (the window includes today): shift(1) before trading on them."""
    d = pd.concat([y, x], axis=1, keys=["y", "x"]).dropna()
    cov = d["y"].rolling(window).cov(d["x"])
    vx, vy = d["x"].rolling(window).var(), d["y"].rolling(window).var()
    beta = cov / vx
    r2 = cov ** 2 / (vx * vy)
    alpha = d["y"].rolling(window).mean() - beta * d["x"].rolling(window).mean()
    fit = alpha + beta * d["x"]
    resid = d["y"] - fit
    sd = np.sqrt((1 - r2) * vy)
    return pd.DataFrame({"beta": beta, "r2": r2, "resid": resid, "resid_z": resid / sd})


def zscore(s: pd.Series, window: int) -> pd.Series:
    return (s - s.rolling(window).mean()) / s.rolling(window).std()


# ----------------------------------------------------------------------------------------------- PCA dislocation
def pca_residual_last(X: np.ndarray, n_pc: int) -> np.ndarray:
    """Residual of the last row of X (T x N) after projecting on the top n_pc PCs of X (fit on all rows)."""
    mu = X.mean(axis=0)
    Z = X - mu
    _, _, vt = np.linalg.svd(Z, full_matrices=False)
    V = vt[:n_pc].T
    z = Z[-1]
    return z - V @ (V.T @ z)


def dislocation_index(X: pd.DataFrame, n_pc: int, min_obs: int = 250, z_window: int | None = None) -> pd.DataFrame:
    """Expanding-window PCA of spreads (columns = country x tenor, bp). Per day: residual vector of that day,
    cross-sectional std (dispersion), and its expanding z-score. Returns columns dispersion, dislocation_z, plus
    the residuals (positive = cheap). z_window=None = expanding."""
    A = X.to_numpy(float)
    if np.isnan(A).any():
        raise ValueError("NaN in spread panel: dropna or fill (same dates for every column) before PCA")
    if not 0 < n_pc < A.shape[1]:
        raise ValueError(f"n_pc must be in 1..{A.shape[1] - 1} for {A.shape[1]} series")
    if len(A) < min_obs or min_obs <= n_pc:
        raise ValueError(f"need min_obs ({min_obs}) > n_pc and <= history ({len(A)} rows)")
    rows, disp = [], []
    for t in range(min_obs, len(A) + 1):
        r = pca_residual_last(A[:t], n_pc)
        rows.append(r)
        disp.append(r.std(ddof=1))
    idx = X.index[min_obs - 1:]
    out = pd.DataFrame(rows, index=idx, columns=X.columns)
    d = pd.Series(disp, index=idx)
    if z_window is None:
        z = (d - d.expanding().mean()) / d.expanding().std()
    else:
        z = zscore(d, z_window)
    out.insert(0, "dislocation_z", z)
    out.insert(0, "dispersion", d)
    return out


# ----------------------------------------------------------------------------------------------- IO helpers
def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def _series(curve_par: pd.DataFrame, curve_id: str, tenor: str, snap: str | None) -> pd.Series:
    d = curve_par[(curve_par.curve_id == curve_id) & (curve_par.tenor == tenor) & (curve_par.start == "0D")]
    if snap:
        d = d[d.snap == snap]
    if d.snap.nunique() > 1:
        raise SystemExit(f"{curve_id} {tenor}: several snaps {sorted(d.snap.unique())}; pass --snap (never mix snaps)")
    s = d.assign(date=pd.to_datetime(d["date"])).set_index("date")["par_rate_pct"].sort_index()
    if s.empty:
        raise SystemExit(f"no rows for {curve_id} {tenor}")
    return s


def _periodic_changes(s: pd.Series, freq: str) -> pd.Series:
    """Last obs per period, first difference in bp. Drops the still-open final period (e.g. Thu-Fri of a W-WED week),
    which would otherwise enter as a 2-day 'weekly' change."""
    w = s.resample(freq).last()
    return w[w.index <= s.index[-1]].diff() * 100


def _emit(df: pd.DataFrame, path: str | None) -> None:
    if path:
        df.to_csv(path, lineterminator="\n")
    else:
        sys.stdout.write(df.to_csv(lineterminator="\n"))


def cmd_pickup(a) -> None:
    cp, fx = _read(a.curve_par), _read(a.fx_rates)
    home, foreign = a.home_curve[:3], a.foreign_curve[:3]
    yh, yf = _series(cp, a.home_curve, a.tenor, a.snap), _series(cp, a.foreign_curve, a.tenor, a.snap)
    f = fx[fx.pair == a.pair]
    if a.snap:
        f = f[f.snap == a.snap]
    if f.empty:
        raise SystemExit(f"no fx_rates rows for pair {a.pair}")
    if f.snap.nunique() > 1:
        raise SystemExit(f"fx_rates {a.pair}: several snaps {sorted(f.snap.unique())}; pass --snap (never mix snaps)")
    f = f.assign(date=pd.to_datetime(f["date"]))
    spot = f[f.tenor == "SPOT"].set_index("date")["outright_fx"]
    fwd = f[f.tenor == a.hedge_tenor].set_index("date")
    d = pd.concat([yh.rename("yh"), yf.rename("yf"), spot.rename("spot"), fwd["outright_fx"].rename("fwd")],
                  axis=1).dropna()
    if "value_date" in fwd and "value_date" in f[f.tenor == "SPOT"]:
        vs = pd.to_datetime(f[f.tenor == "SPOT"].set_index("date")["value_date"])
        days = (pd.to_datetime(fwd["value_date"]) - vs).dt.days.reindex(d.index).fillna(a.days)
    else:
        days = pd.Series(a.days, index=d.index)
    if d.empty:
        raise SystemExit("no common dates for yields, spot and forward: check tenor/pair/snap")
    if a.home_freq or a.foreign_freq:
        d["yh"] = d["yh"].map(lambda v: to_annual(v, a.home_freq or 1))
        d["yf"] = d["yf"].map(lambda v: to_annual(v, a.foreign_freq or 1))
    rows = []
    for dt, r in d.iterrows():
        s = home_per_foreign(a.pair, r.spot, home, foreign)
        fw = home_per_foreign(a.pair, r.fwd, home, foreign)
        rows.append(hedged_pickup_bp(r.yf, r.yh, s, fw, days[dt], a.basis))
    out = pd.Series(rows, index=d.index, name="hedged_pickup_bp").to_frame()
    out["z_6m"] = zscore(out["hedged_pickup_bp"], a.z_window)
    _emit(out, a.out)


def cmd_beta(a) -> None:
    cp = _read(a.curve_par)
    y = _periodic_changes(_series(cp, a.local, a.tenor, a.snap), a.freq)
    x = _periodic_changes(_series(cp, a.anchor, a.tenor, a.snap), a.freq)
    out = rolling_beta(y, x, a.window)
    _emit(out, a.out)


def cmd_dislocation(a) -> None:
    cp = _read(a.curve_par)
    base = {t: _series(cp, a.base_curve, t, a.snap) for t in a.tenors.split(",")}
    cols = {}
    for c in a.curves.split(","):
        for t in a.tenors.split(","):
            cols[f"{c}|{t}"] = (_series(cp, c, t, a.snap) - base[t]) * 100.0
    X = pd.DataFrame(cols).dropna()
    try:
        out = dislocation_index(X, a.npc, a.min_obs)
    except ValueError as e:
        raise SystemExit(f"dislocation: {e}")
    last = out.iloc[-1]
    print(f"{out.index[-1].date()}: dispersion {last['dispersion']:.2f}bp  dislocation_z {last['dislocation_z']:.2f}")
    print("residual bp (positive = cheap vs Germany):")
    print(last.drop(["dispersion", "dislocation_z"]).sort_values(ascending=False).round(2).to_string())
    if a.out:
        out.to_csv(a.out, lineterminator="\n")


# ----------------------------------------------------------------------------------------------- self-test
def selftest() -> None:
    ok = True

    def check(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {name}: got {got:.4f}, want {want:.4f} (+/-{tol})")

    # 1. hedged pickup: fwd 0.5% below spot over 90d on a 360 basis = -2.0% p.a.; 4.5 - 2.0 - 3.0 = -50bp
    check("hedged pickup", hedged_pickup_bp(4.5, 3.0, 1.00, 0.995, 90, 360), -50.0, 1e-9)
    # 2. CIP consistency: forward built from simple money-market rates => hedge carry = (rh-rf)/(1+rf*d/365)
    rh, rf, d = 0.040, 0.005, 91
    F = (1 + rh * d / 365) / (1 + rf * d / 365)
    check("CIP hedge carry", hedge_carry_pct(1.0, F, d, 365) / 100, (rh - rf) / (1 + rf * d / 365), 1e-12)
    # 2b. rate-differential form equals the forward-point form when F is built with the same differential + basis
    yf_, rf_, yh_, rh_, b_ = 2.6, 2.0, 4.2, 4.0, -7.0
    Fm = 1 + (rh_ - rf_ + b_ / 100.0) / 100.0 * 91 / 365
    check("rates form = forward form", hedged_pickup_rates_bp(yf_, rf_, yh_, rh_, b_),
          hedged_pickup_bp(yf_, yh_, 1.0, Fm, 91, 365), 1e-9)
    check("rates form value", hedged_pickup_rates_bp(2.6, 2.0, 4.2, 4.0, 0.0), 40.0, 1e-9)
    # 2c. hand-computed, non-zero basis: (3.0-2.0) - (4.5-4.0) = 0.5% = 50bp; basis -20bp on the home leg -> 30bp
    check("rates form with basis", hedged_pickup_rates_bp(3.0, 2.0, 4.5, 4.0, -20.0), 30.0, 1e-9)
    #     exact-parity forward (home leg earns r_h + b) gives 29.11bp: within 1bp of the simple rates form, same sign
    Fx = (1 + 0.038 * 91 / 365) / (1 + 0.02 * 91 / 365)
    check("forward form with basis", hedged_pickup_bp(3.0, 4.5, 1.0, Fx, 91, 365), 29.107, 0.005)
    # 2d. compounding: 4.5% semi-annual = 4.550625% annual; 4.5% annual unchanged
    check("to_annual", to_annual(4.5, 2), 4.550625, 1e-9)
    # 3. pair orientation: USDJPY outright 150 -> home(USD)-per-foreign(JPY) = 1/150
    check("home_per_foreign", home_per_foreign("USDJPY", 150.0, "USD", "JPY"), 1 / 150, 1e-12)
    check("home_per_foreign direct", home_per_foreign("EURUSD", 1.17, "USD", "EUR"), 1.17, 1e-12)
    # 4. USD ASW of a JGB: (11 - (-64.5)) / 0.95 = 79.47bp (Huggins & Schaller worked case, source rounds to 79)
    check("USD ASW JGB", usd_asw_foreign_bp(11.0, -64.5, 0.95, 1.0), 75.5 / 0.95, 1e-9)
    # 5. DV01 hedge: long 100 of A (DV01 0.08/unit) vs B (DV01 0.04/unit) -> short 200 of B
    check("dv01 hedge", dv01_hedge_notional(100.0, 0.08, 0.04), -200.0, 1e-12)
    # 5b. cross-currency: A = EUR 100 (DV01 0.08 EUR/unit), B in USD (DV01 0.04 USD/unit), 1.25 USD per EUR -> -250
    check("dv01 hedge fx", dv01_hedge_notional(100.0, 0.08, 0.04, 1.25), -250.0, 1e-12)
    # 6. pair carry: 150bp - 2 x 100bp = -50bp
    check("pair carry", pair_carry_bp(4.5, 3.0, 8.0, 2.0, 1.0, 4.0), -50.0, 1e-9)

    rng = np.random.default_rng(7)
    # 7. rolling beta recovers simulated beta 0.8, sigma_e 0.5: R2 = .64/(.64+.25) = 0.719
    n = 3000
    x = pd.Series(rng.normal(size=n))
    y = 0.8 * x + rng.normal(scale=0.5, size=n)
    rb = rolling_beta(y, x, 1000).dropna()
    check("rolling beta", rb["beta"].mean(), 0.8, 0.03)
    check("rolling r2", rb["r2"].mean(), 0.64 / 0.89, 0.03)
    # 7b. residual sign and scale: positive shock on the last y point must give a positive residual; z has sd ~1
    y2 = y.copy()
    y2.iloc[-1] += 3.0
    rb2 = rolling_beta(y2, x, 250)
    good = rb2["resid"].iloc[-1] > 2.0 and rb2["resid_z"].iloc[-1] > 4.0
    ok &= bool(good)
    print(f"{'ok  ' if good else 'FAIL'} resid sign/size after +3 shock: {rb2['resid'].iloc[-1]:.2f}, z {rb2['resid_z'].iloc[-1]:.2f}")
    check("resid_z sd", rb["resid_z"].std(), 1.0, 0.08)

    # 8. PCA residual: 2-factor panel + noise; +4 shock on column 5 of the last row must be the cheapest, ~4 in size
    T, N = 400, 12
    load = rng.normal(size=(2, N))
    X = rng.normal(size=(T, 2)) @ load + rng.normal(scale=0.2, size=(T, N))
    X[-1, 5] += 4.0
    r = pca_residual_last(X, 2)
    ok &= int(np.argmax(r)) == 5
    print(f"{'ok  ' if int(np.argmax(r)) == 5 else 'FAIL'} PCA cheapest column: {int(np.argmax(r))} (want 5)")
    check("PCA residual size", r[5], 4.0, 0.7)
    # dislocation index spikes on the shock day
    Xdf = pd.DataFrame(X, index=pd.RangeIndex(T))
    di = dislocation_index(Xdf, 2, min_obs=300)
    good = di["dislocation_z"].iloc[-1] > 3 and abs(di["dislocation_z"].iloc[:-1]).max() < 4
    ok &= bool(good)
    print(f"{'ok  ' if good else 'FAIL'} dislocation z on shock day {di['dislocation_z'].iloc[-1]:.2f} (want > 3)")

    # 9. guards: short history, NaN and n_pc >= N must raise rather than return garbage
    Xnan = Xdf.copy()
    Xnan.iloc[3, 0] = np.nan
    for name, args in (("short history", (Xdf, 2, 1000)), ("n_pc >= N", (Xdf, N, 100)),
                       ("NaN", (Xnan, 2, 100))):
        try:
            dislocation_index(*args)
            raised = False
        except ValueError:
            raised = True
        ok &= raised
        print(f"{'ok  ' if raised else 'FAIL'} guard {name}")
    # 10. weekly changes drop the still-open final week: data to Fri 2026-11-13, W-WED -> last label Wed 11-11 only
    idx = pd.bdate_range("2026-10-26", "2026-11-13")
    wk = _periodic_changes(pd.Series(np.arange(len(idx), dtype=float), index=idx), "W-WED")
    good = wk.index[-1] == pd.Timestamp("2026-11-11") and abs(wk.iloc[-1] - 500.0) < 1e-9
    ok &= bool(good)
    print(f"{'ok  ' if good else 'FAIL'} open week dropped: last {wk.index[-1].date()}, change {wk.iloc[-1]:.0f}bp (want 2026-11-11, 500)")

    if not ok:
        sys.exit(1)
    print("selftest passed")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("pickup", help="FX-hedged yield pickup series from curve_par + fx_rates")
    p.add_argument("--curve-par", required=True)
    p.add_argument("--fx-rates", required=True)
    p.add_argument("--home-curve", required=True, help="e.g. USD-GOVT-US (first 3 chars = home currency)")
    p.add_argument("--foreign-curve", required=True, help="e.g. EUR-GOVT-DE")
    p.add_argument("--tenor", default="10Y")
    p.add_argument("--pair", required=True, help="fx_rates pair linking the two currencies, e.g. EURUSD")
    p.add_argument("--hedge-tenor", default="3M")
    p.add_argument("--days", type=float, default=91, help="used when value_date is missing")
    p.add_argument("--basis", type=float, default=365.0)
    p.add_argument("--z-window", type=int, default=126, help="~6 months of business days")
    p.add_argument("--snap")
    p.add_argument("--out")
    p.add_argument("--home-freq", type=int, help="compounding periods/yr of the home yield quote (2 semi, 1 annual); "
                   "set either freq to convert both yields to annual before differencing")
    p.add_argument("--foreign-freq", type=int, help="same for the foreign yield quote")
    b = sub.add_parser("beta", help="rolling beta/R2/z of local yield changes on an anchor market's")
    b.add_argument("--curve-par", required=True)
    b.add_argument("--local", required=True)
    b.add_argument("--anchor", required=True)
    b.add_argument("--tenor", default="10Y")
    b.add_argument("--freq", default="W-WED", help="pandas offset; weekly Wednesday avoids payroll Fridays and T/T+1")
    b.add_argument("--window", type=int, default=52)
    b.add_argument("--snap")
    b.add_argument("--out")
    g = sub.add_parser("dislocation", help="expanding PCA-residual screen on country-minus-base spreads (bp)")
    g.add_argument("--curve-par", required=True)
    g.add_argument("--base-curve", required=True, help="e.g. EUR-GOVT-DE")
    g.add_argument("--curves", required=True, help="comma list of issuer curves, e.g. EUR-GOVT-FR,EUR-GOVT-IT")
    g.add_argument("--tenors", default="2Y,5Y,10Y,30Y")
    g.add_argument("--snap")
    g.add_argument("--out")
    g.add_argument("--npc", type=int, default=3)
    g.add_argument("--min-obs", type=int, default=250)
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return
    {"pickup": cmd_pickup, "beta": cmd_beta, "dislocation": cmd_dislocation}.get(a.cmd, lambda _: ap.print_help())(a)


if __name__ == "__main__":
    main()
