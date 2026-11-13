#!/usr/bin/env python3
"""Event sampling, triple-barrier / meta labels, sample weights, purging and FFD fracdiff for rates-RV ML.

Implements the methods of Lopez de Prado, Advances in Financial Machine Learning (2018), Ch.2-5 and 7, adapted to
rates series quoted in bp.

Conventions
- `x`: level of the traded package in bp (yield, spread, fly, basis, ASW) on a business-day index. No logs:
  EUR, JPY, CHF and SEK yields have been negative.
- `side`: +1 = the position makes money when x rises, -1 = when x falls. P&L is in bp per unit of package DV01,
  so pnl_bp = side * (x_t - x_t0) + side * cumulative carry.
- `carry`: optional daily carry + roll-down in bp earned by a side=+1 position (a side=-1 position earns -carry).
- A label i "uses" the bar changes x_t - x_{t-1} for t0_i < t <= t1_i (AFML 4.3, returns r_{t-1,t}).

CLI (input CSV/Parquet with a `date` column plus the level column, e.g. a package series built from curve_par):
    python labeling.py label --input pkg.csv --col level_bp [--side-col side] [--carry-col carry_bp] --out labels.csv
    python labeling.py fracdiff --input pkg.csv --col level_bp [--thres 0.01]
    python labeling.py --selftest
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- sampling
def ewm_vol(x: pd.Series, span: int = 100) -> pd.Series:
    """EWM std of daily bp changes (AFML Snippet 3.1, on bp differences instead of % returns)."""
    return x.diff().ewm(span=span, min_periods=min(span, 20)).std()


def cusum_events(x: pd.Series, h) -> pd.Index:
    """Symmetric CUSUM filter on bp changes (AFML Snippet 2.4). h: scalar or Series (bp) aligned to x."""
    hs = pd.Series(float(h), index=x.index) if np.isscalar(h) else pd.Series(h).reindex(x.index)
    s_pos = s_neg = 0.0
    out = []
    for t, v in x.diff().dropna().items():
        if not np.isfinite(hs[t]):  # threshold warm-up: do not accumulate, or the first valid h fires on old drift
            s_pos = s_neg = 0.0
            continue
        s_pos, s_neg = max(0.0, s_pos + v), min(0.0, s_neg + v)
        if s_neg < -hs[t]:
            s_neg = 0.0
            out.append(t)
        elif s_pos > hs[t]:
            s_pos = 0.0
            out.append(t)
    return pd.Index(out)


# ---------------------------------------------------------------- labels
def triple_barrier(x: pd.Series, events, trgt, pt: float = 1.0, sl: float = 1.0, horizon: int = 20,
                   side=None, carry=None, min_trgt: float = 0.0, vertical_label: str = "sign") -> pd.DataFrame:
    """Triple-barrier labels (AFML 3.4-3.6) on a bp level series.

    trgt: barrier unit in bp at each event (scalar or Series), e.g. ewm_vol(x) * sqrt(horizon).
    pt, sl: multiples of trgt for profit-take / stop-loss; 0 disables that barrier.
    horizon: vertical barrier in bars after t0.
    side: None -> learn the side, labels in {-1, 0, +1} (use pt == sl). Series/scalar of +-1 -> meta-labels {0, 1}.
    Events whose vertical barrier lies beyond the data and that touched nothing are dropped (outcome unknown).
    """
    x = x.dropna()
    idx = x.index
    n = len(idx)
    ev = pd.Index(events).intersection(idx)
    tr = pd.Series(trgt, index=ev, dtype=float) if np.isscalar(trgt) else pd.Series(trgt).reindex(ev)
    meta = side is not None
    sd = pd.Series(1.0 if side is None else side, index=ev, dtype=float) if (side is None or np.isscalar(side)) \
        else pd.Series(side).reindex(ev)
    cy = np.zeros(n) if carry is None else pd.Series(carry).reindex(idx).fillna(0.0).to_numpy()
    xv = x.to_numpy()
    rows = []
    for t0 in ev:
        u, s = tr[t0], sd[t0]
        if not np.isfinite(u) or u <= min_trgt or s == 0 or not np.isfinite(s):
            continue
        i = idx.get_loc(t0)
        j_end = min(i + horizon, n - 1)
        if j_end <= i:
            continue
        path = s * (xv[i + 1:j_end + 1] - xv[i]) + s * np.cumsum(cy[i + 1:j_end + 1])
        hit_pt = np.flatnonzero(path > pt * u) if pt > 0 else np.array([], int)
        hit_sl = np.flatnonzero(path < -sl * u) if sl > 0 else np.array([], int)
        k_pt = hit_pt[0] if hit_pt.size else np.inf
        k_sl = hit_sl[0] if hit_sl.size else np.inf
        if k_pt == np.inf and k_sl == np.inf:
            if i + horizon > n - 1:
                continue  # vertical barrier not yet reached: label unknown
            k, barrier = len(path) - 1, "vert"
        elif k_pt <= k_sl:
            k, barrier = int(k_pt), "pt"
        else:
            k, barrier = int(k_sl), "sl"
        ret = float(path[k])
        if meta:
            label = int(ret > 0)
        elif barrier == "vert" and vertical_label == "zero":
            label = 0
        else:
            label = int(np.sign(ret))
        rows.append((t0, idx[i + 1 + k], ret, barrier, u, s, label))
    return pd.DataFrame(rows, columns=["t0", "t1", "ret_bp", "barrier", "trgt_bp", "side", "label"]).set_index("t0")


# ---------------------------------------------------------------- sample weights
def indicator_matrix(index, t0, t1) -> np.ndarray:
    """1_{t,i} = 1 if label i spans the bar-t change (t0_i < t <= t1_i). Shape (bars, labels)."""
    # ponytail: dense bars x labels matrix; fine for daily data (5k x 2k), use sparse/interval sums for tick data
    pos = pd.Index(index)
    a, b = pos.get_indexer(pd.Index(t0)), pos.get_indexer(pd.Index(t1))
    if (a < 0).any() or (b < 0).any():
        raise ValueError("t0/t1 must be in the bar index")
    m = np.zeros((len(pos), len(a)))
    for j, (i0, i1) in enumerate(zip(a, b)):
        m[i0 + 1:i1 + 1, j] = 1.0
    return m


def avg_uniqueness(m: np.ndarray) -> np.ndarray:
    """Average uniqueness u_i = mean over the label's life of 1/c_t (AFML Snippet 4.4)."""
    c = m.sum(axis=1)
    u = np.divide(m, c[:, None], out=np.zeros_like(m), where=c[:, None] > 0)
    return u.sum(axis=0) / m.sum(axis=0)


