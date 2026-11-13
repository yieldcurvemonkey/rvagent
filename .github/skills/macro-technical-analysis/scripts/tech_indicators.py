#!/usr/bin/env python3
"""Technical overlays for G10 rates series: price/TR indices, futures settles, par yields (bp) and spreads.

Functions take pandas Series and return pandas objects. The CLI reads one series from a CSV with a
`date` column (YYYY-MM-DD) and a value column, and writes the indicator table.

  python -I scripts/tech_indicators.py --selftest
  python -I scripts/tech_indicators.py --csv series.csv --value-col value --out indicators.csv
  python -I scripts/tech_indicators.py --csv yields.csv --value-col par_rate_pct --yield-pct --out ind.csv

Sign rule (state it with every signal). Signals named for a view (momentum_consensus, momentum_dummy) are in
DURATION terms: +1 = bullish price = yields falling = long duration (receive). momentum_consensus reads a PRICE
series (futures settle, TR index); for a yield series pass the negated yield (the CLI does this under
--yield-pct). momentum_dummy reads a YIELD in bp and gives +1 when the yield is below its MA. Raw indicators
(sma, ema, rsi_wilder, macd, bollinger, atr) are in the series' own units, so on a yield a high RSI means
yields rose. A spread series (e.g. 10y minus 2y in bp) is read as a steepener trend when rising; do not invert
it. Event study: +1 means "gain when x rises"; pass x_is_yield=True so a duration-sign signal on a yield series
gains when the yield falls.

Look-ahead: every function uses data up to and including t only. A signal computed on the close of t can be
traded no earlier than the next session, so the event study enters at t + lag (default 1).
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pandas as pd


# ---------- moving averages and oscillators ----------

def sma(x: pd.Series, n: int) -> pd.Series:
    """Simple moving average over n observations (NaN until n values exist)."""
    return x.rolling(n, min_periods=n).mean()


def ema(x: pd.Series, span: int) -> pd.Series:
    """EMA with alpha = 2/(span+1), seeded with the first value: EMA_t = (1-a) EMA_{t-1} + a x_t.
    NaN until `span` observations exist; the seed still biases roughly the first three spans, so discard that."""
    return x.ewm(alpha=2.0 / (span + 1), adjust=False, min_periods=span).mean()


def ema_mu(d: int) -> float:
    """Recursion weight mu = 1 - 2/(d+1) in EMA_t = mu EMA_{t-1} + (1-mu) x_t. mu = 0.96 gives d = 49."""
    return 1.0 - 2.0 / (d + 1)


def rsi_wilder(x: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI on the level series x: RS = avg gain / avg loss (Wilder smoothing, alpha = 1/n),
    RSI = 100 - 100 / (1 + RS). Equal average gains and losses give 50. Applied to a yield series,
    a low RSI means yields have fallen fast (receivers crowded), a high RSI the reverse. A perfectly flat
    window (no gains, no losses) returns NaN. Seeded with the first move rather than Wilder's SMA seed:
    allow about 100 bars before trusting the level."""
    d = x.diff()
    gain = d.clip(lower=0.0)
    loss = (-d).clip(lower=0.0)
    ag = gain.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    al = loss.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return 100.0 - 100.0 / (1.0 + ag / al)


def macd(x: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9) -> pd.DataFrame:
    """MACD line = EMA(fast) - EMA(slow); signal = EMA(sig) of the line; hist = line - signal."""
    line = ema(x, fast) - ema(x, slow)
    signal = ema(line, sig)
    return pd.DataFrame({"macd": line, "signal": signal, "hist": line - signal})


