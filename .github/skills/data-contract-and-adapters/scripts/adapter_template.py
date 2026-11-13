"""Adapter template for the canonical RV data contract (tables and units: ../references/schemas.md).

Copy to adapters/<source>_adapter.py, then either
  * subclass DataSource and implement tables() and read() against your source (vendor SDK, database, internal
    pricer), converting to canonical columns and units at this edge; or
  * have an export job write canonical CSV/Parquet into data/ and use FileSource unchanged.
read_asof() makes any read point-in-time. Vendor-specific code lives only in adapters/, never in a skill.

    python adapter_template.py data --table curve_par --start 2026-01-01 --as-of 2026-11-10 --where tenor=10Y
    python adapter_template.py data --table infl_fixings --as-of 2026-03-20 --key index_id,ref_month
    python adapter_template.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

DATE_NAME = re.compile(r"^(date|.*_date|valid_from|valid_to|eligible_from|eligible_to)$")
VALIDITY = (("valid_from", "valid_to"), ("eligible_from", "eligible_to"))
RESULT_COLS = ("allotted_ccy", "stop_yield_pct", "avg_yield_pct", "wi_yield_pct", "tail_bp", "bid_to_cover")  # auctions


def to_utc(t) -> pd.Timestamp:
    """Decision instant in UTC. A bare date (YYYY-MM-DD) means the end of that day."""
    ts = pd.Timestamp(t)
    if isinstance(t, str) and len(t.strip()) == 10:
        ts += pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")


def point_in_time(df: pd.DataFrame, as_of, key: list[str] | None = None) -> pd.DataFrame:
    """Keep rows knowable at `as_of`; with `key`, keep only the latest vintage (by pub_ts_utc) per key.

    date <= as_of date; pub_ts_utc <= as_of (null = never known); ts_utc and exec_ts_utc <= as_of when present;
    valid_from <= d < valid_to and eligible_from <= d < eligible_to (null end = open). Auction result columns are
    blanked (row kept) unless results_ts_utc <= as_of.
    """
    t = to_utc(as_of)
    d = pd.Timestamp(t.date())
    m = pd.Series(True, index=df.index)
    if "date" in df:
        m &= df["date"] <= d
    if "pub_ts_utc" in df:
        m &= df["pub_ts_utc"] <= t
    for c in ("ts_utc", "exec_ts_utc"):
        if c in df:
            m &= df[c].isna() | (df[c] <= t)
    for lo, hi in VALIDITY:
        if lo in df:
            m &= df[lo] <= d
        if hi in df:
            m &= df[hi].isna() | (df[hi] > d)
    out = df[m]
    if "results_ts_utc" in out:
        hide = out["results_ts_utc"].isna() | (out["results_ts_utc"] > t)
        out = out.copy()
        out.loc[hide, [c for c in RESULT_COLS if c in out]] = float("nan")
    if key and "pub_ts_utc" in out:
        out = out.sort_values("pub_ts_utc", kind="stable").drop_duplicates(key, keep="last")
    return out.reset_index(drop=True)


class DataSource(ABC):
    """Minimum adapter interface. Every method returns canonical tables with canonical column names and units."""

    name = "abstract"

    @abstractmethod
    def tables(self) -> set[str]:
        """Canonical table names this source can serve."""

    @abstractmethod
    def read(self, table: str, start=None, end=None, where: dict | None = None) -> pd.DataFrame:
        """Rows of `table` with start <= date <= end (when the table has `date`) and column == value per `where`.
        Date columns as datetime64, `*ts_utc` columns as tz-aware UTC. Raise FileNotFoundError/KeyError when the
        table is not available, so the agent asks for it instead of guessing."""

    def read_asof(self, table: str, as_of, key: list[str] | None = None, start=None, end=None,
                  where: dict | None = None) -> pd.DataFrame:
        """Point-in-time read: what a decision taken at `as_of` could have seen."""
        return point_in_time(self.read(table, start, end, where), as_of, key)


def _load(f: Path) -> pd.DataFrame:
    if f.suffix == ".parquet":
        try:
            df = pd.read_parquet(f)
        except ImportError as e:  # pyarrow is optional
            raise SystemExit(f"reading {f.name} needs pyarrow: pip install pyarrow ({e})")
    else:
        df = pd.read_csv(f)
    for c in df.columns:
        if DATE_NAME.match(c):
            df[c] = pd.to_datetime(df[c])
        elif c.endswith("ts_utc"):
            df[c] = pd.to_datetime(df[c], utc=True, format="ISO8601")
    return df


class FileSource(DataSource):
    """Reads canonical tables from <root>/<table>.parquet, <root>/<table>.csv or a <root>/<table>/ folder of parts."""

    name = "files"

    def __init__(self, root="data"):
        self.root = Path(root)

    def _files(self, table: str) -> list[Path]:
        d = self.root / table
        if d.is_dir():
            return sorted(d.rglob("*.parquet")) + sorted(d.rglob("*.csv"))
        return [p for p in (self.root / f"{table}.parquet", self.root / f"{table}.csv") if p.exists()]

    def tables(self) -> set[str]:
        if not self.root.exists():
            return set()
        return {p.stem for p in self.root.iterdir() if p.suffix in (".csv", ".parquet")} | {
            p.name for p in self.root.iterdir() if p.is_dir() and self._files(p.name)}

    def read(self, table, start=None, end=None, where=None):
        files = self._files(table)
        if not files:
            raise FileNotFoundError(f"no canonical '{table}' under {self.root}: ask the user or the data adapter")
        df = pd.concat([_load(f) for f in files], ignore_index=True)
        if "date" in df:
            if start is not None:
                df = df[df["date"] >= pd.Timestamp(start)]
            if end is not None:
                df = df[df["date"] <= pd.Timestamp(end)]
        for c, v in (where or {}).items():
            df = df[df[c].isin(v if isinstance(v, (list, tuple, set)) else [v])]
        return df.reset_index(drop=True)


def price_from_32nds(q: str, fut_quarters: bool = False) -> float:
    """Treasury 32nds text -> decimal points: '99-282' = 99 + 28.25/32; '115-19+' = 115 + 19.5/32.
    Cash-bond reading: the optional third character is eighths of a 32nd ('+' = 4/8). CME 2y/3y/5y note futures
    (quarter-of-32nd ticks) print 2, 5, 7 for 1/4, 1/2, 3/4: pass fut_quarters=True. A leading '-' negates
    (rich/cheap fields). Check the contract's tick grid after converting."""
    m = re.fullmatch(r"\s*([+-]?)(\d+)-(\d{2})([0-7+]?)\s*", q)
    if not m or int(m.group(3)) > 31:
        raise ValueError(f"not a 32nds price: {q!r}")
    sign, whole, n32, frac = m.groups()
    if fut_quarters:
        if frac not in ("", "0", "2", "5", "7"):
            raise ValueError(f"not a quarter-32nd futures price: {q!r}")
        part = {"": 0, "0": 0, "2": .25, "5": .5, "7": .75}[frac]
    else:
        part = (4 if frac == "+" else int(frac or 0)) / 8
    value = int(whole) + (int(n32) + part) / 32
    return -value if sign == "-" else value


