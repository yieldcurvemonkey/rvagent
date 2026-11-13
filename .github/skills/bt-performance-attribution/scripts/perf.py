#!/usr/bin/env python3
"""Performance metrics and P&L-explain helpers for RV backtests.

Self-contained (numpy / pandas only). Conventions: P&L in currency, rates in bp. A "delta" or risk vector S below is
the P&L per +1bp rate move, so S = -dv01_ccy when DV01 is signed positive for long duration (receive fixed / long bond).
Gamma is the change of that delta per bp: positive for receivers / long bonds.

CLI:
    python perf.py tearsheet pnl.csv [--strategy ID] [--package ALL] [--periods 252] [--capital 1e8]
    python perf.py --selftest
`pnl.csv` / `.parquet` follows the canonical `pnl` table: date, strategy_id, package_id, mtm_ccy, carry_ccy,
financing_ccy, cost_ccy, total_ccy.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

PNL_PARTS = ["mtm_ccy", "carry_ccy", "financing_ccy", "cost_ccy"]


# ---------------------------------------------------------------- risk-adjusted metrics
def sharpe(r, periods: int = 252, rf: float = 0.0) -> float:
    """Annualised Sharpe = mean(r - rf)/std(r, ddof=1) * sqrt(periods). rf per period; 0 for unfunded swaps/futures.
    Assumes serially uncorrelated returns; periods = real number of observations per year (252 daily, 12 monthly)."""
    x = np.asarray(pd.Series(r).dropna(), float) - rf
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    return float("nan") if sd == 0 else float(x.mean() / sd * np.sqrt(periods))


def sharpe_se(sr_annual: float, n_obs: int, periods: int = 252) -> float:
    """Standard error of an annualised Sharpe, iid returns: sqrt((1 + SR_p^2/2)/T) * sqrt(periods), SR_p per period."""
    if n_obs < 2:
        return float("nan")
    sr_p = sr_annual / np.sqrt(periods)
    return float(np.sqrt((1 + sr_p ** 2 / 2) / n_obs) * np.sqrt(periods))


def sortino(r, periods: int = 252, mar: float = 0.0) -> float:
    """Annualised mean excess over MAR / downside deviation, deviation = sqrt(mean(min(r - mar, 0)^2)) over ALL obs."""
    x = np.asarray(pd.Series(r).dropna(), float) - mar
    if len(x) == 0:
        return float("nan")
    dd = np.sqrt(np.mean(np.minimum(x, 0.0) ** 2))
    return float("nan") if dd == 0 else float(x.mean() / dd * np.sqrt(periods))


def hit_rate(r) -> float:
    """#positive / (#total - #flat)."""
    x = pd.Series(r).dropna()
    x = x[x != 0]
    return float("nan") if len(x) == 0 else float((x > 0).mean())


def drawdown(pnl) -> pd.DataFrame:
    """Drawdown of a cumulative-P&L path (additive, ccy). Columns: cum, hwm, dd (<= 0), uw (consecutive periods
    under water, 0 at a new high). HWM starts at 0 (the starting equity). A NaN P&L day counts as 0 (path continues).
    For compounded returns use cum=(1+r).cumprod()-1 and dd=(1+cum)/(1+hwm)-1 (<= 0, loss from peak) instead."""
    cum = pd.Series(pnl, dtype=float).fillna(0.0).cumsum()
    hwm = cum.cummax().clip(lower=0.0)
    dd = cum - hwm
    uw = (dd < 0).astype(int)
    uw = uw.groupby((uw == 0).cumsum()).cumsum()
    return pd.DataFrame({"cum": cum, "hwm": hwm, "dd": dd, "uw": uw})


def max_drawdown(pnl) -> tuple[float, int]:
    """(max drawdown as a negative ccy number, longest time under water in periods)."""
    d = drawdown(pnl)
    if d.empty:
        return float("nan"), 0
    return float(d["dd"].min()), int(d["uw"].max())


def calmar(pnl, periods: int = 252) -> float:
    """Annualised mean P&L / |max drawdown| (same currency units)."""
    mdd, _ = max_drawdown(pnl)
    return float("nan") if (mdd == 0 or np.isnan(mdd)) else float(pd.Series(pnl).mean() * periods / abs(mdd))