def bollinger(x: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Bands = SMA(n) +/- k * sample SD(n); %B = (x - lower) / (upper - lower)."""
    mid = sma(x, n)
    sd = x.rolling(n, min_periods=n).std(ddof=1)
    upper = mid + k * sd
    lower = mid - k * sd
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower, "pct_b": (x - lower) / (upper - lower)})


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """TR = max(H - L, |H - prev close|, |L - prev close|). For a close-only series pass the close as high and
    low: TR = |dP|, which is about half the true OHLC range (E|dP| ~ 0.8 sigma vs E[range] ~ 1.6 sigma)."""
    pc = close.shift(1)
    return pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Average true range as a simple moving average of TR over n bars (Wilder's original smooths with
    alpha = 1/n; the two differ little). A close-only ATR is about half the OHLC value: double it before
    applying a k x ATR stop calibrated on OHLC data."""
    return true_range(high, low, close).rolling(n, min_periods=n).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.DataFrame:
    """Wilder DMI/ADX. Needs daily HIGH and LOW. On close-only data DX collapses to |2 RSI - 100| and the
    20/30 thresholds do not apply (a pure random walk then sits above 30 about 10 percent of the time).
    +DM = up-move if it exceeds the down-move and is positive; -DM likewise; DI = 100 smooth(DM) / smooth(TR);
    DX = 100 |+DI - -DI| / (+DI + -DI); ADX = Wilder smoothing (alpha 1/n) of DX."""
    up = high.diff()
    dn = -low.diff()
    plus = up.where((up > dn) & (up > 0), 0.0).where(up.notna())
    minus = dn.where((dn > up) & (dn > 0), 0.0).where(dn.notna())
    tr = true_range(high, low, close).where(up.notna())

    def w(v):
        return v.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()

    pdi, mdi = 100.0 * w(plus) / w(tr), 100.0 * w(minus) / w(tr)
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi)
    return pd.DataFrame({"plus_di": pdi, "minus_di": mdi, "adx": w(dx)})


# ---------- trend and momentum reads ----------

def momentum_consensus(price: pd.Series, short: int = 21, long: int = 252) -> pd.Series:
    """Two-horizon consensus on a PRICE index: +1 if above both SMAs, -1 if below both, else 0 (ties are 0,
    so a flat or stale series is neutral). NaN until the long SMA exists. Defaults are 21 and 252 trading
    days (1m and 12m). Duration sign: +1 = long duration. For a yield series pass the negated yield."""
    s = sma(price, short)
    l_ = sma(price, long)
    out = pd.Series(0.0, index=price.index)
    out[(price > s) & (price > l_)] = 1.0
    out[(price < s) & (price < l_)] = -1.0
    out[l_.isna() | s.isna() | price.isna()] = np.nan
    return out


def tmac_sum(price: pd.Series, windows=(10, 20, 30)) -> pd.Series:
    """Triple moving-average cross sum, -9..+9 for three windows (BofA Technicals Explained): nine conditions
    scored +1 / -1 / 0: price vs each SMA (3), each SMA vs each longer SMA (3 pairs: shorter above = +1), and
    the slope of each SMA (3). Slope is MA_t - MA_{t-1} (an implementation choice; the source gives none).
    Ties score 0, so even sums occur and thresholds such as 6, 2 and 0 are reachable. On a PRICE series
    positive = bullish price = long duration; for a yield pass the negated yield. NaN until the longest SMA exists."""
    w = sorted(windows)
    mas = [sma(price, n) for n in w]
    parts = [np.sign(price - m) for m in mas]
    parts += [np.sign(mas[i] - mas[j]) for i in range(len(w)) for j in range(i + 1, len(w))]
    parts += [np.sign(m.diff()) for m in mas]
    out = sum(parts)
    out[mas[-1].isna() | mas[-1].shift(1).isna() | price.isna()] = np.nan
    return out


def ma_aggregator(price: pd.Series, windows=(5, 10, 20, 30, 50, 100, 200)) -> pd.Series:
    """Moving-average aggregator (MAA, BofA FX Quant Primer, 2018) in percent: the share of pairwise comparisons
    among [price, SMA(w) for w in windows] in which the shorter-horizon series is above the longer-horizon one
    (ordering: price, then ascending windows; ties are not bullish: an implementation choice). The default 7
    windows give 8 series and 28 pairs; 100 = all bullish, 50 = 14 of 28. Source labels: uptrend above 60,
    downtrend below 40. NaN until the longest SMA exists. Same sign rule as tmac_sum (price series)."""
    series = [price] + [sma(price, n) for n in sorted(windows)]
    pairs = [(i, j) for i in range(len(series)) for j in range(i + 1, len(series))]
    bull = sum((series[i] > series[j]).astype(float) for i, j in pairs)
    out = 100.0 * bull / len(pairs)
    out[series[-1].isna() | price.isna()] = np.nan
    return out


