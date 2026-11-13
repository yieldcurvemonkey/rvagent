#!/usr/bin/env python3
"""Repo and funding arithmetic for G10 rates RV.

Covers act/360 repo cash and interest, haircuts, specialness, implied repo (IRR) from
the basis net of carry, a synthetic term-repo cost, a compounded SOFR-style index,
the SOFR-minus-FF sign from futures prices, and the repo-funded capital hurdle.

Units: rates in percent per annum (4.25 = 4.25%), spreads in bp, futures prices per
100 face (price = 100 - rate), money in currency units, durations in days.

Library use: import the functions (scalars or numpy arrays work for the arithmetic).
CLI use:     python scripts/repo_funding_math.py specialness --csv PATH
             python scripts/repo_funding_math.py --selftest
"""
from __future__ import annotations

import argparse
import sys

BASIS = 360.0  # USD money-market day count (act/360); pass basis=365.0 for act/365 conventions


def repurchase_amount(cash, repo_pct, days, basis=BASIS):
    """Repurchase price of a repo: cash * (1 + r * d / basis)."""
    return cash * (1.0 + repo_pct / 100.0 * days / basis)


def repo_interest(market_value, haircut_frac, repo_pct, days, basis=BASIS):
    """Interest on cash lent against collateral: MV * (1 - h) * r * d / basis."""
    return market_value * (1.0 - haircut_frac) * repo_pct / 100.0 * days / basis


def repo_rate_pct(invoice, repurchase, days, basis=BASIS):
    """Repo rate from the invoice (cash) and repurchase amounts: (P_rp - P_cash)/P_cash * basis/d."""
    return (repurchase - invoice) / invoice * basis / days * 100.0


def haircut_split(market_value, haircut_frac):
    """Return (cash lent, margin held back) for collateral at market value with haircut h."""
    cash = market_value * (1.0 - haircut_frac)
    return cash, market_value - cash


def specialness_bp(gc_pct, special_pct):
    """Specialness in bp = (GC - special repo) * 100. Positive when the bond is special."""
    return (gc_pct - special_pct) * 100.0


def specialness_drag(notional, gc_pct, special_pct, years=1.0):
    """Annual cost of shorting a special: notional * (GC - special) / 100 * years."""
    return notional * (gc_pct - special_pct) / 100.0 * years


def implied_repo_pct(ctd_term_repo_pct, bnoc_px, dirty_px, days, basis=BASIS):
    """Implied repo (IRR) = CTD term repo - BNOC / dirty * basis / n.

    bnoc_px: basis net of carry in price points per 100 face (same units as dirty_px).
    days: calendar days from settlement to the assumed delivery date.
    """
    return ctd_term_repo_pct - bnoc_px / dirty_px * basis / days * 100.0


def bnoc_from_irr(term_repo_pct, irr_pct, dirty_px, days, basis=BASIS):
    """Inverse of implied_repo_pct: BNOC implied by an IRR and a term repo rate."""
    return (term_repo_pct - irr_pct) / 100.0 * dirty_px * days / basis


def synthetic_term_cost_pct(ois_fixed_pct, gc_minus_effr_avg_bp):
    """Cost of a synthetic term repo: pay fixed OIS, fund at GC.

    Cost = OIS fixed + average(GC - EFFR). If GC averages 8bp below EFFR, cost = OIS - 0.08.
    """
    return ois_fixed_pct + gc_minus_effr_avg_bp / 100.0


def compound_index_step(index_prev, rate_pct, days, basis=BASIS):
    """One step of a compounded overnight index: I_t = I_{t-1} * (1 + r * d / basis)."""
    return index_prev * (1.0 + rate_pct / 100.0 * days / basis)


def sofr_index_interest(principal, index_start, index_end):
    """Interest earned on a compounded index: principal * (I_end / I_start - 1)."""
    return principal * (index_end / index_start - 1.0)


def term_rate_pct(index_start, index_end, days, basis=BASIS):
    """Simple-equivalent term rate from two index levels: (I_end/I_start - 1) * basis / D."""
    return (index_end / index_start - 1.0) * basis / days * 100.0


def futures_basis_bp(sofr1m_px, ff30d_px):
    """1M SOFR future price minus 30-day fed funds future price in bp. Equals -(SOFR - EFFR) in bp, so a positive value means SOFR priced below EFFR."""
    return (sofr1m_px - ff30d_px) * 100.0


def sofr_minus_ff_bp_from_futures(sofr1m_px, ff30d_px):
    """Realised-equivalent SOFR minus EFFR (bp) implied by the two futures prices."""
    return (ff30d_px - sofr1m_px) * 100.0


def capital_hurdle_pnl(notional, leverage_ratio, roce, years):
    """Minimum P&L for a repo-funded position: LR * notional * RoCE * years."""
    return notional * leverage_ratio * roce * years


def capital_cost_basis_bp(g, q, d):
    """Unsecured-minus-secured O/N basis from capital cost: g * q * d, in bp.

    g = cost of equity, q = BIS risk weight of the interbank exposure, d = capital ratio.
    """
    return g * q * d * 1.0e4


# ---------------------------------------------------------------- self-test

def _check(label, got, want, tol, failures):
    ok = abs(got - want) <= tol
    print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got:.6f}, want {want:.6f} (tol {tol})")
    if not ok:
        failures.append(label)