def return_concentration(r) -> float:
    """HHI concentration of positive returns h+ in [0,1] (0 = uniform, 1 = one return makes all the profit)."""
    x = np.asarray(pd.Series(r).dropna(), float)
    x = x[x > 0]
    n = len(x)
    if n < 2:
        return float("nan")
    w = x / x.sum()
    return float((np.sum(w ** 2) - 1.0 / n) / (1.0 - 1.0 / n))


def nonparam_sharpe(r) -> float:
    """Median / inter-quartile range (per period): robust to fat tails; compare with the parametric Sharpe."""
    x = pd.Series(r).dropna()
    iqr = x.quantile(0.75) - x.quantile(0.25)
    return float("nan") if iqr == 0 else float(x.median() / iqr)


# ---------------------------------------------------------------- P&L explain helpers
def pnl_component_split(pnl: pd.DataFrame, tol: float = 0.01) -> pd.Series:
    """Sum canonical pnl components; raises if total_ccy != mtm + carry + financing + cost on any row.
    Returns totals plus carry share of |gross| = |carry| / (|mtm|+|carry|+|financing|+|cost|)."""
    gap = (pnl["total_ccy"] - pnl[PNL_PARTS].sum(axis=1, skipna=False)).abs()
    bad = ~(gap <= tol)  # NaN in any part or in the total also counts as a break
    if bad.any():
        raise ValueError(f"{int(bad.sum())} rows break total = mtm + carry + financing + cost")
    s = pnl[PNL_PARTS + ["total_ccy"]].sum()
    s["carry_share_of_gross"] = abs(s["carry_ccy"]) / pnl[PNL_PARTS].abs().sum().sum()
    return s


def taylor_pnl(delta, dr, gamma=None) -> float:
    """First/second-order explain: sum_j delta_j*dr_j + 0.5*sum_jk gamma_jk*dr_j*dr_k. delta per bp, dr in bp.
    gamma may be a scalar/vector (diagonal) or a matrix (cross-gamma). Result in the delta's currency."""
    d, x = np.atleast_1d(np.asarray(delta, float)), np.atleast_1d(np.asarray(dr, float))
    out = float(d @ x)
    if gamma is not None:
        g = np.asarray(gamma, float)
        out += 0.5 * (float(x @ g @ x) if g.ndim == 2 else float(np.sum(g * x * x)))
    return out


def explain_residual(actual, components) -> dict:
    """Residual = actual - sum(components) (per row). ratio = sum|residual| / sum|gross|, gross = sum|actual|.
    Acceptance used in this skill: ratio <= 0.10 on the full run, and no persistent sign in the residual mean."""
    a = np.asarray(actual, float)
    res = a - np.sum([np.asarray(c, float) for c in components], axis=0)
    return {"residual": res, "ratio": float(np.abs(res).sum() / np.abs(a).sum()), "mean": float(res.mean())}


def sequential_bond_explain(p_start, p_aged, p_actual_curve, p_end, cash) -> dict:
    """Sequential repricing (Tuckman & Serrat): carry-roll-down = aged - start (same spread, scenario curve);
    rates = actual-curve - aged (same spread); spread = end - actual-curve; cash carry = coupons/financing.
    Prices per 100, DIRTY (full) prices, cash = coupons received in the window minus financing. With CLEAN prices add the
    change in accrued interest to cash. total = p_end - p_start + cash."""
    c = {"carry_roll_down": p_aged - p_start, "rates": p_actual_curve - p_aged, "spread": p_end - p_actual_curve,
         "cash_carry": cash}
    c["total"] = sum(c.values())
    return c


def change_basis(S, dr, T) -> tuple[np.ndarray, np.ndarray]:
    """Transform risk S' = T S and moves dr' = T^{-T} dr so that S'.dr' == S.dr (invertible square T). For a non-square
    T the pseudo-inverse is used and S'.dr' is only an approximation (exact when dr lies in the row space of T).
    Never combine transformed risk with the *real* moves of the new basis."""
    T = np.asarray(T, float)
    return T @ np.asarray(S, float), np.linalg.pinv(T).T @ np.asarray(dr, float)


