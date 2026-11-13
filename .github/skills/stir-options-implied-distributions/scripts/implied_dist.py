"""Risk-neutral distribution of a STIR futures rate from listed options on that future.

Two estimators, both in RATE space (rate = 100 - futures price, in percent):
  bl      Breeden-Litzenberger: OTM premiums -> Bachelier normal vols -> smoothing spline in strike
          -> re-price calls on a fine grid -> q(k) = (1/DF) d2C/dk2.  Wings beyond the quoted strikes
          use flat vol (normal tails), and the mass that lands there is reported.
  mixture Mixture of normals on a policy lattice: means base + n*step, common width s (bp at expiry),
          weights >= 0 summing to 1 and repricing the futures rate, fitted by NNLS to OTM premiums.
          Weights read directly as meeting-outcome probabilities.

Conventions: a CALL on the futures PRICE is a PUT on the rate (and vice versa). Premiums are in price
points, which equal percent of rate. DF = 1 for futures-style margined options (ICE/Eurex STIR); for
premium-paid-up-front options (CME SR3) pass the OIS discount factor from today to option expiry.

CLI reads canonical `opt_quotes` and `opt_static` (CSV or Parquet):
  python implied_dist.py --opt-quotes opt_quotes.parquet --opt-static opt_static.parquet \
      --date 2026-11-10 --underlying FUT:SR3:2026-12 --base-rate-pct 3.88 --df 0.99
  python implied_dist.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline
from scipy.optimize import brentq, nnls
from scipy.stats import norm


# ---------------------------------------------------------------- pricing
def bachelier(fwd, strike, t, vol_bp, kind="call", df=1.0):
    """Normal-model premium in percent. fwd/strike in percent, vol in bp per year. call pays (r - k)+."""
    s = np.maximum(np.asarray(vol_bp, float) / 100.0 * np.sqrt(t), 1e-12)
    d = (np.asarray(fwd, float) - np.asarray(strike, float)) / s
    call = df * ((fwd - strike) * norm.cdf(d) + s * norm.pdf(d))
    return call if kind == "call" else call - df * (fwd - strike)


def implied_nvol(price, fwd, strike, t, kind="call", df=1.0):
    """Normal vol in bp; NaN if the premium is at/below intrinsic or not invertible."""
    intrinsic = df * max((fwd - strike) if kind == "call" else (strike - fwd), 0.0)
    if not np.isfinite(price) or price <= intrinsic + 1e-10:
        return np.nan
    f = lambda v: bachelier(fwd, strike, t, v, kind, df) - price
    try:
        return brentq(f, 1e-3, 5000.0, xtol=1e-8)
    except ValueError:
        return np.nan


def to_rate_space(quotes: pd.DataFrame, fut_px: float, min_prem=0.0) -> pd.DataFrame:
    """quotes: strike_px, option_right (C/P on price), premium_px. Returns OTM rate-space quotes with
    premium >= min_prem (percent; drops cabinet / minimum-tick wings that carry no information)."""
    q = quotes.copy()
    q["k"] = 100.0 - q["strike_px"].astype(float)
    q["kind"] = np.where(q["option_right"].str.upper() == "C", "put", "call")
    fwd = 100.0 - fut_px
    otm = ((q["kind"] == "call") & (q["k"] >= fwd)) | ((q["kind"] == "put") & (q["k"] < fwd))
    q = q[otm & (q["premium_px"] >= min_prem)].sort_values("k").drop_duplicates("k")
    return q[["k", "kind", "premium_px"]].reset_index(drop=True)


# ---------------------------------------------------------------- Breeden-Litzenberger
def bl_density(k, prem, kinds, fwd, t, df=1.0, smooth_bp=0.5, h=0.0025):
    """Returns (grid, density, diag). k, fwd in percent; smooth_bp = RMS vol-fit tolerance in bp."""
    k = np.asarray(k, float)
    vols = np.array([implied_nvol(p, fwd, kk, t, kd, df) for p, kk, kd in zip(prem, k, kinds)])
    ok = np.isfinite(vols)
    k, vols = k[ok], vols[ok]
    if len(k) < 5:
        raise ValueError(f"need >= 5 invertible OTM quotes, got {len(k)}")
    spl = UnivariateSpline(k, vols, k=3, s=len(k) * smooth_bp ** 2)
    smile = lambda x: spl(np.clip(x, k.min(), k.max()))  # ponytail: flat-vol wings; SABR wings if tails matter
    width = 8 * float(np.median(vols)) / 100 * np.sqrt(t)
    grid = np.arange(min(k.min(), fwd - width), max(k.max(), fwd + width) + h, h)
    c = bachelier(fwd, grid, t, smile(grid), "call", df)
    q = np.zeros_like(grid)
    q[1:-1] = (c[:-2] - 2 * c[1:-1] + c[2:]) / h ** 2 / df
    raw_mass = q.sum() * h
    neg_mass = -q[q < 0].sum() * h
    q = np.clip(q, 0, None)
    q /= q.sum() * h
    outside = q[(grid < k.min()) | (grid > k.max())].sum() * h
    diag = dict(n_quotes=int(len(k)), raw_mass=raw_mass, neg_mass=neg_mass, mass_outside_strikes=outside,
                fit_rmse_bp=float(np.sqrt(np.mean((spl(k) - vols) ** 2))), atm_nvol_bp=float(smile(fwd)))
    return grid, q, diag


def moments(grid, q, fwd=None):
    h = grid[1] - grid[0]
    p = q * h
    m = (grid * p).sum()
    sd = np.sqrt(((grid - m) ** 2 * p).sum())
    cdf = np.cumsum(p)
    qt = lambda a: float(np.interp(a, cdf, grid))
    out = dict(mean_pct=m, sd_bp=sd * 100, skew=((grid - m) ** 3 * p).sum() / sd ** 3,
               ex_kurt=((grid - m) ** 4 * p).sum() / sd ** 4 - 3, mode_pct=float(grid[np.argmax(q)]),
               median_pct=qt(0.5), mean_minus_median_bp=(m - qt(0.5)) * 100,
               p05_pct=qt(0.05), p25_pct=qt(0.25), p75_pct=qt(0.75), p95_pct=qt(0.95))
    if fwd is not None:
        out["mean_minus_fwd_bp"] = (m - fwd) * 100
    return out


def prob_below(grid, q, level):
    h = grid[1] - grid[0]
    return float(q[grid < level].sum() * h)


def lattice_probs(grid, q, base, step_bp=25.0):
    """Bin density into cells base + n*step +/- step/2. Returns DataFrame n_moves, level_pct, prob."""
    step = step_bp / 100
    h = grid[1] - grid[0]
    n = np.round((grid - base) / step).astype(int)
    s = pd.Series(q * h).groupby(n).sum()
    return pd.DataFrame({"n_moves": s.index, "level_pct": base + s.index * step, "prob": s.values})


# ---------------------------------------------------------------- mixture of normals on a lattice
def mixture_fit(k, prem, kinds, fwd, t, df=1.0, base=None, step_bp=25.0, smear_bp=None, n_pad=2):
    """Weights on lattice nodes base + n*step. smear_bp: component sd at expiry (bp); None = grid search."""
    k = np.asarray(k, float)
    prem = np.asarray(prem, float)
    kinds = np.asarray(kinds)
    base = fwd if base is None else base
    step = step_bp / 100
    lo = int(np.floor((min(k.min(), fwd) - base) / step)) - n_pad
    hi = int(np.ceil((max(k.max(), fwd) - base) / step)) + n_pad
    nodes = np.arange(lo, hi + 1)
    mu = base + nodes * step

    def solve(s_bp):
        s = s_bp / 100
        d = (mu[None, :] - k[:, None]) / s
        call = df * ((mu[None, :] - k[:, None]) * norm.cdf(d) + s * norm.pdf(d))
        a = np.where((kinds == "call")[:, None], call, call - df * (mu[None, :] - k[:, None]))
        lam = 10 * np.abs(a).max()
        a_aug = np.vstack([a, lam * np.ones(len(mu)), lam * mu])
        b_aug = np.concatenate([prem, [lam, lam * fwd]])
        w, _ = nnls(a_aug, b_aug)
        rmse_bp = float(np.sqrt(np.mean((a @ w - prem) ** 2)) * 100)
        return w, rmse_bp

    grid_s = [smear_bp] if smear_bp else np.arange(2.0, 30.5, 0.5)
    best = min(((s,) + solve(s) for s in grid_s), key=lambda r: r[2])
    s_bp, w, rmse = best
    out = pd.DataFrame({"n_moves": nodes, "level_pct": mu, "prob": w / w.sum()})
    return out, dict(smear_bp=float(s_bp), fit_rmse_bp=rmse, implied_mean_pct=float((w / w.sum()) @ mu))


# ---------------------------------------------------------------- CLI
def _read(path):
    return pd.read_parquet(path) if str(path).lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def run_cli(a):
    oq, st = _read(a.opt_quotes), _read(a.opt_static)
    st = st[st["underlying_id"] == a.underlying]
    oq = oq[(oq["date"].astype(str) == a.date) & (oq["snap"] == a.snap)]
    if "data_ok" in oq:
        oq = oq[oq["data_ok"].fillna(True).astype(bool)]
    df_ = oq.merge(st[["opt_id", "strike_px", "option_right", "expiry_date"]], on="opt_id")
    if df_.empty:
        sys.exit(f"no option quotes for {a.underlying} on {a.date} ({a.snap})")
    expiry = a.expiry or str(df_["expiry_date"].astype(str).max())  # latest expiry = quarterly standard
    df_ = df_[df_["expiry_date"].astype(str) == expiry]
    if "oi_cnt" in df_ and df_["oi_cnt"].notna().any():
        df_ = df_[df_["oi_cnt"].fillna(0) >= a.min_oi]
    mid = (df_["bid_px"] + df_["ask_px"]) / 2 if {"bid_px", "ask_px"} <= set(df_) else np.nan
    df_ = df_.assign(premium_px=df_["premium_px"].fillna(mid) if "premium_px" in df_ else mid)
    fut_px = a.fut_px if a.fut_px else float(df_["underlying_px"].median())
    fwd = 100 - fut_px
    t = (pd.Timestamp(expiry) - pd.Timestamp(a.date)).days / 365.0
    rq = to_rate_space(df_, fut_px, a.min_prem_bp / 100)
    if len(rq) < 5:
        sys.exit(f"only {len(rq)} usable OTM quotes for {a.underlying} {expiry}; need >= 5")
    base = a.base_rate_pct if a.base_rate_pct is not None else fwd
    print(f"{a.underlying} expiry {expiry} T={t:.4f}y fwd={fwd:.4f}% df={a.df} OTM quotes={len(rq)} "
          f"base={base:.4f}%{'' if a.base_rate_pct is not None else ' (DEFAULT = forward; pass --base-rate-pct)'}")
    tables = []
    if a.method in ("bl", "both"):
        g, q, diag = bl_density(rq["k"], rq["premium_px"], rq["kind"], fwd, t, a.df, a.smooth_bp)
        print("BL diagnostics:", {k_: round(float(v), 4) for k_, v in diag.items()})
        print("BL moments:", {k_: round(float(v), 4) for k_, v in moments(g, q, fwd).items()})
        for lvl in a.thresholds:
            print(f"P(rate < {lvl}%) = {prob_below(g, q, lvl):.3f}")
        lp = lattice_probs(g, q, base, a.step_bp).set_index("n_moves")["prob"]
        alt = [lattice_probs(*bl_density(rq["k"], rq["premium_px"], rq["kind"], fwd, t, a.df, a.smooth_bp * f)[:2],
                             base, a.step_bp).set_index("n_moves")["prob"] for f in (0.5, 2.0)]
        sens = max(float(lp.sub(x, fill_value=0).abs().max()) for x in alt) * 100
        print(f"BL smoothing sensitivity (cells at 0.5x/2x smooth): {sens:.1f}pp")
        tables.append(lp.rename("prob_bl").reset_index().assign(level_pct=lambda d: base + d.n_moves * a.step_bp / 100))
    if a.method in ("mixture", "both"):
        mx, info = mixture_fit(rq["k"], rq["premium_px"], rq["kind"], fwd, t, a.df, base, a.step_bp)
        print("Mixture fit:", {k_: round(float(v), 4) for k_, v in info.items()})
        tables.append(mx.rename(columns={"prob": "prob_mixture"}))
    out = tables[0]
    for tb in tables[1:]:
        out = out.merge(tb, on=["n_moves", "level_pct"], how="outer")
    out = out.sort_values("n_moves")[["n_moves", "level_pct"] + [c for c in out if c.startswith("prob")]]
    out = out[out.filter(like="prob").max(axis=1) >= 0.0005]
    print(out.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    if a.out:
        out.to_csv(a.out, index=False)


# ---------------------------------------------------------------- self-test
def selftest():
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"[{'ok' if ok else 'FAIL'}] {name}: got {got:.6f} want {want:.6f} tol {tol}")
        if not ok:
            fails.append(name)

    # 1. Bachelier vs textbook: Sep-22 Euribor call on price = put on rate (Tuckman & Serrat 4e, Table 16.3)
    check("bachelier textbook put", float(bachelier(-0.235, -0.25, 203 / 365, 68.42, "put")), 0.1961, 5e-5)

    # strike ladder like SR3: 6.25bp within +/-100bp, 12.5bp out to +/-200bp; quotes in PRICE space
    def ladder(fwd):
        off = np.unique(np.r_[np.arange(-1.0, 1.0001, 0.0625), np.arange(-2.0, 2.0001, 0.125)])
        k = np.round(fwd + off, 6)
        return pd.DataFrame({"strike_px": np.r_[100 - k, 100 - k], "option_right": ["C"] * len(k) + ["P"] * len(k)})

    # 2. Known normal, premium up front (df = 0.98): BL must recover mean, sd, zero skew, lattice cells
    fwd, t, vol, dfac = 3.75, 0.5, 60.0, 0.98
    qq = ladder(fwd)
    kr = 100 - qq["strike_px"]
    kind_r = np.where(qq["option_right"] == "C", "put", "call")
    qq["premium_px"] = [float(bachelier(fwd, k_, t, vol, kd, dfac)) for k_, kd in zip(kr, kind_r)]
    rq = to_rate_space(qq, 100 - fwd)
    g, q, diag = bl_density(rq["k"], rq["premium_px"], rq["kind"], fwd, t, dfac, smooth_bp=0.01)
    mo = moments(g, q, fwd)
    sd_true = vol * np.sqrt(t)
    check("normal raw mass (df handled)", diag["raw_mass"], 1.0, 0.005)
    check("normal mean - fwd (bp)", mo["mean_minus_fwd_bp"], 0.0, 0.25)
    check("normal sd (bp)", mo["sd_bp"], sd_true, 0.02 * sd_true)
    check("normal skew", mo["skew"], 0.0, 0.05)
    lp = lattice_probs(g, q, 3.75).set_index("n_moves")["prob"]
    for n in (-1, 0, 2):
        a_, b_ = (3.75 + (n - 0.5) * 0.25 - fwd) * 100 / sd_true, (3.75 + (n + 0.5) * 0.25 - fwd) * 100 / sd_true
        check(f"normal cell n={n}", lp[n], norm.cdf(b_) - norm.cdf(a_), 0.005)
    check("normal P(r<3.0)", prob_below(g, q, 3.0), norm.cdf((3.0 - fwd) * 100 / sd_true), 0.005)

    # 3. Known lattice mixture (futures-style, df = 1): mixture fit recovers weights and smear; BL recovers cells
    base, s_bp, t = 4.30, 10.0, 0.5
    w_true = {1: 0.06, 0: 0.28, -1: 0.07, -2: 0.36, -4: 0.23}
    mu = np.array([base + n * 0.25 for n in w_true])
    w = np.array(list(w_true.values()))
    fwd = float(w @ mu)
    qq = ladder(round(fwd / 0.0625) * 0.0625)
    kr = (100 - qq["strike_px"]).to_numpy()
    kind_r = np.where(qq["option_right"] == "C", "put", "call")
    sd = s_bp / 100
    d = (mu[None, :] - kr[:, None]) / sd
    call = ((mu[None, :] - kr[:, None]) * norm.cdf(d) + sd * norm.pdf(d)) @ w
    qq["premium_px"] = np.where(kind_r == "call", call, call - (fwd - kr))
    rq = to_rate_space(qq, 100 - fwd)
    mx, info = mixture_fit(rq["k"], rq["premium_px"], rq["kind"], fwd, t, 1.0, base)
    mx = mx.set_index("n_moves")["prob"]
    check("mixture smear (bp)", info["smear_bp"], s_bp, 0.5)
    for n, wt in w_true.items():
        check(f"mixture weight n={n}", mx[n], wt, 0.02)
    check("mixture implied mean", info["implied_mean_pct"], fwd, 1e-3)
    g, q, diag = bl_density(rq["k"], rq["premium_px"], rq["kind"], fwd, t, 1.0, smooth_bp=0.01)
    lp = lattice_probs(g, q, base).set_index("n_moves")["prob"]
    for n in (0, -2, -4):
        lo, hi = base + (n - 0.5) * 0.25, base + (n + 0.5) * 0.25
        want = float(sum(wt * (norm.cdf((hi - m) / sd) - norm.cdf((lo - m) / sd)) for wt, m in zip(w, mu)))
        check(f"BL cell on mixture n={n}", lp[n], want, 0.015)
    check("BL mean on mixture (bp)", moments(g, q, fwd)["mean_minus_fwd_bp"], 0.0, 0.5)

    # 4. Same mixture with +/- half-tick (0.125bp) premium noise: lattice weights still within 4pp
    noisy = qq.assign(premium_px=qq["premium_px"] + np.random.default_rng(7).uniform(-0.00125, 0.00125, len(qq)))
    rq = to_rate_space(noisy, 100 - fwd, min_prem=0.005)
    mx, _ = mixture_fit(rq["k"], rq["premium_px"], rq["kind"], fwd, t, 1.0, base)
    mx = mx.set_index("n_moves")["prob"]
    check("noisy mixture max weight error", max(abs(mx.get(n, 0) - w_true.get(n, 0)) for n in mx.index), 0.0, 0.04)

    # 5. CLI end to end on canonical tables (price-space strikes, two expiries, latest picked)
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        ids = [f"OPT:SR3:2027-03-12:{r}:{s:.4f}" for r, s in zip(qq["option_right"], qq["strike_px"])]
        stat = pd.DataFrame({"opt_id": ids, "underlying_id": "FUT:SR3:2027-03", "option_right": qq["option_right"],
                             "strike_px": qq["strike_px"], "expiry_date": "2027-03-12"})
        quotes = pd.DataFrame({"date": "2026-09-11", "snap": "settle", "opt_id": ids, "premium_px": qq["premium_px"],
                               "underlying_px": 100 - fwd, "oi_cnt": 500})
        decoy_ids = [i.replace("2027-03-12", "2026-12-11") for i in ids]
        stat = pd.concat([stat, stat.assign(opt_id=decoy_ids, expiry_date="2026-12-11")])
        quotes = pd.concat([quotes, quotes.assign(opt_id=decoy_ids, premium_px=quotes["premium_px"] * 0.5)])
        for name, frame in (("oq.csv", quotes), ("os.csv", stat)):
            frame.to_csv(os.path.join(tmp, name), index=False)
        out = os.path.join(tmp, "probs.csv")
        main(["--opt-quotes", os.path.join(tmp, "oq.csv"), "--opt-static", os.path.join(tmp, "os.csv"),
              "--date", "2026-09-11", "--underlying", "FUT:SR3:2027-03", "--base-rate-pct", str(base),
              "--method", "both", "--thresholds", "3.5", "--out", out])
        res = pd.read_csv(out).set_index("n_moves")["prob_mixture"]
        check("CLI mixture weight n=-2", res[-2], 0.36, 0.02)

    print("SELFTEST", "FAILED: " + ", ".join(fails) if fails else "PASSED")
    return 1 if fails else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--opt-quotes"), p.add_argument("--opt-static")
    p.add_argument("--date"), p.add_argument("--underlying", help="fut_id, e.g. FUT:SR3:2026-12")
    p.add_argument("--snap", default="settle")
    p.add_argument("--expiry", help="option expiry YYYY-MM-DD (default: latest listed on the underlying)")
    p.add_argument("--fut-px", type=float, help="override underlying futures price")
    p.add_argument("--df", type=float, default=1.0, help="1.0 futures-style margined; DF to expiry if paid up front")
    p.add_argument("--base-rate-pct", type=float, help="settlement rate of the contract if policy is unchanged")
    p.add_argument("--step-bp", type=float, default=25.0)
    p.add_argument("--smooth-bp", type=float, default=0.5, help="RMS normal-vol fit tolerance (bp)")
    p.add_argument("--min-prem-bp", type=float, default=0.5, help="drop OTM premiums below this (bp)")
    p.add_argument("--min-oi", type=float, default=100)
    p.add_argument("--thresholds", type=float, nargs="*", default=[], help="report P(rate < level) for each")
    p.add_argument("--method", choices=["bl", "mixture", "both"], default="both")
    p.add_argument("--out", help="write lattice probabilities CSV")
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.opt_quotes and a.opt_static and a.date and a.underlying):
        p.error("--opt-quotes, --opt-static, --date and --underlying are required (or --selftest)")
    run_cli(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
