"""Pull HC/LO tag applications out of the assignment PDFs.

Minerva footnotes look like: superscript 3 in the body, and at the bottom of the
page "3 #breakitdown: how I applied it". For each one this writes a row with
  tag            the hashtag (LOs keep the course prefix)
  source         footnote | body_justification | mention
  justification  the footnote text, hashtag removed
  context        the last three sentences before the superscript (max 120 words);
                 for plain mentions, the sentence with the hashtag plus the one before
plus the assignment info from data/inventory.tsv.

Run: python src/extract_sections.py
"""
import csv, re, sys, pathlib, collections
import fitz  # PyMuPDF
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tags import normalise

TAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9_\-]{2,})")
NUM_RE = re.compile(r"^\s*(\d{1,2})\s*$")
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")
MAX_CTX_WORDS = 120

def load_inventory(path):
    inv = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            for res in r["resources"].split(";"):
                inv[res.partition(":")[0]] = r
    return inv

def spans_in_order(page):
    out = []
    for bi, b in enumerate(page.get_text("dict")["blocks"]):
        if b["type"] != 0:
            continue
        for li, l in enumerate(b["lines"]):
            for s in l["spans"]:
                if s["text"].strip() == "" and len(s["text"]) < 2:
                    continue
                out.append(dict(text=s["text"], size=s["size"], sup=bool(s["flags"] & 1),
                                y=s["bbox"][1], block=bi, line=li))
    return out

def body_size(spans):
    c = collections.Counter()
    for s in spans:
        c[round(s["size"], 1)] += len(s["text"])
    return c.most_common(1)[0][0] if c else 11.0

def is_note_number(s, bsize):
    return bool(NUM_RE.match(s["text"])) and s["size"] < 0.8 * bsize and not s["sup"]

def split_footnotes(spans, bsize, page_h):
    """Return (body_spans, {n: note_text}). The footnote region starts at the first
    small, non-superscript number in the lower 55% of the page whose following text
    carries a hashtag within its first 30 characters."""
    start = None
    for i, s in enumerate(spans):
        if is_note_number(s, bsize) and s["y"] > 0.45 * page_h:
            follow = " ".join(x["text"] for x in spans[i + 1:i + 5])
            if "#" in follow[:30]:
                start = i
                break
    if start is None:
        return spans, {}
    body, notes = spans[:start], {}
    i = start
    while i < len(spans):
        s = spans[i]
        if is_note_number(s, bsize):
            n = int(NUM_RE.match(s["text"]).group(1))
            j = i + 1; buf = []
            while j < len(spans) and not is_note_number(spans[j], bsize):
                buf.append(spans[j]["text"]); j += 1
            notes[n] = " ".join(buf)
            i = j
        else:
            i += 1
    return body, notes

def body_stream(body):
    """Body text with superscript markers replaced by [[FNn]] tokens."""
    parts = []
    for s in body:
        if s["sup"] and NUM_RE.match(s["text"]):
            parts.append(f" [[FN{int(NUM_RE.match(s['text']).group(1))}]] ")
        else:
            parts.append(s["text"])
    txt = " ".join(parts)
    return re.sub(r"[ \t]+", " ", txt.replace("\n", " ")).strip()

REDACT = set()
_redact_file = pathlib.Path(__file__).parent.parent / "data" / "redact_names.txt"
if _redact_file.exists():
    REDACT = {w.strip() for w in _redact_file.read_text().splitlines() if w.strip() and not w.startswith("#")}
REDACT_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, REDACT), key=len, reverse=True)) + r")\b") if REDACT else None