def pc_attribution(S, dr, E) -> pd.DataFrame:
    """Per-PC P&L for linear risk S (ccy/bp) and raw (non-demeaned) bp moves dr. E = orthonormal eigenvector matrix
    (columns = PCs, rows = instruments, estimated on bp changes). pc_pnl_i = (E'S)_i * (E'dr)_i; sums to S.dr."""
    E = np.asarray(E, float)
    S, dr = np.asarray(S, float), np.asarray(dr, float)
    risk, move = E.T @ S, E.T @ dr
    out = pd.DataFrame({"pc_risk": risk, "pc_move": move, "pc_pnl": risk * move}, index=range(1, len(risk) + 1))
    out.index.name = "pc"
    return out


# ---------------------------------------------------------------- tearsheet
def tearsheet(pnl, periods: int = 252, capital: float | None = None) -> pd.Series:
    """Headline stats for a total-P&L series (ccy), NaN days dropped. With `capital`, Sharpe etc. use r = pnl/capital."""
    p = pd.Series(pnl, dtype=float).dropna().reset_index(drop=True)
    r = p / capital if capital else p
    mdd, tuw = max_drawdown(p)
    return pd.Series({
        "n_obs": len(p), "total_pnl": p.sum(), "ann_mean": r.mean() * periods, "ann_vol": r.std(ddof=1) * np.sqrt(periods),
        "sharpe": sharpe(r, periods), "sharpe_se": sharpe_se(sharpe(r, periods), len(p), periods),
        "sortino": sortino(r, periods), "max_dd_ccy": mdd, "max_tuw_periods": tuw, "calmar": calmar(p, periods),
        "hit_rate": hit_rate(p), "skew": float(r.skew()), "excess_kurt": float(r.kurt()),
        "nonparam_sharpe_per_period": nonparam_sharpe(r), "h_plus": return_concentration(p),
    })


