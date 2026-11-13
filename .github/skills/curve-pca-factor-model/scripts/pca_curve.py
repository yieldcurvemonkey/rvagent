"""PCA factor model for rate curves: loadings, residual rich/cheap, PC-neutral weights, PC risk and P&L attribution.

Units: rates in bp (percent x 100). Risk vectors `s` are DV01 per bp, POSITIVE = long duration (receive fixed),
so P&L = -s . dy with dy in bp. Residual = actual - model; POSITIVE = yield above model = CHEAP (receive).

Conventions
- fit mode "changes": PCA of daily first differences (use for hedge ratios, risk, P&L attribution).
- fit mode "levels":  PCA of levels (use for rich/cheap residuals on a ~1y window, ideally non-overlapping forwards).
- scale=False (default): covariance PCA on bp, which keeps the vol term structure. scale=True: correlation PCA.
  Either way `risk_in_pc` and `neutral_weights` rescale correctly, so exposures are always about DV01 s.
- Signs are pinned: PC1 sum > 0; PC2 long end > short end; PC3 wings > belly; PC>=4 largest |entry| > 0.

CLI (canonical `curve_par` table, columns date, curve_id, start, tenor, par_rate_pct, optional snap):
    python pca_curve.py fit      --input curve_par.csv --curve-id USD-SOFR --mode changes --window 756
    python pca_curve.py screen   --input curve_par.csv --curve-id EUR-ESTR --start 0D,1Y,2Y,3Y --k 3 --window 261 --walk-forward
    python pca_curve.py neutral  --input curve_par.csv --curve-id USD-SOFR --legs 2Y,5Y,10Y --fixed 5Y=1 --npcs 2
    python pca_curve.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------------------- core fit
def pin_signs(E: np.ndarray) -> np.ndarray:
    """Flip columns of E (n x m) so PC1 is positive, PC2 slopes up with maturity, PC3 has wings above belly."""
    E = E.copy()
    n, m = E.shape
    for j in range(m):
        if j == 0:
            ok = E[:, 0].sum() > 0
        elif j == 1:
            ok = E[-1, 1] - E[0, 1] > 0
        elif j == 2:
            ok = 0.5 * (E[0, 2] + E[-1, 2]) - E[n // 2, 2] > 0
        else:
            ok = E[np.argmax(np.abs(E[:, j])), j] > 0
        if not ok:
            E[:, j] = -E[:, j]
    return E


class PCAFit:
    """Eigen-decomposition of the covariance (or correlation) of a T x n panel of rates in bp."""

    def __init__(self, X, mode: str = "changes", scale: bool = False, demean: bool = True):
        X = pd.DataFrame(X).astype(float)
        if mode not in ("changes", "levels"):
            raise ValueError("mode must be 'changes' or 'levels'")
        self.mode, self.scale_flag, self.cols = mode, scale, list(X.columns)
        Z = X.diff().dropna() if mode == "changes" else X.dropna()
        if len(Z) < 3 * Z.shape[1]:
            raise ValueError(f"only {len(Z)} observations for {Z.shape[1]} series: need >= 3x")
        # demean=False: zero-mean second-moment matrix, the risk convention (a steady 10bp/day trend is risk, not zero vol)
        self.mean = Z.mean().to_numpy() if demean else np.zeros(Z.shape[1])
        Zc = Z.to_numpy() - self.mean
        dof = len(Z) - (1 if demean else 0)
        self.scale = np.sqrt((Zc ** 2).sum(0) / dof) if scale else np.ones(Z.shape[1])
        Y = Zc / self.scale
        C = Y.T @ Y / dof
        w, V = np.linalg.eigh(C)
        o = np.argsort(w)[::-1]
        self.eigvals, self.E = w[o], pin_signs(V[:, o])
        self.nobs = len(Z)

    @property
    def var_share(self) -> np.ndarray:
        return self.eigvals / self.eigvals.sum()

    def scaled_loadings(self) -> pd.DataFrame:
        """bp move of each series per +1 sd move of each PC: scale * E * sqrt(eigenvalue). Rows = series."""
        L = (self.scale[:, None] * self.E) * np.sqrt(np.maximum(self.eigvals, 0))
        return pd.DataFrame(L, index=self.cols, columns=[f"PC{i + 1}" for i in range(len(self.cols))])

    def scores(self, X) -> pd.DataFrame:
        """PC scores of a panel in the fit's own mode (diffs for 'changes', levels for 'levels'): E'((x - mean)/scale).
        Units: bp for covariance PCA (variance = eigenvalue), series-sd units for correlation PCA."""
        X = pd.DataFrame(X)[self.cols].astype(float)
        Z = X.diff() if self.mode == "changes" else X
        S = ((Z.to_numpy() - self.mean) / self.scale) @ self.E
        return pd.DataFrame(S, index=X.index, columns=[f"PC{i + 1}" for i in range(S.shape[1])])

    def model(self, X, k: int = 3) -> pd.DataFrame:
        """k-factor reconstruction in the fit's own mode, bp."""
        X = pd.DataFrame(X)[self.cols].astype(float)
        S = self.scores(X).to_numpy()[:, :k]
        R = (S @ self.E[:, :k].T) * self.scale + self.mean
        return pd.DataFrame(R, index=X.index, columns=self.cols)

    def resid(self, X, k: int = 3) -> pd.DataFrame:
        """actual - model (bp). For mode 'levels' positive = cheap. Zero for k = n by construction."""
        X = pd.DataFrame(X)[self.cols].astype(float)
        base = X.diff() if self.mode == "changes" else X
        return base - self.model(X, k)


