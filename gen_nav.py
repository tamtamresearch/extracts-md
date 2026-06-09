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
        "name_1": field(fm, "name_1"),
        "name_2": field(fm, "name_2"),
        "name_3": field(fm, "name_3"),
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
    ]
    
    for folder, m in docs:
        # Build standard identifier with year
        std_line = f"**[{m['standard'] or folder}:{m['published']}]({folder}/index.md)**"
        
        p.append(std_line)
        
        # Build name parts: combine earlier parts, show last part separately
        name_parts = [m['name_1'], m['name_2'], m['name_3']]
        name_parts = [part for part in name_parts if part]  # filter empty
        
        if len(name_parts) == 1:
            # Only one part - show as single line
            p.append(name_parts[0])
        elif len(name_parts) > 1:
            # Multiple parts - combine all but last with "–", add hard break before last part
            combined = " – ".join(name_parts[:-1])
            # Two spaces at end = hard line break in Markdown
            p.append(combined + "  ")
            p.append(name_parts[-1])
        
        p.append("")  # blank line between entries
    
    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(p) + "\n")

    print(f"wrote SUMMARY.md and index.md for {len(docs)} extracts")


if __name__ == "__main__":
    main()