def attribution_weights(x: pd.Series, m: np.ndarray, carry=None) -> np.ndarray:
    """|sum of bp changes / concurrency over the label's life|, scaled to sum to I (AFML Snippet 4.10, bp not log)."""
    dx = x.diff().fillna(0.0).to_numpy()
    if carry is not None:
        dx = dx + pd.Series(carry).reindex(x.index).fillna(0.0).to_numpy()
    c = m.sum(axis=1)
    r = np.divide(dx, c, out=np.zeros_like(dx), where=c > 0)
    w = np.abs(r @ m)
    return w * len(w) / w.sum() if w.sum() > 0 else np.ones_like(w)


def time_decay(avg_u: pd.Series, c_last: float = 1.0) -> pd.Series:
    """Piecewise-linear decay on cumulative uniqueness (AFML Snippet 4.11). Newest = 1, oldest ~ c_last;
    c_last < 0 zeroes the oldest |c_last| share."""
    cw = avg_u.sort_index().cumsum()
    tot = cw.iloc[-1]
    slope = (1.0 - c_last) / tot if c_last >= 0 else 1.0 / ((c_last + 1.0) * tot)
    return (1.0 - slope * tot + slope * cw).clip(lower=0.0)


def seq_bootstrap_probs(m: np.ndarray, drawn) -> np.ndarray:
    """Draw probabilities for the next sequential-bootstrap draw given drawn label columns (AFML 4.5.3)."""
    c = m[:, list(drawn)].sum(axis=1) if len(drawn) else np.zeros(m.shape[0])
    u = m / (1.0 + c)[:, None]
    ubar = u.sum(axis=0) / m.sum(axis=0)
    return ubar / ubar.sum()


