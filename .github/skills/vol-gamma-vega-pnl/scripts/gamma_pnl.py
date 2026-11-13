"""Gamma / vega / theta P&L of delta-hedged rates options (normal / Bachelier model).

Conventions
  rates, strikes, moves  bp;  vol  normal vol, bp per year;  T  years (business-day clock: trading days / 252)
  option value           bp of annuity (cash = value_bp * pv01, pv01 = annuity * notional * 1e-4 = ccy per bp)
  payer = call on the rate (long payer: +delta, +gamma, +vega, -theta; DV01 of a payer is NEGATIVE, -delta * pv01)
  gamma  1/bp (delta change per bp);  vega  bp of value per +1bp of vol;  theta  bp of value per YEAR (negative long)
  Exact normal-model identities used by the selftest:  theta = -0.5 sig^2 gamma ;  vega = sig * T * gamma
  ATM, hedged at implied sig_i, realised sig_r, continuous hedge, zero drift:
      E[P&L] = value(sig_r) - value(sig_i) = (sig_r - sig_i) * sqrt(T / (2 pi))   (= vega * (sig_r - sig_i))

CLI
  python gamma_pnl.py greeks --fwd-pct 3.727 --strike-pct 3.727 --nvol 110 --T 1 --pv01 77800 [--kind payer]
  python gamma_pnl.py explain --csv opt.csv --strike-pct 3.7 --expiry-date 2027-03-31 --pv01 77800 [--kind payer]
        csv: date, atm_fwd_pct, nvol_bp  for ONE option (fixed expiry/underlying; interpolate vol_surface first)
  python gamma_pnl.py realized --csv opt.csv [--window 21] [--col atm_fwd_pct]       (delivered vol, implied/realised)
  python gamma_pnl.py walk --vols 87.5 101.8 ... --weights 0.0417 0.0833 ...         (walk vol)
  python gamma_pnl.py sim --nvol 100 --T 0.25 --real 100 --cost-bp 0.3 --thresholds 0 0.1 0.25 0.5
  python gamma_pnl.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

DAYS = 252


# ---------- Greeks ----------
def bachelier(F, K, sig, T, kind="payer"):
    """Normal-model value, delta, gamma, vega, theta (units in module docstring). Arrays or scalars."""
    F, K, sig, T = (np.asarray(x, dtype=float) for x in (F, K, sig, T))
    w = 1.0 if kind == "payer" else -1.0
    sd = np.maximum(sig * np.sqrt(np.maximum(T, 1e-12)), 1e-12)  # guard sig=0 / T=0 (value -> intrinsic)
    d = (F - K) / sd
    pdf = norm.pdf(d)
    value = w * (F - K) * norm.cdf(w * d) + sd * pdf
    delta = w * norm.cdf(w * d)
    gamma = pdf / sd
    vega = np.sqrt(np.maximum(T, 1e-12)) * pdf
    theta = -0.5 * sig**2 * gamma  # per year; exact in the normal model
    return {"value": value, "delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def daily_breakeven(sig, days=DAYS):
    """(daily bp vol, unhedged-straddle daily breakeven move sqrt(2/pi)*daily vol)."""
    s = sig / math.sqrt(days)
    return s, math.sqrt(2.0 / math.pi) * s


def delivered_vol(fwd_bp, window=21, days=DAYS):
    """Delivered normal vol (bp/yr): zero-mean RMS of daily changes of the forward (bp) over `window` days x sqrt(days).
    NaN in the window, or fewer than `window` changes, gives NaN (no silent shortening)."""
    ch = pd.Series(np.asarray(fwd_bp, dtype=float)).diff()
    return np.sqrt((ch**2).rolling(window).mean() * days)


def walk_vol(vols, weights):
    """Walk vol = sqrt(sum w_i sig_i^2); weights are the time-weights of each intermediate expiry (sum to 1)."""
    v, w = np.asarray(vols, float), np.asarray(weights, float)
    return float(np.sqrt(np.sum(w * v**2) / np.sum(w)))


def convexity_value(gamma_cash, sig_bp, T, gamma_end=None):
    """Expected P&L of a linear convex position: 0.5 * Gamma * (sig sqrt(T))^2.
    gamma_cash = DV01 change per bp (ccy/bp^2). With gamma_end, gamma decays linearly to it over T
    (time-integrated). Constant gamma overstates the value of a decaying position."""
    g_avg = gamma_cash if gamma_end is None else 0.5 * (gamma_cash + gamma_end)
    return 0.5 * g_avg * sig_bp**2 * T


# ---------- daily P&L explain ----------
def explain_day(F0, F1, s0, s1, T0, T1, K, kind="payer"):
    """Split one day's delta-hedged P&L (long option, hedged at close-0 delta) into gamma, vega, theta, residual.
    Returns bp of annuity. gamma/vega/theta use day-0 greeks; residual = vanna + volga + higher order."""
    g = bachelier(F0, K, s0, T0, kind)
    v0 = float(g["value"])
    v1 = float(bachelier(F1, K, s1, T1, kind)["value"])
    dF, ds, dt = F1 - F0, s1 - s0, T0 - T1
    total = v1 - v0 - float(g["delta"]) * dF
    gam, veg, th = 0.5 * float(g["gamma"]) * dF**2, float(g["vega"]) * ds, float(g["theta"]) * dt
    return {"total": total, "gamma": gam, "vega": veg, "theta": th, "residual": total - gam - veg - th}


def explain_series(df, K_bp, expiry, kind="payer", days=DAYS):
    """df: date, F_bp, vol_bp. Rows on or after expiry and rows with NaN are dropped (a gap is spanned by one
    multi-day step, so P&L is explained over the gap). Remaining time = business days / 252."""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.dropna(subset=["F_bp", "vol_bp"])
    d = d[d["date"] < pd.Timestamp(expiry)].sort_values("date").reset_index(drop=True)
    d["T"] = [np.busday_count(x.date(), pd.Timestamp(expiry).date()) / days for x in d["date"]]
    rows = []
    for i in range(1, len(d)):
        a, b = d.iloc[i - 1], d.iloc[i]
        r = explain_day(a.F_bp, b.F_bp, a.vol_bp, b.vol_bp, a["T"], b["T"], K_bp, kind)
        r.update(date=b["date"].date(), dF_bp=b.F_bp - a.F_bp, dvol_bp=b.vol_bp - a.vol_bp)
        rows.append(r)
    return pd.DataFrame(rows)


# ---------- hedging simulation ----------
def hedge_sim(F0, K, sig_i, sig_r, T, n_steps=252, n_paths=5000, hedge_sig=None, threshold=0.0,
              cost_bp=0.0, kind="payer", seed=0):
    """Long option bought at sig_i value, delta-hedged with the underlying along a driftless normal path of vol sig_r.
    hedge_sig: vol used for the hedge delta (default sig_i). threshold: re-hedge only if |delta - hedge| > threshold
    (delta units, 0 = every step). cost_bp: half bid/offer per unit of delta traded (bp of rate).
    Returns (pnl_bp array, mean number of hedge trades). ponytail: no jumps, no skew; add a jump term if tails matter."""
    hs = sig_i if hedge_sig is None else hedge_sig
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    z = rng.standard_normal((n_paths, n_steps))
    F = F0 + np.cumsum(sig_r * math.sqrt(dt) * z, axis=1)
    F = np.concatenate([np.full((n_paths, 1), float(F0)), F], axis=1)
    v0 = float(bachelier(F0, K, sig_i, T, kind)["value"])
    h = np.zeros(n_paths)
    pnl = np.zeros(n_paths)
    n_hedge = np.zeros(n_paths)
    for t in range(n_steps):
        tau = T - t * dt
        delta = bachelier(F[:, t], K, hs, tau, kind)["delta"]
        move = np.abs(delta - h) > threshold if threshold > 0 else np.ones(n_paths, bool)
        trade = np.where(move, delta - h, 0.0)
        pnl -= cost_bp * np.abs(trade)
        n_hedge += move
        h = h + trade
        pnl -= h * (F[:, t + 1] - F[:, t])  # long option hedged with -h units of the underlying
    w = 1.0 if kind == "payer" else -1.0
    pnl += np.maximum(w * (F[:, -1] - K), 0.0) - v0
    return pnl, float(n_hedge.mean())


# ---------- CLI helpers ----------
def _read(path):
    return pd.read_parquet(path) if path.lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def cmd_greeks(a):
    F, K = a.fwd_pct * 100.0, a.strike_pct * 100.0
    g = {k: float(v) for k, v in bachelier(F, K, a.nvol, a.T, a.kind).items()}
    dv, be = daily_breakeven(a.nvol)
    sign = -1.0 if a.kind == "payer" else 1.0  # DV01 sign: payer short duration
    print(f"{a.kind} F={F:.1f}bp K={K:.1f}bp vol={a.nvol}bp T={a.T}y  daily vol {dv:.2f}bp  straddle daily BE move {be:.2f}bp")
    print(f"value {g['value']:.2f}bp  delta {g['delta']:.4f}  gamma {g['gamma']:.6f}/bp  vega {g['vega']:.3f}bp/volbp  theta {g['theta']:.2f}bp/yr")
    if a.pv01:
        p = a.pv01
        print(f"cash: premium {g['value']*p:,.0f}  DV01 {sign*abs(g['delta'])*p:,.0f}/bp  gamma {g['gamma']*p:,.1f} per bp (delta change; a long option's DV01 falls by this)  "
              f"vega {g['vega']*p:,.0f}/volbp  theta {g['theta']*p/DAYS:,.0f}/trading day ({g['theta']*p/365:,.0f}/calendar day)")


def cmd_explain(a):
    df = _read(a.csv).rename(columns={"atm_fwd_pct": "F_bp", "nvol_bp": "vol_bp"})
    df["F_bp"] = df["F_bp"] * 100.0
    out = explain_series(df, a.strike_pct * 100.0, a.expiry_date, a.kind)
    if out.empty:
        sys.exit("explain: fewer than 2 valid rows before expiry")
    p = a.pv01 or 1.0
    for c in ("total", "gamma", "vega", "theta", "residual"):
        out[c] *= p
    pd.set_option("display.width", 160)
    print(out.round(1).to_string(index=False))
    print("cum", out[["total", "gamma", "vega", "theta", "residual"]].sum().round(0).to_dict(), "(ccy)" if a.pv01 else "(bp of annuity)")


def cmd_realized(a):
    df = _read(a.csv)
    df = df.sort_values("date").reset_index(drop=True)
    rv = delivered_vol(df[a.col].astype(float) * 100.0, a.window)  # pct -> bp
    out = pd.DataFrame({"date": df["date"], "delivered_nvol_bp": rv})
    if "nvol_bp" in df:
        out["implied_nvol_bp"] = df["nvol_bp"]
        out["implied_over_delivered"] = df["nvol_bp"] / rv
    print(out.dropna().tail(a.tail).round(2).to_string(index=False))


def cmd_sim(a):
    F = 300.0
    print(f"long ATM {a.kind}, implied {a.nvol}bp, realised {a.real}bp, T={a.T}y, {a.steps} steps, half-cost {a.cost_bp}bp/delta")
    print("threshold  hedges  mean_bp  std_bp  mean/std")
    for th in a.thresholds:
        p, n = hedge_sim(F, F, a.nvol, a.real, a.T, a.steps, a.paths, threshold=th, cost_bp=a.cost_bp, kind=a.kind, seed=1)
        print(f"{th:9.2f} {n:7.1f} {p.mean():8.3f} {p.std():7.3f} {p.mean()/p.std():9.3f}")


# ---------- selftest ----------
def selftest() -> int:
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.5f} want {want:.5f} (tol {tol})")
        if not ok:
            fails.append(name)

    # 1. exact normal-model identities, and finite-difference greeks
    F, K, s, T = 300.0, 310.0, 90.0, 0.5
    for kind in ("payer", "receiver"):
        g = {k: float(v) for k, v in bachelier(F, K, s, T, kind).items()}
        check(f"{kind} theta = -0.5 sig^2 gamma", g["theta"], -0.5 * s**2 * g["gamma"], 1e-9)
        check(f"{kind} vega = sig T gamma", g["vega"], s * T * g["gamma"], 1e-9)
        h = 1e-3
        up, dn = bachelier(F + h, K, s, T, kind), bachelier(F - h, K, s, T, kind)
        check(f"{kind} fd delta", float(up["value"] - dn["value"]) / (2 * h), g["delta"], 1e-6)
        check(f"{kind} fd gamma", float(up["delta"] - dn["delta"]) / (2 * h), g["gamma"], 1e-6)
        check(f"{kind} fd vega", float(bachelier(F, K, s + h, T, kind)["value"] - bachelier(F, K, s - h, T, kind)["value"]) / (2 * h), g["vega"], 1e-6)
        check(f"{kind} fd theta", float(bachelier(F, K, s, T - 1e-5, kind)["value"] - bachelier(F, K, s, T + 1e-5, kind)["value"]) / 2e-5, g["theta"], 1e-4)
    par = float(bachelier(F, K, s, T, "payer")["value"] - bachelier(F, K, s, T, "receiver")["value"])
    check("put-call parity", par, F - K, 1e-9)
    check("ATM value = sig sqrt(T/2pi)", float(bachelier(F, F, s, T)["value"]), s * math.sqrt(T / (2 * math.pi)), 1e-9)

    # 2. published cross-checks (BofA Vol Primer, 23 Feb 2024): 100m 3m10y ATM payer, 106bp vol, pv01 ~78k
    g = {k: float(v) for k, v in bachelier(300, 300, 106, 0.25).items()}
    check("3m10y theta/calendar day ~ 9,104", -g["theta"] * 78000 / 365, 9104, 250)
    check("daily vol 110bp = 6.93", daily_breakeven(110)[0], 6.93, 0.01)

    # 3. walk vol worked example (BofA): 1y1y, 3m delivered -> 132.3bp
    wv = walk_vol([87.5, 101.8, 113.8, 122.8, 141.5, 143.8, 142.8], [0.0417, 0.0833, 0.0833, 0.1667, 0.25, 0.25, 0.125])
    check("walk vol 1y1y", wv, 132.3, 0.3)

    # 4. convexity of a linear position: 0.5 * (139.38*sqrt2)^2 * 12.2 ~ 237k (QF-SE example quotes ~240k)
    check("constant-gamma convexity value", convexity_value(12.2, 139.38, 2.0), 237007.0, 50.0)
    check("decaying gamma is smaller", float(convexity_value(12.2, 139.38, 2.0, gamma_end=1.8) < 0.7 * convexity_value(12.2, 139.38, 2.0)), 1.0, 0.0)

    # 5. one-day explain: gamma + theta dominate; residual small when vol is unchanged
    r = explain_day(300, 304, 100, 100, 0.25, 0.25 - 1 / 252, 300)
    check("explain residual small (dvol=0)", abs(r["residual"]) / abs(r["total"]), 0.0, 0.02)
    r = explain_day(300, 302, 100, 100.5, 0.25, 0.25 - 1 / 252, 300)
    check("explain residual small (with dvol)", abs(r["residual"]) / abs(r["total"]), 0.0, 0.05)

    # 6. Monte Carlo: hedge at implied, ATM. mean P&L = (sig_r - sig_i) sqrt(T/2pi); replication error falls with sqrt(steps)
    sig_i, T0 = 100.0, 0.5
    for sr in (100.0, 150.0):
        p, _ = hedge_sim(300, 300, sig_i, sr, T0, 126, 20000, seed=3)
        want = (sr - sig_i) * math.sqrt(T0 / (2 * math.pi))
        check(f"MC mean pnl sig_r={sr:.0f}", float(p.mean()), want, 4 * float(p.std()) / math.sqrt(len(p)))
    sd_few = hedge_sim(300, 300, 100, 100, 0.5, 12, 8000, seed=4)[0].std()
    sd_many = hedge_sim(300, 300, 100, 100, 0.5, 192, 8000, seed=4)[0].std()
    check("replication error ratio ~ sqrt(16)=4", float(sd_few / sd_many), 4.0, 1.0)
    # 7. threshold hedging trades less often, costs scale with trades
    _, n_all = hedge_sim(300, 300, 100, 100, 0.25, 63, 2000, threshold=0.0, seed=5)
    _, n_th = hedge_sim(300, 300, 100, 100, 0.25, 63, 2000, threshold=0.25, seed=5)
    check("threshold cuts hedge count", float(n_th < 0.5 * n_all), 1.0, 0.0)
    c0 = hedge_sim(300, 300, 100, 100, 0.25, 63, 4000, cost_bp=0.0, seed=6)[0].mean()
    c1 = hedge_sim(300, 300, 100, 100, 0.25, 63, 4000, cost_bp=0.5, seed=6)[0].mean()
    check("costs reduce pnl", float(c1 < c0 - 1.0), 1.0, 0.0)
    # 8. exact convexity value with linear decay: 0.5 * avg(12.2, 1.8) * 139.38^2 * 2y
    check("convexity linear decay", convexity_value(12.2, 139.38, 2.0, gamma_end=1.8), 135987.5, 1.0)
    # 9. straddle daily breakeven = sqrt(2/pi) x daily vol (primer: 110bp -> 6.93bp/day)
    dv, be = daily_breakeven(110)
    check("straddle daily BE = 0.7979 x 6.93", be, math.sqrt(2 / math.pi) * 6.929, 0.01)
    # 10. delivered vol: alternating +/-5bp daily moves -> 5 sqrt(252); NaN in window -> NaN; short history -> NaN
    f = np.cumsum(np.r_[0.0, np.tile([5.0, -5.0], 30)])
    dvol = delivered_vol(f, 21)
    check("delivered vol +/-5bp", float(dvol.iloc[-1]), 5 * math.sqrt(252), 1e-9)
    f2 = f.copy(); f2[-3] = np.nan
    check("NaN in window gives NaN", float(np.isnan(delivered_vol(f2, 21).iloc[-1])), 1.0, 0.0)
    check("short history gives NaN", float(delivered_vol(f[:10], 21).isna().all()), 1.0, 0.0)
    # 11. explain_series: flat forward at the strike and flat vol -> total P&L = value(last day) - value(start); vega = 0, gamma = 0
    days = pd.bdate_range("2026-01-05", "2026-04-02")
    flat = pd.DataFrame({"date": days, "F_bp": 300.0, "vol_bp": 100.0})
    ex = explain_series(flat, 300.0, "2026-04-03")
    T0 = np.busday_count(days[0].date(), pd.Timestamp("2026-04-03").date()) / DAYS
    want = float(bachelier(300, 300, 100, 1 / DAYS)["value"] - bachelier(300, 300, 100, T0)["value"])
    check("explain_series flat total", float(ex["total"].sum()), want, 1e-9)
    check("explain_series flat gamma+vega = 0", float(abs(ex["gamma"].sum() + ex["vega"].sum())), 0.0, 1e-12)
    check("explain_series theta ~ total (<5% off)", float(ex["theta"].sum() / ex["total"].sum()), 1.0, 0.05)
    gap = flat.drop(flat.index[20:30]).copy()
    gap.loc[gap.index[25], "F_bp"] = np.nan  # a NaN row is dropped and the gap spanned, not mis-timed
    eg = explain_series(gap, 300.0, "2026-04-03")
    check("explain_series gap: theta ~ total (<5% off)", float(eg["theta"].sum() / eg["total"].sum()), 1.0, 0.05)
    # 12. receiver DV01 sign and put-call delta: payer delta - receiver delta = 1
    gp, gr = bachelier(300, 300, 100, 0.25, "payer"), bachelier(300, 300, 100, 0.25, "receiver")
    check("payer delta - receiver delta = 1", float(gp["delta"] - gr["delta"]), 1.0, 1e-12)
    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "PASSED")
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sp = ap.add_subparsers(dest="cmd")
    g = sp.add_parser("greeks")
    g.add_argument("--fwd-pct", type=float, required=True)
    g.add_argument("--strike-pct", type=float, required=True)
    g.add_argument("--nvol", type=float, required=True)
    g.add_argument("--T", type=float, required=True)
    g.add_argument("--pv01", type=float, default=0.0)
    g.add_argument("--kind", default="payer", choices=["payer", "receiver"])
    e = sp.add_parser("explain")
    e.add_argument("--csv", required=True)
    e.add_argument("--strike-pct", type=float, required=True)
    e.add_argument("--expiry-date", required=True)
    e.add_argument("--pv01", type=float, default=0.0)
    e.add_argument("--kind", default="payer", choices=["payer", "receiver"])
    r = sp.add_parser("realized")
    r.add_argument("--csv", required=True)
    r.add_argument("--col", default="atm_fwd_pct")
    r.add_argument("--window", type=int, default=21)
    r.add_argument("--tail", type=int, default=10)
    w = sp.add_parser("walk")
    w.add_argument("--vols", type=float, nargs="+", required=True)
    w.add_argument("--weights", type=float, nargs="+", required=True)
    s = sp.add_parser("sim")
    s.add_argument("--nvol", type=float, required=True)
    s.add_argument("--real", type=float, required=True)
    s.add_argument("--T", type=float, default=0.25)
    s.add_argument("--cost-bp", type=float, default=0.0)
    s.add_argument("--steps", type=int, default=63)
    s.add_argument("--paths", type=int, default=5000)
    s.add_argument("--thresholds", type=float, nargs="+", default=[0.0, 0.1, 0.25])
    s.add_argument("--kind", default="payer", choices=["payer", "receiver"])
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "walk":
        print(f"walk vol {walk_vol(a.vols, a.weights):.2f}bp")
        return 0
    if a.cmd is None:
        ap.print_help()
        return 2
    {"greeks": cmd_greeks, "explain": cmd_explain, "realized": cmd_realized, "sim": cmd_sim}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
