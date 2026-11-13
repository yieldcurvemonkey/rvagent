"""CCP basis (CME-LCH, Eurex-LCH, JSCC-LCH) tools.

Convention used by every function: basis_bp = rate(other CCP) - rate(LCH), in bp, for the same index, tenor and
start. Positive = paying fixed costs more at the other CCP (pay at LCH, receive at the other CCP to earn it).
The canonical `ccp_basis` table may store either orientation (its default is LCH minus CME); `normalise` flips it.

Functions
  normalise(df, ref)          canonical ccp_basis rows -> basis_bp quoted as (other CCP - ref), column ccp_x
  annuity(rate_pct, years)    flat-rate annual-pay annuity (years per 1.0 of running spread)
  forward_basis(b1,t1,b2,t2)  single-curve forward basis between t1 and t2 (annuity-weighted)
  breakeven_bp(...)           personal breakeven basis for a switch/arb: PV(proceeds) = PV(fees + IM funding)
  switch_benefit(...)         IM-funding + default-fund saving of a CCP switch (Clarus 2015 rule of thumb)
  mva_bp(...)                 dealer MVA model: funding cost of incremental IM profile / DV01 = fair basis in bp
  period_end_dummies(idx)     quarter-end / year-end dummies (month-end window: day >= 25)
  fv_regression(y, X, ...)    per-tenor OLS fair value of the basis + expanding residual z (no look-ahead in z)
  screen(df, ...)             per (ccy, index, ccp, tenor): level, z, percentile, range, 3m change, 5y5y fwd basis

CLI: python ccp_basis.py --ccp-basis ccp_basis.csv [--lookback 252] [--rate-pct 3.0] [--out screen.csv]
     python ccp_basis.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

TENOR_YEARS = {"M": 1 / 12, "Y": 1.0}


def tenor_years(t: str) -> float:
    """'10Y' -> 10.0, '18M' -> 1.5; anything else (ON, 1W, ...) -> NaN so it is skipped, not a crash."""
    try:
        return float(t[:-1]) * TENOR_YEARS[t[-1].upper()]
    except (KeyError, ValueError, IndexError):
        return float("nan")


def normalise(df: pd.DataFrame, ref: str = "LCH") -> pd.DataFrame:
    """Return rows involving `ref` with basis_bp = other CCP minus ref and the other CCP in `ccp_x`."""
    d = df.copy()
    if "basis_bp" not in d:
        d["basis_bp"] = np.nan
    if {"rate_a_pct", "rate_b_pct"} <= set(d):
        d["basis_bp"] = d["basis_bp"].fillna(100.0 * (d["rate_a_pct"] - d["rate_b_pct"]))
    a_is_ref, b_is_ref = d["ccp_a"].eq(ref), d["ccp_b"].eq(ref)
    d = d[a_is_ref ^ b_is_ref].copy()
    flip = d["ccp_a"].eq(ref)
    d["ccp_x"] = np.where(flip, d["ccp_b"], d["ccp_a"])
    d["basis_bp"] = np.where(flip, -d["basis_bp"], d["basis_bp"])
    d["sign_convention"] = d["ccp_x"] + "_minus_" + ref
    return d.drop(columns=[c for c in ("ccp_a", "ccp_b", "rate_a_pct", "rate_b_pct") if c in d])


def annuity(rate_pct: float, years: float) -> float:
    """Annual-pay annuity at a flat rate, (1 - (1+r)^-T)/r; equals `years` at r = 0 (smooth in fractional T)."""
    r = rate_pct / 100.0
    if abs(r) < 1e-12:
        return float(years)
    return float((1 - (1 + r) ** -years) / r)


def forward_basis(b1: float, t1: float, b2: float, t2: float, rate_pct: float = 3.0) -> float:
    """Forward basis t1->t2 from spot bases, single curve: (b2*A2 - b1*A1) / (A2 - A1)."""
    if t2 <= t1:
        raise ValueError("need t2 > t1")
    a1, a2 = annuity(rate_pct, t1), annuity(rate_pct, t2)
    return (b2 * a2 - b1 * a1) / (a2 - a1)


def breakeven_bp(notional: float, im_by_year, fund_spread_by_year, fees_by_year, dfs=None) -> float:
    """Basis (bp running, annual accrual) at which PV(basis proceeds) = PV(fees + IM x funding spread).

    im_by_year: IM outstanding during each year, both CCPs summed (currency).
    fund_spread_by_year: funding cost of that IM, decimal per year (your cost minus what the CCP pays on collateral).
    fees_by_year: execution + CCP + clearing-broker fees paid in each year (currency, positive = cost).
    """
    im, s, fees = (np.asarray(x, float) for x in (im_by_year, fund_spread_by_year, fees_by_year))
    df = np.ones_like(im) if dfs is None else np.asarray(dfs, float)
    cost_pv = float(np.sum(df * (fees + im * s)))
    return cost_pv / (notional * 1e-4 * float(np.sum(df)))


def switch_benefit(im_reduction: float, fund_spread: float, annuity_years: float,
                   df_frac: float = 0.08, equity_cost: float = 0.10, amortise: float = 0.5,
                   df_years: float = 1.0) -> dict:
    """Value of the IM a CCP switch releases (both CCPs summed in `im_reduction`).

    IM funding saved = IM x funding spread x annuity, x `amortise` (0.5: IM runs off roughly linearly).
    Default-fund saving = DF (df_frac x IM) x equity cost, an ANNUAL cost: the default `df_years=1` reproduces the
    Clarus 2015 figure (one year only); use df_years = annuity_years * amortise for a like-for-like horizon.
    """
    im_val = im_reduction * fund_spread * annuity_years * amortise
    df_val = im_reduction * df_frac * equity_cost * df_years
    return {"im_funding": im_val, "default_fund": df_val, "total": im_val + df_val}


def mva_bp(im_profile, fund_spread: float, dv01: float, dt: float = 1.0, dfs=None) -> float:
    """Fair basis (bp) from funding the incremental IM: sum(DF_t * IM_t * spread * dt) / DV01 (DV01 in currency/bp).

    im_profile: incremental IM held in each period (currency), both CCPs summed or one CCP at a time.
    fund_spread: your cost of funds minus what the CCP pays on cash, decimal per year.
    dfs: discount factors per period; DV01 is a discounted annuity, so pass them for long trades (default: none,
    which overstates the basis by roughly a fifth for a linearly tapering 30Y at 2.5%).
    """
    im = np.asarray(im_profile, float)
    df = 1.0 if dfs is None else np.asarray(dfs, float)
    return float(np.sum(df * im * fund_spread * dt) / dv01)


def period_end_dummies(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """quarter_end = Mar/Jun/Sep/Dec and day >= 25; year_end = Dec and day >= 25."""
    late = idx.day >= 25
    return pd.DataFrame({"quarter_end": (np.isin(idx.month, [3, 6, 9, 12]) & late).astype(float),
                         "year_end": ((idx.month == 12) & late).astype(float)}, index=idx)


def fv_regression(y: pd.Series, X: pd.DataFrame, min_obs: int = 30, z_min: int = 20):
    """OLS fair value of basis y (bp) on factors X; returns (frame[basis, fv, resid, z], coef Series).

    Zero-variance columns are dropped. Fit is FULL-SAMPLE (in-sample fair value, so not a backtest by itself);
    z = (resid_t - mean_{<t}) / std_{<t} on an expanding window (>= z_min obs), so z_t never sees the future residuals.
    """
    d = pd.concat([y.rename("y"), X], axis=1).dropna()
    if len(d) < min_obs:
        raise ValueError(f"need >= {min_obs} observations, got {len(d)}")
    cols = [c for c in X.columns if d[c].std() > 0]
    A = np.column_stack([np.ones(len(d)), d[cols].to_numpy(float)])
    beta, *_ = np.linalg.lstsq(A, d["y"].to_numpy(float), rcond=None)
    fv = pd.Series(A @ beta, index=d.index)
    res = d["y"] - fv
    z = (res - res.expanding(z_min).mean().shift(1)) / res.expanding(z_min).std().shift(1)
    return (pd.DataFrame({"basis": d["y"], "fv": fv, "resid": res, "z": z}),
            pd.Series(beta, index=["const"] + cols))


def screen(df: pd.DataFrame, lookback: int = 252, rate_pct: float = 3.0, chg_days: int = 63) -> pd.DataFrame:
    """Per (ccy, index_id, ccp_x, tenor): latest basis, z, percentile, lookback min/max, change, plus 5y5y fwd."""
    keys = ["ccy", "index_id", "ccp_x"]
    out = []
    df = df.sort_values(["date", "snap"] if "snap" in df else ["date"]).drop_duplicates(
        keys + ["tenor", "date"], keep="last")  # one snap per day: the last snap label sorted
    for k, g in df.groupby(keys + ["tenor"]):
        s = g.sort_values("date").set_index("date")["basis_bp"].dropna()
        if len(s) < 20:
            continue
        w = s.iloc[-lookback:]
        sd = w.std(ddof=1)
        out.append(dict(zip(keys + ["tenor"], k), date=s.index[-1], basis_bp=s.iloc[-1],
                        z=(s.iloc[-1] - w.mean()) / sd if sd > 0 else np.nan,
                        pctile=(w <= s.iloc[-1]).mean(), min_bp=w.min(), max_bp=w.max(),
                        chg_bp=s.iloc[-1] - s.iloc[-1 - chg_days] if len(s) > chg_days else np.nan, n=len(w)))
    res = pd.DataFrame(out)
    if res.empty:
        return res
    res["years"] = res["tenor"].map(tenor_years)
    fwd = {}
    for k, g in res.groupby(keys):
        b = dict(zip(g["years"], g["basis_bp"]))
        if 5.0 in b and 10.0 in b:
            fwd[k] = forward_basis(b[5.0], 5, b[10.0], 10, rate_pct)
    res["fwd5y5y_bp"] = [fwd.get(tuple(r), np.nan) for r in res[keys].itertuples(index=False)]
    return res.sort_values(keys + ["years"]).drop(columns="years").reset_index(drop=True)


def _selftest() -> int:
    ok = True

    def check(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name}: got {got:.6f} want {want:.6f}")

    # 1. orientation: canonical default LCH - CME (+0.5) must come back as CME - LCH (-0.5)
    raw = pd.DataFrame({"date": ["2026-11-10"], "ccy": ["USD"], "index_id": ["USD-SOFR"], "tenor": ["10Y"],
                        "ccp_a": ["LCH"], "ccp_b": ["CME"], "rate_a_pct": [3.8150], "rate_b_pct": [3.8100],
                        "basis_bp": [np.nan]})
    n = normalise(raw)
    check("normalise LCH-CME -> CME-LCH", float(n["basis_bp"].iloc[0]), -0.5, 1e-9)
    # 2. forward basis at zero rates is the tenor-weighted identity: (2.30*10 - 1.85*5)/5 = 2.75
    #    (spot 5y 1.85 / 10y 2.30 from Clarus Barnes 26 May 2015; the article's 5y5y read was +2.9 on its curve)
    check("5y5y fwd basis, zero rates", forward_basis(1.85, 5, 2.30, 10, 0.0), 2.75, 1e-12)
    check("flat basis -> flat forward", forward_basis(1.2, 5, 1.2, 10, 4.0), 1.2, 1e-12)
    # 3. breakeven, analytic: 100mm, IM 4mm at 1% for 5y + 1,000/yr fees -> 41,000/yr / 10,000 per bp = 4.1bp
    check("breakeven analytic", breakeven_bp(100e6, [4e6] * 5, [0.01] * 5, [1000] * 5), 4.1, 1e-12)
    #    published answer: Clarus Skarecky 22 Jun 2015, 100mm 5Y. Funding cost by year 19,335/44,543/53,420/42,970/21,303,
    #    fees = 12,500 proceeds - net-of-fee cash flows 5,411/8,615/9,413/10,291/11,312; article breakeven 3.932bp
    #    (undiscounted here gives 3.98: within 0.1bp, the article's discounting is not reproduced)
    fund = [19335, 44543, 53420, 42970, 21303]
    fees = [12500 - x for x in (5411, 8615, 9413, 10291, 11312)]
    check("Clarus 3.93bp breakeven (approx)", breakeven_bp(100e6, fund, [1.0] * 5, fees), 3.932, 0.1)
    #    annuity: closed form vs explicit sum, fractional tenor, zero rate
    check("annuity 5y at 3%", annuity(3.0, 5), sum(1.03 ** -k for k in range(1, 6)), 1e-12)
    check("annuity zero rate fractional", annuity(0.0, 1.5), 1.5, 1e-12)
    # 4. Clarus Khwaja 26 May 2015: $34m IM released, 50bp, 5y annuity 4.6 -> 782k, halved 391k; DF 8%x10% -> 272k
    sb = switch_benefit(34e6, 0.005, 4.6)
    check("switch IM funding value", sb["im_funding"], 391_000.0, 1e-6)
    check("switch default-fund value", sb["default_fund"], 272_000.0, 1e-6)
    #    default fund is an annual cost: df_years scales it (3 years -> 3 x 272k)
    check("switch default-fund x3y", switch_benefit(34e6, 0.005, 4.6, df_years=3.0)["default_fund"], 816_000.0, 1e-6)
    # 5. z-score/screen on a known series: 0..99 then last = 99 -> z = (99-49.5)/std(0..99)
    d = pd.DataFrame({"date": pd.bdate_range("2025-01-01", periods=100), "ccy": "USD", "index_id": "USD-SOFR",
                      "ccp_x": "CME", "tenor": "10Y", "basis_bp": np.arange(100.0)})
    r = screen(d, lookback=100)
    check("screen z", float(r["z"].iloc[0]), 49.5 / np.arange(100.0).std(ddof=1), 1e-9)
    # 6. MVA, analytic: flat 10m IM for 30y at 20bp / DV01 225k = 600,000/225,000 = 2.6667bp
    check("mva flat IM", mva_bp([10e6] * 30, 0.002, 225_000), 600_000 / 225_000, 1e-12)
    check("mva discounted", mva_bp([10e6] * 2, 0.002, 225_000, dfs=[0.9, 0.8]), 10e6 * 0.002 * 1.7 / 225_000, 1e-12)
    #    linear taper 10m -> 0 (annual steps k=0..29): sum = 10m*(30 - 14.5) = 155m -> 310,000/225,000
    check("mva tapering IM", mva_bp([10e6 * (1 - k / 30) for k in range(30)], 0.002, 225_000), 310_000 / 225_000, 1e-12)
    # 7. fair-value regression: known coefficients recovered; zero-variance column dropped; z has no look-ahead
    rng = np.random.default_rng(7)
    ix = pd.bdate_range("2024-01-01", periods=400)
    X = pd.DataFrame({"x1": rng.normal(size=400), "x2": rng.normal(size=400), "dead": 1.0}, index=ix)
    y = pd.Series(0.5 + 1.5 * X["x1"] - 0.8 * X["x2"] + rng.normal(scale=0.1, size=400), index=ix)
    out, beta = fv_regression(y, X)
    check("fv beta x1", beta["x1"], 1.5, 0.05)
    check("fv beta x2", beta["x2"], -0.8, 0.05)
    check("fv dropped dead col", float("dead" in beta.index), 0.0, 0)
    y2 = y.copy()
    y2.iloc[-1] += 5.0
    out2, _ = fv_regression(y2, X)
    r = out["resid"]
    check("z uses only past residuals", out["z"].iloc[-1], (r.iloc[-1] - r.iloc[:-1].mean()) / r.iloc[:-1].std(ddof=1), 1e-9)
    check("shock shows in last z", float(out2["z"].iloc[-1] > 5.0), 1.0, 0)
    pe = period_end_dummies(pd.DatetimeIndex(["2025-03-28", "2025-12-30", "2025-12-10", "2025-04-28"]))
    check("period-end dummies", float(pe["quarter_end"].sum() * 10 + pe["year_end"].sum()), 21.0, 0)
    print("selftest", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--ccp-basis", help="canonical ccp_basis table (CSV or Parquet)")
    p.add_argument("--ref", default="LCH", help="reference CCP (default LCH, the market's truth curve)")
    p.add_argument("--lookback", type=int, default=252)
    p.add_argument("--rate-pct", type=float, default=3.0, help="flat rate for forward-basis annuities")
    p.add_argument("--out")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if not a.ccp_basis:
        p.error("--ccp-basis is required (or --selftest)")
    read = pd.read_parquet if a.ccp_basis.endswith(".parquet") else pd.read_csv
    df = read(a.ccp_basis, parse_dates=["date"]) if read is pd.read_csv else read(a.ccp_basis)
    if "data_ok" in df:
        df = df[df["data_ok"].astype(str).str.lower() != "false"]
    res = screen(normalise(df, a.ref), a.lookback, a.rate_pct)
    if a.out:
        res.to_csv(a.out, index=False)
    print(res.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