def momentum_dummy(yield_bp: pd.Series, n: int = 126, band_bp: float = 5.0) -> pd.Series:
    """Yield momentum dummy on a YIELD series in bp: +1 if the yield is more than band_bp BELOW its
    n-period MA (bond bullish), -1 if more than band_bp ABOVE, 0 inside the band (whipsaw filter).
    n = 126 is about six months of daily data; the source used month-end data (n = 6). The band is in level
    space, so on daily sampling it is a far smaller fraction of the typical deviation and filters little:
    prefer month-end sampling, or scale band_bp to the series' volatility. Duration sign: +1 = long duration."""
    ma = sma(yield_bp, n)
    dev = yield_bp - ma
    out = pd.Series(0.0, index=yield_bp.index)
    out[dev < -band_bp] = 1.0
    out[dev > band_bp] = -1.0
    out[ma.isna()] = np.nan
    return out


def sigma_move(ret: pd.Series, lam: float = 0.97, warmup: int = 20) -> pd.Series:
    """Return divided by the PRIOR-day EWMA volatility: sigma_t = r_t / sqrt(var_{t-1}), with
    var_t = lam var_{t-1} + (1 - lam) r_t^2 (zero-mean). The variance is seeded with the mean square of the
    first `warmup` finite returns and those positions are NaN, so one small first return cannot inflate the
    early values. NaN returns are skipped; a zero prior variance gives NaN, not an error. The FOMC and
    payrolls triggers in the source use a trailing one-month SD instead: see sigma_move_rolling."""
    r = ret.to_numpy(dtype=float)
    out = np.full(len(r), np.nan)
    seed, var = [], np.nan
    for t, rt in enumerate(r):
        if np.isnan(rt):
            continue
        if np.isnan(var):
            seed.append(rt * rt)
            if len(seed) >= warmup:
                var = float(np.mean(seed))
            continue
        if var > 0.0:
            out[t] = rt / math.sqrt(var)
        var = lam * var + (1.0 - lam) * rt * rt
    return pd.Series(out, index=ret.index)


def sigma_move_rolling(ret: pd.Series, n: int = 21) -> pd.Series:
    """Return divided by the sample SD of the previous n returns (today excluded): the trailing one-month
    definition used by the event rules. NaN until n prior returns exist."""
    return ret / ret.shift(1).rolling(n, min_periods=n).std(ddof=1)


# ---------- levels and expectations ----------

def fib_bounce_from_low(low: float, high: float, r: float) -> float:
    """Retracement level of a bounce from a low after a fall from high: low + r (high - low)."""
    return low + r * (high - low)


def fib_pullback_from_high(low: float, high: float, r: float) -> float:
    """Retracement level of a pullback from a high after a rise from low: high - r (high - low)."""
    return high - r * (high - low)


def expected_trend_return(sigma: float, rho: float, mu: float = 0.0,
                          mu_f: float = 0.0, sigma_f: float = 1.0) -> float:
    """Gaussian expected return of a trend rule (Acar 1994 form, as presented in Dunis, Laws & Naim 2003):
    E(r) = sqrt(2/pi) sigma rho exp(-mu_f^2 / (2 sigma_f^2)) + mu (1 - 2 Phi(-mu_f / sigma_f)),
    rho = corr(next-period return, trend forecast). Without drift: E(r) = sqrt(2/pi) sigma rho."""
    phi_neg = 0.5 * (1.0 + math.erf((-mu_f / sigma_f) / math.sqrt(2.0)))
    return (math.sqrt(2.0 / math.pi) * sigma * rho * math.exp(-(mu_f ** 2) / (2 * sigma_f ** 2))
            + mu * (1.0 - 2.0 * phi_neg))


