#!/usr/bin/env python3
"""CSA / collateral / xVA arithmetic for G10 swap fair value.

Functions (numpy / pandas in, numbers / pandas out):
  ctd_discount_factors  intrinsic multi-CSA (cheapest-to-deliver collateral) DFs: each day (or block of days)
                        discount at the HIGHEST O/N rate across the eligible collateral curves. Excludes the
                        collateral switch option value.
  daily_on_rates        O/N forward rates (pct) on a daily grid from curve_zero node DFs (log-linear DF).
  cva                   CVA = LGD * sum_i p_i * EE_i * DF_i  (p_i = marginal default prob in period i).
  funding_cost          sum_i s * X_i * dt_i * DF_i. FVA (X = EPE or ENE) or MVA (X = expected IM).
  to_bp_running         PV adjustment / DV01 -> bp of fixed rate.
  expected_positive     E[max(X, 0)] for X ~ N(mu, sigma^2). Used for EE and collateral-option estimates.
  collateral_carry      one-period benefit to the poster of posting cash vs a repo'd bond with a haircut.

Conventions: rates in pct (4.25 = 4.25%), spreads in bp, DFs dimensionless, money in the trade currency.
Every CTD input curve must discount cashflows of ONE currency under different collateral (e.g. EUR:EUR-CSA and
EUR:USD-CSA built with the xccy basis). Never compare raw SOFR with raw ESTR.

CLI:
  python csa_xva.py ctd --curve-zero curve_zero.parquet --date 2026-11-10 --snap eod_ldn \
      --curves EUR-ESTR,EUR-CSA-USD --day-basis 360 --out ctd.csv
  python csa_xva.py xva --profile profile.csv --lgd 0.6 --fund-spread-bp 50 --im-spread-bp 20 --dv01 225000
      (profile columns: t_years, df, and any of ee, pd, epe, ene, im; user-supplied, not a canonical table)
  python csa_xva.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm


# --------------------------------------------------------------------------- discounting under collateral choice
def ctd_discount_factors(on_rates: pd.DataFrame, day_basis: float = 365.0, steps=None) -> pd.DataFrame:
    """DFs per collateral curve and for the intrinsic CTD curve.

    on_rates: one row per calendar day (row i = rate from day i to i+1), one column per collateral option, pct.
    steps: optional list of block lengths in days (e.g. [2, 1]); the last length repeats. Within a block each curve's
    rate is its compounded block rate and the CTD takes the max of block rates. Block DFs are >= exact DFs.
    Returns DataFrame indexed 0..n (day count), DF(0) = 1.
    """
    r = on_rates.to_numpy(float) / 100.0
    if np.isnan(r).any():                                         # a NaN would silently poison every later DF
        raise ValueError("on_rates contains NaN; fill or truncate the curves before building the CTD curve")
    d = 1.0 / day_basis
    growth = 1.0 + r * d                                          # (n, k) one-day growth factors
    out = pd.DataFrame(np.vstack([np.ones(r.shape[1]), 1.0 / np.cumprod(growth, axis=0)]),
                       columns=on_rates.columns)
    n = len(r)
    if not steps:
        ctd_growth = growth.max(axis=1)                           # highest attainable O/N rate each day
        out["CTD"] = np.r_[1.0, 1.0 / np.cumprod(ctd_growth)]
        return out
    dfs, i, j, steps = [1.0], 0, 0, list(steps)
    while i < n:
        m = min(steps[min(j, len(steps) - 1)], n - i)
        block = growth[i:i + m].prod(axis=0)                     # each curve's compounded growth over the block
        prev = dfs[-1]
        dfs += [np.nan] * (m - 1)                                 # only block ends are evaluated
        dfs.append(prev / block.max())
        i, j = i + m, j + 1
    dfs = pd.Series(dfs[: n + 1])
    # fill inside blocks log-linearly between evaluated block ends
    out["CTD"] = np.exp(np.log(dfs).interpolate())
    return out


def daily_on_rates(curve_zero: pd.DataFrame, curve_ids, asof, snap=None, day_basis: float = 365.0,
                   horizon_days: int | None = None) -> pd.DataFrame:
    """Daily O/N forward rates (pct) from canonical curve_zero rows, log-linear in DF between nodes."""
    ccys = {c.split("-")[0] for c in curve_ids}
    if len(ccys) != 1:
        raise ValueError(f"CTD curves must discount ONE cashflow currency; got {sorted(ccys)}. Build the "
                         "cross-collateral curves (e.g. EUR cashflows under USD cash) first.")
    cz = curve_zero.copy()
    cz["date"] = pd.to_datetime(cz["date"])
    cz["node_date"] = pd.to_datetime(cz["node_date"])
    cz = cz[cz["date"] == pd.Timestamp(asof)]
    if snap is not None and "snap" in cz:
        cz = cz[cz["snap"] == snap]
    cols = {}
    for cid in curve_ids:
        c = cz[cz["curve_id"] == cid].sort_values("node_date")
        if c.empty:
            raise ValueError(f"curve_id {cid} not found for {asof}")
        if c["node_date"].duplicated().any():
            raise ValueError(f"curve_id {cid} has duplicate node_dates on {asof} (several snaps?); pass snap")
        t = (c["node_date"] - pd.Timestamp(asof)).dt.days.to_numpy()
        lndf = np.log(c["discount_factor"].to_numpy(float))
        t, lndf = np.r_[0, t[t > 0]], np.r_[0.0, lndf[t > 0]]
        cols[cid] = (t, lndf)
    last = min(t[-1] for t, _ in cols.values())
    n = int(min(last, horizon_days) if horizon_days else last)
    grid = np.arange(n + 1)
    rates = {cid: (np.exp(-np.diff(np.interp(grid, t, ln))) - 1.0) * day_basis * 100.0
             for cid, (t, ln) in cols.items()}
    idx = pd.Timestamp(asof) + pd.to_timedelta(grid[:-1], unit="D")
    return pd.DataFrame(rates, index=idx)


# --------------------------------------------------------------------------- credit, funding, margin
def cva(ee, pd_marginal, df, lgd: float = 1.0) -> float:
    """CVA = LGD * sum p_i * EE_i * DF_i (Darbyshire, Pricing and Trading IRDs, 3rd ed., s.5.3.5)."""
    ee, p, v = (np.asarray(x, float) for x in (ee, pd_marginal, df))
    return float(lgd * np.sum(p * ee * v))


def funding_cost(profile, spread_bp, dt, df) -> float:
    """sum s * X_i * dt_i * DF_i. FVA: X = EPE (cost at borrow spread) or ENE (benefit at lend spread).
    MVA: X = expected incremental IM, s = funding rate minus IM remuneration."""
    x, s, t, v = (np.asarray(a, float) for a in (profile, spread_bp, dt, df))
    return float(np.sum(s / 1e4 * x * t * v))


def to_bp_running(pv_adj: float, dv01: float) -> float:
    """Convert a PV adjustment (currency) to bp of fixed rate using trade DV01 (currency per bp, positive)."""
    return pv_adj / dv01


def expected_positive(mu, sigma):
    """E[max(X,0)], X ~ N(mu, sigma^2) = mu*Phi(mu/sigma) + sigma*phi(mu/sigma). sigma=0 -> max(mu,0)."""
    mu, sigma = np.asarray(mu, float), np.asarray(sigma, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(sigma > 0, mu / np.where(sigma > 0, sigma, 1.0), 0.0)
    return np.where(sigma > 0, mu * norm.cdf(z) + sigma * norm.pdf(z), np.maximum(mu, 0.0))


def collateral_carry(liability: float, haircut: float, collateral_rate_pct: float, unsecured_pct: float,
                     days: float = 1.0, day_basis: float = 365.0) -> float:
    """Poster's one-period income from covering `liability` with collateral earning `collateral_rate_pct`
    (cash remuneration, or repo rate on a reverse-repo'd bond), market value liability*(1+haircut); the haircut
    top-up is borrowed unsecured. haircut=0 is the cash case. Highest value = CTD collateral."""
    d = days / day_basis
    return liability * (1 + haircut) * collateral_rate_pct / 100 * d - liability * haircut * unsecured_pct / 100 * d


# --------------------------------------------------------------------------- CLI
def _read(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def _cli_ctd(a):
    ids = a.curves.split(",")
    on = daily_on_rates(_read(a.curve_zero), ids, a.date, a.snap, a.day_basis, a.horizon_days)
    dfs = ctd_discount_factors(on, a.day_basis)
    ctd = on.idxmax(axis=1)
    sw = ctd[ctd != ctd.shift()]
    print("CTD collateral curve by start date (intrinsic, excludes switch-option value):")
    print(sw.to_string())
    node_dates = pd.Timestamp(a.date) + pd.to_timedelta(dfs.index, unit="D")
    res = pd.DataFrame({"date": a.date, "snap": a.snap or "", "curve_id": "CTD:" + "+".join(ids),
                        "node_date": node_dates.date, "discount_factor": dfs["CTD"].to_numpy(),
                        "source": "csa_xva.ctd"})
    for cid in ids:
        res[f"df_{cid}"] = dfs[cid].to_numpy()
    if a.out:
        res.to_csv(a.out, index=False)
        print(f"wrote {len(res)} daily rows to {a.out}")
    else:
        print(res.iloc[np.r_[0:3, -3:0]].to_string(index=False))


def _cli_xva(a):
    p = _read(a.profile).sort_values("t_years")
    if p.isna().any().any():
        sys.exit(f"profile has NaN in {list(p.columns[p.isna().any()])}; fill or drop those rows first")
    # funding rows are period ENDS (dt_i = t_i - t_{i-1}); CVA rows use pd = P(default in the period at that row)
    dt = np.diff(np.r_[0.0, p["t_years"].to_numpy(float)])
    rows = {}
    if {"ee", "pd"} <= set(p):
        rows["CVA"] = cva(p["ee"], p["pd"], p["df"], a.lgd)
    if "epe" in p and a.fund_spread_bp is not None:
        rows["FVA_cost(EPE)"] = funding_cost(p["epe"], a.fund_spread_bp, dt, p["df"])
    if "ene" in p and a.lend_spread_bp is not None:
        rows["FVA_benefit(ENE)"] = -funding_cost(p["ene"], a.lend_spread_bp, dt, p["df"])
    if "im" in p and a.im_spread_bp is not None:
        rows["MVA"] = funding_cost(p["im"], a.im_spread_bp, dt, p["df"])
    if not rows:
        sys.exit("profile needs columns ee+pd (CVA), epe/ene (FVA) or im (MVA), with the matching spread flags")
    out = pd.DataFrame({"pv_cost": rows})
    out.loc["total"] = out["pv_cost"].sum()
    if a.dv01:
        out["bp_running"] = out["pv_cost"] / a.dv01
    print(out.round(4).to_string())


# --------------------------------------------------------------------------- self-test (known answers)
def _selftest() -> None:
    fails = []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.8f} want {want:.8f}")
        if not ok:
            fails.append(name)

    # 1. Darbyshire, Coding Interest Rates, s.6.6: C1={1,2,3}%, C2={3,2,1}%, C3={2,2.5,2}% -> CTD {3,2.5,3}%
    on = pd.DataFrame({"C1": [1.0, 2.0, 3.0], "C2": [3.0, 2.0, 1.0], "C3": [2.0, 2.5, 2.0]})
    ex = ctd_discount_factors(on, 365.0)["CTD"]
    for i, w in enumerate([0.99991781, 0.99984933, 0.99976716], start=1):
        check(f"CIR multi-CSA exact DF day {i}", ex[i], w, 5e-9)
    ap = ctd_discount_factors(on, 365.0, steps=[2, 1])["CTD"]
    check("CIR 2-day block DF day 2", ap[2], 0.99986303, 1.5e-8)
    check("CIR 2-day block DF day 3", ap[3], 0.99978086, 1.5e-8)
    if not (ap[3] >= ex[3]):
        fails.append("block approximation must give DF >= exact")

    # 2. Darbyshire, Pricing and Trading IRDs, Ex 5.6: JPY CSA vs USD CSA (JPY cashflows), ACT/365
    jp = pd.DataFrame({"JPY": [2.00, 2.05, 2.15, 2.20], "USD": [2.10] * 4})
    d = ctd_discount_factors(jp, 365.0)
    for i, w in enumerate([0.999942, 0.999885, 0.999826, 0.999766], start=1):
        check(f"Ex5.6 combined DF t+{i}", d["CTD"][i], w, 1e-6)
    check("Ex5.6 JPY-only DF t+4", d["JPY"][4], 0.999770, 1e-6)
    if not (d["CTD"] <= d[["JPY", "USD"]].min(axis=1) + 1e-15).all():
        fails.append("CTD DF must be <= every single-CSA DF")

    # 3. Ex 5.14 CVA from EE of Ex 5.12 (collateralised) and Ex 5.13 (uncollateralised), LGD 100%
    v = [1.000, 0.963, 0.928, 0.906, 0.856]
    check("Ex5.14 CVA collateralised", cva([450e3, 443e3, 393e3, 263e3, 131e3], [0.001] * 5, v), 1591.727, 0.01)
    check("Ex5.14 CVA uncollateralised",
          cva([357e3, 3278e3, 5045e3, 4064e3, 1206e3], [0.01, 0.004, 0.001, 0.001, 0.001], v), 25593.0, 0.5)
    check("Ex5.14 CVA collateralised, LGD 60% (-40%)",
          cva([450e3, 443e3, 393e3, 263e3, 131e3], [0.001] * 5, v, lgd=0.6), 955.0362, 0.01)

    # 4. Ex 5.5: GBP100mm liability; cash at RFR 0.75% vs gilts (repo RFR+8bp) with 2% / 6% haircuts, unsecured 2.5%
    check("Ex5.5 post cash", collateral_carry(100e6, 0.0, 0.75, 2.5), 2054.79, 0.01)
    check("Ex5.5 post 3Y gilt", collateral_carry(100e6, 0.02, 0.83, 2.5), 2182.47, 0.01)
    check("Ex5.5 post 15Y gilt", collateral_carry(100e6, 0.06, 0.83, 2.5), 1999.45, 0.01)

    # 5. E[max(X,0)] for X ~ N(0, s^2) = s / sqrt(2 pi) (Darbyshire s.5.3.3); sigma=0 -> intrinsic
    check("E+ N(0,1)", float(expected_positive(0.0, 1.0)), 1 / np.sqrt(2 * np.pi), 1e-12)
    check("E+ sigma=0", float(expected_positive(2.0, 0.0)), 2.0, 1e-12)

    # 6. Funding: 50bp on 1mm posted for 1y, undiscounted = 5,000 (During: O/N+50bp funding, O/N remuneration)
    check("funding 50bp x 1mm x 1y", funding_cost([1e6] * 4, 50, [0.25] * 4, [1.0] * 4), 5000.0, 1e-9)
    check("funding discounted (DF 0.9)", funding_cost([1e6], 50, [1.0], [0.9]), 4500.0, 1e-9)
    check("bp running", to_bp_running(726545.0, 225000.0), 3.229089, 1e-6)

    # 7. daily_on_rates recovers a flat 3% O/N rate (ACT/360) from curve_zero nodes; currency guard
    a0, r0 = pd.Timestamp("2026-11-10"), 3.0
    nd = np.array([7, 30, 365, 730])
    czf = pd.DataFrame({"date": a0, "curve_id": "EUR-X", "node_date": a0 + pd.to_timedelta(nd, unit="D"),
                        "discount_factor": (1 + r0 / 100 / 360) ** -nd.astype(float)})
    onr = daily_on_rates(czf, ["EUR-X"], a0, day_basis=360.0)
    check("O/N from curve_zero, max |err| (pct)", float((onr["EUR-X"] - r0).abs().max()), 0.0, 1e-9)
    check("O/N grid length (days)", float(len(onr)), 730.0, 0)
    try:
        daily_on_rates(pd.concat([czf, czf.assign(curve_id="USD-X")]), ["EUR-X", "USD-X"], a0)
        fails.append("currency guard did not raise")
    except ValueError:
        pass

    if fails:
        print(f"SELFTEST FAILED: {fails}")
        sys.exit(1)
    print("selftest passed")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("ctd", help="intrinsic multi-CSA curve from curve_zero")
    c.add_argument("--curve-zero", required=True)
    c.add_argument("--date", required=True)
    c.add_argument("--snap")
    c.add_argument("--curves", required=True, help="comma list of curve_ids, same cashflow currency")
    c.add_argument("--day-basis", type=float, default=365.0, help="RFR day-count denominator (360 or 365); take it from swap_conventions")
    c.add_argument("--horizon-days", type=int)
    c.add_argument("--out")
    x = sub.add_parser("xva", help="CVA/FVA/MVA from an exposure / IM profile")
    x.add_argument("--profile", required=True)
    x.add_argument("--lgd", type=float, default=0.6)
    x.add_argument("--fund-spread-bp", type=float)
    x.add_argument("--lend-spread-bp", type=float)
    x.add_argument("--im-spread-bp", type=float)
    x.add_argument("--dv01", type=float)
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
    elif a.cmd == "ctd":
        _cli_ctd(a)
    elif a.cmd == "xva":
        _cli_xva(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
