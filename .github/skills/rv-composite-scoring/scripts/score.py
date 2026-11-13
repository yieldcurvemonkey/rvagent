#!/usr/bin/env python3
"""Composite RV scoring: combine normalised metrics into one ranking score and show contributions.

Conventions (same as SKILL.md)
  side = +1  "receive-type": P&L rises when the structure's level FALLS (receive fixed, long bond, sell the fly).
  side = -1  "pay-type".  Default side = sign(z) i.e. fade the deviation from history.
  carry_bp   = carry+roll over the horizon of the receive-type position, bp (positive = it earns).
  vol_bp     = vol of the structure level over the SAME horizon, bp.
  z          = (level - mean) / std, ddof=1, level in bp (positive = level high = receive-type cheap).
  pca_z      = optional PCA residual z, same orientation; if present it REPLACES z in the level slot (no double count).
  half-life in calendar days, pctile in 0..1 (rank of the level in its window).
  Optional columns: side, pca_z, pctile, halflife_days, hit_frac, cost_bp, hist_days.

Modes:  composite (gated weighted sum) | jscore (carry/vol + z, receiver convention) | frontier (projection score).
CLI:    python score.py metrics.csv [--mode composite] [--out ranked.csv]
Test:   python -I score.py --selftest
"""
import argparse
import sys

import numpy as np
import pandas as pd

DEFAULT_W = {"z": 0.40, "ctv": 0.25, "pctl": 0.15, "hl": 0.20, "hit": 0.0}


def zscore(s: pd.Series, window: int = 756) -> pd.Series:
    """Rolling z of the level vs its own trailing window (ddof=1, window includes today; 756 = 3y of business days)."""
    r = s.rolling(window, min_periods=window)
    return (s - r.mean()) / r.std(ddof=1)


def halflife_days(s: pd.Series, scale: float = 365 / 252) -> float:
    """AR(1) on levels: dx = a + b*x_{t-1}; half-life = -ln2/ln(1+b) in observations x scale. inf if no reversion.
    Default scale 365/252 converts business-day observations to CALENDAR days; pass scale=1 for observations."""
    x = s.dropna().to_numpy(float)
    if len(x) < 10 or np.ptp(x[:-1]) == 0:
        return np.nan
    b = np.polyfit(x[:-1], np.diff(x), 1)[0]
    return float(-np.log(2) / np.log(1 + b) * scale) if -1 < b < 0 else np.inf


def ou_expected_sharpe(x, mu, sigma, k, h, carry=0.0):
    """Exact OU conditional Sharpe over horizon h (years) for the position that profits from x falling to mu.
    ER = (x-mu)(1-e^{-kh}) + carry ; sd = sigma*sqrt((1-e^{-2kh})/(2k)). sigma in bp/sqrt(yr), k per year."""
    er = (x - mu) * (1 - np.exp(-k * h)) + carry
    sd = sigma * np.sqrt((1 - np.exp(-2 * k * h)) / (2 * k))
    return er / sd


def j_score(carry_bp, vol_bp, z, vol_floor=0.5):
    """Nordea-style J = carry/vol + z for a receiver (z positive = rate high vs history). For payers flip both signs."""
    return carry_bp / np.maximum(vol_bp, vol_floor) + z


def pctile_to_scorecard(x: float, hist) -> float:
    """Percentile rank of x inside its own history mapped linearly to -5..+5 (not comparable across markets)."""
    h = np.asarray(hist, float)
    return 10 * float((h <= x).mean()) - 5