def selftest():
    f = []
    # Repo loan: 109,898,438 for 44 days at 0.015% repays 109,900,452 (Tuckman & Serrat 2022, Ch.10).
    _check("repurchase 44d @0.015%", repurchase_amount(109_898_438, 0.015, 44), 109_900_452, 1.0, f)
    # Same collateral at 3% haircut: cash 106,601,485, margin 3,296,953 (Tuckman & Serrat 2022, Ch.10).
    cash, margin = haircut_split(109_898_438, 0.03)
    _check("haircut 3% cash", cash, 106_601_485, 1.0, f)
    _check("haircut 3% margin", margin, 3_296_953, 1.0, f)
    # Invoice 101,000,000 repurchased at 101,000,280.56 next day = 0.1% (Huggins & Schaller 2022, Intro).
    _check("repo rate from invoice", repo_rate_pct(101_000_000, 101_000_280.56, 1), 0.1, 1e-4, f)
    # Interest on 100 dirty, 1% haircut, 2% repo, 30 days = 99 * 0.02 * 30/360 = 0.165.
    # (The source prints 0.166; the arithmetic gives 0.165.)
    _check("repo interest 100/1%/2%/30d", repo_interest(100.0, 0.01, 2.0, 30), 0.165, 1e-9, f)
    # SOFR Index interest: USD 1mm, 15-Sep-21 to 15-Dec-21 earns 82.78 (Huggins & Schaller 2022, Ch.3).
    _check("SOFR index interest", sofr_index_interest(1_000_000, 1.04227169, 1.04235797), 82.78, 0.01, f)
    # Specialness: GC 5%, special 3% -> 200bp; short $100mm 5s drags $2mm a year.
    _check("specialness bp", specialness_bp(5.0, 3.0), 200.0, 1e-9, f)
    _check("specialness drag", specialness_drag(100e6, 5.0, 3.0), 2_000_000.0, 1e-6, f)
    # Implied repo: BNOC 0 gives IRR = term repo; BNOC 0.25 on dirty 100 over 90 days shaves 1.0%.
    _check("IRR with zero BNOC", implied_repo_pct(3.5, 0.0, 100.0, 90), 3.5, 1e-12, f)
    _check("IRR with BNOC 0.25, 90d", implied_repo_pct(3.5, 0.25, 100.0, 90), 2.5, 1e-9, f)
    _check("BNOC round trip", bnoc_from_irr(3.5, 2.5, 100.0, 90), 0.25, 1e-9, f)
    # Synthetic term repo: 1y OIS 0.45% with GC 8bp under EFFR gives 0.37% (Credit Suisse 2010).
    _check("synthetic term repo", synthetic_term_cost_pct(0.45, -8.0), 0.37, 1e-9, f)
    # Futures sign: SOFR 4.00 vs FF 3.85 is realised +15bp, futures basis -15bp (Conks 2026 example).
    _check("realised SOFR-FF from futures", sofr_minus_ff_bp_from_futures(96.00, 96.15), 15.0, 1e-9, f)
    _check("futures basis sign", futures_basis_bp(96.00, 96.15), -15.0, 1e-9, f)
    # Capital hurdle: $100mm for 3m at 3% LR and 10% RoCE needs 75,000; at 6% LR it needs 150,000
    # (Quantitative Finance Stack Exchange, 6 Apr 2019).
    _check("hurdle 3% LR", capital_hurdle_pnl(100e6, 0.03, 0.10, 0.25), 75_000.0, 1e-6, f)
    _check("hurdle 6% LR", capital_hurdle_pnl(100e6, 0.06, 0.10, 0.25), 150_000.0, 1e-6, f)
    # Capital cost basis: g=10%, q=20%, d=8% gives 16bp (Huggins & Schaller 2024, Ch.11).
    _check("g*q*d basis bp", capital_cost_basis_bp(0.10, 0.20, 0.08), 16.0, 1e-9, f)
    # Compounding: one-day step recovers r exactly; 91 daily steps at 4% beat the simple 4% (compounding > simple).
    _check("term rate one-day step", term_rate_pct(1.0, compound_index_step(1.0, 4.25, 1), 1), 4.25, 1e-9, f)
    idx = 1.0
    for _ in range(91):
        idx = compound_index_step(idx, 4.0, 1)
    _check("91d compounded vs closed form", idx, (1 + 0.04 / 360) ** 91, 1e-12, f)
    _check("91d simple-equivalent rate", term_rate_pct(1.0, idx, 91), ((1 + 0.04 / 360) ** 91 - 1) * 360 / 91 * 100, 1e-9, f)
    print("PASS" if not f else f"FAILED: {len(f)} check(s)")
    return 0 if not f else 1


# ---------------------------------------------------------------- CLI

def _specialness_csv(path):
    try:
        import pandas as pd
    except ImportError:
        print("pandas is required for the specialness command", file=sys.stderr)
        return 2
    df = pd.read_csv(path)
    need = {"collateral", "term", "rate_pct", "gc_rate_pct"}
    if not need <= set(df.columns):
        print(f"missing columns: {sorted(need - set(df.columns))}", file=sys.stderr)
        return 2
    if "data_ok" in df.columns:  # drop rows the adapter flagged bad (never average them in)
        df = df[df["data_ok"].astype(str).str.lower().isin(["true", "1"])]
    df = df.dropna(subset=["rate_pct", "gc_rate_pct"])
    if df.empty:
        print("no usable rows (check data_ok and missing rates)", file=sys.stderr)
        return 2
    df["specialness_bp"] = (df["gc_rate_pct"] - df["rate_pct"]) * 100.0
    out = df.groupby(["collateral", "term"])["specialness_bp"].agg(["mean", "max", "count"])
    print(out.round(2).to_string())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    sub = ap.add_subparsers(dest="cmd")
    sp = sub.add_parser("specialness", help="specialness_bp summary from a repo_rates CSV")
    sp.add_argument("--csv", required=True, help="canonical repo_rates CSV path")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.cmd == "specialness":
        return _specialness_csv(args.csv)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