def signal_forward_changes(x: pd.Series, signal: pd.Series, horizons=(5, 20, 45, 80), lag: int = 1,
                           x_is_yield: bool = False) -> pd.DataFrame:
    """Event study: signal_t * (x_{t+lag+h} - x_{t+lag}) on every non-zero signal, i.e. entry `lag` bars after
    the signal (default 1: a close-t signal is traded at the next close). The sign is "gain when x rises";
    set x_is_yield=True so a duration-sign signal (+1 = long duration) on a yield series gains when the yield
    falls. Per horizon: n; n_indep (about n / h: windows overlap, so n overstates the evidence, use n_indep
    or a block bootstrap for inference); mean signed change; hit rate (share > 0); base_mean (unconditional
    mean change over all dates in the same sign convention, the always-long comparator). Units are those of
    x (bp for yields or spreads, points for prices)."""
    rows = []
    sgn = -1.0 if x_is_yield else 1.0
    entry = x.shift(-lag)
    for h in horizons:
        fwd = sgn * (x.shift(-(lag + h)) - entry)
        m = signal.notna() & fwd.notna() & (signal != 0)
        s = signal[m] * fwd[m]
        rows.append({"horizon": h, "n": int(m.sum()), "n_indep": round(m.sum() / h, 1),
                     "mean_signed": float(s.mean()) if len(s) else np.nan,
                     "hit_rate": float((s > 0).mean()) if len(s) else np.nan,
                     "base_mean": float(fwd.mean()) if fwd.notna().any() else np.nan})
    return pd.DataFrame(rows)


# ---------- self-test (known answers) ----------

def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol


def _same(a: pd.Series, b: pd.Series) -> bool:
    """Equal where both are finite and NaN in the same places."""
    return bool((a.isna() == b.isna()).all() and np.allclose(a.dropna().to_numpy(), b.dropna().to_numpy()))


