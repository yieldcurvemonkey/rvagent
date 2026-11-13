#!/usr/bin/env python3
"""Dictionary hawk/dove scoring of central-bank text (transparent baseline for a Hawk-Dove Score).

Sentence pipeline: topic filter -> relevance weight w -> 5-point score theta in {0, .25, .5, .75, 1}.
Document score   HDS_k = 200 * sum_i (w_i / sum w) * (theta_i - 0.5)        range -100 (dove) .. +100 (hawk)
Speaker series   HDS_t = sum_k W_k * HDS_k / sum_k W_k over speeches with t-90d <= date_k <= t,  W_k = sum_i w_ki
Surprise index   HDSI_t = cumulative sum of (HDS_k - previous HDS of the same speaker)

Direction logic: each direction word (rise/fall, strong/weak, above/below ...) is paired with the nearest topic word
within WINDOW tokens; contribution = direction sign * topic polarity (unemployment/slack = -1, others +1), flipped by
a negator up to NEG_SCOPE tokens before it ("not hesitate" is not a negation). Policy-action words (hike, tighten,
raise, cut, loosen, restrictive, accommodative) count +/-2 on their own. Hedges (may, could, gradual...) cap |theta-0.5|
at 0.25.

CLI:  python cb_text_score.py --texts cb_texts.csv --out-docs docs.csv --out-daily daily.csv
      texts columns: doc_id, cb, speaker, doc_type, pub_ts_utc, text   (CSV or Parquet)
      python cb_text_score.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd

WINDOW, NEG_SCOPE, NEUTRAL_W = 6, 3, 0.5   # pairing window, negation scope (tokens), weight of topic-only sentences

PHRASES = [  # normalise multi-word concepts to one token before tokenising (order matters)
    (r"\bu\.s\.", "us"), (r"\bunemployment rate\b", "unemployment"), (r"\bspare capacity\b", "slack"),
    (r"\blabou?r markets?\b", "labourmarket"), (r"\bwage growth\b", "wages"), (r"\binterest rates?\b", "rates"),
    (r"\bpolicy rates?\b", "rates"), (r"\bbank rate\b", "rates"), (r"\bcash rate\b", "rates"),
    (r"\bprice pressures?\b", "inflation"), (r"\binflation expectations\b", "inflation"),
]
TOPICS = {  # token -> (topic, polarity)
    **{t: ("inflation", 1) for t in ["inflation", "inflationary", "prices", "cpi", "pce", "hicp", "wages"]},
    **{t: ("labour", 1) for t in ["labourmarket", "employment", "jobs", "payrolls", "hiring"]},
    **{t: ("labour", -1) for t in ["unemployment", "slack", "joblessness"]},
    **{t: ("growth", 1) for t in ["growth", "gdp", "activity", "demand", "output", "economy", "spending",
                                  "consumption"]},
    **{t: ("policy", 1) for t in ["rates", "rate", "policy", "stance", "monetary"]},
}
UP = re.compile(r"^(ris(e|es|ing|en)|rose|increas\w*|higher|high|elevated|strong\w*|robust|persistent\w*|upside|"
                r"accelerat\w*|firm\w*|tight|tighter|above|sticky|rebound\w*|surg\w*|overheat\w*|resilient)$")
DOWN = re.compile(r"^(fall|falls|falling|fell|fallen|declin\w*|lower|low|weak\w*|soft\w*|subdued|moderat\w*|"
                  r"eas(e|es|ed|ing)|downside|slow\w*|cool\w*|below|decelerat\w*|contract\w*)$")
ACT_UP = re.compile(r"^(hike|hikes|hiking|tighten|tightening|tightened|raise|raising|raised|restrictive)$")
ACT_DOWN = re.compile(r"^(cut|cuts|cutting|loosen\w*|accommodative|accommodation)$")
NEG = re.compile(r"^(not|no|never|without|neither|nor|unlikely|\w+n't)$")
NOT_NEG_NEXT = {"hesitate", "only", "just", "least"}
HEDGE = re.compile(r"^(may|might|could|possibly|perhaps|somewhat|slightly|modest\w*|gradual\w*|some)$")
TOPIC_ORDER = ["policy", "inflation", "labour", "growth"]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(text)).strip()
    # ponytail: fixed abbreviation list; "...in the U.S. The ..." now merges two sentences. Use a trained splitter if it matters.
    text = re.sub(r"\b(U\.S|U\.K|Mr|Mrs|Ms|Dr|e\.g|i\.e|vs)\.", lambda m: m.group(1).replace(".", ""), text)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text) if s]


def tokens(sentence: str) -> list[str]:
    s = sentence.lower().replace("’", "'")
    for pat, rep in PHRASES:
        s = re.sub(pat, rep, s)
    return re.findall(r"[a-z]+(?:'[a-z]+)?", s)


def _negated(toks: list[str], j: int) -> bool:
    for i in range(max(0, j - NEG_SCOPE), j):
        if NEG.match(toks[i]) and not (i + 1 < len(toks) and toks[i + 1] in NOT_NEG_NEXT):
            return True
    return False


def score_sentence(sentence: str) -> dict:
    """theta (0..1), relevance weight w, net direction count, primary topic ('other' if none)."""
    toks = tokens(sentence)
    topic_pos = [(i, *TOPICS[t]) for i, t in enumerate(toks) if t in TOPICS]
    net, hedged = 0, any(HEDGE.match(t) for t in toks)
    for j, t in enumerate(toks):
        if ACT_UP.match(t) or ACT_DOWN.match(t):
            c = 2 if ACT_UP.match(t) else -2
        elif UP.match(t) or DOWN.match(t):
            near = [(abs(i - j), pol) for i, _, pol in topic_pos if 0 < abs(i - j) <= WINDOW]
            if not near:
                continue
            c = (1 if UP.match(t) else -1) * min(near)[1]
        else:
            continue
        net += -c if _negated(toks, j) else c
    counts = {k: sum(1 for _, tp, _ in topic_pos if tp == k) for k in TOPIC_ORDER}
    primary = max(TOPIC_ORDER, key=lambda k: counts[k]) if any(counts.values()) else "other"
    if net == 0:
        theta, w = 0.5, (NEUTRAL_W if topic_pos else 0.0)
    else:
        step = 0.25 if (hedged or abs(net) == 1) else 0.5
        theta, w = 0.5 + np.sign(net) * step, 1.0
    return {"theta": float(theta), "w": float(w), "net": int(net), "topic": primary}


def score_document(text: str) -> dict:
    sents = [score_sentence(s) for s in split_sentences(text)]
    n = len(sents)
    w = np.array([s["w"] for s in sents], float)
    th = np.array([s["theta"] for s in sents], float)
    W = w.sum()
    hds = 200.0 * float(np.sum(w / W * (th - 0.5))) if W > 0 else np.nan
    out = {"hds": hds, "weight": W, "n_sent": n, "n_scored": int((w > 0).sum()),
           "relevance": W / n if n else np.nan, "relevance_scored": W / (w > 0).sum() if (w > 0).any() else np.nan}
    for k in TOPIC_ORDER + ["other"]:
        out[f"share_{k}"] = sum(s["topic"] == k for s in sents) / n if n else np.nan
    return out


def score_documents(texts: pd.DataFrame, cutoff_hour_utc: float = 24.0) -> pd.DataFrame:
    """texts: doc_id, cb, speaker, doc_type, pub_ts_utc, text -> one row per document with HDS and topic shares.
    date = the market day the document is known for: published at/after cutoff_hour_utc (the snap) -> next day."""
    rows = [dict(r._asdict(), **score_document(r.text)) for r in texts.itertuples(index=False)]
    out = pd.DataFrame(rows).drop(columns="text")
    ts = pd.to_datetime(out["pub_ts_utc"], utc=True)
    out["date"] = (ts + pd.Timedelta(hours=24 - cutoff_hour_utc)).dt.tz_convert(None).dt.normalize()
    return out.sort_values(["cb", "date", "doc_id"]).reset_index(drop=True)


def aggregate(docs: pd.DataFrame, window_days: int = 90, dates=None) -> pd.DataFrame:
    """Relevance-weighted trailing average of document HDS per cb, docs with t-window <= date <= t (point in time)."""
    out = []
    for cb, g in docs.dropna(subset=["hds"]).groupby("cb"):
        idx = pd.DatetimeIndex(dates) if dates is not None else pd.date_range(g["date"].min(), g["date"].max())
        d, h, wt = g["date"].values, g["hds"].values, g["weight"].values
        for t in idx:
            m = (d <= np.datetime64(t)) & (d >= np.datetime64(t - pd.Timedelta(days=window_days)))
            if not m.any():
                continue
            om = wt[m] / wt[m].sum()
            mean = float(om @ h[m])
            out.append({"date": t, "cb": cb, "hds_avg": mean, "n_docs": int(m.sum()),
                        "dispersion": float(np.sqrt(om @ (h[m] - mean) ** 2))})
    return pd.DataFrame(out)


def surprise_index(docs: pd.DataFrame) -> pd.DataFrame:
    """Per cb: increment = HDS_k minus the same speaker's previous HDS (0 for a first speech); index = cumsum.
    speaker_avg5 = mean of the speaker's previous 5 documents (current one excluded); surprise = hds - speaker_avg5."""
    keys = ["date", "pub_ts_utc", "doc_id"] if "pub_ts_utc" in docs else ["date", "doc_id"]
    d = docs.dropna(subset=["hds"]).sort_values(keys).copy()
    g = d.groupby(["cb", "speaker"])["hds"]
    d["increment"] = g.diff().fillna(0.0)
    d["speaker_avg5"] = g.transform(lambda s: s.shift().rolling(5, min_periods=1).mean())
    d["surprise"] = d["hds"] - d["speaker_avg5"]
    d["hdsi"] = d.groupby("cb")["increment"].cumsum()
    return d[["date", "cb", "speaker", "doc_id", "hds", "speaker_avg5", "surprise", "increment", "hdsi"]]