def composite(df: pd.DataFrame, weights=None, z_cap=4.0, ctv_cap=3.0, hl_max=90.0,
              vol_floor=0.5, cost_hurdle=0.0, hl_cap=180.0, ctv_gate=0.0, thin_days=756) -> pd.DataFrame:
    """Gated weighted composite. Each component is >= 0 and only counts when it agrees with the trade direction (side).
    NaN / missing components contribute 0 (conservative: missing data lowers the score, it never raises it).
    ctv_gate: carry/vol (horizon basis, side-signed) below this gives a zero carry component.
    cost_hurdle (scalar, score units) is added to cost_bp/vol_bp x w_z/z_cap when a cost_bp column exists
    (cost in vol units, converted at the z slot's score per sigma)."""
    w = {**DEFAULT_W, **(weights or {})}
    w = {k: v / sum(w.values()) for k, v in w.items()}  # weights are renormalised so the max score stays 1
    d = df.copy()
    g = lambda k: d[k] if k in d else pd.Series(np.nan, index=d.index)
    z = d["pca_z"].fillna(d["z"]) if "pca_z" in d else d["z"]
    d["side"] = (np.sign(z) if "side" not in d else d["side"]).fillna(0).astype(int)
    vol = g("vol_bp").clip(lower=vol_floor)
    ctv = d["side"] * g("carry_bp") / vol
    c = pd.DataFrame(index=d.index)
    c["z"] = (d["side"] * z).clip(upper=z_cap) / z_cap
    c["ctv"] = (ctv.clip(-ctv_cap, ctv_cap) / ctv_cap).where(ctv >= ctv_gate, 0.0)
    c["pctl"] = d["side"] * (g("pctile") - 0.5) * 2
    c["hl"] = (1 - g("halflife_days") / hl_max).clip(-1, 1)
    c["hit"] = ((g("hit_frac") - 0.5) * 2).clip(0, 1)
    c = c.clip(lower=0).fillna(0.0)
    for k in w:
        d["contrib_" + k] = w[k] * c[k]
    mag = d[["contrib_" + k for k in w]].sum(axis=1)
    hurdle = cost_hurdle + (g("cost_bp") / vol).fillna(0) * w["z"] / z_cap
    d["score"] = (mag - hurdle).clip(lower=0) * (d["side"] != 0)
    d["ctv_raw"] = ctv
    dis = (np.sign(g("pca_z")) * np.sign(g("z")) < 0)
    fl = pd.DataFrame({"no_reversion": g("halflife_days") > hl_cap, "carry_against": ctv < 0, "z_disagree": dis,
                       "z>4": z.abs() > z_cap, "thin_history": g("hist_days") < thin_days,
                       "vol_floored": g("vol_bp") <= vol_floor})
    d["flags"] = [" ".join(fl.columns[m]) for m in fl.to_numpy()]
    d["rank"] = d["score"].rank(ascending=False, method="min")
    return d.sort_values("score", ascending=False)


def frontier_score(X: np.ndarray, signs) -> np.ndarray:
    """Projection score on the 'efficient frontier' of attractive trades (3-factor: Carry, Entry, Trend).
    X: n x k coordinates (e.g. carry/vol, z, trend); signs: attractive sign pattern. Goldman orientation is
    [+1,-1,+1]; for this skill's z>0 = receive-type-cheap orientation (trend>0 = level rising) use [+1,+1,-1]
    (flipping axis signs is an orthogonal map, so scores are identical).
    A trade is attractive if all signs line up with `signs`, or all with -signs. Fit the last coordinate on the
    others (LS through the origin) using attractive trades only; score = |projection of the trade onto that
    line/plane|, i.e. distance from the origin. Non-attractive trades get NaN. Refit per screen."""
    X = np.asarray(X, float)
    s = np.asarray(signs, float)
    ok = (np.all(np.sign(X) * s > 0, axis=1)) | (np.all(np.sign(X) * s < 0, axis=1))
    out = np.full(len(X), np.nan)
    if ok.sum() < X.shape[1]:
        return out
    A = X[ok][:, :-1]
    coef = np.linalg.lstsq(A, X[ok][:, -1], rcond=None)[0]
    B = np.vstack([np.eye(X.shape[1] - 1), coef])  # k x (k-1) basis of the fitted plane
    P = B @ np.linalg.pinv(B)  # orthogonal projector onto it
    out[ok] = np.linalg.norm(X[ok] @ P.T, axis=1)
    return out


def bucket_report(score: pd.Series, fwd: pd.Series, q: int = 5) -> pd.DataFrame:
    """Calibration check: mean realised forward P&L and hit rate by score bucket. Should rise monotonically.
    Overlapping horizons: n is NOT the number of independent trades (about n_dates / horizon are)."""
    ok = score.notna() & fwd.notna()
    score, fwd = score[ok], fwd[ok]
    b = pd.qcut(score.rank(method="first"), q, labels=False)
    g = fwd.groupby(b)
    return pd.DataFrame({"n": g.size(), "mean_pnl": g.mean(), "hit": g.apply(lambda v: (v > 0).mean())})