def seq_bootstrap(m: np.ndarray, size: int | None = None, seed: int = 0) -> list:
    """Sequential bootstrap sample of label columns (AFML Snippet 4.5)."""
    rng = np.random.default_rng(seed)
    drawn = []
    for _ in range(size or m.shape[1]):
        drawn.append(int(rng.choice(m.shape[1], p=seq_bootstrap_probs(m, drawn))))
    return drawn


# ---------------------------------------------------------------- leakage
def purged_train_mask(t0, t1, test_start, test_end, embargo=None) -> np.ndarray:
    """True = usable for training. Drops labels whose [t0, t1] overlaps [test_start, test_end + embargo] (AFML 7.4).
    test_start = first test label's t0; test_end = LAST test label's t1 (not its t0), else up to H bars leak.
    embargo: Timedelta / number (same type as the times) or None. Apply once per test block."""
    t0, t1 = np.asarray(t0), np.asarray(t1)
    end = test_end if embargo is None else test_end + embargo
    return ~((t0 <= end) & (t1 >= test_start))


# ---------------------------------------------------------------- fractional differentiation
def ffd_weights(d: float, thres: float = 1e-2, max_len: int = 100_000) -> np.ndarray:
    """FFD weights, newest first: w0 = 1, w_k = -w_{k-1} (d - k + 1) / k, stop when |w_k| < thres (AFML 5.4-5.5)."""
    w = [1.0]
    for k in range(1, max_len):
        wk = -w[-1] * (d - k + 1) / k
        if abs(wk) < thres:
            break
        w.append(wk)
    return np.array(w)


def frac_diff_ffd(x: pd.Series, d: float, thres: float = 1e-2) -> pd.Series:
    """Fixed-width-window fracdiff: X~_t = sum_k w_k X_{t-k}. First len(w)-1 points are dropped."""
    w = ffd_weights(d, thres)
    xf = x.ffill().dropna()
    if len(xf) < len(w):
        return pd.Series(dtype=float, name=x.name)
    out = pd.Series(np.convolve(xf.to_numpy(), w, mode="valid"), index=xf.index[len(w) - 1:], name=x.name)
    return out[x.reindex(out.index).notna()]


def min_ffd_d(x: pd.Series, grid=None, thres: float = 1e-2, alpha: float = 0.05) -> tuple[float, pd.DataFrame]:
    """Smallest d on the grid whose FFD series rejects a unit root (ADF, maxlag=1, constant; AFML Snippet 5.4)."""
    try:
        from statsmodels.tsa.stattools import adfuller
    except ImportError as e:  # optional dependency
        raise RuntimeError("min_ffd_d needs statsmodels") from e
    grid = np.round(np.linspace(0, 1, 11), 2) if grid is None else grid
    rows = []
    for d in grid:
        f = frac_diff_ffd(x, d, thres)
        if len(f) < 50:
            continue
        stat, p = adfuller(f, maxlag=1, regression="c", autolag=None)[:2]
        rows.append((d, stat, p, len(ffd_weights(d, thres)), len(f), np.corrcoef(x.reindex(f.index), f)[0, 1]))
    tab = pd.DataFrame(rows, columns=["d", "adf_stat", "p_value", "window", "n_obs", "corr_with_level"]).set_index("d")
    ok = tab.index[tab["p_value"] < alpha]
    return (float(ok.min()) if len(ok) else np.nan), tab


