"""Build the modelling table from data/processed/sections.csv.

build_table() returns (apps, mentions): apps has one row per footnote or body
justification, mentions has the plain hashtag mentions. Both get the columns
text_justification, text_context, text_both and a _masked copy of each.
"""
from __future__ import annotations
import re, sys, pathlib
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tags import family, is_lo, name_words, FAMILY_NAMES

CORNERSTONE_COURSE = re.compile(r"^(FA|EA|MC|CX)5[01]$")

def load_sections(path="data/processed/sections.csv") -> pd.DataFrame:
    df = pd.read_csv(path).fillna("")
    df["is_lo"] = df.tag.map(is_lo)
    return df

def usage_by_cornerstone(df: pd.DataFrame) -> dict:
    """{tag: {FA: n, EA: n, ...}} counted over Year-1 cornerstone courses only."""
    sub = df[df.course.str.match(CORNERSTONE_COURSE)]
    out = {}
    for (tag, course), n in sub.groupby(["tag", "course"]).size().items():
        out.setdefault(tag, {})[course[:2]] = out.get(tag, {}).get(course[:2], 0) + int(n)
    return out

def assign_families(df: pd.DataFrame) -> pd.DataFrame:
    usage = usage_by_cornerstone(df)
    df = df.copy()
    df["family"] = [family(t, usage.get(t)) for t in df.tag]
    df["family_rule"] = ["LO" if is_lo(t) else ("usage" if _usage_decides(usage.get(t)) else "handbook") for t in df.tag]
    return df

def _usage_decides(u: dict | None) -> bool:
    if not u:
        return False
    best = max(u.values())
    return best >= 2 and sum(1 for v in u.values() if v == best) == 1

MASK_GENERIC = ["hc", "hcs", "lo", "los", "habit", "habits", "foundational concept", "foundational concepts",
                "footnote", "footnotes", "applied", "apply", "applying", "application"]

def mask_text(text: str, tag: str) -> str:
    """Remove the tag's own name words and generic HC words from the text."""
    out = text
    for w in sorted(name_words(tag), key=len, reverse=True):
        out = re.sub(r"(?i)\b" + re.escape(w) + r"\b", " ", out)
    for w in MASK_GENERIC:
        out = re.sub(r"(?i)\b" + re.escape(w) + r"\b", " ", out)
    return re.sub(r"\s+", " ", out).strip()

def build_table(path="data/processed/sections.csv"):
    df = assign_families(load_sections(path))
    apps = df[df.source.isin(["footnote", "body_justification"])].copy()
    ment = df[df.source == "mention"].copy()
    for d in (apps, ment):
        d["text_justification"] = d.justification
        d["text_context"] = d.context
        d["text_both"] = (d.justification + " " + d.context).str.strip()
        for col in ("text_justification", "text_context", "text_both"):
            d[col + "_masked"] = [mask_text(t, g) for t, g in zip(d[col], d.tag)]
    apps = apps[apps.family != "UNK"]
    ment = ment[ment.family != "UNK"]
    return apps.reset_index(drop=True), ment.reset_index(drop=True)

def tag_summary(apps: pd.DataFrame) -> pd.DataFrame:
    s = apps.groupby(["tag", "family"]).size().reset_index(name="n").sort_values("n", ascending=False)
    s["family_name"] = s.family.map(FAMILY_NAMES)
    return s.reset_index(drop=True)

if __name__ == "__main__":
    apps, ment = build_table()
    print(apps.family.value_counts()); print(tag_summary(apps).head(25).to_string())