def selftest() -> int:
    fails = []

    def check(name, ok):
        if not ok:
            fails.append(name)

    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    check("sma(1..5, 3) last == 4", _close(sma(x, 3).iloc[-1], 4.0))
    e = ema(pd.Series([1.0, 2.0, 3.0]), 3)  # alpha 0.5: 1, 1.5, 2.25
    check("ema span 3 last == 2.25", _close(e.iloc[-1], 2.25))
    check("ema_mu(49) == 0.96", _close(ema_mu(49), 0.96))

    up = pd.Series(np.arange(60, dtype=float))
    check("rsi of a rising series == 100", _close(rsi_wilder(up).iloc[-1], 100.0))
    down = pd.Series(-np.arange(60, dtype=float))
    check("rsi of a falling series == 0", _close(rsi_wilder(down).iloc[-1], 0.0))
    # Equal up and down moves: the two-bar average of RSI is exactly 50 in steady state (ripple cancels).
    alt = pd.Series([1.0 if i % 2 == 0 else -1.0 for i in range(300)]).cumsum()
    check("rsi of alternating +-1 averages ~50", abs(rsi_wilder(alt).iloc[-2:].mean() - 50.0) < 0.5)
    # Hand calc, n = 2 (alpha 0.5): x = 0,1,0,2 -> gains 1,0,2 / losses 0,1,0 -> avg gain 1.25, avg loss 0.25,
    # RS = 5, RSI = 100 - 100/6 = 83.333. Pins the smoothing constant (1/n, not 2/(n+1)).
    check("rsi n=2 hand value == 83.333", _close(rsi_wilder(pd.Series([0.0, 1.0, 0.0, 2.0]), 2).iloc[-1],
                                                 100.0 - 100.0 / 6.0, 1e-9))

    const = pd.Series(np.full(120, 3.0))
    check("macd of a constant series == 0", np.allclose(macd(const)["macd"].dropna().to_numpy(), 0.0))
    ramp = pd.Series(np.arange(400, dtype=float))  # EMA lags a unit ramp by (span-1)/2: line -> 12.5 - 5.5 = 7
    mr = macd(ramp)
    check("macd of a unit ramp converges to 7 (spans 12/26)", _close(mr["macd"].iloc[-1], 7.0, 1e-6))
    check("macd hist of a unit ramp converges to 0", _close(mr["hist"].iloc[-1], 0.0, 1e-6))

    # Independent pure-python MACD (alpha 2/(span+1), seeded with the first value) pins all three spans.
    def _ema_ref(v, span):
        a_, o = 2.0 / (span + 1), [v[0]]
        for q in v[1:]:
            o.append((1 - a_) * o[-1] + a_ * q)
        return o
    vv = [float((i * 7) % 11) for i in range(200)]
    ln = [p_ - q_ for p_, q_ in zip(_ema_ref(vv, 12), _ema_ref(vv, 26))]
    check("macd line/signal/hist match a reference recursion (12/26/9)",
          np.allclose(macd(pd.Series(vv))["signal"].iloc[-1], _ema_ref(ln, 9)[-1], atol=1e-9)
          and np.allclose(macd(pd.Series(vv))["macd"].iloc[-1], ln[-1], atol=1e-9))

    lin = pd.Series(np.arange(1, 41, dtype=float))  # last 20 = 21..40: mean 30.5, sample var 35
    bb = bollinger(lin)
    check("bollinger upper = 30.5 + 2 sqrt(35)", _close(bb["upper"].iloc[-1], 30.5 + 2 * math.sqrt(35.0), 1e-9))
    check("bollinger %B last = (40 - lower)/(4 sqrt 35)",
          _close(bb["pct_b"].iloc[-1], (40.0 - (30.5 - 2 * math.sqrt(35.0))) / (4 * math.sqrt(35.0)), 1e-9))

    h = pd.Series([10.0, 10.0])
    lo = pd.Series([9.0, 9.0])
    c = pd.Series([7.0, 9.5])
    check("true range = 3 when prior close is far below", _close(true_range(h, lo, c).iloc[1], 3.0))
    hh = pd.Series(np.full(30, 10.0))
    ll = pd.Series(np.full(30, 7.0))
    cc = pd.Series(np.full(30, 8.5))
    check("atr of constant TR 3 == 3", _close(atr(hh, ll, cc, 14).iloc[-1], 3.0))
    cl = pd.Series([1.0, 3.0, 2.0, 6.0])  # close-only TR = |dP| = 2, 1, 4
    check("close-only TR == |dP|", np.allclose(true_range(cl, cl, cl).iloc[1:].to_numpy(), [2.0, 1.0, 4.0]))
    check("atr n=2 of |dP| 1, 4 == 2.5 (mean, not max)", _close(atr(cl, cl, cl, 2).iloc[-1], 2.5))

    # ADX: unit-ramp close with high/low = close +/- 0.5: TR 1.5, +DM 1, -DM 0 -> +DI 66.67, -DI 0, DX 100, ADX 100.
    rc = pd.Series(np.arange(80, dtype=float))
    ax = adx(rc + 0.5, rc - 0.5, rc)
    check("adx of a ramp: ADX == 100", _close(ax["adx"].iloc[-1], 100.0, 1e-9))
    check("adx of a ramp: +DI == 66.667, -DI == 0",
          _close(ax["plus_di"].iloc[-1], 100.0 / 1.5, 1e-9) and _close(ax["minus_di"].iloc[-1], 0.0))
    # n = 1 (no smoothing). Bar 0 H10 L8 C9; bar 1 H11 L6 (down-move 2 > up-move 1): +DM 0, -DM 2, TR 5 -> -DI 40, +DI 0.
    a1 = adx(pd.Series([10.0, 11.0]), pd.Series([8.0, 6.0]), pd.Series([9.0, 10.0]), n=1)
    check("adx dominant-move rule: -DI == 40, +DI == 0", _close(a1["minus_di"].iloc[-1], 40.0) and _close(a1["plus_di"].iloc[-1], 0.0))
    zz = pd.Series([0.0, 1.0] * 60)  # up/down in turn: no net direction
    az = adx(zz + 0.5, zz - 0.5, zz)
    check("adx of a zig-zag is below 20", az["adx"].iloc[-1] < 20.0)

    inc = pd.Series(np.arange(300, dtype=float))
    dec = pd.Series(np.arange(300, dtype=float)[::-1])
    check("consensus rising price == +1", momentum_consensus(inc).iloc[-1] == 1.0)
    check("consensus falling price == -1", momentum_consensus(dec).iloc[-1] == -1.0)
    flat_then_up = pd.Series(np.concatenate([np.full(260, 100.0), [100.0, 101.0, 102.0]]))
    check("consensus NaN before long SMA exists", np.isnan(momentum_consensus(flat_then_up.iloc[:100]).iloc[-1]))
    check("consensus of a flat (tied) series == 0", momentum_consensus(pd.Series(np.full(300, 100.0))).iloc[-1] == 0.0)
    # 231 days at 200, then 21 days at 100, then 150: SMA21 ~ 102.4 (price above), SMA252 ~ 191.7 (price below)
    mixed = pd.Series(np.concatenate([np.full(231, 200.0), np.full(21, 100.0), [150.0]]))
    check("consensus mixed (above 1m, below 12m) == 0", momentum_consensus(mixed).iloc[-1] == 0.0)

    # TMAC by hand, windows (2, 3, 4) on 1,2,3,4,6,5: price 5 vs MA2 5.5 / MA3 5.0 / MA4 4.5 = -1, 0, +1;
    # MA2 > MA3 > MA4 = +3; MA slopes (5.5 vs 5.0, 5.0 vs 4.333, 4.5 vs 3.75) all up = +3; sum = 6.
    tm = pd.Series([1.0, 2.0, 3.0, 4.0, 6.0, 5.0])
    check("tmac sum by hand == 6", tmac_sum(tm, (2, 3, 4)).iloc[-1] == 6.0)
    check("tmac ramp == +9, falling ramp == -9, flat == 0",
          tmac_sum(inc).iloc[-1] == 9.0 and tmac_sum(dec).iloc[-1] == -9.0
          and tmac_sum(pd.Series(np.full(300, 100.0))).iloc[-1] == 0.0)
    check("tmac NaN before the longest SMA exists", np.isnan(tmac_sum(inc.iloc[:25]).iloc[-1]))
    # MAA by hand, windows (2, 3): series price 5, MA2 5.5, MA3 5.0. Pairs: (price, MA2) no, (price, MA3) tie = no,
    # (MA2, MA3) yes -> 1 of 3 = 33.33.
    check("maa by hand == 33.33", _close(ma_aggregator(tm, (2, 3)).iloc[-1], 100.0 / 3.0, 1e-9))
    check("maa ramp == 100, falling ramp == 0 (28 pairs)",
          ma_aggregator(inc).iloc[-1] == 100.0 and ma_aggregator(dec).iloc[-1] == 0.0)

    y = pd.Series([400.0] * 200 + [420.0])  # yield jumps 20 bp above its flat MA
    check("momentum dummy: yield far above MA = -1", momentum_dummy(y, n=126, band_bp=5.0).iloc[-1] == -1.0)
    yd = pd.Series([400.0] * 200 + [380.0])  # yield 20 bp below its flat MA: bond bullish
    check("momentum dummy: yield far below MA = +1", momentum_dummy(yd, n=126, band_bp=5.0).iloc[-1] == 1.0)
    y2 = pd.Series([400.0] * 200 + [402.0])  # inside the 5 bp band
    check("momentum dummy: inside band = 0", momentum_dummy(y2, n=126, band_bp=5.0).iloc[-1] == 0.0)

    check("fib bounce 61.8 pct of 1.0 to 2.0 == 1.618", _close(fib_bounce_from_low(1.0, 2.0, 0.618), 1.618))
    check("fib pullback 38.2 pct of 1.0 to 2.0 == 1.618", _close(fib_pullback_from_high(1.0, 2.0, 0.382), 1.618))

    check("acar expected return with no drift == sqrt(2/pi) sigma rho",
          _close(expected_trend_return(1.0, 1.0), math.sqrt(2 / math.pi), 1e-12))
    # Drift term alone (rho = 0), mu = 1, mu_f = sigma_f = 1: 1 - 2 Phi(-1) = 0.682689 (the 1-sigma coverage).
    check("acar drift term == 0.682689", _close(expected_trend_return(1.0, 0.0, mu=1.0, mu_f=1.0, sigma_f=1.0),
                                                 0.6826894921370859, 1e-9))
    check("acar exp term == sqrt(2/pi) exp(-1/2)",
          _close(expected_trend_return(1.0, 1.0, mu_f=1.0, sigma_f=1.0), math.sqrt(2 / math.pi) * math.exp(-0.5), 1e-12))

    # Event study. Rising x, constant +1 signal: any lag gives +5 over h = 5, hit rate 1.
    trend = pd.Series(np.arange(100, dtype=float))
    sig = pd.Series(1.0, index=trend.index)
    fs = signal_forward_changes(trend, sig, horizons=(5,))
    check("forward study mean signed change == 5", _close(fs["mean_signed"].iloc[0], 5.0))
    check("forward study hit rate == 1", _close(fs["hit_rate"].iloc[0], 1.0))
    check("forward study n == 94 (100 - lag - h) and base_mean == 5",
          fs["n"].iloc[0] == 94 and _close(fs["base_mean"].iloc[0], 5.0))
    # Execution lag: x jumps by 10 after t = 2. A signal at t = 2 earns it at lag 0 and misses it at lag 1.
    step = pd.Series([0.0, 0.0, 0.0, 10.0, 10.0, 10.0, 10.0])
    one = pd.Series([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0])
    check("event study lag 0 captures the jump", _close(signal_forward_changes(step, one, (1,), lag=0)["mean_signed"].iloc[0], 10.0))
    check("event study lag 1 does not", _close(signal_forward_changes(step, one, (1,), lag=1)["mean_signed"].iloc[0], 0.0))
    # Yield sign: yield falls 1bp a day, +1 duration signal must WIN (hit rate 1, +5bp over 5 days); a short loses.
    yfall = pd.Series(500.0 - np.arange(100, dtype=float))
    fy = signal_forward_changes(yfall, sig, horizons=(5,), x_is_yield=True)
    check("yield event study: long duration on falling yield == +5, hit 1",
          _close(fy["mean_signed"].iloc[0], 5.0) and _close(fy["hit_rate"].iloc[0], 1.0))
    fy2 = signal_forward_changes(yfall, -sig, horizons=(5,), x_is_yield=True)
    check("yield event study: short duration on falling yield == -5, hit 0",
          _close(fy2["mean_signed"].iloc[0], -5.0) and _close(fy2["hit_rate"].iloc[0], 0.0))

    # sigma_move: var0 = 1e-4; var1 = 0.97e-4 + 0.03 * 9e-4 = 1.24e-4; sigma_2 = 0.01 / sqrt(1.24e-4) = 0.89803
    rets = pd.Series([0.01, 0.03, 0.01])
    sm = sigma_move(rets, lam=0.97, warmup=1)
    check("sigma move second return == 3.0", _close(sm.iloc[1], 3.0, 1e-9))
    check("sigma move with lam 0.97 == 0.89803", abs(sm.iloc[2] - 0.89803) < 1e-4)
    lead = sigma_move(pd.Series([np.nan, 0.01, 0.03, 0.01]), lam=0.97, warmup=1)
    check("sigma move skips a leading NaN", np.isnan(lead.iloc[0]) and abs(lead.iloc[3] - 0.89803) < 1e-4)
    zero = sigma_move(pd.Series([0.0, 0.01, 0.02]), warmup=1)
    check("sigma move with a zero seed does not raise and is NaN", np.isnan(zero.iloc[1]))
    check("sigma move is NaN through the warm-up", sigma_move(pd.Series([0.01, 0.02, 0.01, 0.03]), warmup=3).iloc[:3].isna().all())
    rng = np.random.default_rng(7)
    z = sigma_move(pd.Series(rng.standard_normal(20000) * 0.05)).dropna()
    check("sigma move of iid returns has SD close to 1", 0.95 < z.std() < 1.08)
    # Rolling version: prior 3 returns 1,2,3 have SD 1; today's 4 -> 4.
    check("sigma_move_rolling excludes today",
          _close(sigma_move_rolling(pd.Series([1.0, 2.0, 3.0, 4.0]), n=3).iloc[3], 4.0))

    # Causality: values at t must not change when later data are appended (no look-ahead).
    px = pd.Series(100.0 + np.cumsum(rng.standard_normal(500)))
    for name, f in [("sma", lambda s: sma(s, 55)), ("ema", lambda s: ema(s, 26)), ("rsi", rsi_wilder),
                    ("macd", lambda s: macd(s)["hist"]), ("bollinger", lambda s: bollinger(s)["pct_b"]),
                    ("consensus", momentum_consensus), ("dummy", lambda s: momentum_dummy(s, 126, 2.0)),
                    ("sigma_move", sigma_move), ("tmac", tmac_sum), ("maa", ma_aggregator), ("adx", lambda s: adx(s + 1, s - 1, s)["adx"])]:
        check("no look-ahead: " + name, _same(f(px).iloc[:300], f(px.iloc[:300])))

    # CLI path: a falling yield (percent) must read as +1 long duration under --yield-pct.
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "y.csv")
        dates = pd.date_range("2020-01-01", periods=300, freq="B")
        pd.DataFrame({"date": dates, "value": 5.0 - 0.01 * np.arange(300)}).to_csv(fp, index=False)
        r_ = run_csv(fp, "value", None, True)
        check("CLI: falling yield -> consensus +1 and dummy +1",
              r_["momentum_consensus"].iloc[-1] == 1.0 and r_["yield_momentum_dummy"].iloc[-1] == 1.0)

    if fails:
        print("SELFTEST FAILED:", ", ".join(fails))
        return 1
    print("selftest ok")
    return 0