# ---------------------------------------------------------------- self-test
def _selftest() -> None:
    def close(a, b, tol=1e-9):
        return np.allclose(np.asarray(a, float), np.asarray(b, float), atol=tol)

    # FFD weights: analytic values
    assert close(ffd_weights(1.0, 1e-5), [1, -1]), ffd_weights(1.0)
    assert close(ffd_weights(2.0, 1e-5), [1, -2, 1])
    assert close(ffd_weights(0.0, 1e-5), [1])
    assert close(ffd_weights(0.5, 1e-5)[:4], [1, -0.5, -0.125, -0.0625])
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2015-01-01", periods=600)
    rw = pd.Series(np.cumsum(rng.normal(0, 3, 600)), index=idx)
    assert close(frac_diff_ffd(rw, 1.0, 1e-5), rw.diff().dropna()), "FFD(d=1) must equal first difference"
    assert close(frac_diff_ffd(rw, 0.0, 1e-5), rw), "FFD(d=0) must equal the level"

    # CUSUM: changes +0.6, +0.6 (S+=1.2>1 -> event), -0.3, -0.8 (S-=-1.1<-1 -> event), +0.5
    xs = pd.Series(np.cumsum([0, 0.6, 0.6, -0.3, -0.8, 0.5]), index=idx[:6])
    assert list(cusum_events(xs, 1.0)) == [idx[2], idx[4]], list(cusum_events(xs, 1.0))
    hw = pd.Series([np.nan, np.nan, 1.0, 1.0, 1.0, 1.0], index=idx[:6])
    assert list(cusum_events(xs, hw)) == [idx[4]], list(cusum_events(xs, hw))  # no event from warm-up drift

    # Triple barrier on deterministic paths, unit 1bp, barriers at +-2bp, vertical 5 bars
    up = pd.Series(np.arange(10.0), index=idx[:10])
    lab = triple_barrier(up, [idx[0]], 1.0, 2, 2, horizon=5)
    assert lab.loc[idx[0], "t1"] == idx[3] and lab.loc[idx[0], "label"] == 1 and lab.loc[idx[0], "barrier"] == "pt"
    lab = triple_barrier(-up, [idx[0]], 1.0, 2, 2, horizon=5)
    assert lab.loc[idx[0], "label"] == -1 and lab.loc[idx[0], "barrier"] == "sl"
    flat = pd.Series(0.0, index=idx[:10])
    lab = triple_barrier(flat, [idx[0]], 1.0, 2, 2, horizon=5)
    assert lab.loc[idx[0], "t1"] == idx[5] and lab.loc[idx[0], "barrier"] == "vert" and lab.loc[idx[0], "label"] == 0
    # carry alone (+0.5bp/day for side +1) crosses +2bp on day 5
    lab = triple_barrier(flat, [idx[0]], 1.0, 2, 2, horizon=8, carry=pd.Series(0.5, index=idx[:10]))
    assert lab.loc[idx[0], "t1"] == idx[5] and lab.loc[idx[0], "label"] == 1
    # the opposite side pays that carry: side -1 is stopped out on day 5 -> meta-label 0
    lab = triple_barrier(flat, [idx[0]], 1.0, 2, 2, horizon=8, side=-1, carry=pd.Series(0.5, index=idx[:10]))
    assert lab.loc[idx[0], "barrier"] == "sl" and lab.loc[idx[0], "label"] == 0
    # meta-label: side -1 on a rising path is a loss -> 0; side +1 -> 1
    lab = triple_barrier(up, [idx[0], idx[1]], 1.0, 2, 2, horizon=5, side=pd.Series([-1, 1], index=idx[:2]))
    assert list(lab["label"]) == [0, 1] and lab["ret_bp"].iloc[0] < 0
    # an event too close to the end that touches nothing is dropped
    assert triple_barrier(flat, [idx[7]], 1.0, 2, 2, horizon=5).empty

    # Uniqueness and sequential bootstrap: AFML 4.5.3 (labels on r_{0,3}, r_{2,4}, r_{4,6})
    bars = idx[:7]
    m = indicator_matrix(bars, bars[[0, 2, 4]], bars[[3, 4, 6]])
    assert close(m.sum(axis=1), [0, 1, 1, 2, 1, 1, 1])
    assert close(avg_uniqueness(m), [5 / 6, 3 / 4, 1.0])
    assert close(seq_bootstrap_probs(m, [1]), [5 / 14, 3 / 14, 6 / 14])
    assert close(seq_bootstrap_probs(m, []), [1 / 3, 1 / 3, 1 / 3])
    # return attribution: bar changes all +1bp -> |1+1+1/2|, |1/2+1|, |1+1| scaled to sum 3
    w = attribution_weights(pd.Series(np.arange(7.0), index=bars), m)
    assert close(w, np.array([2.5, 1.5, 2.0]) * 3 / 6.0)
    # time decay: c=1 no decay; c=0 newest 1 and linear in cumulative uniqueness
    au = pd.Series([1.0, 1.0, 1.0, 1.0], index=idx[:4])
    assert close(time_decay(au, 1.0), [1, 1, 1, 1])
    assert close(time_decay(au, 0.0), [0.25, 0.5, 0.75, 1.0])
    assert close(time_decay(au, -0.5), [0, 0, 0.5, 1.0])

    # Purging: test block bars 10-12, embargo 2 bars
    t0, t1 = np.array([0, 5, 8, 11, 13, 15]), np.array([4, 9, 10, 12, 14, 18])
    assert list(purged_train_mask(t0, t1, 10, 12, embargo=2)) == [True, True, False, False, False, True]

    # min d: white noise needs no differencing; a random walk does but less than 1 (if statsmodels present)
    try:
        import statsmodels  # noqa: F401
    except ImportError:
        print("statsmodels missing: min_ffd_d test skipped")
    else:
        wn = pd.Series(rng.normal(0, 1, 2000), index=pd.bdate_range("2010-01-01", periods=2000))
        assert min_ffd_d(wn)[0] == 0.0
        # seed chosen so the level is clearly I(1) (ADF p ~ 0.96 at d=0); a random walk rejects 5% of the time
        rw2 = pd.Series(np.random.default_rng(2).normal(0, 1, 2000).cumsum(), index=wn.index)
        dstar, tab = min_ffd_d(rw2)
        assert 0.0 < dstar <= 1.0 and tab.loc[0.0, "p_value"] > 0.5 and tab.loc[1.0, "p_value"] < 0.01, tab
    print("selftest passed")


