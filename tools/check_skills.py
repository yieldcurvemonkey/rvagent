"""Validate every skill under .github/skills, run bundled script self-tests, and rebuild the catalog.

Usage:
    python tools/check_skills.py                # validate + self-tests
    python tools/check_skills.py --catalog      # also rewrite docs/skill-catalog.md
    python tools/check_skills.py --no-scripts   # skip script self-tests
    python tools/check_skills.py --only curve-butterflies,fi-carry-and-rolldown

Exit code 1 if any skill has errors (warnings do not fail).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".github" / "skills"
CATALOG = ROOT / "docs" / "skill-catalog.md"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = {"name", "description", "argument-hint", "user-invocable", "disable-model-invocation",
                "license", "metadata", "compatibility", "allowed-tools", "context"}
PREFIXES = {
    "rv": "Workflows", "fi": "Fixed-income fundamentals", "curve": "Curve RV", "bond": "Bond RV",
    "spread": "Spread RV", "fut": "Futures, basis & delivery", "stir": "STIR, money markets & funding",
    "xccy": "Cross-currency", "vol": "Volatility & convexity", "infl": "Inflation", "macro": "Macro overlay",
    "flow": "Flows & positioning", "quant": "Quant & statistics", "ml": "Machine learning",
    "bt": "Backtesting & evaluation", "port": "Portfolio & risk", "data": "Data", "eng": "Engineering & delivery",
}
# Local paths / raw file names must never appear in a skill (references are cited by title).
PATH_PATTERNS = [
    (re.compile(r"[A-Za-z]:[\\/]"), "absolute Windows path"),
    (re.compile(r"/(?:Users|home)/\w+"), "absolute home path"),
    (re.compile(r"\b(?:print|Attachment) ?\(\d+\)"), "raw download file name"),
    (re.compile(r"Citi Velocity\d+"), "raw download file name"),
    (re.compile(r"[\w\-() ]+\.pdf\b", re.I), "PDF file name (cite the document title instead)"),
]
# Vendor / infra coupling is only allowed inside adapters/, never in skills (references section excepted).
COUPLING = re.compile(r"\b(blpapi|xbbg|pdblp|BDH\(|BDP\(|BDS\(|refinitiv\.data|eikon\.|ARBS|RVUtils|SDRUtils|"
                      r"MultiProductMDP|TimeseriesBuilder)\b")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def split_frontmatter(text: str):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    return yaml.safe_load(text[3:end]) or {}, text[end + 4:]


def check_skill(d: Path, run_scripts: bool):
    errors, warns = [], []
    f = d / "SKILL.md"
    if not f.exists():
        return [f"{d.name}: missing SKILL.md"], warns, None
    text = f.read_text(encoding="utf-8")
    try:
        fm, body = split_frontmatter(text)
    except yaml.YAMLError as e:
        return [f"{d.name}: frontmatter YAML error: {e}"], warns, None
    if fm is None:
        return [f"{d.name}: missing YAML frontmatter"], warns, None

    name, desc = fm.get("name"), fm.get("description")
    if name != d.name:
        errors.append(f"name '{name}' must equal folder name '{d.name}'")
    if not isinstance(name, str) or not NAME_RE.match(name or "") or len(name) > 64:
        errors.append(f"invalid name '{name}' (lowercase letters/digits/single hyphens, <=64 chars)")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("missing description")
    elif len(desc) > 1024:
        errors.append(f"description is {len(desc)} chars (max 1024)")
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        errors.append(f"unknown frontmatter keys: {sorted(extra)}")
    if name and name.split("-")[0] not in PREFIXES:
        warns.append(f"prefix '{name.split('-')[0]}' not in category list {sorted(PREFIXES)}")

    refs = re.search(r"(?ms)^## References\s*\n(.*?)(?=^## |\Z)", body)
    if not refs or not re.search(r"(?m)^\s*[-*] \S", refs.group(1)):
        errors.append("missing '## References' section with at least one bullet")
    main = body[: refs.start()] if refs else body

    for rx, why in PATH_PATTERNS:
        m = rx.search(body)
        if m:
            errors.append(f"{why}: '{m.group(0)[:60]}'")
    m = COUPLING.search(main)
    if m:
        errors.append(f"vendor/infra coupling outside References: '{m.group(0)}' (put it in adapters/)")

    for link in LINK_RE.findall(body):
        if re.match(r"^[a-z]+://", link) or link.startswith("mailto:"):
            continue
        if not (d / link).resolve().exists():
            errors.append(f"broken relative link: {link}")

    lines = body.count("\n")
    if lines < 60:
        warns.append(f"body is short ({lines} lines)")

    if run_scripts:
        for py in sorted((d / "scripts").glob("*.py")) if (d / "scripts").exists() else []:
            r = subprocess.run([sys.executable, "-I", str(py), "--selftest"], capture_output=True, text=True,
                               timeout=600, cwd=str(d))
            if r.returncode != 0:
                tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
                errors.append(f"selftest failed: scripts/{py.name}: {' | '.join(tail)}")
    return [f"{d.name}: {e}" for e in errors], [f"{d.name}: {w}" for w in warns], fm


def write_catalog(rows):
    out = ["# Skill catalog", "",
           "Generated by `python tools/check_skills.py --catalog`. Do not edit by hand.", ""]
    by_prefix: dict[str, list] = {}
    for name, desc in rows:
        by_prefix.setdefault(name.split("-")[0], []).append((name, desc))
    for p, title in PREFIXES.items():
        if p not in by_prefix:
            continue
        out += [f"## {title} (`{p}-`)", "", "| Skill | What it does / when to use |", "|---|---|"]
        for name, desc in sorted(by_prefix[p]):
            d = " ".join(desc.split()).replace("|", "\\|")
            out.append(f"| [{name}](../.github/skills/{name}/SKILL.md) | {d} |")
        out.append("")
    CATALOG.parent.mkdir(exist_ok=True)
    CATALOG.write_text("\n".join(out), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--no-scripts", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = {s for s in a.only.split(",") if s}
    dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir() and (not only or p.name in only))
    errors, warns, rows = [], [], []
    for d in dirs:
        e, w, fm = check_skill(d, not a.no_scripts)
        errors += e
        warns += w
        if fm and isinstance(fm.get("description"), str):
            rows.append((d.name, fm["description"]))
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{len(dirs)} skills checked, {len(errors)} errors, {len(warns)} warnings")
    if a.catalog and not only:
        write_catalog(rows)
        print(f"catalog written: {CATALOG.relative_to(ROOT)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