# ---------- CLI ----------

def run_csv(path: str, value_col: str, out: str | None, yield_pct: bool) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
    if df.index.has_duplicates:
        raise ValueError("duplicate dates in input: one row per date is required")
    x = df[value_col].astype(float)
    res = pd.DataFrame(index=x.index)
    res["value"] = x
    res["sma55"] = sma(x, 55)
    res["sma200"] = sma(x, 200)
    res["rsi14"] = rsi_wilder(x, 14)
    m = macd(x)
    res["macd"] = m["macd"]
    res["macd_signal"] = m["signal"]
    res["boll_pct_b"] = bollinger(x)["pct_b"]
    # consensus is read on a price: under --yield-pct the series is a yield, so negate it (+1 = long duration)
    res["momentum_consensus"] = momentum_consensus(-x if yield_pct else x)
    res["tmac_sum"] = tmac_sum(-x if yield_pct else x)
    res["maa_pct"] = ma_aggregator(-x if yield_pct else x)
    if yield_pct:
        res["yield_momentum_dummy"] = momentum_dummy(x * 100.0, n=126, band_bp=5.0)
    if out:
        res.to_csv(out, float_format="%.6f")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run known-answer checks and exit")
    ap.add_argument("--csv", help="input CSV with a date column (YYYY-MM-DD) and a value column")
    ap.add_argument("--value-col", default="value", help="column to analyse (default: value)")
    ap.add_argument("--yield-pct", action="store_true",
                    help="value is a yield in percent: add the bp momentum dummy and read the consensus on the negated yield")
    ap.add_argument("--out", help="output CSV path")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.csv:
        ap.print_help()
        return 2
    res = run_csv(args.csv, args.value_col, args.out, args.yield_pct)
    print(res.tail(5).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
