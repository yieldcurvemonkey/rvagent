"""Validate canonical tables against references/schemas.md (the single source of truth, parsed at run time).

Errors (exit 1): unknown table, missing required column, null in a required column, unparseable dtype, value
outside the unit's sanity range, duplicate primary key, observation/knowledge time after the as-of cutoff, failed
row identity (the "Checks:" line in schemas.md). Warnings: unknown extra column, pct/bp column that looks decimal.

    python validate_data.py data/curve_par.csv data/bond_quotes.parquet [--as-of 2026-11-11]
    python validate_data.py data/repo_rates/ --table repo_rates      # a folder of CSV/Parquet parts
    python validate_data.py --lint | --list | --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

SCHEMA = Path(__file__).resolve().parents[1] / "references" / "schemas.md"
DTYPES = {"str", "date", "ts", "float", "int", "bool"}
# Tripwires for unit mistakes (x100, x10000, 32nds), not outlier filters. Reject, never rescale.
RANGES = {"pct": (-100, 100), "bp": (-5000, 5000), "nvol_bp": (0, 2000), "px": (-100, 1000), "df": (1e-6, 2),
          "prob": (0, 1), "frac": (-1, 1), "fx": (1e-12, 1e6), "index": (1e-12, 1e6), "days": (0, 1e5),
          "years": (0, 100)}
# unit -> required name ending (nvol_bp first so it wins over _bp)
SUFFIX = {"nvol_bp": "nvol_bp", "pct": "_pct", "bp": "_bp", "px": "_px", "df": "discount_factor", "prob": "prob",
          "frac": "_frac", "ccy": "_ccy", "cnt": "_cnt", "fxpts": "_fxpts", "fx": "_fx", "index": "index_level",
          "days": "_days", "years": "_years"}
UNITS = set(SUFFIX) | {"ratio", "-"}
TIME_COLS = ("date", "ts_utc", "pub_ts_utc", "exec_ts_utc", "results_ts_utc")  # may never be later than the as-of cutoff
DATE_NAME = re.compile(r"^(date|.*_date|valid_from|valid_to|eligible_from|eligible_to)$")
TZ_TEXT = r"(?:Z|[+-]\d\d:?\d\d)$"
TRUE, FALSE = {"true", "1", "1.0"}, {"false", "0", "0.0"}


def load_schema(path=SCHEMA) -> dict:
    """schemas.md -> {table: {"key": [...], "checks": [...], "cols": {name: {"dtype", "unit", "req"}}}}."""
    tables, cur, in_cols = {}, None, False
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### `([a-z_]+)`", line)
        if m:
            cur, in_cols = tables.setdefault(m.group(1), {"key": [], "checks": [], "cols": {}}), False
        elif cur is None:
            continue
        elif line.startswith("Primary key:"):
            cur["key"] = [c.strip() for c in line.split("`")[1].split(",") if c.strip() not in ("", "-")]
        elif line.startswith("Checks:"):
            cur["checks"] = re.findall(r"`([^`]+)`", line)
        elif line.startswith("| column | dtype |"):
            in_cols = True
        elif in_cols and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not set(cells[0]) <= {"-", ":"}:
                cur["cols"][cells[0]] = {"dtype": cells[1], "unit": cells[2], "req": cells[3] == "Y"}
        else:
            in_cols = False
    return tables


def lint(schema: dict) -> list[str]:
    """Self-consistency of schemas.md: keys, dtype/unit vocabularies, unit-in-name and time-naming rules."""
    out = []
    for t, s in schema.items():
        if not s["cols"]:
            out.append(f"{t}: no column table")
        for k in s["key"]:
            if k not in s["cols"] or not s["cols"][k]["req"]:
                out.append(f"{t}: key column '{k}' missing or not required")
        for c, d in s["cols"].items():
            if d["dtype"] not in DTYPES or d["unit"] not in UNITS:
                out.append(f"{t}.{c}: bad dtype/unit {d['dtype']}/{d['unit']}")
            if (d["dtype"] == "date") != bool(DATE_NAME.match(c)) or (d["dtype"] == "ts") != c.endswith("ts_utc"):
                out.append(f"{t}.{c}: date/ts naming rule broken for dtype {d['dtype']}")
            want = next((u for u, suf in SUFFIX.items() if c.endswith(suf)), None)
            if want != (d["unit"] if d["unit"] in SUFFIX else None):
                out.append(f"{t}.{c}: unit '{d['unit']}' does not match the name (expected {want})")
    return out


def _parse(s: pd.Series, dtype: str):
    """Return (parsed series, number of non-null values that are not valid for dtype)."""
    nn = s.notna()
    if dtype in ("float", "int"):
        v = pd.to_numeric(s, errors="coerce")
        bad = int((nn & v.isna()).sum())
        return v, bad + (int((v.notna() & (v % 1 != 0)).sum()) if dtype == "int" else 0)
    if dtype in ("date", "ts") and pd.api.types.is_datetime64_any_dtype(s):
        if dtype == "ts":  # keep tz-aware UTC; naive timestamps are ambiguous: reject
            if s.dt.tz is None:
                return pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns, UTC]"), int(nn.sum())
            return s.dt.tz_convert("UTC"), 0
        return (s.dt.tz_convert(None) if s.dt.tz is not None else s), 0
    txt = s.astype(str).str.strip()
    if dtype == "date":
        v = pd.to_datetime(s.where(nn & txt.str.fullmatch(r"\d{4}-\d{2}-\d{2}")), errors="coerce")
        return v, int((nn & v.isna()).sum())
    if dtype == "ts":
        v = pd.to_datetime(s.where(nn & txt.str.contains(TZ_TEXT)), utc=True, errors="coerce", format="ISO8601")
        return v, int((nn & v.isna()).sum())
    if dtype == "bool":
        low = txt.str.lower()
        return low.isin(TRUE).where(nn), int((nn & ~low.isin(TRUE | FALSE)).sum())
    return s, 0


def validate(df: pd.DataFrame, table: str, schema: dict, as_of: pd.Timestamp) -> list[tuple[str, str, str]]:
    """Return findings as (level, code, message). as_of is a tz-aware UTC cutoff."""
    if table not in schema or table.startswith("_"):
        return [("ERROR", "E_TABLE", f"unknown table '{table}'")]
    spec = schema[table]
    cols = {**schema.get("_common", {"cols": {}})["cols"], **spec["cols"]}
    out = [("ERROR", "E_MISSING_COL", c) for c, d in spec["cols"].items() if d["req"] and c not in df.columns]
    out += [("WARN", "W_EXTRA_COL", c) for c in df.columns if c not in cols]
    parsed = {}
    for c in [c for c in df.columns if c in cols]:
        d, s = cols[c], df[c]
        if d["req"] and s.isna().any():
            out.append(("ERROR", "E_NULL_REQ", f"{c}: {int(s.isna().sum())} of {len(s)} null"))
        v, bad = _parse(s, d["dtype"])
        parsed[c] = v
        if bad:
            out.append(("ERROR", "E_DTYPE", f"{c}: {bad} values are not {d['dtype']}"))
        if d["dtype"] in ("float", "int") and d["unit"] in RANGES:
            lo, hi = RANGES[d["unit"]]
            x = v.dropna()
            n = int(((x < lo) | (x > hi)).sum())
            if n:
                out.append(("ERROR", "E_RANGE", f"{c}: {n} values outside [{lo}, {hi}] {d['unit']}"))
            ax = x.abs()
            if len(ax) >= 10 and 0 < ax.max() < {"pct": 0.25, "bp": 0.05}.get(d["unit"], 0):
                out.append(("WARN", "W_DECIMAL", f"{c}: max |x| = {ax.max():.4g}; decimal stored as {d['unit']}?"))
        if c in TIME_COLS and d["dtype"] in ("date", "ts"):
            late = v.dt.normalize() > pd.Timestamp(as_of.date()) if d["dtype"] == "date" else v > as_of  # NaT-safe
            if late.sum():
                out.append(("ERROR", "E_FUTURE", f"{c}: {int(late.sum())} rows after as-of {as_of}"))
    if spec["key"] and all(k in df.columns for k in spec["key"]):
        dup = int(df.duplicated(subset=spec["key"]).sum())
        if dup:
            out.append(("ERROR", "E_DUP_KEY", f"{dup} duplicate rows on ({', '.join(spec['key'])})"))
    for expr in spec["checks"]:
        refs = sorted({w for w in re.findall(r"[a-z_][a-z0-9_]*", expr) if w in cols})
        if not all(r in parsed for r in refs):
            continue  # optional inputs absent: identity not testable
        frame = pd.DataFrame({r: parsed[r] for r in refs}).dropna()
        n = int((~frame.eval(expr).astype(bool)).sum()) if len(frame) else 0
        if n:
            out.append(("ERROR", "E_CHECK", f"{n} rows fail `{expr}`"))
    return out


def read_table(path: Path) -> pd.DataFrame:
    """One CSV/Parquet file, or every CSV/Parquet file under a folder. CSV is read as text and parsed here."""
    files = sorted(path.rglob("*.parquet")) + sorted(path.rglob("*.csv")) if path.is_dir() else [path]
    if not files:
        raise SystemExit(f"no CSV/Parquet files under {path}")
    return pd.concat([pd.read_parquet(f) if f.suffix == ".parquet" else pd.read_csv(f, dtype=str) for f in files],
                     ignore_index=True)


def cutoff(text: str | None) -> pd.Timestamp:
    """As-of cutoff in UTC. A bare date means the end of that day. Default: now."""
    if not text:
        return pd.Timestamp.now(tz="UTC")
    t = pd.Timestamp(text)
    if len(text.strip()) == 10:
        t += pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")


REQUIRED_TABLES = {
    "calendars", "cb_meetings", "rate_indices", "swap_conventions", "bond_static", "fut_static", "fut_basket",
    "opt_static", "symbol_map", "roll_map", "curve_par", "curve_zero", "rate_fixings", "bond_quotes", "repo_rates",
    "fut_quotes", "stir_quotes", "opt_quotes", "vol_surface", "swap_spreads", "basis_swaps", "ccp_basis", "fx_rates",
    "infl_fixings", "infl_swaps", "infl_seasonals", "auctions", "positioning", "flows_trades", "events_probs",
    "macro_series", "signals", "positions", "trades", "pnl", "csa_terms", "bond_holdings", "cds_quotes", "issuance_plan",
    "callable_issuance", "mbs_tba", "mbs_pool_stats", "dealer_flow", "book_snapshots", "bid_offer", "cb_texts",
    "trial_log"}


def selftest(schema: dict) -> int:
    missing = REQUIRED_TABLES - set(schema)
    assert not missing, f"schemas.md lacks tables: {sorted(missing)}"
    problems = lint(schema)
    assert not problems, "schemas.md lint:\n" + "\n".join(problems)
    cut = cutoff("2026-11-11")

    def codes(df, table="curve_par"):
        return {c for _, c, _ in validate(df, table, schema, cut)}

    dates = [f"2026-11-0{d}" for d in range(4, 10)]
    good = pd.DataFrame({"date": [d for d in dates for _ in (0, 1)], "snap": "eod_ny", "curve_id": "USD-SOFR",
                         "start": "0D", "tenor": ["2Y", "10Y"] * 6,
                         "par_rate_pct": [f"{3.6 + 0.02 * i:.2f}" for i in range(12)], "source": "t"})
    assert codes(good) == set(), validate(good, "curve_par", schema, cut)
    bad_row = lambda col, val: good.assign(**{col: [val] + list(good[col][1:])})  # noqa: E731
    cases = {
        "E_RANGE": bad_row("par_rate_pct", "371"),                      # bp stored in a pct column
        "W_DECIMAL": good.assign(par_rate_pct=pd.to_numeric(good.par_rate_pct) / 100),
        "E_DUP_KEY": pd.concat([good, good.iloc[[0]]], ignore_index=True),
        "E_FUTURE": bad_row("date", "2026-11-12"),
        "E_NULL_REQ": good.assign(source=None),                         # present but null: reject, never skip
        "E_MISSING_COL": good.drop(columns="tenor"),
        "E_DTYPE": bad_row("date", "11/10/2026"),
        "W_EXTRA_COL": good.assign(foo=1),
    }
    for want, df in cases.items():
        assert codes(df) == {want}, (want, validate(df, "curve_par", schema, cut))
    assert codes(good, "no_such_table") == {"E_TABLE"}

    gilt = pd.DataFrame({"date": ["2026-11-10"], "snap": "eod_ldn", "instrument_id": "BOND:GB00BXXXXX00",
                         "clean_px": ["98.4375"], "accrued_px": ["-0.0817"], "dirty_px": ["98.3558"], "source": "t"})
    assert codes(gilt, "bond_quotes") == set()                          # negative ex-dividend accrued is legal
    assert codes(gilt.assign(dirty_px="98.5192"), "bond_quotes") == {"E_CHECK"}  # dirty = clean - accrued: sign bug

    # every other row identity: a consistent row passes, a sign/decimal slip fails (values from the SKILL examples)
    ident = {
        "stir_quotes": (dict(date="2026-11-10", snap="settle", fut_id="FUT:SR3:2027-03", price_px="96.255",
                             rate_pct="3.745", source="t"), dict(rate_pct="0.03745")),
        "repo_rates": (dict(date="2026-11-10", snap="eod_ny", ccy="USD", collateral="X", term="ON", rate_pct="3.70",
                            gc_rate_pct="3.93", specialness_bp="23", source="t"), dict(specialness_bp="-23")),
        "ccp_basis": (dict(date="2026-11-10", snap="eod_ny", ccy="USD", index_id="USD-SOFR", tenor="10Y",
                           ccp_a="LCH", ccp_b="CME", rate_a_pct="3.8150", rate_b_pct="3.8100", basis_bp="0.5",
                           source="t"), dict(basis_bp="-0.5")),
        "auctions": (dict(issuer="US", auction_date="2026-11-09", instrument_id="BOND:X", stop_yield_pct="4.112",
                          wi_yield_pct="4.105", tail_bp="0.7", source="t"), dict(tail_bp="-0.7")),
        "pnl": (dict(date="2026-11-09", strategy_id="s", package_id="p", ccy="USD", mtm_ccy="18250", carry_ccy="410",
                     financing_ccy="-120", cost_ccy="-790", total_ccy="17750"), dict(total_ccy="18750")),
    }
    for t, (row, slip) in ident.items():
        assert codes(pd.DataFrame([row]), t) == set(), (t, validate(pd.DataFrame([row]), t, schema, cut))
        assert codes(pd.DataFrame([{**row, **slip}]), t) == {"E_CHECK"}, t
    cot = pd.DataFrame({"date": ["2026-11-03"], "pub_ts_utc": ["2026-11-06T20:30:00Z"], "report": "cftc_tff",
                        "contract": "ZN", "trader_class": "leveraged_funds", "source": "t"})
    assert codes(cot, "positioning") == set()
    assert codes(cot.assign(pub_ts_utc="2026-11-06 20:30:00"), "positioning") == {"E_DTYPE"}   # naive ts
    assert codes(cot.assign(pub_ts_utc="2026-11-13T20:30:00Z"), "positioning") == {"E_FUTURE"}
    # typed frames, as Parquet delivers them: datetime64 date, tz-aware ts, real bool
    typed = cot.assign(date=pd.to_datetime(cot.date), pub_ts_utc=pd.to_datetime(cot.pub_ts_utc, utc=True),
                       data_ok=True)
    assert codes(typed, "positioning") == set(), validate(typed, "positioning", schema, cut)
    late = typed.assign(pub_ts_utc=pd.to_datetime(["2026-11-13T20:30:00Z"], utc=True))
    assert codes(late, "positioning") == {"E_FUTURE"}
    assert codes(typed.assign(pub_ts_utc=typed.pub_ts_utc.dt.tz_localize(None)), "positioning") == {"E_DTYPE"}
    cds = pd.DataFrame({"date": ["2026-11-10"] * 2, "snap": "close", "entity": "IT", "tenor": "5Y", "ccy": "USD",
                        "settlement": ["physical", "cash"], "definitions": "2014", "coupon_bp": "100",
                        "par_spread_bp": ["62.5", "58.0"], "recovery_frac": "0.40", "source": "t"})
    assert codes(cds, "cds_quotes") == set(), validate(cds, "cds_quotes", schema, cut)  # two contracts coexist
    assert codes(cds.assign(settlement="physical"), "cds_quotes") == {"E_DUP_KEY"}      # same contract twice
    assert codes(cds.assign(recovery_frac="40"), "cds_quotes") == {"E_RANGE"}           # percent stored as frac
    assert codes(cds.assign(par_spread_bp=None, upfront_px="0.35"), "cds_quotes") == set()  # upfront-only quote is legal
    assert codes(cds.drop(columns="definitions"), "cds_quotes") == {"E_MISSING_COL"}        # contract terms are required
    n = 16
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        pass
    else:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "positioning.parquet"
            typed.to_parquet(f)
            assert codes(read_table(f), "positioning") == set()
            n += 1
    print(f"selftest passed: {len(schema) - 1} tables parsed, lint clean, {len(cases) + n} cases")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="canonical CSV/Parquet files or folders (table = file stem or folder)")
    ap.add_argument("--table", help="table name when it cannot be inferred from the path")
    ap.add_argument("--as-of", help="cutoff for observation/knowledge times (date or ISO timestamp); default now")
    ap.add_argument("--schema", default=str(SCHEMA), help="path to schemas.md")
    ap.add_argument("--lint", action="store_true", help="check schemas.md itself")
    ap.add_argument("--list", action="store_true", help="list tables and primary keys")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    schema = load_schema(a.schema)
    if a.selftest:
        return selftest(schema)
    if a.list:
        for t, s in schema.items():
            print(f"{t:18} key: {', '.join(s['key'])}")
        return 0
    if a.lint:
        problems = lint(schema)
        print("\n".join(problems) or "schemas.md lint clean")
        return 1 if problems else 0
    if not a.paths:
        ap.error("give at least one path, or --lint/--list/--selftest")
    cut, n_err = cutoff(a.as_of), 0
    for p in map(Path, a.paths):
        table = a.table or (p.name if p.is_dir() else p.stem)
        df = read_table(p)
        found = validate(df, table, schema, cut)
        for level, code, msg in found:
            print(f"{level:5} {table} {code} {msg}")
        errs = sum(level == "ERROR" for level, _, _ in found)
        n_err += errs
        print(f"{table}: {len(df)} rows, {errs} errors, {len(found) - errs} warnings")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