def _load(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith((".parquet", ".pq")) else pd.read_csv(path)


# ---------------------------------------------------------------- self-test
def _close(a, b, tol=1e-9, msg="", atol=1e-12):
    if not np.isclose(a, b, rtol=tol, atol=atol):
        raise AssertionError(f"{msg}: got {a!r}, expected {b!r}")


def selftest() -> None:
    # 1. Sharpe on [1..5]: mean 3, sd sqrt(2.5) -> 3/1.5811388 * sqrt(252)
    _close(sharpe([1, 2, 3, 4, 5]), 3 / np.sqrt(2.5) * np.sqrt(252), msg="sharpe")
    # 2. SE: SR_p = 0.1, T = 100 -> sqrt((1+0.005)/100)
    _close(sharpe_se(0.1 * np.sqrt(252), 100), np.sqrt(1.005 / 100) * np.sqrt(252), msg="sharpe_se")
    # 3. Sortino: r=[2,-1,3,-3]: downside dev sqrt((1+9)/4), mean 0.25
    _close(sortino([2, -1, 3, -3], periods=1), 0.25 / np.sqrt(2.5), msg="sortino")
    # 4. Drawdown of cum path 5,3,8,2,6 (pnl 5,-2,5,-6,4): max dd -6 from HWM 8; under water 2 periods at the end
    _close(max_drawdown([5, -2, 5, -6, 4])[0], -6.0, msg="max dd")
    assert max_drawdown([5, -2, 5, -6, 4])[1] == 2, "time under water"
    # start below zero: first loss counts against the starting equity
    _close(max_drawdown([-3, 1])[0], -3.0, msg="dd from start")
    # 5. hit rate ignores flat days
    _close(hit_rate([1, -1, 0, 0, 2]), 2 / 3, msg="hit rate")
    # 6. HHI: uniform = 0, one dominant -> near 1, exact value for [1,1,2]: w=[.25,.25,.5]
    _close(return_concentration([1, 1, 1, 1]), 0.0, msg="hhi uniform")
    _close(return_concentration([1, 1, 2]), (0.375 - 1 / 3) / (1 - 1 / 3), msg="hhi")
    # 7. Taylor, single 10y IRS (Darbyshire, Coding Interest Rates, Ex 12.2): 841.37*10 + 0.5*100*(-0.86)
    _close(taylor_pnl([841.37], [10.0], [-0.86]), 8370.70, tol=1e-9, msg="taylor")
    # 7b. Taylor residual on a one-cashflow bond PV = exp(-r t): third-order only (-t^3/6 e^{-rt} dr^3)
    t, r0, dr = 10.0, 0.035, 1e-4  # 1bp
    pv = lambda r: np.exp(-r * t)
    delta, gam = -t * pv(r0) * 1e-4, t * t * pv(r0) * 1e-8  # per bp
    full = pv(r0 + dr) - pv(r0)
    ex = explain_residual([full], [[taylor_pnl([delta], [1.0], [gam])]])
    _close(ex["residual"][0], -(t ** 3) / 6 * pv(r0) * dr ** 3, tol=1e-3, atol=0.0, msg="taylor residual")  # ~1e-10: relative test only
    # 7c. matrix and diagonal gamma: 1*3+2*4 = 11; 0.5*(2*9 + 2*1*12 + 4*16) = 53 -> 64; diagonal 0.5*(2*9+4*16) = 41 -> 52
    _close(taylor_pnl([1, 2], [3, 4], [[2, 1], [1, 4]]), 64.0, msg="cross-gamma")
    _close(taylor_pnl([1, 2], [3, 4], [2, 4]), 52.0, msg="diag gamma")
    # 7d. residual ratio: actual [10,-10], buckets [6,-6]+[3,-3] -> residual [1,-1], ratio 2/20
    ex2 = explain_residual([10, -10], [[6, -6], [3, -3]])
    _close(ex2["ratio"], 0.1, msg="resid ratio"), _close(ex2["mean"], 0.0, msg="resid mean")
    # 7e. calmar: pnl 5,-2,5,-6,4 -> mean 1.2, max dd 6 -> 0.2 ; non-parametric: [1..5] median 3, IQR 2 -> 1.5
    _close(calmar([5, -2, 5, -6, 4], periods=1), 0.2, msg="calmar")
    _close(calmar([5, -2, 5, -6, 4], periods=10), 2.0, msg="calmar annualised")
    _close(nonparam_sharpe([1, 2, 3, 4, 10]), 1.5, msg="nonparam")  # median, not mean, over IQR
    # 7f. short / NaN histories do not crash; a NaN day does not reset time under water
    assert np.isnan(sharpe([1.0])) and np.isnan(max_drawdown([])[0]) and np.isnan(sharpe_se(1.0, 1))
    assert max_drawdown([5, -2, np.nan, -1, 4])[1] == 3, "NaN day must not reset time under water"
    # 8. Sequential bond explain (Tuckman & Serrat, UST 7.625s of 11/15/22, Tables 3.6-3.8)
    c = sequential_bond_explain(114.87654, 111.11555, 111.29847, 111.39690, 3.81250)
    _close(c["carry_roll_down"], -3.76099, tol=1e-5, msg="crd")
    _close(c["rates"], 0.18292, tol=1e-5, msg="rates")
    _close(c["spread"], 0.09843, tol=1e-5, msg="spread")
    _close(c["total"], 0.33286, tol=1e-5, msg="total")
    # 9. Basis change invariance: swap-spread trade, DV01 bond +102, swap -99; moves +2, +1.7 -> P&L 35.7 in 3 bases
    S, dr_ = np.array([102.0, -99.0]), np.array([2.0, 1.7])
    _close(S @ dr_, 35.7, tol=1e-9, msg="outright pnl")
    S2, d2 = change_basis(S, dr_, [[1, 0], [1, 1]])  # swap spread + swap
    _close(S2[0], 102.0), _close(S2[1], 3.0)
    _close(d2[0], 0.3), _close(d2[1], 1.7)
    _close(S2 @ d2, 35.7, tol=1e-9, msg="swap-spread basis pnl")
    S3, d3 = change_basis(S, dr_, [[1, 1], [0, -1]])  # swap spread + bond: risk [3; 99], moves [2; 0.3]
    _close(S3[0], 3.0), _close(S3[1], 99.0), _close(d3[0], 2.0), _close(d3[1], 0.3)
    _close(S3 @ d3, 35.7, tol=1e-9, msg="spread+bond pnl")
    # 9b. non-square (Darbyshire Ex 10.6): A=1Y..4Y, B=1Y,4Y. True 53.6; pseudo-inverse moves ~(1.9, 2.6), P&L ~55.5-56.7 (closer than reverse 63.8)
    SB, dB = change_basis([5, 7, 8, 4], [2.0, 2.0, 2.2, 3.0], [[1, .33, .11, 0], [0, .67, .89, 1]])
    assert np.abs(dB - [1.9, 2.6]).max() < 0.1 and 55 < SB @ dB < 57, "pinv transformed moves"
    # 10. PC attribution: risk proportional to PC1 -> PC risk [c,0,..]; per-PC P&L sums to S.dr for ANY orthonormal E
    rng = np.random.default_rng(7)
    load = np.array([200, 320, 420, 430, 410, 400, 410.0])
    A = np.column_stack([load] + [rng.normal(size=7) for _ in range(6)])
    E, _ = np.linalg.qr(A)
    E[:, 0] *= np.sign(E[:, 0] @ load)  # QR may flip sign
    c1 = 1000.0
    Sx = c1 * E[:, 0]
    mv = rng.normal(size=7) * 3
    pa = pc_attribution(Sx, mv, E)
    _close(pa["pc_risk"].iloc[0], c1, tol=1e-9, msg="pc1 risk")
    assert np.abs(pa["pc_risk"].iloc[1:]).max() < 1e-9, "other PC risks must be 0"
    _close(pa["pc_pnl"].sum(), Sx @ mv, tol=1e-9, msg="pc pnl sum")
    # 11. Component split catches a broken identity
    df = pd.DataFrame({"mtm_ccy": [100.0, -50.0], "carry_ccy": [10.0, 10.0], "financing_ccy": [-5.0, -5.0],
                       "cost_ccy": [-1.0, 0.0]})
    df["total_ccy"] = df[PNL_PARTS].sum(axis=1)
    s = pnl_component_split(df)
    _close(s["total_ccy"], 59.0, msg="split total")
    df.loc[1, "total_ccy"] += 5
    for bad_df in (df, (lambda d: d.assign(total_ccy=d[PNL_PARTS].sum(axis=1)))(df.assign(carry_ccy=[np.nan, 10.0]))):
        try:
            pnl_component_split(bad_df)
        except ValueError:
            continue
        raise AssertionError("identity break (or NaN component) not detected")
    # 12. tearsheet runs and Sharpe matches the direct call
    x = pd.Series(rng.normal(0.2, 1.0, 500))
    _close(tearsheet(x)["sharpe"], sharpe(x), msg="tearsheet")
    print("selftest OK")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("tearsheet", help="headline stats + component split from a canonical pnl table")
    t.add_argument("path")
    t.add_argument("--strategy")
    t.add_argument("--package", default="ALL")
    t.add_argument("--periods", type=int, default=252)
    t.add_argument("--capital", type=float, default=None, help="denominator for returns; omit to use ccy P&L")
    a = ap.parse_args(argv)
    if a.selftest:
        try:
            selftest()
        except AssertionError as e:
            print(f"SELFTEST FAILED: {e}", file=sys.stderr)
            return 1
        return 0
    if a.cmd == "tearsheet":
        df = _load(a.path)
        if a.strategy:
            df = df[df["strategy_id"] == a.strategy]
        if not a.strategy and df["strategy_id"].nunique() > 1:
            print("several strategy_id values in file: pass --strategy", file=sys.stderr)
            return 2
        df = df[df["package_id"] == a.package].sort_values("date")
        if df.empty:
            print("no rows for that strategy/package", file=sys.stderr)
            return 2
        print(tearsheet(df["total_ccy"], a.periods, a.capital).to_string())
        print(pnl_component_split(df).to_string())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