def selftest() -> int:
    # 32nds: quotes as printed in BofA Global Research, U.S. Rates Data: Futures Basis Report (7 Aug 2025)
    assert price_from_32nds("115-17") == 115.53125
    assert price_from_32nds("99-282") == 99.8828125
    assert price_from_32nds("115-19+") == 115.609375
    assert price_from_32nds("-0-073") == -0.23046875
    assert price_from_32nds("117-162", True) == 117 + 16.25 / 32 and price_from_32nds("117-167", True) == 117 + 16.75 / 32
    assert price_from_32nds("117-167") == 117 + 16.875 / 32   # cash reading of the same text differs: know the contract
    for bad in ("99.88", "99-32", "99-1"):
        try:
            price_from_32nds(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pd.DataFrame({"date": ["2026-11-06", "2026-11-06", "2026-11-09", "2026-11-09", "2026-11-10", "2026-11-10"],
                      "snap": "eod_ny", "curve_id": "USD-SOFR", "start": "0D", "tenor": ["2Y", "10Y"] * 3,
                      "par_rate_pct": [3.61, 3.79, 3.62, 3.80, 3.63, 3.82], "source": "t"}
                     ).to_csv(root / "curve_par.csv", index=False)
        # CPI vintage revised one month later; the second print must stay invisible before its release instant
        pd.DataFrame({"index_id": "EUR-HICPXT", "ref_month": "2026-01", "index_level": [100.0, 100.3],
                      "pub_ts_utc": ["2026-02-11T10:00:00Z", "2026-03-11T10:00:00Z"], "source": "t"}
                     ).to_csv(root / "infl_fixings.csv", index=False)
        # a tap on 10-Jun-2026 raises the amount outstanding: two versions of one bond
        pd.DataFrame({"instrument_id": "BOND:DE000BUXXXX0", "valid_from": ["2026-01-15", "2026-06-10"],
                      "valid_to": ["2026-06-10", None], "amount_out_ccy": [20e9, 25e9]}
                     ).to_csv(root / "bond_static.csv", index=False)
        src = FileSource(root)
        assert src.tables() == {"curve_par", "infl_fixings", "bond_static"}, src.tables()
        got = src.read("curve_par", start="2026-11-09", where={"tenor": "10Y"})
        assert got.par_rate_pct.tolist() == [3.80, 3.82], got
        assert src.read_asof("curve_par", "2026-11-09").date.max() == pd.Timestamp("2026-11-09")

        def cpi(t):
            return src.read_asof("infl_fixings", t, key=["index_id", "ref_month"]).index_level.tolist()
        assert cpi("2026-02-01") == []
        assert cpi("2026-02-20") == [100.0]
        assert cpi("2026-03-11T09:59:59Z") == [100.0]
        assert cpi("2026-03-20") == [100.3]

        def amount(t):
            return src.read_asof("bond_static", t).amount_out_ccy.tolist()
        assert amount("2026-01-14") == [] and amount("2026-06-09") == [20e9] and amount("2026-06-10") == [25e9]
        # an auction row stays visible as a schedule, but its results appear only at results_ts_utc
        pd.DataFrame({"issuer": "US", "auction_date": ["2026-11-12", "2026-11-19"], "instrument_id": "BOND:X",
                      "stop_yield_pct": [4.112, 4.2], "tail_bp": [0.7, 0.1],
                      "results_ts_utc": ["2026-11-12T18:00:00Z", None]}).to_csv(root / "auctions.csv", index=False)
        au = src.read_asof("auctions", "2026-11-12T17:59:59Z")
        assert len(au) == 2 and au.stop_yield_pct.isna().all() and au.tail_bp.isna().all(), au
        assert src.read_asof("auctions", "2026-11-12T18:00:00Z").stop_yield_pct.tolist()[0] == 4.112
        assert src.read_asof("auctions", "2026-11-30").stop_yield_pct.isna().tolist() == [False, True]
        try:
            src.read("repo_rates")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("missing table must raise")
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            pass
        else:
            src.read("curve_par").to_parquet(root / "curve_zero.parquet")  # any table name: round-trip only
            back = src.read("curve_zero")
            assert back.equals(src.read("curve_par")), back
    print("selftest passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default="data", help="folder holding canonical tables")
    ap.add_argument("--table")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--as-of", help="point-in-time cutoff (date = end of that day, or ISO timestamp)")
    ap.add_argument("--key", help="comma-separated key for latest-vintage selection (with --as-of)")
    ap.add_argument("--where", action="append", default=[], help="column=value filter, repeatable")
    ap.add_argument("--out", help="write the result to this CSV/Parquet path instead of printing")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    src = FileSource(a.root)
    if not a.table:
        print("\n".join(sorted(src.tables())) or f"no canonical tables under {a.root}")
        return 0
    where = dict(w.split("=", 1) for w in a.where)
    key = a.key.split(",") if a.key else None
    df = src.read_asof(a.table, a.as_of, key, a.start, a.end, where) if a.as_of else src.read(a.table, a.start,
                                                                                             a.end, where)
    if a.out:
        (df.to_parquet if a.out.endswith(".parquet") else lambda p: df.to_csv(p, index=False))(a.out)
    else:
        print(df.to_string(max_rows=40))
    return 0


if __name__ == "__main__":
    sys.exit(main())