def clean(txt):
    txt = re.sub(r"\[\[FN\d+\]\]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    if REDACT_RE is not None:
        txt = REDACT_RE.sub("[NAME]", txt)
    return txt

def sentences(txt):
    return [x.strip() for x in SENT_RE.split(txt) if x.strip()]

def context_before_marker(stream, n):
    tok = f"[[FN{n}]]"
    pos = stream.find(tok)
    if pos < 0:
        return ""
    before = clean(stream[:pos])
    sents = sentences(before)[-3:]
    words = " ".join(sents).split()
    return " ".join(words[-MAX_CTX_WORDS:])

def context_around(stream, m_start, m_end):
    before = clean(stream[:m_start]); after = clean(stream[m_end:])
    s_before = sentences(before)
    tail = s_before[-1] if s_before else ""
    prev = s_before[-2] if len(s_before) > 1 else ""
    # if the hashtag sits at the end of a sentence, 'tail' already ends with punctuation
    head = sentences(after)[0] if sentences(after) and not re.search(r"[.!?]\s*$", tail) else ""
    words = " ".join([prev, tail, head]).split()
    return " ".join(words[-MAX_CTX_WORDS:])

def tag_list(txt):
    return [normalise(t) for t in TAG_RE.findall(txt)]

def extract(raw_dir, inventory, out_csv):
    inv = load_inventory(inventory)
    rows, seen = [], set()
    def emit(**kw):
        key = (kw["file"], kw["page"], kw["tag"], kw["source"], (kw["justification"] + kw["context"])[:60])
        if key in seen:
            return
        seen.add(key); rows.append(kw)
    for pdf in sorted(pathlib.Path(raw_dir).rglob("*.pdf")):
        rid = pdf.name.split("_")[1]
        meta = inv.get(rid, {})
        base = dict(assignment_id=meta.get("aid", ""), course=meta.get("course", pdf.parent.name),
                    title=meta.get("title", ""), due=meta.get("due", ""), group=meta.get("group", ""),
                    file=pdf.name)
        try:
            doc = fitz.open(pdf)
        except Exception as e:
            print("skip", pdf, e, file=sys.stderr); continue
        for pno, page in enumerate(doc):
            spans = spans_in_order(page)
            if not spans:
                continue
            bsize = body_size(spans)
            body, notes = split_footnotes(spans, bsize, page.rect.height)
            stream = body_stream(body)
            # 1) footnote applications
            for n, note in notes.items():
                tags = tag_list(note)
                if not tags:
                    continue
                emit(**base, page=pno + 1, marker=n, source="footnote", tag=tags[0],
                     all_tags=";".join(tags), justification=clean(TAG_RE.sub(" ", note)).lstrip(" :.-–"),
                     context=context_before_marker(stream, n))
            # 2) body justifications: a paragraph (block) that starts with a hashtag
            blocks = collections.OrderedDict()
            for s in body:
                blocks.setdefault(s["block"], []).append(s["text"])
            btexts = [re.sub(r"\s+", " ", " ".join(v)).strip() for v in blocks.values()]
            for bi, bt in enumerate(btexts):
                m = re.match(r"^(?:\d{1,2}\s*[:.)]?\s*)?#([A-Za-z][A-Za-z0-9_\-]{2,})\s*[:\-–—]?\s*(.*)$", bt, re.S)
                if not m:
                    continue
                tag, rest = normalise(m.group(1)), m.group(2).strip()
                if len(rest.split()) < 6 and bi + 1 < len(btexts) and not btexts[bi + 1].startswith("#"):
                    rest = (rest + " " + btexts[bi + 1]).strip()
                if len(rest.split()) >= 6:
                    emit(**base, page=pno + 1, marker="", source="body_justification", tag=tag,
                         all_tags=";".join(tag_list(bt)), justification=clean(TAG_RE.sub(" ", rest)),
                         context="")
            # 3) plain mentions inside the body stream
            for m in TAG_RE.finditer(stream):
                tag = normalise(m.group(1))
                ctx = clean(TAG_RE.sub(" ", context_around(stream, m.start(), m.end())))
                if len(ctx.split()) >= 5:
                    emit(**base, page=pno + 1, marker="", source="mention", tag=tag, all_tags=tag,
                         justification="", context=ctx)
    pathlib.Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    cols = ["assignment_id","course","title","due","group","file","page","marker","source","tag","all_tags","justification","context"]
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out_csv}")
    return rows

if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/processed/sections.csv"
    inv = sys.argv[3] if len(sys.argv) > 3 else "data/inventory.tsv"
    extract(raw, inv, out)
