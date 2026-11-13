#!/usr/bin/env python3
"""Balance-sheet hurdle arithmetic for G10 rates RV (swap spreads, cash-futures basis, repo, haircuts).

Functions (numbers / numpy / pandas in, numbers / pandas out):
  haircut_cost_bp       running cost of a repo haircut: haircut_frac * excess funding cost (bp p.a.).
  widener_economics     swap-spread widener (long bond in repo + pay fixed swap): carry, leverage exposure,
                        ROE and the breakeven spread for a target ROE at a given leverage ratio (SLR/LR).
  basis_lr_hurdle       minimum net basis (price points per 100 face) a leverage-ratio-bound desk needs.
  capital_basis_bp      secured-unsecured basis from capital costs: L - R (Huggins & Schaller).
  saccr_ir_ead          SA-CCR exposure at default for a list of IR swaps (leverage exposure of derivatives).

Conventions: rates in pct (4.25 = 4.25%), spreads in bp, fractions as decimals (0.02 = 2%).
Swap spread = swap rate - govt yield (US convention, negative when swaps trade below govts). Rows stored
govt_minus_swap (EGB ASW convention) are negated before use. A widener earns -spread as carry.

CLI:
  python balance_sheet_hurdles.py widener --swap-spreads swap_spreads.parquet --ccy USD --curve-id USD-SOFR \
      --measure spread_mm --float-pct 3.90 --repo-pct 3.95 --fund-pct 4.40 --haircut 0.02 --im 0.04 \
      --pfe 0.015 --slr 0.05 --target-roe 0.15 [--repo repo_rates.parquet] [--out out.csv]
      (--repo: per date, takes ON GC rate_pct and the median haircut_frac for --ccy, overriding the flags)
  python balance_sheet_hurdles.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


def haircut_cost_bp(haircut_frac, excess_funding_bp):
    """Running yield cost (bp p.a.) of funding a haircut at `excess_funding_bp` over the repo rate."""
    return np.asarray(haircut_frac, float) * np.asarray(excess_funding_bp, float)


def widener_economics(spread_bp, float_pct, repo_pct, fund_pct, haircut=0.0, im=0.0, pfe=0.0,
                      slr=0.05, target_roe=0.15, tax=0.0):
    """Per unit of bond notional, one-year hold (Boyarchenko et al., FRBNY EPR 2018, Tables 1-3).

    carry_bp  = float - (1 - h)*repo - (h + im)*fund - spread       (all bp p.a.)
    exposure  = 1 + h + im + pfe        (gross bond + haircut + IM receivable + PFE add-on, per unit notional)
    equity    = slr * exposure
    roe       = carry * (1 - tax) / equity
    breakeven = spread at which roe == target_roe
    """
    f, r, u = (np.asarray(x, float) * 100.0 for x in (float_pct, repo_pct, fund_pct))
    base = f - (1.0 - haircut) * r - (haircut + im) * u            # carry before the spread, bp
    spread = np.asarray(spread_bp, float)
    carry = base - spread
    equity = slr * (1.0 + haircut + im + pfe)
    roe = carry / 1e4 * (1.0 - tax) / equity
    breakeven = base - target_roe * equity * 1e4 / (1.0 - tax)
    return {"carry_bp": carry, "exposure": 1.0 + haircut + im + pfe, "equity_frac": equity, "roe": roe,
            "breakeven_bp": breakeven, "cushion_bp": breakeven - spread}


def basis_lr_hurdle(lr=0.03, roce=0.10, days=90, day_basis=360):
    """Net basis (price points per 100 face) needed to pay for leverage capital over `days`.

    A long or short basis position adds its gross bond (or reverse repo) notional to leverage exposure.
    """
    return 100.0 * lr * roce * days / day_basis


def capital_basis_bp(R_pct, q, d, g_pct, b_pct, p=0.0, c=0.0):
    """Secured-unsecured basis L - R in bp (Huggins & Schaller).

    L = [R + p(1-c) + q*d*(g - b)] / (1 - p(1-c)); R secured rate, p PD, c recovery, q risk weight,
    d capital ratio, g cost of equity, b marginal cost of funds. All rates as decimals internally.
    """
    R, g, b = R_pct / 100.0, g_pct / 100.0, b_pct / 100.0
    k = p * (1.0 - c)
    L = (R + k + q * d * (g - b)) / (1.0 - k)
    return (L - R) * 1e4


def _mf(row):
    if row.get("mf") is not None and not pd.isna(row.get("mf")):
        return float(row["mf"])
    return {"cleared": 0.175, "collateralised": 0.25}.get(row.get("margin", "cleared"), 1.0)


def saccr_ir_ead(trades: pd.DataFrame, rc=0.0, alpha=1.4):
    """SA-CCR EAD for IR derivatives (Darbyshire, Ch.17.3 simplification).

    trades columns: hedging_set (e.g. 'USD-SOFR'), start_y, end_y (years, >= 0), notional, direction (+1 pay
    fixed / long rate risk, -1 receive), optional margin ('cleared', 'collateralised', 'uncollateralised') or mf.
    AN = N * (exp(-0.05 S) - exp(-0.05 E)) / 0.05; buckets <1y, 1-5y, >5y by end date;
    PFE_set = 0.5% * sqrt(E1^2 + E2^2 + E3^2 + 1.4 E1E2 + 1.4 E2E3 + 0.6 E1E3); EAD = alpha * (RC + sum PFE).
    """
    t = trades.copy()
    s, e = t["start_y"].clip(lower=0).astype(float), t["end_y"].clip(lower=0).astype(float)
    t["an"] = t["notional"] * (np.exp(-0.05 * s) - np.exp(-0.05 * e)) / 0.05
    t["mf_"] = t.apply(_mf, axis=1)
    short_unc = (t.get("margin", pd.Series("cleared", index=t.index)) == "uncollateralised") & (e < 1)
    t.loc[short_unc, "mf_"] = np.sqrt(e[short_unc])
    t["bucket"] = np.select([e < 1, e <= 5], [1, 2], 3)
    t["eff"] = t["direction"] * t["an"] * t["mf_"]
    pfe = 0.0
    for _, g in t.groupby("hedging_set"):
        E = g.groupby("bucket")["eff"].sum().reindex([1, 2, 3], fill_value=0.0).to_numpy()
        pfe += 0.005 * np.sqrt(max(E @ E + 1.4 * E[0] * E[1] + 1.4 * E[1] * E[2] + 0.6 * E[0] * E[2], 0.0))
    return alpha * (rc + pfe)


def _read(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def run_widener(a):
    ss = _read(a.swap_spreads)
    ss = ss[(ss["ccy"] == a.ccy) & (ss["measure"] == a.measure)]
    if a.curve_id:
        ss = ss[ss["curve_id"] == a.curve_id]
    if "data_ok" in ss:
        ss = ss[ss["data_ok"].fillna(True).astype(bool)]
    if ss.empty:
        sys.exit("no swap_spreads rows match --ccy/--measure/--curve-id")
    sign = np.where(ss["sign_convention"] == "govt_minus_swap", -1.0, 1.0)
    ss = ss.assign(spread_bp=sign * ss["value_bp"])
    ss["repo_pct"], ss["haircut"] = a.repo_pct, a.haircut
    if a.repo:
        rp = _read(a.repo)
        rp = rp[(rp["ccy"] == a.ccy) & (rp["term"] == "ON") & rp["collateral"].astype(str).str.startswith("GC")]
        by = rp.groupby("date").agg(repo_pct=("rate_pct", "median"),
                                    haircut=("haircut_frac", "median") if "haircut_frac" in rp else ("rate_pct", "size"))
        if "haircut_frac" not in rp:
            by["haircut"] = np.nan
        ss = ss.drop(columns=["repo_pct", "haircut"]).merge(by, left_on="date", right_index=True, how="left")
        ss["repo_pct"] = ss["repo_pct"].fillna(a.repo_pct)
        ss["haircut"] = ss["haircut"].fillna(a.haircut)
    rows = []
    for _, r in ss.iterrows():
        w = widener_economics(r["spread_bp"], a.float_pct, r["repo_pct"], a.fund_pct, r["haircut"], a.im, a.pfe,
                              a.slr, a.target_roe, a.tax)
        rows.append({"date": r["date"], "ref": r["ref"], "spread_bp": r["spread_bp"], "repo_pct": r["repo_pct"],
                     "haircut_frac": r["haircut"], "carry_bp": float(w["carry_bp"]), "roe": float(w["roe"]),
                     "breakeven_bp": float(w["breakeven_bp"]), "cushion_bp": float(w["cushion_bp"])})
    out = pd.DataFrame(rows).sort_values(["date", "ref"])
    out.to_csv(a.out, index=False) if a.out else print(out.round(4).to_string(index=False))


def selftest():
    ok = True

    def check(label, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {label}: got {got:.4f} want {want} (tol {tol})")

    # 1. FRBNY EPR 2018 Table 1: carry before spread $27,490 on $10mm; spread -10bp -> $37,490.
    #    Inputs: Libor 0.6%, repo 0.3%, unsecured 0.5%, haircut 2.8%, IM 3.9%. PFE $600 per 1% SLR -> 0.006.
    kw = dict(float_pct=0.6, repo_pct=0.3, fund_pct=0.5, haircut=0.028, im=0.039, pfe=0.006)
    w = widener_economics(-10.0, slr=0.01, **kw)
    check("FRBNY carry $ on 10mm at -10bp", float(w["carry_bp"]) * 1e3, 37490.0, 0.5)
    # 2. FRBNY Table 2 ROE at SLR 1..6%: 35/17/12/9/7/6 % (rounded).
    for slr, want in zip(range(1, 7), [35, 17, 12, 9, 7, 6]):
        check(f"FRBNY ROE at SLR {slr}%", 100 * float(widener_economics(-10.0, slr=slr / 100, **kw)["roe"]), want, 0.6)
    #    Table 2 total equity (exact): 107,300 at SLR 1% and 643,800 at 6% on $10mm.
    for slr, want in [(0.01, 107300.0), (0.06, 643800.0)]:
        check(f"FRBNY Table 2 equity at SLR {slr:.0%}",
              float(widener_economics(-10.0, slr=slr, **kw)["equity_frac"]) * 1e7, want, 1e-6)
    # 3. FRBNY Table 3 breakevens reproduce within ~1bp (paper's Table 3 inputs are not fully stated).
    for roe, slr, want in [(0.15, 0.05, -54), (0.30, 0.06, -166), (0.05, 0.01, 21), (0.20, 0.04, -59)]:
        check(f"FRBNY breakeven ROE {roe:.0%} SLR {slr:.0%}",
              float(widener_economics(0.0, slr=slr, target_roe=roe, **kw)["breakeven_bp"]), want, 1.5)
    # 4. TBAC Feb 2021: 5% LR, >12% after-tax RoE, Libor-repo 15bp, 20% tax -> spread < -60bp (exact).
    check("TBAC breakeven", float(widener_economics(0.0, 0.15, 0.0, 0.0, slr=0.05, target_roe=0.12,
                                                    tax=0.20)["breakeven_bp"]), -60.0, 1e-9)
    # 5. Huggins & Schaller: 2% haircut funded 500bp over SOFR -> 10bp on 5Y UST SOFR-ASW.
    check("haircut cost 2% x 500bp", float(haircut_cost_bp(0.02, 500)), 10.0, 1e-12)
    # 6. QFSE: 3% (6%) LR, 10% RoCE, 3m -> 7.5 (15) cents per 100 face.
    check("basis hurdle LR 3%", basis_lr_hurdle(0.03, 0.10, 90) * 100, 7.5, 1e-9)
    check("basis hurdle LR 6%", basis_lr_hurdle(0.06, 0.10, 90) * 100, 15.0, 1e-9)
    # 7. Huggins & Schaller SOFR book: p=0, q=20%, d=8%: L-R = 1.6% x (g-b); g-b = 5% -> 8bp.
    check("capital basis 1.6% x 5%", capital_basis_bp(2.0, 0.20, 0.08, 10.0, 5.0), 8.0, 1e-9)
    # 7b. credit term, analytic: R=2%, p=1%, c=40%, no capital charge -> L=(0.02+0.006)/0.994.
    check("capital basis credit term", capital_basis_bp(2.0, 0.0, 0.0, 10.0, 5.0, p=0.01, c=0.4),
          (0.026 / 0.994 - 0.02) * 1e4, 1e-9)
    # 8. SA-CCR: one cleared 0x10y swap, N=100: AN=100(1-e^-0.5)/0.05=786.94; E3=0.175 AN; EAD=1.4*0.005*E3.
    tr = pd.DataFrame({"hedging_set": ["USD"], "start_y": [0.0], "end_y": [10.0], "notional": [100.0],
                       "direction": [1], "margin": ["cleared"]})
    check("SA-CCR EAD single 10y", saccr_ir_ead(tr), 1.4 * 0.005 * 0.175 * 100 * (1 - np.exp(-0.5)) / 0.05, 1e-9)
    # offsetting pay/receive of the same trade in one hedging set nets to zero PFE
    tr2 = pd.concat([tr, tr.assign(direction=-1)])
    check("SA-CCR full offset", saccr_ir_ead(tr2), 0.0, 1e-12)
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("widener", help="ROE / breakeven of a swap-spread widener per date and tenor")
    w.add_argument("--swap-spreads", required=True, help="canonical swap_spreads CSV/Parquet")
    w.add_argument("--repo", help="canonical repo_rates CSV/Parquet (optional)")
    w.add_argument("--ccy", default="USD")
    w.add_argument("--curve-id")
    w.add_argument("--measure", default="spread_mm")
    w.add_argument("--float-pct", type=float, required=True, help="floating index rate received, pct")
    w.add_argument("--repo-pct", type=float, required=True, help="GC repo rate paid, pct")
    w.add_argument("--fund-pct", type=float, required=True, help="unsecured rate for haircut and IM, pct")
    w.add_argument("--haircut", type=float, default=0.02)
    w.add_argument("--im", type=float, default=0.04)
    w.add_argument("--pfe", type=float, default=0.015, help="PFE add-on per unit notional (Basel >5y IR: 1.5%%)")
    w.add_argument("--slr", type=float, default=0.05)
    w.add_argument("--target-roe", type=float, default=0.15)
    w.add_argument("--tax", type=float, default=0.0)
    w.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "widener":
        run_widener(a)


if __name__ == "__main__":
    main()
