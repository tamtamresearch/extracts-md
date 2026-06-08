#!/usr/bin/env python3
"""Generate the mdBook navigation from the converted extracts.

Scans  output/<doc>/index.md , reads each front-matter, and writes:
  * output/SUMMARY.md   - mdBook table of contents
  * output/index.md     - landing page (overview table of all extracts)

Standard library only. Re-run whenever extracts are added or changed.
"""
import glob
import os
import re
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "output"


def field(fm, key):
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm, re.M)
    return m.group(1) if m else ""


def read_meta(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---", txt, re.S)
    fm = m.group(1) if m else ""
    return {
        "standard": field(fm, "standard"),
        "name": field(fm, "name"),
        "published": field(fm, "published"),
        "edition": field(fm, "edition"),
        "pages": field(fm, "pages"),
    }


def sort_key(folder):
    # natural-ish sort: split letters / numbers
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", folder)]


def main():
    docs = []
    for idx in glob.glob(os.path.join(OUT, "*", "index.md")):
        folder = os.path.basename(os.path.dirname(idx))
        meta = read_meta(idx)
        docs.append((folder, meta))
    docs.sort(key=lambda d: sort_key(d[0]))

    # ---- SUMMARY.md ----
    s = ["# Summary", "", "[Overview](index.md)", ""]
    for folder, m in docs:
        label = m["standard"] or folder
        s.append(f"- [{label}]({folder}/index.md)")
    with open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(s) + "\n")

    # ---- landing index.md ----
    p = [
        "# ITS Standard Extracts",
        "",
        "Informative extracts of selected ISO / CEN / EN technical standards "
        "prepared for ISO/TC 204. Each extract summarises selected chapters of "
        "the source standard and retains the original chapter numbering. "
        "An extract does **not** replace the standard itself.",
        "",
        "| Standard | Title | Published | Ed. | Pages |",
        "| --- | --- | --- | --- | --- |",
    ]
    for folder, m in docs:
        title = m["name"].split(" – ")[1] if " – " in m["name"] else m["name"]
        p.append(
            f"| [{m['standard'] or folder}]({folder}/index.md) "
            f"| {title} | {m['published']} | {m['edition']} | {m['pages']} |"
        )
    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(p) + "\n")

    print(f"wrote SUMMARY.md and index.md for {len(docs)} extracts")


if __name__ == "__main__":
    main()