def _selftest():
    ok = True

    def chk(name, got, want, tol=1e-6):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(("PASS " if good else "FAIL ") + f"{name}: got {got:.6g} want {want:.6g}")

    chk("zscore", zscore(pd.Series([1., 2, 3, 4, 5]), 5).iloc[-1], 2 / np.std([1, 2, 3, 4, 5], ddof=1))
    t = np.arange(60)
    chk("halflife exact decay", halflife_days(pd.Series(5 + 3 * 0.9 ** t), scale=1), np.log(2) / -np.log(0.9), 1e-6)
    # Huggins & Schaller OU example: 1w and 1m Sharpe 0.91 / 1.78
    a = dict(x=12.35, mu=1.046, sigma=28.25, k=16.5)
    chk("OU Sharpe 1w", ou_expected_sharpe(h=1 / 52, **a), 0.91, 0.01)
    chk("OU Sharpe 1m", ou_expected_sharpe(h=1 / 12, **a), 1.78, 0.01)
    chk("OU Sharpe analytic hl=h", ou_expected_sharpe(x=10, mu=0, sigma=20, k=np.log(2) / 0.25, h=0.25, carry=2),
        7 / (20 * np.sqrt((1 - 0.25) / (2 * np.log(2) / 0.25))), 1e-9)
    chk("J-score Nordea belly", j_score(79.3, 46.5, 0.64), 2.34, 0.01)
    chk("scorecard median", pctile_to_scorecard(0.5, np.linspace(0, 1, 101)), 0.0, 0.11)
    df = pd.DataFrame({"z": [2.0, 2.0, -2.0], "carry_bp": [15., -15., -15.], "vol_bp": [10.] * 3,
                       "pctile": [0.9, 0.9, 0.1], "halflife_days": [18.] * 3})
    r = composite(df).sort_index()
    chk("composite sell, carry pays", r.score[0], 0.4 * .5 + .25 * .5 + .15 * .8 + .2 * .8)
    chk("composite sell, carry against", r.score[1], 0.4 * .5 + .15 * .8 + .2 * .8)
    chk("composite mirror buy", r.score[2], 0.605)
    chk("cost hurdle", composite(df, cost_hurdle=0.1).sort_index().score[0], 0.505)
    X = np.array([[1, -1], [2, -2], [-3, 3], [1, 1.0]])
    f = frontier_score(X, [1, -1])
    chk("frontier 2f on-line", f[0], np.sqrt(2)); chk("frontier 2f far", f[2], 3 * np.sqrt(2))
    ok &= bool(np.isnan(f[3])); print(("PASS" if np.isnan(f[3]) else "FAIL") + " frontier non-attractive is NaN")
    b = -22 / 18  # LS slope through origin for (1,-1),(2,-2),(-3,3),(2,-4): sum(xy)/sum(x^2)
    f2 = frontier_score(np.array([[1, -1], [2, -2], [-3, 3], [2, -4.0]]), [1, -1])
    chk("frontier 2f off-line projection", f2[3], abs(2 + b * -4) / np.sqrt(1 + b * b))
    X3 = np.array([[1, -1, 2], [2, -1, 3], [1, -2, 3], [-1, 1, -2], [1, 1, 1.0]])  # on plane x3 = x1 - x2
    f3 = frontier_score(X3, [1, -1, 1])
    chk("frontier 3f", f3[0], np.sqrt(6)); chk("frontier 3f opposite", f3[3], np.sqrt(6))
    # sign-orientation invariance of the frontier (Goldman [+,-] vs this skill's [+,+])
    XG = np.array([[1, -1], [2, -2], [-3, 3], [2, -4.0], [1, 1]])
    chk("frontier orientation invariant", np.nansum(frontier_score(XG * [1, -1], [1, 1])), np.nansum(frontier_score(XG, [1, -1])))
    # NaN z, pca_z replaces z, disagreement flag, explicit contrary side, gate, cost_bp
    e = pd.DataFrame({"z": [np.nan, 1.0, 1.0, 2.0], "pca_z": [np.nan, 2.0, -2.0, np.nan], "side": [1, 1, 1, -1],
                      "carry_bp": [5., 0., 0., 0.], "vol_bp": [10.] * 4, "pctile": [.5] * 4, "halflife_days": [90.] * 4}).drop(columns="side")
    re = composite(e).sort_index()
    chk("NaN z scores 0", re.score[0], 0.0)
    chk("pca_z replaces z", re.score[1], 0.4 * 0.5)
    f2 = re["flags"][2] == "z_disagree"
    ok &= bool(f2); print(("PASS" if f2 else "FAIL") + " z_disagree flag")
    rs = composite(e.assign(side=[1, 1, 1, -1])).sort_index()
    chk("explicit side against z gives no z credit", rs.score[3], 0.0)
    chk("carry gate", composite(df, ctv_gate=2.0).sort_index().score[0], 0.48)
    chk("cost_bp hurdle", composite(df.assign(cost_bp=1.0)).sort_index().score[0], 0.605 - (1.0 / 10) * 0.4 / 4)
    jr = j_score(1.7 * 10, 10.0, -0.3)
    chk("jscore carry-led trade is a receiver", np.sign(jr) * jr, 1.4)
    chk("jscore payer sign", np.sign(j_score(-15.0, 10.0, -2.0)) * j_score(-15.0, 10.0, -2.0), 3.5)
    chk("vol floored flag", float(composite(df.assign(vol_bp=0.1))["flags"].str.contains("vol_floored").all()), 1.0)
    br = bucket_report(pd.Series(np.arange(50.0)), pd.Series(np.arange(50.0) - 20), 5)
    chk("bucket top mean / bottom hit", br.mean_pnl.iloc[-1] + br.hit.iloc[0], 24.5 + 0.0)
    mono = bool(br.mean_pnl.is_monotonic_increasing)
    ok &= mono; print(("PASS" if mono else "FAIL") + " bucket report monotonic")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", nargs="?", help="CSV/Parquet of candidates (columns per mode, see docstring)")
    p.add_argument("--mode", default="composite", choices=["composite", "jscore", "frontier"])
    p.add_argument("--weights", help="override, e.g. z=0.5,ctv=0.2,hit=0.1")
    p.add_argument("--hl-max", type=float, default=90.0)
    p.add_argument("--cost-hurdle", type=float, default=0.0)
    p.add_argument("--ctv-gate", type=float, default=0.0, help="carry/vol (horizon basis) below this gives zero carry credit")
    p.add_argument("--out")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.input:
        p.error("input required")
    df = pd.read_parquet(a.input) if a.input.endswith(".parquet") else pd.read_csv(a.input)
    if a.mode == "composite":
        w = dict((k, float(v)) for k, v in (kv.split("=") for kv in a.weights.split(","))) if a.weights else None
        res = composite(df, w, hl_max=a.hl_max, cost_hurdle=a.cost_hurdle, ctv_gate=a.ctv_gate)
    elif a.mode == "jscore":  # receiver J, signed by side so payers rank on equal terms
        jr = j_score(df.carry_bp, df.vol_bp.where(df.vol_bp > 0.5), df.z)  # vol at/below the floor -> NaN, never ranked
        side = df["side"] if "side" in df else np.sign(jr)
        res = df.assign(j=side * jr).sort_values("j", ascending=False)
    else:  # frontier: carry/vol from carry_bp/vol_bp (or a carry_vol column), z, optional trend (z>0 = receive-type cheap)
        df = df if "carry_vol" in df else df.assign(carry_vol=df.carry_bp / df.vol_bp.where(df.vol_bp > 0.5))
        cols = ["carry_vol", "z"] + (["trend"] if "trend" in df else [])
        res = df.assign(frontier=frontier_score(df[cols].to_numpy(), [1, 1, -1][:len(cols)])).sort_values(
            "frontier", ascending=False)
    (res.to_csv(a.out, index=False) if a.out else print(res.to_string(index=False)))


if __name__ == "__main__":
    main()
