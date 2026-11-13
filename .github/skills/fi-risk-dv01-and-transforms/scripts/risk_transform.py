"""Risk-strip transforms for a rates book: Jacobian change of basis, re-bucketing, hedge mapping, CoVaR and
VaR-minimising hedges, second-order P&L explain.

Conventions
    S   risk strip = DV01 per bucket, currency per bp, POSITIVE = long duration (gains when that rate falls).
    dr  rate moves in bp. Linear P&L = -S.dr ; second order adds +0.5 dr' G dr (G = d2P/dr2 per bp^2).
    J   Jacobian from basis A to basis B: J[i, j] = d r_A[j] / d r_B[i].
        Risk:  S_B = J @ S_A.   Moves: dr_B = pinv(J).T @ dr_A, so S_B.dr_B = S_A.dr_A (P&L invariant).
    H   hedge matrix: column j = DV01 strip of ONE unit of hedge instrument j on the same buckets as S.
    Q   covariance of daily bp changes of the bucket rates (bp^2). CoVaR multiplier c = sqrt(S' Q S).
All maps are linear, so they work for either DV01 sign convention as long as S and H share it.

CLI (risk ladder CSV: columns tenor, dv01_ccy; covariance from the canonical `curve_par` table):
    python risk_transform.py --risk ladder.csv --curve-par curve_par.parquet --curve-id USD-SOFR \
        --snap eod_ny --lookback 250 --hedge-tenors 2Y,5Y,10Y,30Y --out risk_usd
    python risk_transform.py --risk ladder.csv --rebucket 2Y,5Y,10Y,30Y
    python risk_transform.py --selftest

Library helpers (import or copy): bond_dv01 (central-difference DV01 of a fixed-coupon bond), bootstrap_annual and
par_partials (par-swap key-rate DV01s of any fixed cash-flow stream by bump-and-reprice).
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd

Z99, Z95 = 2.326, 1.645  # one-sided normal quantiles used for VaR from c


# ---------------------------------------------------------------- basis changes
def transform_risk(S, J):
    """S_B = J S_A (J[i, j] = d r_A[j] / d r_B[i])."""
    return np.asarray(J, float) @ np.asarray(S, float)


def transform_moves(dr, J):
    """dr_B = pinv(J)^T dr_A: the moves that keep linear P&L identical in basis B."""
    return np.linalg.pinv(np.asarray(J, float)).T @ np.asarray(dr, float)


def par_to_fwd_jacobian(annuity):
    """Par -> consecutive-forward risk Jacobian from par analytic deltas (annuities) A_1 < A_2 < ...

    Pricing identity R_j A_j = sum_{i<=j} F_i a_i with forward annuities a_i = A_i - A_{i-1}, so
    d R_j / d F_i = a_i / A_j for i <= j, else 0. Returns J with S_fwd = J @ S_par (upper triangular).
    Holds annuities fixed (first-order); use numeric bumps when dates misalign or the curve is far from flat.
    """
    A = np.asarray(annuity, float)
    a = np.diff(np.r_[0.0, A])
    n = len(A)
    return np.array([[a[i] / A[j] if i <= j else 0.0 for j in range(n)] for i in range(n)])


def tenor_years(t: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([DWMY])", str(t).strip().upper())
    if not m:
        raise ValueError(f"bad tenor {t!r}")
    return float(m.group(1)) * {"D": 1 / 365, "W": 7 / 365, "M": 1 / 12, "Y": 1.0}[m.group(2)]


def linear_rebucket(from_years, to_years):
    """M (len(to) x len(from)): each source bucket split linearly between the two adjacent target pillars,
    100% to the end pillar outside the range. Columns sum to 1, so total DV01 is preserved."""
    f, t = np.asarray(from_years, float), np.asarray(to_years, float)
    M = np.zeros((len(t), len(f)))
    for j, x in enumerate(f):
        if x <= t[0]:
            M[0, j] = 1.0
        elif x >= t[-1]:
            M[-1, j] = 1.0
        else:
            k = np.searchsorted(t, x) - 1
            w = (t[k + 1] - x) / (t[k + 1] - t[k])
            M[k, j], M[k + 1, j] = w, 1.0 - w
    return M


# ---------------------------------------------------------------- hedges and VaR
def hedge_exact(S, H):
    """Notionals n with S + H n = 0 (square H) or least-squares residual (non-square). Returns (n, residual strip)."""
    S, H = np.asarray(S, float), np.asarray(H, float)
    n = np.linalg.lstsq(H, -S, rcond=None)[0]
    return n, S + H @ n


def covar(S, Q):
    """CoVaR multiplier c = sqrt(S'QS) (1-sd daily P&L) and Euler allocation diag(S) Q S / c (sums to c)."""
    S, Q = np.asarray(S, float), np.asarray(Q, float)
    c = float(np.sqrt(S @ Q @ S))
    return c, S * (Q @ S) / c if c > 0 else np.zeros_like(S)


def varmin_hedge(S, Q, H):
    """Hedge notionals minimising (S + Hn)' Q (S + Hn): n = -(H'QH)^-1 H'QS. Returns (n, post-hedge strip, c_after).
    With H = unit vectors on buckets h this is the bucket-restricted solution -Q_hh^-1 Q_h. S."""
    S, Q, H = np.asarray(S, float), np.asarray(Q, float), np.asarray(H, float)
    n = -np.linalg.solve(H.T @ Q @ H, H.T @ Q @ S)
    post = S + H @ n
    return n, post, float(np.sqrt(post @ Q @ post))


def single_trades(S, Q):
    """Best single-bucket VaR-minimising trade per bucket, -(QS)_i / Q_ii, and the c after each (one at a time)."""
    S, Q = np.asarray(S, float), np.asarray(Q, float)
    t = -(Q @ S) / np.diag(Q)
    after = []
    for i in range(len(S)):
        s2 = S.copy()
        s2[i] += t[i]
        after.append(float(np.sqrt(s2 @ Q @ s2)))
    return t, np.array(after)


def pnl_explain(S, dr, G=None):
    """Second-order P&L: -S.dr + 0.5 dr'G dr (S = DV01 long-positive, dr and G in bp)."""
    dr = np.asarray(dr, float)
    out = -float(np.asarray(S, float) @ dr)
    return out + (0.5 * float(dr @ np.asarray(G, float) @ dr) if G is not None else 0.0)


# ---------------------------------------------------------------- DV01 and par-rate partials
def bond_price(y_pct, coupon_pct, years, freq=2):
    """Clean-on-coupon-date price per 100 face of a fixed bond at yield y (percent, freq-times compounding)."""
    n, y = int(round(years * freq)), y_pct / 100.0 / freq
    k = np.arange(1, n + 1)
    return float(np.sum(coupon_pct / freq / (1 + y) ** k) + 100.0 / (1 + y) ** n)


def bond_dv01(y_pct, coupon_pct, years, freq=2, bump_bp=1.0):
    """DV01 per 100 face per bp, positive for a long: -(P(y+h) - P(y-h)) / (2h) with h in bp (central difference)."""
    h = bump_bp / 100.0
    return -(bond_price(y_pct + h, coupon_pct, years, freq) - bond_price(y_pct - h, coupon_pct, years, freq)) / (2 * bump_bp)


def bootstrap_annual(par_pct):
    """Discount factors d_1..d_N from annual-pay par swap rates (percent) for EVERY year 1..N:
    d_n = (1 - R_n * sum_{i<n} d_i) / (1 + R_n)."""
    d = []
    for r in np.asarray(par_pct, float) / 100.0:
        d.append((1.0 - r * sum(d)) / (1.0 + r))
    return np.array(d)


def par_partials(times, cfs, node_years, node_pct, bump_bp=1.0):
    """Key-rate (par-swap partial) DV01 of a fixed cash-flow stream, per bp, positive = long duration.

    Par curve = linear interpolation of node_pct between node_years (flat beyond), annual pay; bump ONE node by
    +-bump_bp, re-bootstrap, revalue (central difference). Sum of partials = parallel DV01. A near-par instrument
    maturing on a node shows risk only there; between nodes the split depends on the interpolation.
    """
    times, cfs = np.asarray(times, float), np.asarray(cfs, float)
    yrs = np.arange(1, int(np.ceil(max(max(times), max(node_years)))) + 1)

    def pv(nodes):
        d = bootstrap_annual(np.interp(yrs, node_years, nodes))
        return float(np.sum(cfs * np.interp(times, np.r_[0, yrs], np.r_[1.0, d])))  # ponytail: DF interpolated linearly between integer years

    base, out = np.asarray(node_pct, float), []
    for j in range(len(base)):
        up, dn = base.copy(), base.copy()
        up[j] += bump_bp / 100.0
        dn[j] -= bump_bp / 100.0
        out.append(-(pv(up) - pv(dn)) / (2 * bump_bp))
    return np.array(out)


# ---------------------------------------------------------------- canonical data
def read_table(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if str(path).lower().endswith((".parquet", ".pq")) else pd.read_csv(path)


def cov_from_curve_par(df, curve_id, tenors, lookback=250, snap=None):
    """Q (bp^2) of daily changes of spot-starting par rates (curve_par.par_rate_pct is percent -> x100)."""
    d = df[(df["curve_id"] == curve_id) & (df["start"].astype(str) == "0D")]
    if "data_ok" in d:
        d = d[d["data_ok"].fillna(True).astype(bool)]
    if snap is not None:
        d = d[d["snap"] == snap]
    elif "snap" in d and d["snap"].nunique() > 1:
        raise SystemExit("several snaps in curve_par: pass --snap (never mix snaps in one series)")
    wide = d.pivot_table(index="date", columns="tenor", values="par_rate_pct").sort_index()
    missing = [t for t in tenors if t not in wide.columns]
    if missing:
        raise SystemExit(f"tenors missing from curve_par: {missing}")
    chg = wide[list(tenors)].diff().dropna().tail(lookback) * 100.0
    if len(chg) < 20:
        raise SystemExit(f"only {len(chg)} complete daily changes in curve_par for {list(tenors)}: cannot estimate Q")
    if len(chg) < 100:
        print(f"warning: only {len(chg)} daily changes (>= 100 recommended)", file=sys.stderr)
    return chg.cov().to_numpy(), len(chg)


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    ok = True

    def check(name, got, want, tol):
        nonlocal ok
        good = np.allclose(np.asarray(got, float), np.asarray(want, float), atol=tol, rtol=0)
        ok &= bool(good)
        print(f"{'ok  ' if good else 'FAIL'} {name}: got {np.round(got, 4)} want {want}")

    # 1. Invariance of S.dr under a change of basis (Stack Exchange swap-spread example, source sign: S.dr = P&L).
    #    Outright (bond, swap) -> (bond-swap spread, swap). Sign-free: in house signs flip S and P&L = -S.dr.
    S, dr = np.array([102.0, -99.0]), np.array([2.0, 1.7])
    T = np.array([[1.0, 0.0], [1.0, 1.0]])
    check("swap-spread risk", transform_risk(S, T), [102, 3], 1e-12)
    check("swap-spread moves", transform_moves(dr, T), [0.3, 1.7], 1e-12)
    check("S.dr invariant", transform_risk(S, T) @ transform_moves(dr, T), 35.7, 1e-9)
    check("per-coordinate parts", transform_risk(S, T) * transform_moves(dr, T), [30.6, 5.1], 1e-9)
    # 2. Darbyshire PTIRD Ex 10.1: par (1Y,2Y,3Y) -> forwards (0Y1Y,1Y1Y,2Y1Y).
    J = np.array([[1, 0.513, 0.346], [0, 0.487, 0.329], [0, 0, 0.325]])
    check("par->fwd Ex 10.1", transform_risk([-820, -1100, 4000], J), [0, 780, 1300], 1.0)
    # 2b. Trader-model coordinates (Darbyshire Ex 16.3): S = (2Y -65, 5Y 100, 10Y -15) = (2Y 20, 2s5s 85, 5s10s -15)
    #     = (2Y -15, 2s5s10s 50, 10Y 35); unit strips are the columns of U, coordinates c = U^-1 S, J = U^-1.
    S3 = [-65.0, 100.0, -15.0]
    U1 = np.array([[1, -1, 0], [0, 1, -1], [0, 0, 1]], float)  # columns 2Y, 2s5s (-1,+1,0), 5s10s (0,-1,+1)
    U2 = np.array([[1, -1, 0], [0, 2, 0], [0, -1, 1]], float)  # columns 2Y, 2s5s10s (-1,+2,-1), 10Y
    check("trader model 2Y/2s5s/5s10s", transform_risk(S3, np.linalg.inv(U1)), [20, 85, -15], 1e-9)
    check("trader model 2Y/2s5s10s/10Y", transform_risk(S3, np.linalg.inv(U2)), [-15, 50, 35], 1e-9)
    # 3. Par->fwd Jacobian from analytic deltas (Darbyshire Ex 10.4/10.5): 0.51 = 0.988/1.956, 0.48 (printed 0.47) = 4.296/9.043,
    #    inverse -1.02 = -0.988/0.968, 2.10 = 9.043/4.296.
    Jpf = par_to_fwd_jacobian([0.988, 1.956, 4.747, 9.043])
    check("J par->fwd entries", [Jpf[0, 1], Jpf[3, 3]], [0.988 / 1.956, 4.296 / 9.043], 1e-12)
    Jinv = np.linalg.inv(Jpf)
    check("J fwd->par entries", [Jinv[0, 1], Jinv[1, 1], Jinv[3, 3]], [-0.988 / 0.968, 1.956 / 0.968, 9.043 / 4.296],
          1e-9)
    s_par = np.array([-11.0, 87.0, 36.0, -266.0])
    check("par->fwd->par round trip", Jinv @ (Jpf @ s_par), s_par, 1e-9)
    # 4. Linear re-bucketing 5..10y -> 5/7/10y (QFSE "PCA and risk bucketing" matrix).
    M = linear_rebucket([5, 6, 7, 8, 9, 10], [5, 7, 10])
    check("rebucket matrix", M, [[1, .5, 0, 0, 0, 0], [0, .5, 1, 2 / 3, 1 / 3, 0], [0, 0, 0, 1 / 3, 2 / 3, 1]], 1e-12)
    check("rebucket preserves total", M.sum(axis=0), np.ones(6), 1e-12)
    # 5. VaR-min proxy hedge, Darbyshire PTIRD Ex 21.9: c 133,153 -> 101,958 trading only the two 3M buckets.
    Q = np.array([[30.3, 13.1, 0.29, 0.16], [13.1, 8.41, 0.09, 0.10], [0.29, 0.09, 0.16, 0.07],
                  [0.16, 0.10, 0.07, 0.05]])
    S = np.array([-4000.0, -18000.0, -110000.0, -290000.0])
    c, alloc = covar(S, Q)
    check("CoVaR c", c, 133153, 1.0)
    check("allocation sums to c", alloc.sum(), c, 1e-6)
    n, post, c2 = varmin_hedge(S, Q, np.eye(4)[:, :2])
    check("VaR-min trade", n, [5790, 19838], 1.0)
    check("VaR-min c after", c2, 101958, 1.0)
    t, after = single_trades(S, Q)
    n1, _, c1 = varmin_hedge(S, Q, np.eye(4)[:, [0]])
    check("single trade = 1-col VaR-min", [t[0], after[0]], [n1[0], c1], 1e-6)
    # 6. Exact hedge with a full-rank hedge matrix leaves zero residual; par hedges are diagonal.
    H = np.array([[0.98, 0.10, 0.0], [0.0, 1.94, 0.3], [0.0, 0.0, 4.61]])
    n, res = hedge_exact([0.03, 0.11, 0.54], H)
    check("exact hedge residual", res, [0, 0, 0], 1e-12)
    # 7. Second-order P&L, Darbyshire CIR Ex 12.2: paid 10Y EUR IRS 1mm, delta 841.37 (payer) -> DV01 -841.37,
    #    gamma -0.86 per bp^2, +10bp -> 8,370.70.
    check("delta+gamma P&L", pnl_explain([-841.37], [10.0], [[-0.86]]), 8370.70, 1e-6)
    # 8. Units: par rates in percent, daily +/-0.01 -> 1bp changes -> variance ~1 bp^2.
    dates = pd.date_range("2024-01-01", periods=301, freq="B")
    lvl = 3.0 + 0.01 * (np.arange(301) % 2)
    df = pd.DataFrame({"date": np.repeat(dates, 2), "curve_id": "X", "start": "0D", "snap": "eod_ny",
                       "tenor": np.tile(["2Y", "10Y"], 301), "par_rate_pct": np.repeat(lvl, 2)})
    Qs, nobs = cov_from_curve_par(df, "X", ["2Y", "10Y"], lookback=250)
    check("cov units bp^2", [Qs[0, 0], Qs[0, 1], nobs], [250 / 249, 250 / 249, 250], 1e-9)
    # 9. DV01 by central difference (Coleman 2011: 10y 3.5% bond at par, prices 99.1664 / 100.8417, DV01 8.38/100bp
    #    i.e. 0.0838 per bp) and the closed form for a par bond (Tuckman: (1/(100 y))[1-(1+y/2)^-2T]).
    check("Coleman bond DV01 per bp", bond_dv01(3.5, 3.5, 10), 0.0838, 5e-5)
    check("par bond closed form", bond_dv01(3.5, 3.5, 10), (1 / (100 * 0.035)) * (1 - 1.0175 ** -20), 1e-6)
    # 10. Par partials, known answers (integer-year nodes, so no interpolation ambiguity).
    yrs, flat = np.arange(1, 11), np.full(10, 3.0)
    d = bootstrap_annual(flat)
    check("bootstrap flat curve", d, 1.03 ** -yrs, 1e-12)
    bond5 = np.r_[np.full(4, 3.0), 103.0]  # 3% 5y annual bond = the 5y par swap: risk only at the 5y node = annuity x 1bp
    pp = par_partials(np.arange(1, 6), bond5, yrs, flat)
    check("par bond: partials only at own node", pp, np.r_[np.zeros(4), d[:5].sum() * 0.01, np.zeros(5)] * 1.0, 1e-6)
    z10 = par_partials([10], [100.0], yrs, flat)
    check("10y zero: sum of partials = parallel DV01", z10.sum(), 10 * 100 / 1.03 ** 11 * 1e-4, 1e-6)
    check("10y zero: negative partials at short nodes, positive at 10y",
          [float(z10[:9].max() < 0), float(z10[9] > z10.sum())], [1.0, 1.0], 0)
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--risk", help="CSV with columns tenor, dv01_ccy (par-rate bucket DV01, long-duration positive)")
    p.add_argument("--rebucket", help="comma list of target pillars, e.g. 2Y,5Y,10Y,30Y (linear split)")
    p.add_argument("--curve-par", help="canonical curve_par table (csv/parquet) for the covariance")
    p.add_argument("--curve-id")
    p.add_argument("--snap")
    p.add_argument("--lookback", type=int, default=250, help="daily changes used for Q (default 250 = 1y)")
    p.add_argument("--hedge-tenors", help="buckets allowed for the VaR-min hedge, e.g. 2Y,5Y,10Y,30Y")
    p.add_argument("--out", help="output prefix for CSVs")
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.risk:
        p.error("--risk is required (or --selftest)")
    lad = read_table(a.risk)
    tenors, S = list(lad["tenor"].astype(str)), lad["dv01_ccy"].to_numpy(float)
    order = np.argsort([tenor_years(t) for t in tenors])
    tenors, S = [tenors[i] for i in order], S[order]
    print(f"total DV01 {S.sum():,.0f} | gross {np.abs(S).sum():,.0f} | buckets {len(S)}")
    if a.rebucket:
        tgt = sorted(a.rebucket.split(","), key=tenor_years)
        M = linear_rebucket([tenor_years(t) for t in tenors], [tenor_years(t) for t in tgt])
        tenors, S = tgt, M @ S
        print("re-bucketed (linear):", {t: float(x) for t, x in zip(tenors, np.round(S, 0))})
    table = pd.DataFrame({"tenor": tenors, "dv01_ccy": S})
    if a.curve_par:
        if not a.curve_id:
            p.error("--curve-id is required with --curve-par")
        Q, nobs = cov_from_curve_par(read_table(a.curve_par), a.curve_id, tenors, a.lookback, a.snap)
        c, alloc = covar(S, Q)
        print(f"c (1-sd daily P&L) {c:,.0f} | VaR95 {Z95 * c:,.0f} | VaR99 {Z99 * c:,.0f} | {nobs} daily changes")
        t, after = single_trades(S, Q)
        table = table.assign(var_alloc_ccy=alloc, best_single_trade_dv01=t, c_after_single=after,
                             c_cut_pct=100 * (1 - after / c))
        if a.hedge_tenors:
            hs = a.hedge_tenors.split(",")
            bad = [h for h in hs if h not in tenors]
            if bad:
                p.error(f"--hedge-tenors not in the risk ladder buckets: {bad}")
            idx = [tenors.index(h) for h in hs]
            n, post, c2 = varmin_hedge(S, Q, np.eye(len(S))[:, idx])
            print(f"VaR-min hedge on {hs}: trades {dict(zip(hs, (float(x) for x in np.round(n, 0))))} | c {c:,.0f} -> {c2:,.0f} "
                  f"({100 * (1 - c2 / c):.1f}% cut)")
            table["post_hedge_dv01"] = post
    print(table.round(2).to_string(index=False))
    if a.out:
        table.to_csv(f"{a.out}_risk.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
