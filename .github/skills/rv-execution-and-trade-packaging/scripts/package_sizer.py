#!/usr/bin/env python3
"""Package sizing for G10 rates RV: DV01-neutral legs, STIR pack/bundle yields, CCP switch cost.

Sign convention (repo design rule): DV01 positive = receive fixed = long duration.
Structure weights are receive-direction DV01 weights over ascending tenors.
Notional is in $mm, positive = receive fixed. PV01 is $ per bp per $1mm of notional.

CLI (inputs are canonical tables; see data-contract-and-adapters):
  python -I scripts/package_sizer.py size --curve curve_par.csv --curve-id USD-SOFR \
      --date 2026-11-10 --snap eod_ny --tenors 3Y,5Y,10Y --structure fly --target-dv01 50000
  python -I scripts/package_sizer.py pack --prices 97.49,97.31,97.21,97.16
  python -I scripts/package_sizer.py bundle --prices <4N comma-separated STIR prices>
  python -I scripts/package_sizer.py switch --basis-bp 1.2 --notional 1e9 --tenor 5
  python -I scripts/package_sizer.py --selftest

Approximation: size/annuity uses annual fixed legs with unit accrual (ACT/360, calendars and
stubs ignored). Use a convention-correct annuity for production sizing.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

# Receive-direction weights over ascending tenors (sum to zero). Each is normalised so the
# largest-|weight| leg carries exactly target_dv01 (belly for a fly, longer leg for a spread).
WEIGHTS = {
    "spread": [-1.0, 1.0],               # receive the longer leg, pay the shorter
    "fly": [-1.0, 2.0, -1.0],            # receive the belly, pay the wings (50/50 DV01 wings)
    "condor": [-1.0, 1.0, 1.0, -1.0],    # receive the two inner legs, pay the outer legs
    "pascal": [1.0, -3.0, 3.0, -1.0],    # receive the 6/7/8 fly, pay the 5/6/7 fly (tenors 5..8)
}


def structure_weights(structure: str) -> np.ndarray:
    if structure not in WEIGHTS:
        raise ValueError(f"unknown structure {structure!r}; use one of {sorted(WEIGHTS)}")
    w = np.array(WEIGHTS[structure], dtype=float)
    return w / np.abs(w).max()


def size_package(pv01_per_mm: pd.Series, structure: str, target_dv01: float, pay: bool = False) -> pd.DataFrame:
    """DV01-neutral leg notionals for a spread, fly, condor or pascal.

    pv01_per_mm: $/bp per $1mm for each leg, index = tenor labels in ascending maturity order.
    target_dv01: $/bp of the largest-weight leg (belly for a fly). Legs sum to zero DV01.
    Returns one row per leg: weight, dv01 ($/bp, signed), pv01_per_mm, notional_mm (signed).
    """
    w = structure_weights(structure)
    pv01 = pd.Series(pv01_per_mm, dtype=float)
    if len(pv01) != len(w):
        raise ValueError(f"{structure} needs {len(w)} legs, got {len(pv01)}")
    if not np.isfinite(pv01.to_numpy()).all() or (pv01 <= 0).any():
        raise ValueError("PV01 per mm must be finite and positive")
    sign = -1.0 if pay else 1.0
    dv01 = sign * w * float(target_dv01)
    return pd.DataFrame({
        "tenor": pv01.index,
        "weight": sign * w,
        "dv01": dv01,
        "pv01_per_mm": pv01.to_numpy(),
        "notional_mm": dv01 / pv01.to_numpy(),
    })


def annuity_from_par(par_pct) -> tuple[np.ndarray, np.ndarray]:
    """Annual-fixed bootstrap from par rates in percent for years 1..N.

    Returns (discount factors, annuity) per year, with unit accrual.
    DF_n = (1 - r_n * sum_{i<n} DF_i) / (1 + r_n).
    """
    par = np.asarray(par_pct, dtype=float) / 100.0
    dfs: list[float] = []
    for r in par:
        dfs.append((1.0 - r * sum(dfs)) / (1.0 + r))
    dfs_arr = np.array(dfs)
    return dfs_arr, np.cumsum(dfs_arr)


def pv01_per_mm_from_annuity(annuity: float) -> float:
    """$/bp per $1mm for a fixed leg with the given annuity (sum of accrual x DF)."""
    return float(annuity) * 1e-4 * 1e6


def dv01_match_notional(n_known: float, dv01_known: float, dv01_other: float) -> float:
    """Notional of the other leg that matches DV01 (per unit notional DV01s)."""
    return n_known * dv01_known / dv01_other


def pack_yield(prices) -> float:
    """Pack of four consecutive quarterly STIR contracts, decimal annual yield.
    Pack = [prod_{i=1..4} (1 + (100 - P_i)/100 * 0.25)] - 1, forward-start from the first expiry."""
    p = np.asarray(prices, dtype=float)
    if p.size != 4:
        raise ValueError("a pack is exactly four quarterly prices")
    return float(np.prod(1.0 + (100.0 - p) / 100.0 * 0.25) - 1.0)


def bundle_annualised(prices) -> float:
    """Bundle of 4N consecutive quarterly contracts, decimal annualised yield.
    Bundle = [prod_{i=1..4N} (1 + r_i * 0.25)]^(1/N) - 1."""
    p = np.asarray(prices, dtype=float)
    if p.size == 0 or p.size % 4:
        raise ValueError("a bundle is a multiple of four quarterly prices")
    years = p.size // 4
    return float(np.prod(1.0 + (100.0 - p) / 100.0 * 0.25) ** (1.0 / years) - 1.0)


def ccp_switch_cost(basis_bp: float, notional: float, tenor_years: float) -> float:
    """Undiscounted cost of paying a CCP basis over the life of a swap: basis x notional x tenor.
    Excludes discounting, initial-margin funding and fees (see references/package-economics.md)."""
    return basis_bp * 1e-4 * notional * tenor_years


def breakeven_basis_bp(total_cost: float, notional: float, tenor_years: float) -> float:
    """Basis (bp) at which the undiscounted basis income equals the total cost stack."""
    return total_cost * 1e4 / (notional * tenor_years)


def fill_annual(par: pd.Series) -> tuple[pd.Series, bool]:
    """Linearly interpolate par rates (percent) to every integer year from 1 to the longest tenor.

    par: index = integer years (must include 1). Returns (filled series, whether anything was interpolated).
    Interpolation is an approximation: the bootstrapped annuity is only as good as the par curve between nodes.
    """
    years = np.asarray(par.index, dtype=int)
    if years.min() != 1:
        raise ValueError("the curve must include the 1Y par rate")
    full = np.arange(1, years.max() + 1)
    filled = np.interp(full, years, np.asarray(par, dtype=float))
    return pd.Series(filled, index=full), len(full) != len(years)


def _read_table(path: str) -> pd.DataFrame:
    if str(path).lower().endswith(".parquet"):
        try:
            return pd.read_parquet(path)
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise SystemExit("reading parquet needs pyarrow or fastparquet") from exc
    return pd.read_csv(path, dtype=str)


def load_par(path: str, curve_id: str, date: str, snap: str) -> tuple[pd.Series, bool]:
    """Read annual par rates (percent) from a curve_par CSV or Parquet, spot start, integer-year tenors.

    Returns (par by integer year 1..N, whether any years were interpolated).
    """
    df = _read_table(path)
    dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    m = ((df["curve_id"].astype(str) == curve_id) & (dates == date) & (df["snap"].astype(str) == snap)
         & (df["start"].astype(str) == "0D") & df["tenor"].astype(str).str.fullmatch(r"\d+Y"))
    sub = df.loc[m, ["tenor", "par_rate_pct"]].copy()
    if sub.empty:
        raise SystemExit(f"no curve_par rows for {curve_id} {date} {snap} spot-start annual tenors")
    sub["years"] = sub["tenor"].astype(str).str[:-1].astype(int)
    sub["par_rate_pct"] = sub["par_rate_pct"].astype(float)
    sub = sub.dropna(subset=["par_rate_pct"])  # a missing node is interpolated and flagged, never read as NaN
    if sub["years"].duplicated().any():
        raise SystemExit("duplicate curve_par rows for the same tenor; pick one source before sizing")
    par = sub.sort_values("years").set_index("years")["par_rate_pct"]
    return fill_annual(par)


def _cli_size(a) -> int:
    par, interpolated = load_par(a.curve, a.curve_id, a.date, a.snap)
    _, ann = annuity_from_par(par.to_numpy())
    tenors = [t.strip() for t in a.tenors.split(",")]
    years = [int(t[:-1]) for t in tenors]
    if any(b <= a for a, b in zip(years, years[1:])):
        raise SystemExit("--tenors must be strictly ascending (weights are assigned in ascending tenor order)")
    if max(years) > len(ann):
        raise SystemExit(f"requested {max(years)}Y but the curve only reaches {len(ann)}Y")
    pv01 = pd.Series([pv01_per_mm_from_annuity(ann[y - 1]) for y in years], index=tenors)
    out = size_package(pv01, a.structure, a.target_dv01, pay=a.pay)
    out.to_csv(sys.stdout, index=False, float_format="%.6f")
    note = "approximation: annual fixed, unit accrual, spot start"
    if interpolated:
        note += "; missing annual par tenors were linearly interpolated"
    print(f"# {note}; see script docstring", file=sys.stderr)
    return 0


def _cli_prices(a, fn) -> int:
    prices = [float(x) for x in a.prices.split(",")]
    print(f"{fn(prices) * 100:.6f}%")
    return 0


def _cli_switch(a) -> int:
    cost = ccp_switch_cost(a.basis_bp, a.notional, a.tenor)
    print(f"undiscounted basis cost: {cost:,.2f}")
    return 0


def selftest() -> int:
    """Known-answer checks. Returns the number of failures (0 = pass)."""
    fails = []

    def check(name, got, want, tol=1e-9):
        ok = abs(got - want) <= tol
        print(("PASS " if ok else "FAIL ") + f"{name}: got {got:.10g} want {want:.10g}")
        if not ok:
            fails.append(name)

    # Annuity and PV01 from a flat 5% annual par curve: DF_n = 1.05^-n, annuity_5 = (1-1.05^-5)/0.05.
    dfs, ann = annuity_from_par([5.0] * 5)
    check("DF_5 flat 5% par", dfs[4], 1.05 ** -5)
    check("annuity_5 flat 5% par", ann[4], (1 - 1.05 ** -5) / 0.05)
    check("PV01 per mm 5y flat 5%", pv01_per_mm_from_annuity(ann[4]), 100 * (1 - 1.05 ** -5) / 0.05, 1e-6)

    # Spread (receive 5s10s): long 10y leg carries target DV01, short 5y carries minus target.
    s = size_package(pd.Series([400.0, 800.0], index=["5Y", "10Y"]), "spread", 50000)
    check("spread 10y notional_mm", s.loc[1, "notional_mm"], 62.5)
    check("spread 5y notional_mm", s.loc[0, "notional_mm"], -125.0)
    check("spread DV01 sums to zero", s["dv01"].sum(), 0.0)

    # 50/50 fly, belly 5y DV01 = 50,000 (PV01 per mm 3y 274, 5y 482, 10y 903 from a cited source).
    f = size_package(pd.Series([274.0, 482.0, 903.0], index=["3Y", "5Y", "10Y"]), "fly", 50000)
    check("fly belly notional_mm = 50k/482", f.loc[1, "notional_mm"], 50000 / 482)
    check("fly 3y wing notional_mm = -25k/274", f.loc[0, "notional_mm"], -25000 / 274)
    check("fly 10y wing notional_mm = -25k/903", f.loc[2, "notional_mm"], -25000 / 903)
    check("fly DV01 sums to zero", f["dv01"].sum(), 0.0)
    check("fly wings equal DV01", f.loc[0, "dv01"], f.loc[2, "dv01"])

    # Condor and pascal must be DV01-neutral for any PV01s.
    c = size_package(pd.Series([100.0, 200.0, 300.0, 400.0], index=["2Y", "3Y", "4Y", "5Y"]), "condor", 1e4)
    check("condor DV01 sums to zero", c["dv01"].sum(), 0.0)
    for i, want in enumerate([-1e4, 1e4, 1e4, -1e4]):  # receive the inner pair, pay the wings
        check(f"condor leg {i} DV01 sign", c.loc[i, "dv01"], want)
    p = size_package(pd.Series([100.0, 200.0, 300.0, 400.0], index=["5Y", "6Y", "7Y", "8Y"]), "pascal", 1e4)
    check("pascal DV01 sums to zero", p["dv01"].sum(), 0.0)
    for i, want in enumerate([1e4 / 3, -1e4, 1e4, -1e4 / 3]):  # receive 6/7/8 fly, pay 5/6/7 fly
        check(f"pascal leg {i} DV01 sign", p.loc[i, "dv01"], want, 1e-6)

    # Gap interpolation: a linear par curve (4 + 0.1 y) is reproduced exactly between nodes 1, 2, 5, 10.
    nodes = pd.Series([4.1, 4.2, 4.5, 5.0], index=[1, 2, 5, 10])
    filled, was_filled = fill_annual(nodes)
    check("gap-filled 3Y par on linear curve", filled.loc[3], 4.3, 1e-12)
    check("gap-filled 7Y par on linear curve", filled.loc[7], 4.7, 1e-12)
    check("gap flag set when years were interpolated", float(was_filled), 1.0)

    # Pay direction flips every sign.
    pf = size_package(pd.Series([400.0, 800.0], index=["5Y", "10Y"]), "spread", 50000, pay=True)
    check("pay flips notional sign", pf.loc[1, "notional_mm"], -62.5)

    # DV01 match from a cited example: receive $100mm 25y (DV01 0.196), pay 30y (DV01 0.225).
    check("DV01-match 30y notional", dv01_match_notional(100.0, 0.196, 0.225), 100 * 0.196 / 0.225, 1e-9)

    # STIR pack and bundle. Equal prices give (1 + r/4)^4 - 1 exactly.
    check("pack equal prices 97.5", pack_yield([97.5] * 4), (1.00625 ** 4) - 1, 1e-12)
    check("bundle 2y equal prices 97.5", bundle_annualised([97.5] * 8), (1.00625 ** 4) - 1, 1e-12)
    # Cited worked values: pack 2.735%, 2y bundle 2.901%.
    check("pack cited 2.735%", pack_yield([97.49, 97.31, 97.21, 97.16]) * 100, 2.735, 5e-4)
    check("bundle cited 2.901%", bundle_annualised(
        [97.49, 97.31, 97.21, 97.16, 97.10, 97.00, 96.90, 96.87]) * 100, 2.901, 5e-4)

    # CCP switch: 1.2bp on $1bn over 5y is $600k undiscounted; 1.25bp on $100mm over 5y is $62.5k.
    check("switch cost 1.2bp $1bn 5y", ccp_switch_cost(1.2, 1e9, 5), 600000.0, 1e-6)
    check("switch cost 1.25bp $100mm 5y", ccp_switch_cost(1.25, 100e6, 5), 62500.0, 1e-6)
    check("breakeven basis round trip", breakeven_basis_bp(600000.0, 1e9, 5), 1.2, 1e-12)

    print("selftest OK" if not fails else f"selftest FAILED: {fails}")
    return len(fails)


def main() -> int:
    if "--selftest" in sys.argv:
        return 1 if selftest() else 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sz = sub.add_parser("size", help="DV01-neutral legs from a curve_par CSV")
    sz.add_argument("--curve", required=True)
    sz.add_argument("--curve-id", required=True)
    sz.add_argument("--date", required=True)
    sz.add_argument("--snap", required=True)
    sz.add_argument("--tenors", required=True, help="comma list of ascending tenors, e.g. 3Y,5Y,10Y")
    sz.add_argument("--structure", required=True, choices=sorted(WEIGHTS))
    sz.add_argument("--target-dv01", type=float, required=True, help="$/bp of the largest-weight leg")
    sz.add_argument("--pay", action="store_true", help="pay instead of receive")
    pk = sub.add_parser("pack", help="pack yield from four quarterly prices")
    pk.add_argument("--prices", required=True)
    bd = sub.add_parser("bundle", help="bundle annualised yield from 4N quarterly prices")
    bd.add_argument("--prices", required=True)
    sw = sub.add_parser("switch", help="undiscounted CCP basis cost")
    sw.add_argument("--basis-bp", type=float, required=True)
    sw.add_argument("--notional", type=float, required=True)
    sw.add_argument("--tenor", type=float, required=True)
    a = ap.parse_args()
    if a.cmd == "size":
        return _cli_size(a)
    if a.cmd == "pack":
        return _cli_prices(a, pack_yield)
    if a.cmd == "bundle":
        return _cli_prices(a, bundle_annualised)
    return _cli_switch(a)


if __name__ == "__main__":
    sys.exit(main())
