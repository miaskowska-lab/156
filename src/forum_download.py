"""Scrape my submitted assignments and their PDFs from Forum.

Forum has no export, so this logs in with the session cookie from my browser
(DevTools > Application > Cookies > sessionid) and walks the same requests the
Forum page makes, term by term.

    python src/forum_download.py --cookie "sessionid=..." --terms 31 30 32 33 34 35 36 37 38 39
"""
import argparse, csv, pathlib, re, sys
import requests

BASE = "https://forum.minerva.edu"

def get(session, path, **params):
    r = session.get(BASE + path, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cookie", required=True, help='e.g. "sessionid=abc123"')
    ap.add_argument("--terms", nargs="+", type=int, required=True)
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    s = requests.Session(); s.headers["Cookie"] = a.cookie
    out = pathlib.Path(a.out); (out / "raw").mkdir(parents=True, exist_ok=True)
    rows = []
    for term in a.terms:
        page = 1
        while True:
            d = get(s, "/api/v1/paginated-assignments", show_submitted="true", student_list="true", page_size=100,
                    page=page, term_id=term, category=["iterative", "signature", "final", "location-based"],
                    include_description="false")
            for asg in d["results"]:
                sub = asg.get("latest-finalized-assignment-submission")
                if not sub:
                    continue
                res = ";".join(f'{r["resource-id"]}:{(r.get("resource") or {}).get("type", "")}'
                               for r in sub.get("assignment-submission-resources", []))
                rows.append(dict(aid=asg["id"], course=asg["course-code"], title=asg["title"],
                                 due=(asg["due-date"] or "")[:10], group=int(bool(asg["is-group-assignment"])),
                                 sub_id=sub["id"], resources=res))
            if not d.get("next"):
                break
            page += 1
    with open(out / "inventory.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} submitted assignments -> {out/'inventory.tsv'}")
    for r in rows:
        for res in r["resources"].split(";"):
            rid, _, ty = res.partition(":")
            if ty != "pdf":
                continue
            d = out / "raw" / r["course"]; d.mkdir(exist_ok=True)
            slug = re.sub(r"[^A-Za-z0-9]+", "_", r["title"])[:40].strip("_")
            target = d / f'{r["aid"]}_{rid}_{slug}.pdf'
            if target.exists():
                continue
            url = get(s, f"/api/v1/resources/{rid}/signed_url", **{"content-disposition": "inline"})["url"]
            target.write_bytes(requests.get(url, timeout=120).content)
            print("downloaded", target.name)

if __name__ == "__main__":
    main()