# ---------------------------------------------------------------- CLI
def _read(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    return df.assign(date=pd.to_datetime(df["date"])).set_index("date").sort_index()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    lb = sub.add_parser("label", help="CUSUM events + triple-barrier/meta labels + uniqueness weights")
    fd = sub.add_parser("fracdiff", help="min-d FFD table (ADF)")
    for p in (lb, fd):
        p.add_argument("--input", required=True)
        p.add_argument("--col", default="level_bp")
        p.add_argument("--out")
    lb.add_argument("--side-col", help="primary-model side (+1/-1); gives meta-labels")
    lb.add_argument("--carry-col", help="daily carry+roll in bp for side +1 (x rising); on an outright that is minus the receiver's carry")
    lb.add_argument("--horizon", type=int, default=20, help="vertical barrier, bars")
    lb.add_argument("--pt", type=float, default=1.0)
    lb.add_argument("--sl", type=float, default=1.0)
    lb.add_argument("--span", type=int, default=100, help="EWM span of daily bp vol")
    lb.add_argument("--cusum", type=float, default=1.0, help="CUSUM h in units of daily vol; 0 = every bar")
    lb.add_argument("--min-trgt", type=float, default=0.0, help="drop events with barrier unit <= this (bp)")
    fd.add_argument("--thres", type=float, default=1e-2)
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    if not a.cmd:
        ap.print_help()
        return 1
    df = _read(a.input)
    x = df[a.col].astype(float)
    if a.cmd == "fracdiff":
        dstar, tab = min_ffd_d(x, thres=a.thres)
        print(tab.round(4).to_string())
        print(f"d* = {dstar}")
        if a.out:
            tab.to_csv(a.out)
        return 0
    vol = ewm_vol(x, a.span)
    events = x.index[vol.notna()] if a.cusum <= 0 else cusum_events(x, a.cusum * vol)
    side = df[a.side_col] if a.side_col else None
    carry = df[a.carry_col] if a.carry_col else None
    lab = triple_barrier(x, events, vol * np.sqrt(a.horizon), a.pt, a.sl, a.horizon, side, carry, a.min_trgt)
    if lab.empty:
        print("no completed events")
        return 1
    m = indicator_matrix(x.dropna().index, lab.index, lab["t1"])
    lab["avg_uniqueness"] = avg_uniqueness(m)
    lab["weight"] = attribution_weights(x.dropna(), m, carry)
    print(lab.describe(include="all").T.to_string())
    print(f"mean uniqueness {lab['avg_uniqueness'].mean():.3f}; label shares {lab['label'].value_counts(normalize=True).round(3).to_dict()}")
    if a.out:
        lab.to_csv(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