def level_resid_from_changes(levels: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """Level rich/cheap from a change-PCA: regress levels on cumulated k scores (with intercept); positive = cheap.
    The residual MUST be tested for stationarity before use (it is not mean-zero by construction)."""
    f = PCAFit(levels, "changes")
    D = levels.diff().iloc[1:]
    # cumulate RAW (not demeaned) scores: demeaning would strip the drift out of the cumulated factors
    C = pd.DataFrame((D.to_numpy() / f.scale) @ f.E[:, :k], index=D.index).cumsum()
    A = np.column_stack([np.ones(len(C)), C.to_numpy()])
    Y = levels.iloc[1:].to_numpy(float)
    beta, *_ = np.linalg.lstsq(A, Y, rcond=None)
    return pd.DataFrame(Y - A @ beta, index=C.index, columns=levels.columns)


def resid_series(levels: pd.DataFrame, k: int = 3, fit_window: int = 261, walk_forward: bool = False) -> pd.DataFrame:
    """Level residuals (bp, + = cheap). In-sample: one levels-PCA on the last `fit_window` rows, residual of every row in it
    (today is in the fit, so it is flattering). Walk-forward: for each date t fit on the `fit_window` rows strictly BEFORE t
    and score t out-of-sample; first `fit_window` dates are dropped. (k-PC residuals do not depend on eigenvector signs.)"""
    if not walk_forward:
        w = levels.iloc[-fit_window:]
        return PCAFit(w, "levels").resid(w, k)
    if len(levels) <= fit_window:
        raise ValueError(f"walk-forward needs > {fit_window} rows, got {len(levels)}")
    out = {}
    for i in range(fit_window, len(levels)):
        f = PCAFit(levels.iloc[i - fit_window:i], "levels")
        out[levels.index[i]] = f.resid(levels.iloc[i:i + 1], k).iloc[0]
    return pd.DataFrame(out).T


def zscore(r: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    return (r - r.rolling(window).mean()) / r.rolling(window).std(ddof=1)


# ------------------------------------------------------------------------------- risk / hedging
def risk_in_pc(fit: PCAFit, s, per_sd: bool = False) -> pd.Series:
    """Exposure of DV01 vector s to each PC: E'(scale * s), i.e. DV01 per unit of PC score (per bp of PC for covariance PCA).
    per_sd=True multiplies by sqrt(eigenvalue): DV01-bp of P&L-sensitivity to a +1 sd move of each PC."""
    s = np.asarray(s, float)
    r = fit.E.T @ (fit.scale * s)
    if per_sd:
        r = r * np.sqrt(np.maximum(fit.eigvals, 0))
    return pd.Series(r, index=[f"PC{i + 1}" for i in range(len(s))])


def pc_pnl(fit: PCAFit, s, dy) -> pd.DataFrame:
    """P&L by PC for risk s (DV01/bp, + = long) and move dy (bp, same order as fit.cols). Rows sum to -s.dy.
    Use RAW (non-demeaned) moves. Rows PCn..PCm beyond the PCs you keep are your 'unexplained' remainder."""
    s, dy = np.asarray(s, float), np.asarray(dy, float)
    risk = fit.E.T @ (fit.scale * s)
    move = fit.E.T @ (dy / fit.scale)
    idx = [f"PC{i + 1}" for i in range(len(s))]
    return pd.DataFrame({"risk": risk, "move": move, "pnl": -risk * move}, index=idx)


def _eff(fit_or_E, n: int | None = None):
    if isinstance(fit_or_E, PCAFit):
        return fit_or_E.scale[:, None] * fit_or_E.E
    return np.asarray(fit_or_E, float)


def neutral_weights(fit_or_E, legs, fixed: dict, npcs: int = 2, cond_warn: float = 1e8) -> dict:
    """DV01 weights on `legs` (indices into the series) that zero exposure to PC1..PC`npcs`.
    `fixed` maps leg index -> DV01 (e.g. belly = +1). Remaining legs are solved (least-squares/minimum-norm if
    the system is not square). Returns dict(weights, cond, residual_exposure)."""
    Eeff = _eff(fit_or_E)
    free = [j for j in legs if j not in fixed]
    A = Eeff[free, :npcs].T                                   # npcs x nfree
    b = -sum(v * Eeff[j, :npcs] for j, v in fixed.items())
    w, *_ = np.linalg.lstsq(A, b, rcond=None)
    cond = float(np.linalg.cond(A))
    full = dict(fixed)
    full.update({j: float(x) for j, x in zip(free, w)})
    s = np.zeros(Eeff.shape[0])
    for j, v in full.items():
        s[j] = v
    return {"weights": full, "cond": cond, "ill_conditioned": cond > cond_warn,
            "residual_exposure": Eeff.T @ s}


def min_norm_neutral(fit_or_E, t, npcs: int = 1, locked=()) -> np.ndarray:
    """Smallest DV01 adjustment x (min ||x||) so that t + x has zero exposure to PC1..PC`npcs`; legs in `locked`
    may not change. With no lock and orthonormal E this is x = -E_H E_H' t."""
    Eeff, t = _eff(fit_or_E), np.asarray(t, float)
    H = Eeff[:, :npcs]
    free = [j for j in range(len(t)) if j not in set(locked)]
    EF = H[free]
    x = np.zeros_like(t)
    x[free] = -EF @ np.linalg.pinv(EF.T @ EF) @ (H.T @ t)
    return t + x


def pc3_weights(E3: np.ndarray) -> np.ndarray:
    """Fly weights = PC3 loadings of a 3-point PCA (wing, belly, wing), scaled so belly = +1.
    Orthogonal to PC1/PC2 of THAT 3-point PCA, generally not DV01-neutral."""
    return E3[:, 2] / E3[1, 2]


# --------------------------------------------------------------------------------- stability
def rolling_stability(levels: pd.DataFrame, window: int = 252, step: int = 21, k: int = 3) -> pd.DataFrame:
    """Change-PCA on trailing windows: variance shares PC1..PCk, |cosine| of each PC with the previous window
    (sign-aligned), PC1 sign-pinned. Low cosine (< 0.9) = loadings moved; budget for it before trusting weights."""
    rows, prev = [], None
    for i in range(window + 1, len(levels) + 1, step):
        f = PCAFit(levels.iloc[i - window - 1:i], "changes")
        row = {"date": levels.index[i - 1]}
        for j in range(k):
            row[f"share{j + 1}"] = f.var_share[j]
            row[f"cos{j + 1}"] = abs(float(f.E[:, j] @ prev[:, j])) if prev is not None else np.nan
        prev = f.E
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")


def herfindahl(eigvals) -> float:
    e = np.asarray(eigvals, float)
    return float((e ** 2).sum() / e.sum() ** 2)


# -------------------------------------------------------------------------------------- CLI
def _yrs(t: str) -> float:
    m = re.fullmatch(r"(\d+)([DWMY])", t)
    if not m:
        return 0.0
    return int(m.group(1)) * {"D": 1 / 365, "W": 7 / 365, "M": 1 / 12, "Y": 1.0}[m.group(2)]


def load_panel(path: str, curve_id: str, start: str = "0D", snap: str | None = None) -> pd.DataFrame:
    """Wide panel in bp. `start` is one forward-start (default `0D`, columns = tenor) or a comma list such as
    `0D,1Y,2Y` for a forward grid (columns = `<start>x<tenor>`, e.g. `1Yx1Y`, ordered by mid-point of the forward period)."""
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    df = df[df["curve_id"] == curve_id]
    if snap:
        df = df[df["snap"] == snap]
    elif "snap" in df and df["snap"].nunique() > 1:
        raise SystemExit("several snaps present: pass --snap (never mix snaps in one series)")
    starts = start.split(",")
    df = df[df["start"].isin(starts)].copy()
    if len(starts) > 1:
        df["tenor"] = df["start"] + "x" + df["tenor"]
        key = lambda c: _yrs(c.split("x")[0]) + _yrs(c.split("x")[1]) / 2
    else:
        key = _yrs
    p = df.pivot(index="date", columns="tenor", values="par_rate_pct") * 100.0
    p = p[sorted(p.columns, key=key)]
    p.index = pd.to_datetime(p.index)
    return p.sort_index().dropna()


def _main(a) -> None:
    P = load_panel(a.input, a.curve_id, a.start, a.snap)
    if a.cmd == "screen" and a.walk_forward:   # need window + z-window + 1m look-back of out-of-sample residuals
        P = P.iloc[-(a.window + a.zwin + 22):]
    else:
        P = P.iloc[-a.window:]
    if a.cmd == "fit":
        f = PCAFit(P, a.mode, a.scale, not a.no_demean)
        print(f"obs={f.nobs} mode={a.mode} var_share={np.round(f.var_share[:4], 4)}")
        print(f.scaled_loadings().iloc[:, :4].round(3).to_string())
    elif a.cmd == "screen":
        r = resid_series(P, a.k, a.window, a.walk_forward)
        z = zscore(r, a.zwin)
        out = pd.DataFrame({"resid_bp": r.iloc[-1], "z": z.iloc[-1], "resid_1w": r.iloc[-6], "resid_1m": r.iloc[-22]})
        print("positive residual = yield above model = cheap (receive)" + (" [walk-forward: each day scored out-of-sample]" if a.walk_forward else ""))
        print(out.round(2).to_string())
    elif a.cmd == "neutral":
        f = PCAFit(P, "changes", a.scale)
        legs = a.legs.split(",")
        fx = {P.columns.get_loc(legs[legs.index(k)]): float(v) for k, v in (x.split("=") for x in a.fixed.split(","))}
        r = neutral_weights(f, [P.columns.get_loc(l) for l in legs], fx, a.npcs)
        print({P.columns[j]: round(v, 4) for j, v in r["weights"].items()}, "cond=%.1f" % r["cond"])
        if r["ill_conditioned"]:
            print("WARNING: ill-conditioned system, weights unreliable")
        print("exposure to PC1..PC3 (DV01-bp):", np.round(r["residual_exposure"][:3], 4))
        print("DV01 weights, + = receive. Convert to notional: weight / DV01 per unit notional.")


def _parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    for n in ("fit", "screen", "neutral"):
        s = sub.add_parser(n)
        s.add_argument("--input", required=True)
        s.add_argument("--curve-id", required=True)
        s.add_argument("--start", default="0D")
        s.add_argument("--snap")
        s.add_argument("--window", type=int, default=756 if n != "screen" else 261)
        s.add_argument("--mode", default="changes", choices=["changes", "levels"])
        s.add_argument("--scale", action="store_true")
        s.add_argument("--no-demean", action="store_true", help="zero-mean second-moment matrix (risk convention)")
        s.add_argument("--k", type=int, default=3)
        s.add_argument("--zwin", type=int, default=60)
        s.add_argument("--walk-forward", action="store_true")
        s.add_argument("--legs", default="2Y,5Y,10Y")
        s.add_argument("--fixed", default="5Y=1")
        s.add_argument("--npcs", type=int, default=2)
    return p


# ---------------------------------------------------------------------------------- selftest
def selftest() -> int:
    bad = []

    def check(name, ok, info=""):
        if not ok:
            bad.append(name)
        print(("PASS " if ok else "FAIL ") + name + (" " + info if info else ""))

    # 1. analytic eigenvalues: Cov [[7,3],[3,2]] -> (9 +- sqrt(61))/2 = 8.405, 0.595
    w = np.sort(np.linalg.eigvalsh(np.array([[7.0, 3], [3, 2]])))[::-1]
    check("eig analytic", np.allclose(w, [(9 + 61 ** .5) / 2, (9 - 61 ** .5) / 2]))

    # 2. simulated 3-factor curve with KNOWN loadings, vols and an injected idiosyncratic dislocation
    rng = np.random.default_rng(7)
    n, T = 8, 4000
    x = np.linspace(-1, 1, n)
    G = np.column_stack([1.0 + 0.3 * (1 - x ** 2), x, x ** 2 - (x ** 2).mean()])
    Q, _ = np.linalg.qr(G)
    Q = pin_signs(Q)                                         # true loadings, orthonormal
    vols = np.array([5.0, 2.0, 0.8])                         # bp/day per factor
    cols = [f"T{i}" for i in range(n)]
    d = (rng.standard_normal((T, 3)) * vols) @ Q.T + 0.05 * rng.standard_normal((T, n))
    lv = pd.DataFrame(300 + np.cumsum(d, 0), columns=cols, index=pd.bdate_range("2010-01-01", periods=T))
    f = PCAFit(lv, "changes")
    cos = [abs(f.E[:, j] @ Q[:, j]) for j in range(3)]
    check("loadings recovered", min(cos) > 0.995, f"cos={np.round(cos, 4)}")
    check("sign pin", f.E[:, 0].sum() > 0 and f.E[-1, 1] > f.E[0, 1] and f.E[:, 2][[0, -1]].mean() > f.E[n // 2, 2])
    check("eigenvalues ~ vols^2", np.allclose(f.eigvals[:3], vols ** 2, rtol=0.07), f"{np.round(f.eigvals[:3], 2)}")
    exp1 = vols[0] ** 2 / (vols ** 2).sum()
    check("var share PC1", abs(f.var_share[0] - exp1) < 0.01, f"{f.var_share[0]:.3f} vs {exp1:.3f}")

    # 3. residual sign and size, known answer: levels = factor random walks + stationary noise (sd 0.3bp);
    #    +5bp on tenor 3 on the last day. A k=3 reconstruction explains the share q = sum_j Q[3,j]^2 of the
    #    spike, so the residual must be ~ 5 x (1 - q), positive (cheap), and the largest across tenors.
    rng3 = np.random.default_rng(11)
    fac = np.cumsum((rng3.standard_normal((T, 3)) * vols) @ Q.T, 0)
    ls = pd.DataFrame(300 + fac + 0.3 * rng3.standard_normal((T, n)), columns=cols, index=lv.index)
    ls.iloc[-1, 3] += 5.0
    exp = 5.0 * (1 - (Q[3, :3] ** 2).sum())
    r = resid_series(ls, k=3, fit_window=261).iloc[-1]
    check("residual flags cheap tenor", r.idxmax() == "T3" and abs(r["T3"] - exp) < 0.5, f"T3={r['T3']:.2f} vs {exp:.2f}")
    rw = resid_series(ls, k=3, fit_window=261, walk_forward=True).iloc[-1]
    check("walk-forward residual agrees", abs(rw["T3"] - exp) < 0.5, f"{rw['T3']:.2f}")
    # walk-forward must be OUT-of-sample: a huge one-day dislocation on a short window is absorbed by the in-sample fit
    # (it becomes its own PC) but fully visible out-of-sample, where it is 100 x (1 - q).
    lb = ls.iloc[-300:].copy()
    lb.iloc[-1, 3] += 95.0                                   # +100 in total on T3
    ins = resid_series(lb, k=3, fit_window=60)["T3"].iloc[-1]
    oos = resid_series(lb, k=3, fit_window=60, walk_forward=True)["T3"].iloc[-1]
    exp100 = 100.0 * (1 - (Q[3, :3] ** 2).sum())
    check("walk-forward is out-of-sample", abs(oos - exp100) < 3.0 and abs(ins) < 0.5 * exp100,
          f"oos={oos:.1f} in-sample={ins:.1f} expected oos {exp100:.1f}")
    same = PCAFit(lb.iloc[-61:-1], "levels").resid(lb.iloc[-1:], 3).iloc[0]["T3"]
    check("walk-forward = fit on rows before t", abs(same - oos) < 1e-9)
    check("k=n residual is zero", np.abs(PCAFit(lv.iloc[-261:], "levels").resid(lv.iloc[-261:], n).to_numpy()).max() < 1e-8)
    lr = level_resid_from_changes(ls, 3)
    check("change-PCA level residual flags tenor", lr.iloc[-1].idxmax() == "T3" and lr.iloc[-1]["T3"] > 3.0,
          f"{lr.iloc[-1]['T3']:.2f}")

    # 4. PUBLISHED case (Tuckman & Serrat, Table 6.6): receive 20y, pay 10y and 30y, neutral to level and slope.
    L = np.array([[3.44, 0.07], [3.73, 1.02], [3.77, 1.35]])  # 10y, 20y, 30y scaled PC1/PC2 loadings
    dv = np.array([0.09347, 0.17064, 0.23600])
    res = neutral_weights(L, [0, 1, 2], {1: dv[1]}, npcs=2)    # fixed: receive 100 of 20y = DV01 0.17064
    n10, n30 = res["weights"][0] / dv[0] * 100, res["weights"][2] / dv[2] * 100   # notional per 100 of 20y
    check("Tuckman 10s20s30s F10=-49.56", abs(n10 - (-49.56)) < 0.15, f"{n10:.2f}")
    check("Tuckman 10s20s30s F30=-53.60", abs(n30 - (-53.60)) < 0.15, f"{n30:.2f}")
    share10, share30 = -res["weights"][0] / dv[1], -res["weights"][2] / dv[1]
    check("Tuckman risk weights 27.1%/74.1%", abs(share10 - .271) < .003 and abs(share30 - .741) < .004,
          f"{share10:.3f}/{share30:.3f}")

    # 5. PUBLISHED case (Darbyshire Ex 23.1): PC1 = [.65,.59,.44,.20], pay 5Y rec 2Y,10Y t=[-1,2,-1,0].
    E1 = np.array([[.65], [.59], [.44], [.20]])
    t = np.array([-1.0, 2, -1, 0])
    nb = min_norm_neutral(E1, t, 1, locked=[3])
    check("Darbyshire min-adjust (30Y locked)", np.allclose(nb, [-1.07, 1.94, -1.05, 0], atol=0.02) and nb[3] == 0.0,
          f"{np.round(nb, 3)}")
    check("result is PC1-neutral", abs(E1[:, 0] @ nb) < 1e-9)
    nu = min_norm_neutral(E1, t, 1)                          # unlocked: the 30Y must move, by -0.09 x 0.20 / |e1|^2 = -0.018
    check("unlocked adjustment touches 30Y", abs(nu[3] + 0.0179) < 0.0005 and abs(E1[:, 0] @ nu) < 1e-9, f"{np.round(nu, 4)}")

    # 6. P&L attribution adds up: QF.SE case, total = sum(-s.dy)... risks as dPV/dr (negative of DV01) gives +195
    s = -np.array([10, 30, -5, 20, -10, 20, -60.0])           # DV01 convention: s = -(dPV/dr)
    dy = np.array([1, -1, -1, -2, -3, -4, -5.0])
    rng2 = np.random.default_rng(3)
    base = pd.DataFrame(np.cumsum(rng2.standard_normal((500, 7)) * [1, 1.2, 1.5, 1.8, 2, 2, 2], 0))
    for sc in (False, True):
        fq = PCAFit(base, "changes", scale=sc)
        att = pc_pnl(fq, s, dy)
        check(f"PC P&L sums to total (scale={sc})", abs(att["pnl"].sum() - 195.0) < 1e-9, f"{att['pnl'].sum():.6f}")
    fq = PCAFit(base, "changes")
    check("1000 x PC1 maps to [1000,0,..]", np.allclose(risk_in_pc(fq, 1000 * fq.E[:, 0]).to_numpy(), [1000] + [0] * 6, atol=1e-8))
    check("risk per +1 sd = unit risk x sqrt(eigenvalue)",
          np.allclose(risk_in_pc(fq, 1000 * fq.E[:, 0], per_sd=True).iloc[0], 1000 * np.sqrt(fq.eigvals[0])))
    # zero-mean (risk) convention: two series with the same +10bp/day trend and tiny independent noise. The uncentred
    # second moment sees one huge common PC (~ 2 x 100 / 2); the demeaned covariance sees only the noise (share ~ 0.5).
    tr = pd.DataFrame(10.0 + 0.1 * np.random.default_rng(5).standard_normal((300, 2))).cumsum()
    f0, f1 = PCAFit(tr, "changes", demean=False), PCAFit(tr, "changes")
    check("zero-mean PCA keeps the trend as risk", f0.var_share[0] > 0.999 and f1.var_share[0] < 0.7
          and abs(f0.eigvals[0] - 200.0) < 1.0 and np.allclose(abs(f0.E[:, 0]), 2 ** -0.5, atol=1e-3),
          f"{f0.var_share[0]:.4f} vs {f1.var_share[0]:.3f}, eig {f0.eigvals[0]:.1f}")

    # 7. neutral fly on simulated curve: PC1/PC2 exposures vanish, PC3 remains
    f3 = PCAFit(lv, "changes")
    r3 = neutral_weights(f3, [1, 4, 7], {4: 1.0}, npcs=2)
    ex = r3["residual_exposure"]
    check("fly zero PC1/PC2", abs(ex[0]) < 1e-9 and abs(ex[1]) < 1e-9 and abs(ex[2]) > 1e-3, f"{np.round(ex[:3], 4)}")

    # 8. stability tool runs and PC1 is stable
    st = rolling_stability(lv.iloc[:1500], window=252, step=63)
    check("PC1 loading stable", st["cos1"].dropna().min() > 0.99, f"min={st['cos1'].min():.4f}")
    check("herfindahl in (0,1]", 0 < herfindahl(f.eigvals) <= 1)

    # 9. CLI paths on a canonical curve_par table (spot grid and a forward grid), no crash and correct labels
    import contextlib, io, os, tempfile
    ten = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y"]
    base = lv.iloc[-400:, :6].to_numpy() / 100.0 + 2.0       # pct
    rows = [(d, "USD-TEST", "0D", tn, base[i, j], "eod_ny") for i, d in enumerate(lv.index[-400:]) for j, tn in enumerate(ten)]
    rows += [(d, "USD-TEST", "1Y", "1Y", base[i, 2] + 0.1, "eod_ny") for i, d in enumerate(lv.index[-400:])]
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "curve_par.csv")
        pd.DataFrame(rows, columns=["date", "curve_id", "start", "tenor", "par_rate_pct", "snap"]).to_csv(fp, index=False)
        pan = load_panel(fp, "USD-TEST", "0D")
        check("load_panel: bp and tenor order", list(pan.columns) == ten and abs(pan.iloc[0, 0] - (base[0, 0] * 100)) < 1e-6)
        check("load_panel: forward grid labels", "1Yx1Y" in load_panel(fp, "USD-TEST", "0D,1Y").columns)
        ok = True
        for argv in (["fit"], ["fit", "--mode", "levels", "--no-demean"], ["screen"], ["screen", "--walk-forward", "--window", "100"],
                     ["neutral", "--legs", "2Y,5Y,10Y", "--fixed", "5Y=1"]):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    _main(_parser().parse_args(argv + ["--input", fp, "--curve-id", "USD-TEST"] + ([] if "--window" in argv else ["--window", "300"])))
            except Exception as e:  # noqa: BLE001
                ok = False
                print("   CLI", argv, "->", repr(e))
        check("CLI fit / screen / screen --walk-forward / neutral run", ok)

    print("SELFTEST", "FAILED: " + ", ".join(bad) if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    ns = _parser().parse_args()
    if ns.selftest:
        sys.exit(selftest())
    if not ns.cmd:
        _parser().print_help()
        sys.exit(2)
    _main(ns)
