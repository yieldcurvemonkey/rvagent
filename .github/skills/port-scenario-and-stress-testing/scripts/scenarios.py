#!/usr/bin/env python3
"""Scenario and stress P&L on a key-rate DV01 / gamma ladder.

Conventions: yield shocks in bp (+ = sell-off); dv01 in ccy per bp, positive = long duration (receive fixed);
gamma = d2P/dy2 in ccy per bp^2, positive = long convexity.  P&L = -dv01.shock + 0.5 shock' Gamma shock.

Functions take numpy arrays / pandas objects.  CLI reads canonical `curve_par` (CSV/Parquet) for history and a
ladder CSV (bucket, dv01_ccy[, gamma_ccy]).   python -I scripts/scenarios.py --selftest
"""
from __future__ import annotations

import argparse
import math
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm


# ------------------------------------------------------------------ shocks
def tenor_years(label: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([DWMY])", str(label).upper())
    if not m:
        raise ValueError(f"bad tenor {label!r}")
    return float(m.group(1)) * {"D": 1 / 365, "W": 7 / 365, "M": 1 / 12, "Y": 1.0}[m.group(2)]


def knot_shock(tenors_y, knot_t, knot_bp):
    """Piecewise-linear shock across tenors; flat beyond the outer knots (np.interp).
    parallel: knots [0,100],[x,x]; twist: [min,max],[short,long]; pivot twist: [min,pivot,max],[a,0,b]."""
    return np.interp(np.asarray(tenors_y, float), knot_t, knot_bp)


def citi7(tenors_y, size=50.0):
    """Seven-scenario template: forwards, +/-size parallel, bull/bear steepener/flattener (<=2y, 5y, >=10y knots)."""
    t, k = np.asarray(tenors_y, float), [2, 5, 10]
    s = size
    return {
        "up": knot_shock(t, k, [s, s, s]), "down": knot_shock(t, k, [-s, -s, -s]),
        "bull_steepener": knot_shock(t, k, [-s, -s / 2, 0]), "bull_flattener": knot_shock(t, k, [0, -s / 2, -s]),
        "bear_steepener": knot_shock(t, k, [0, s / 2, s]), "bear_flattener": knot_shock(t, k, [s, s / 2, 0]),
    }


def pca_loadings(changes_bp: pd.DataFrame, k: int = 3, demean: bool = False):
    """PCA of daily yield changes (bp). Returns (loadings n x k in bp per +1 SD of the PC, explained ratio, vals).
    Not demeaned by default (risk covariance). Signs: PC1 sum>0 (level up), PC2 last-first>0 (steepening),
    PC3 belly minus mean of wings >0 (belly up)."""
    x = changes_bp.dropna().to_numpy(float)
    x = x - x.mean(0) if demean else x
    cov = x.T @ x / len(x)
    w, v = np.linalg.eigh(cov)
    o = np.argsort(w)[::-1]
    w, v = w[o], v[:, o]
    n = v.shape[0]
    for j in range(min(k, n)):
        col = v[:, j]
        if j == 0:
            s = col.sum()
        elif j == 1:
            s = col[-1] - col[0]
        else:
            s = col[n // 2] - 0.5 * (col[0] + col[-1])
        if s < 0:
            v[:, j] = -col
    return v[:, :k] * np.sqrt(np.clip(w[:k], 0, None)), w[:k] / w.sum(), w


def pc_shock(loadings, sd):
    """Shock (bp) from PC moves given in SD units: loadings @ sd."""
    return np.asarray(loadings) @ np.asarray(sd, float)


# ------------------------------------------------------------------ P&L
def pnl(dv01, shock_bp, gamma=None):
    """Scenario P&L in ccy. shock_bp: (n,) or (m,n). gamma: (n,) diagonal or (n,n) incl. cross-gamma."""
    d = np.asarray(dv01, float)
    s = np.atleast_2d(np.asarray(shock_bp, float))
    out = -(s @ d)
    if gamma is not None:
        g = np.asarray(gamma, float)
        out = out + 0.5 * ((s * s) @ g if g.ndim == 1 else np.einsum("mi,ij,mj->m", s, g, s))
    return out if np.ndim(shock_bp) > 1 else float(out[0])


def window_shocks(levels_bp: pd.DataFrame, windows: dict) -> pd.DataFrame:
    """Historical replay shocks: level(end) - level(start) per bucket (uses last obs on or before each date)."""
    rows = {}
    for name, (a, b) in windows.items():
        lv = levels_bp.sort_index()
        if lv.loc[:a].empty or lv.loc[:b].empty:
            raise ValueError(f"window {name!r} starts before the first observation ({lv.index[0]})")
        rows[name] = lv.loc[:b].iloc[-1] - lv.loc[:a].iloc[-1]
    return pd.DataFrame(rows).T


def rolling_pnl(levels_bp: pd.DataFrame, dv01, h: int, gamma=None) -> pd.Series:
    """P&L of the book over every h-day window of history (overlapping)."""
    sh = levels_bp.diff(h).dropna()
    return pd.Series(pnl(dv01, sh.to_numpy(), gamma), index=sh.index)


def hist_var_es(pnl_series, alpha: float = 0.01):
    """Historical VaR (k-th worst) and ES (mean of k worst), k = ceil(alpha*n). Returns positive losses."""
    x = np.asarray(pnl_series, float)
    x = np.sort(x[~np.isnan(x)])
    if len(x) == 0:
        raise ValueError("no P&L observations")
    k = int(math.ceil(round(alpha * len(x), 9)))
    return float(-x[k - 1]), float(-x[:k].mean())


# ------------------------------------------------------------------ plausibility, covariance risk
def covar(S, Q, conf: float = 0.99):
    """Linear covariance VaR: c = sqrt(S'QS); VaR = Phi^-1(conf) c. Returns (c, VaR)."""
    S = np.asarray(S, float)
    c = float(np.sqrt(S @ np.asarray(Q, float) @ S))
    return c, c * norm.ppf(conf)


def var_allocation(S, Q):
    """Aumann-Shapley (Euler) contributions S_i (QS)_i / c; sum to c. Negative = bucket diversifies."""
    S = np.asarray(S, float)
    return S * (np.asarray(Q, float) @ S) / np.sqrt(S @ Q @ S)


def risk_cov(changes_bp: pd.DataFrame, horizon: int = 1) -> np.ndarray:
    """Un-demeaned covariance of daily bp changes (risk convention), scaled by horizon (sqrt-time: crude)."""
    x = changes_bp.dropna().to_numpy(float)
    return x.T @ x / len(x) * horizon


def sd_multiple(shock, cov):
    """BlackRock/Golub-Tilman: S = |z| / sigma(xi), xi = z/|z|, sigma^2(xi) = xi'cov xi."""
    z = np.asarray(shock, float)
    return float(z @ z / np.sqrt(z @ np.asarray(cov, float) @ z))


def scenario_z(shock, cov):
    """Mahalanobis MD, Z = MD/sqrt(n), volatility z V = sqrt(sum (z_i/sd_i)^2 / n), correlation z C = Z/V."""
    z = np.asarray(shock, float)
    cov = np.asarray(cov, float)
    n = len(z)
    md = float(np.sqrt(z @ np.linalg.pinv(cov) @ z))
    v = float(np.sqrt(np.sum((z / np.sqrt(np.diag(cov))) ** 2) / n))
    return {"MD": md, "Z": md / math.sqrt(n), "V": v, "C": (md / math.sqrt(n)) / v if v > 0 else float("nan")}


def conditional_shock(cov, core_idx, core_shock):
    """Shock the core factors; imply all others by regression: s = cov[:,c] cov[c,c]^-1 s_c (core kept as given)."""
    cov = np.asarray(cov, float)
    c = list(core_idx)
    s = cov[:, c] @ np.linalg.solve(cov[np.ix_(c, c)], np.asarray(core_shock, float))
    s[c] = core_shock
    return s


def reverse_stress(dv01, cov, md: float):
    """Worst linear-loss shock on the ellipsoid d'cov^-1 d = md^2: d* = md cov dv01 / c, loss = md*c, c = sqrt(dv01'cov dv01)."""
    d, cov = np.asarray(dv01, float), np.asarray(cov, float)
    c = float(np.sqrt(d @ cov @ d))
    return md * (cov @ d) / c, md * c


def implied_view(shocks, probs):
    """Ilmanen: scenario set -> implied mean shock, bp vol and correlation per bucket (probability-weighted)."""
    s, p = np.asarray(shocks, float), np.asarray(probs, float)
    p = p / p.sum()
    mu = p @ s
    dev = s - mu
    cov = (dev * p[:, None]).T @ dev
    sd = np.sqrt(np.diag(cov))
    return mu, sd, cov / np.outer(sd, sd)


def invariant_risk(J, H=None, p: float = 0.0, theta: float = 1.0) -> float:
    """Musaelian et al. E[dPi^2] for alpha_i iid N(0,1) (p=0), or mixed normal N(0,theta) w.p. p (all alphas jump).
    Returns the risk (sqrt) = sqrt((1+p(th^2-1))|J|^2 + (1+p(th^4-1))(|H|_F^2/2 + Tr(H)^2/4))."""
    J = np.asarray(J, float)
    lin = (1 + p * (theta ** 2 - 1)) * float(J @ J)
    quad = 0.0
    if H is not None:
        H = np.asarray(H, float)
        quad = (1 + p * (theta ** 4 - 1)) * (0.5 * float((H * H).sum()) + 0.25 * float(np.trace(H)) ** 2)
    return math.sqrt(lin + quad)


# ------------------------------------------------------------------ CLI
def _load(path):
    return pd.read_parquet(path) if str(path).endswith((".parquet", ".pq")) else pd.read_csv(path)


def levels_from_curve_par(df: pd.DataFrame, curve_id: str, buckets) -> pd.DataFrame:
    d = df[(df.curve_id == curve_id) & (df.start == "0D")]
    if "snap" in d and d.snap.nunique() > 1:
        raise SystemExit(f"curve_par has several snaps {sorted(d.snap.unique())}; filter to one snap first")
    d = d.assign(date=pd.to_datetime(d.date), bp=d.par_rate_pct * 100.0)
    lv = d.pivot_table(index="date", columns="tenor", values="bp").sort_index()
    miss = [b for b in buckets if b not in lv.columns]
    if miss:
        raise SystemExit(f"curve_par lacks tenors {miss} for {curve_id}")
    return lv[list(buckets)].dropna()


def run(ladder: pd.DataFrame, levels: pd.DataFrame, windows: dict, horizon: int = 21, lookback: int = 756,
        rev_z: float = 3.0) -> pd.DataFrame:
    b = list(ladder.bucket)
    t = np.array([tenor_years(x) for x in b])
    dv01 = ladder.dv01_ccy.to_numpy(float)
    gam = ladder.gamma_ccy.to_numpy(float) if "gamma_ccy" in ladder else None
    ch = levels.diff().dropna().tail(lookback)
    if len(ch) < max(100, len(t)):
        raise ValueError(f"only {len(ch)} daily changes; need >= max(100, n buckets)")
    cov = risk_cov(ch, horizon)  # un-demeaned, sqrt-time scaling: crude, see SKILL pitfalls
    L, expl, _ = pca_loadings(ch, 3)
    sc = {}
    for s in (25, 50, 100):
        sc[f"parallel+{s}"], sc[f"parallel-{s}"] = np.full(len(t), float(s)), np.full(len(t), -float(s))
    sc.update({f"citi7_{k}": v for k, v in citi7(t).items() if k not in ("up", "down")})
    for j, nm in enumerate(["PC1", "PC2", "PC3"]):
        for m in (-3, -2, 2, 3):
            sd = np.zeros(3)
            sd[j] = m
            sc[f"{nm}{m:+d}sd"] = pc_shock(L * math.sqrt(horizon), sd)  # horizon SD
    for name, row in window_shocks(levels, windows).iterrows():
        sc[f"window:{name}"] = row.to_numpy(float)
    md = rev_z * math.sqrt(len(t))
    sc[f"reverse_Z{rev_z:g}"], _ = reverse_stress(dv01, cov, md)
    rows = []
    for k, s in sc.items():
        z = scenario_z(s, cov)
        rows.append({"scenario": k, "pnl_ccy": pnl(dv01, s, gam), "Z": z["Z"], "C": z["C"],
                     "sd_multiple": sd_multiple(s, cov), **{f"d_{x}": v for x, v in zip(b, s)}})
    out = pd.DataFrame(rows).sort_values("pnl_ccy").reset_index(drop=True)
    out.attrs["pc_explained"] = [float(x) for x in expl]
    return out


# ------------------------------------------------------------------ selftest
def selftest() -> int:
    rng = np.random.default_rng(7)
    ok = True

    def chk(name, cond, info=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name, info)
        ok &= bool(cond)

    # 1 analytic P&L: long 100k/bp, +10bp -> -1,000,000; +0.5*gamma*dy^2 with gamma 2,000/bp^2 -> +100,000
    chk("pnl linear", abs(pnl([100e3], [10]) + 1e6) < 1e-6)
    chk("pnl gamma", abs(pnl([100e3], [10], [2000.0]) - (-1e6 + 1e5)) < 1e-6)
    chk("pnl cross-gamma", abs(pnl([0, 0], [10, -10], np.array([[0, 5.0], [5.0, 0]])) - (0.5 * 2 * 5 * -100)) < 1e-9)
    # 2 shock builders: 8bp flattening around -50 -> short -50, long -58 (RiskVal-style), linear between
    s = knot_shock([1, 10, 30], [1, 30], [-50, -58])
    chk("twist interp", abs(s[0] + 50) < 1e-9 and abs(s[2] + 58) < 1e-9 and -58 < s[1] < -50)
    c7 = citi7([1, 2, 5, 10, 30])
    chk("citi7 bear flattener", list(c7["bear_flattener"]) == [50, 50, 25, 0, 0])
    # 3 BlackRock: 11 perfectly correlated 60bp buckets, 150bp parallel = 2.5 sd, one-sided prob 0.00621
    cov11 = np.full((11, 11), 60.0 ** 2)
    m = sd_multiple(np.full(11, 150.0), cov11)
    chk("sd multiple 2.5", abs(m - 2.5) < 1e-9 and abs(norm.sf(m) - 0.00621) < 1e-5, f"{m:.4f} {norm.sf(m):.5f}")
    # 4 Z / C: rho 0.8; consistent (1,1) sigma shock has C<1; flipped (1,-1) has C>1
    cv = np.array([[1, .8], [.8, 1.0]])
    a, b = scenario_z([1, 1], cv), scenario_z([1, -1], cv)
    chk("corr z-score", abs(a["Z"] - math.sqrt(2 / 1.8 / 2)) < 1e-9 and a["C"] < 1 < b["C"], f"{a['C']:.3f} {b['C']:.3f}")
    # 5 conditional shock: vols 10, 8, rho .8; core x=+10 -> y = 6.4
    cv2 = np.array([[100, 64], [64, 64.0]])
    chk("conditional shock", abs(conditional_shock(cv2, [0], [10.0])[1] - 6.4) < 1e-9)
    # 6 historical VaR/ES: 400 days, worst losses per Darbyshire Ex 14.3 -> VaR1%=30k (4th worst), ES2.5%=42.1k
    w = [-170, -95, -40, -30, -25, -19, -12, -11, -10, -9]
    x = np.r_[np.array(w) * 1e3, np.zeros(390)]
    rng.shuffle(x)
    v1, _ = hist_var_es(x, 0.01)
    _, e25 = hist_var_es(x, 0.025)
    chk("hist var/es", v1 == 30e3 and abs(e25 - 42100) < 1e-6, f"{v1} {e25}")
    # 7 CoVaR on the (rounded) Darbyshire covariance: c ~ 16,174 within 3%; allocations sum to c
    Q = np.array([[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]])
    S = np.array([-10000, 2500, 10000, -4000.0])
    c, v = covar(S, Q, 0.99)
    chk("covar", abs(c / 16174 - 1) < 0.03 and abs(v / c - 2.326) < 1e-3 and abs(var_allocation(S, Q).sum() - c) < 1e-6,
        f"c={c:.0f}")
    # 8 reverse stress: loss = md*c, shock on ellipsoid, and no random shock of equal radius loses more
    d = np.array([-10000, 2500, 10000, -4000.0])
    sh, loss = reverse_stress(d, Q, 3.0)
    chk("reverse stress radius", abs(math.sqrt(sh @ np.linalg.solve(Q, sh)) - 3.0) < 1e-9 and abs(-pnl(d, sh) - loss) < 1e-6)
    r = rng.normal(size=(20000, 4)) @ np.linalg.cholesky(Q).T
    r *= 3.0 / np.sqrt(np.einsum("ij,jk,ik->i", r, np.linalg.inv(Q), r))[:, None]
    chk("reverse stress is worst", (-pnl(d, r)).max() <= loss + 1e-6)
    # 9 Ilmanen Fig.7 scenario set: implied mean +10bp each, vols 80/76/72/69/66, corr >= 0.92 (equal probs)
    sc = np.array([[100] * 5, [-100] * 5, [0] * 5, [100, 87.5, 75, 62.5, 50], [-50, -37.5, -25, -12.5, 0]], float)
    mu, sd, co = implied_view(sc, np.ones(5))
    chk("implied view", np.allclose(mu, 10) and np.allclose(sd, [80, 76, 72, 69, 66], atol=0.6) and co.min() > 0.92,
        f"{sd.round(1)} {co.min():.3f}")
    # 10 PCA recovers known loadings (bp per SD) from simulated changes
    Ltrue = np.column_stack([[1, 2, 3, 2, 1.0], [-2, -1, 0, 1, 2.0]])  # orthogonal: level hump, slope
    Ltrue = Ltrue / np.linalg.norm(Ltrue, axis=0) * np.array([10.0, 3.0])
    z = rng.normal(size=(60000, 2))
    ch = pd.DataFrame(z @ Ltrue.T + rng.normal(scale=0.05, size=(60000, 5)))
    L, ex, _ = pca_loadings(ch, 2)
    chk("pca loadings", np.abs(L - Ltrue).max() < 0.1, f"max err {np.abs(L - Ltrue).max():.3f}")
    chk("pca explained", abs(ex[0] - 100 / 109) < 0.005, f"{ex[0]:.4f}")
    # 11 invariant risk: closed form vs Monte Carlo (normal and mixed normal p=.1, theta=5); x8 / x2 stress multiples
    J = np.array([1.0, -2.0, 0.5])
    H = np.array([[2.0, 0.5, 0], [0.5, -1.0, 0.3], [0, 0.3, 1.0]])
    a = rng.normal(size=(400000, 3))
    th = np.where(rng.random(400000) < 0.1, 5.0, 1.0)[:, None]
    for name, al, p, t in (("normal", a, 0.0, 1.0), ("mixed", a * th, 0.1, 5.0)):
        dpi = al @ J + 0.5 * np.einsum("mi,ij,mj->m", al, H, al)
        chk(f"invariant risk {name}", abs(math.sqrt((dpi ** 2).mean()) / invariant_risk(J, H, p, t) - 1) < 0.03)
    chk("stress multiples", abs(invariant_risk([1.0], None, .1, 5) - 1.844) < 0.01 and
        abs(invariant_risk([0.0], [[1.0]], .1, 5) / invariant_risk([0.0], [[1.0]]) - 7.96) < 0.01)
    # 12 window_shocks / rolling_pnl on a toy path
    lv = pd.DataFrame({"2Y": [100, 110, 120, 130.0], "10Y": [200, 205, 210, 215.0]},
                      index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]))
    ws = window_shocks(lv, {"w": ("2020-01-01", "2020-01-04")})
    chk("window shock", ws.loc["w"].tolist() == [30.0, 15.0] and
        abs(rolling_pnl(lv, [1000, 0], 3).iloc[0] + 30000) < 1e-9)
    # 13 end-to-end CLI path on synthetic curve: P&L of a 2s10s-flat book under +PC1 is tiny vs the 10y-only book
    idx = pd.bdate_range("2022-01-03", periods=800)
    lvl = 300 + np.cumsum(rng.normal(size=(800, 3)) @ np.array([[3, 3, 3], [-1, 0, 1], [0.5, -1, 0.5]], float), 0)
    lv = pd.DataFrame(lvl + np.array([0, 20, 40]), index=idx, columns=["2Y", "5Y", "10Y"])
    lad = pd.DataFrame({"bucket": ["2Y", "5Y", "10Y"], "dv01_ccy": [-50e3, 0, 50e3]})
    res = run(lad, lv, {"w": (str(idx[10].date()), str(idx[60].date()))})
    chk("run()", len(res) > 20 and res.pnl_ccy.is_monotonic_increasing and res.Z.notna().all())
    # 14 risk_cov is un-demeaned (constant drift of 2bp/day keeps variance 4*h, a demeaned cov would give 0);
    # hist_var_es ignores NaN; levels_from_curve_par converts pct -> bp
    chk("uncentered cov", abs(risk_cov(pd.DataFrame({"a": [2.0] * 50}), 5)[0, 0] - 20) < 1e-9)
    chk("var/es NaN", hist_var_es([np.nan, -3.0, -1.0, 0.0, 2.0], 0.25) == (3.0, 3.0))
    cp = pd.DataFrame({"date": ["2024-01-02"] * 2, "snap": "eod", "curve_id": "X", "start": "0D",
                       "tenor": ["2Y", "10Y"], "par_rate_pct": [4.25, 3.9]})
    chk("curve_par pct->bp", levels_from_curve_par(cp, "X", ["2Y", "10Y"]).iloc[0].tolist() == [425.0, 390.0])
    print("ALL PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ladder", help="CSV: bucket (e.g. 2Y), dv01_ccy [, gamma_ccy]")
    ap.add_argument("--curve", help="canonical curve_par CSV/Parquet")
    ap.add_argument("--curve-id", help="curve_id to use, e.g. USD-SOFR")
    ap.add_argument("--window", action="append", default=[], help="name:YYYY-MM-DD:YYYY-MM-DD historical replay")
    ap.add_argument("--horizon-days", type=int, default=21, help="covariance scaling horizon (default 21 = 1m)")
    ap.add_argument("--lookback", type=int, default=756, help="days of changes for covariance/PCA (default 3y)")
    ap.add_argument("--rev-z", type=float, default=3.0, help="Z of the reverse-stress shock (default 3)")
    ap.add_argument("--out", help="write results CSV")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.ladder and a.curve and a.curve_id):
        ap.error("--ladder, --curve and --curve-id are required (or use --selftest)")
    lad = pd.read_csv(a.ladder)
    lv = levels_from_curve_par(_load(a.curve), a.curve_id, list(lad.bucket))
    wins = {w.split(":")[0]: (w.split(":")[1], w.split(":")[2]) for w in a.window}
    res = run(lad, lv, wins, a.horizon_days, a.lookback, a.rev_z)
    pd.set_option("display.width", 200, "display.max_columns", 30)
    print(res.round(2).to_string(index=False))
    print("PC explained variance:", np.round(res.attrs["pc_explained"], 3))
    if a.out:
        res.to_csv(a.out, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