def _read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def selftest() -> int:
    cases = {  # sentence -> expected theta (known answers by construction of the rules)
        "Inflation remains elevated and the labour market is tight.": 1.0,
        "Inflation is not expected to rise further.": 0.25,
        "We will cut interest rates.": 0.0,
        "The unemployment rate rose to 4.5%.": 0.25,
        "Inflation may ease somewhat.": 0.25,
        "We may raise rates.": 0.75,  # hedge caps a +2 policy action at 0.75
        "We will not hesitate to raise rates.": 1.0,
        "There will be no further rate increases.": 0.25,
        "Growth was in line with our projections.": 0.5,
        "The committee met in Frankfurt.": 0.5,
    }
    fails = [f"{s!r}: got {score_sentence(s)['theta']}, want {v}" for s, v in cases.items()
             if score_sentence(s)["theta"] != v]
    if score_sentence("The committee met in Frankfurt.")["w"] != 0.0:
        fails.append("off-topic sentence must get zero weight")
    # doc = hawk (w=1, theta=1) + off-topic (w=0) + neutral topic (w=0.5, theta=.5) -> 200*(2/3*0.5) = 66.667
    doc = score_document("Inflation remains elevated and the labour market is tight. The committee met in Frankfurt. "
                         "Growth was in line with our projections.")
    if not np.isclose(doc["hds"], 200 / 3) or not np.isclose(doc["relevance"], 0.5):
        fails.append(f"document HDS {doc['hds']:.3f} (want 66.667), relevance {doc['relevance']} (want 0.5)")
    d0 = pd.Timestamp("2026-01-01")
    docs = pd.DataFrame({"cb": "X", "speaker": ["a", "b", "a"], "doc_id": ["A", "B", "C"],
                         "date": [d0, d0 + pd.Timedelta(days=30), d0 + pd.Timedelta(days=100)],
                         "hds": [50.0, -10.0, 20.0], "weight": [1.0, 3.0, 2.0]})
    want = {30: 5.0, 90: 5.0, 91: -10.0, 100: 2.0}  # (1*50+3*-10)/4, window edge inclusive, A drops out, (3*-10+2*20)/5
    agg = aggregate(docs, 90, [d0 + pd.Timedelta(days=k) for k in want]).set_index("date")["hds_avg"]
    for k, v in want.items():
        got = agg.get(d0 + pd.Timedelta(days=k), np.nan)
        if not np.isclose(got, v):
            fails.append(f"aggregate day {k}: got {got}, want {v}")
    disp = aggregate(docs, 90, [d0 + pd.Timedelta(days=30)])["dispersion"].iloc[0]
    if not np.isclose(disp, np.sqrt(675.0)):  # sqrt(.25*45^2 + .75*15^2)
        fails.append(f"dispersion day 30: got {disp}, want 25.981")
    si = surprise_index(docs)
    if not np.isclose(si["hdsi"].iloc[-1], -30.0):  # increments 0 (a), 0 (b), 20-50=-30 (a)
        fails.append(f"surprise index end {si['hdsi'].iloc[-1]} (want -30)")
    if not (np.isnan(si["speaker_avg5"].iloc[0]) and np.isclose(si["speaker_avg5"].iloc[-1], 50.0)):
        fails.append("speaker_avg5 must exclude the current document (want NaN first, 50 for C)")
    if len(split_sentences("U.S. inflation is high. Mr. Powell spoke.")) != 2:
        fails.append("abbreviations must not split sentences")
    t = pd.DataFrame({"doc_id": ["E", "L"], "cb": "X", "speaker": "a", "doc_type": "speech", "text": "Inflation is high.",
                      "pub_ts_utc": ["2026-03-02T20:59:00Z", "2026-03-02T21:00:00Z"]})
    if list(score_documents(t, 21.0)["date"].dt.day) != [2, 3]:
        fails.append("document at/after the snap cutoff must count for the next day")
    for f in fails:
        print("FAIL", f)
    print("selftest", "FAILED" if fails else "passed")
    return 1 if fails else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--texts", help="CSV/Parquet: doc_id, cb, speaker, doc_type, pub_ts_utc, text")
    p.add_argument("--out-docs", default="cb_doc_scores.csv")
    p.add_argument("--out-daily", default="cb_hds_daily.csv")
    p.add_argument("--window-days", type=int, default=90)
    p.add_argument("--cutoff-hour-utc", type=float, default=21.0,
                   help="UTC hour of the market snap; later documents count for the next day "
                        "(21 ~ NY close; ~16 London/Europe; ~6 Tokyo/Sydney; 24 = calendar day)")
    p.add_argument("--speech-types", default="speech,press_conference,testimony,qa,interview",
                   help="doc_types averaged into the speaker series; statements/minutes are kept per document")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return selftest()
    if not a.texts:
        p.error("--texts is required (or use --selftest)")
    texts = _read(a.texts)
    if "pub_ts_utc" in texts:  # cb_texts keeps re-releases as vintages: score the first release of each document
        texts = texts.sort_values("pub_ts_utc", kind="stable").drop_duplicates("doc_id", keep="first")
    docs = score_documents(texts, a.cutoff_hour_utc)
    speeches = docs[docs["doc_type"].isin(a.speech_types.split(","))]
    si = surprise_index(speeches)  # speaker baseline from speech-type docs only; statements/minutes stay blank
    docs.merge(si[["doc_id", "speaker_avg5", "surprise"]], on="doc_id", how="left").to_csv(a.out_docs, index=False)
    daily = aggregate(speeches, a.window_days)
    if not daily.empty:
        hdsi = si.groupby(["cb", "date"])["hdsi"].last().reset_index()
        daily = pd.merge_asof(daily.sort_values("date"), hdsi.sort_values("date"), on="date", by="cb")
    daily.to_csv(a.out_daily, index=False)
    print(f"{len(docs)} documents -> {a.out_docs}; {len(daily)} cb-days -> {a.out_daily}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
