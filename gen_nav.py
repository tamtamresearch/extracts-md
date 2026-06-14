#!/usr/bin/env python3
"""Generate mkdocs navigation and the landing page from the converted extracts.

Scans  output/extracts/<doc>/index.md , reads each front-matter, and:
  * rewrites the `nav:` block in mkdocs.yml (between GENERATED NAV markers)
  * writes  output/index.md   - landing page (overview of all extracts)
  * copies  theme/extra.css -> output/stylesheets/extra.css  (preview styling)

Standard library only. Re-run whenever extracts are added or changed.
"""
import glob
import os
import re
import shutil
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "output"
EXTRACTS = os.path.join(OUT, "extracts")

REPO = os.path.dirname(os.path.abspath(__file__))
MKDOCS_YML = os.path.join(REPO, "mkdocs.yml")
CSS_SRC = os.path.join(REPO, "theme", "extra.css")

NAV_START = "# >>> GENERATED NAV START"
NAV_END = "# <<< GENERATED NAV END"


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


def write_nav(docs):
    """Rewrite the nav block in mkdocs.yml between the GENERATED markers."""
    nav = ["nav:", "  - Overview: index.md", "  - Extracts:"]
    for folder, m in docs:
        label = m["standard"] or folder
        nav.append(f"      - {label}: extracts/{folder}/index.md")
    block = NAV_START + "\n" + "\n".join(nav) + "\n" + NAV_END

    text = open(MKDOCS_YML, encoding="utf-8").read()
    pattern = re.compile(
        re.escape(NAV_START) + r".*?" + re.escape(NAV_END), re.S
    )
    if not pattern.search(text):
        raise SystemExit(
            "mkdocs.yml is missing the GENERATED NAV markers; cannot update nav."
        )
    text = pattern.sub(block, text)
    with open(MKDOCS_YML, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_landing(docs):
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
        std_line = (
            f"**[{m['standard'] or folder}:{m['published']}]"
            f"(extracts/{folder}/index.md)**"
        )
        p.append(std_line)

        name_parts = [m["name_1"], m["name_2"], m["name_3"]]
        name_parts = [part for part in name_parts if part]
        if len(name_parts) == 1:
            p.append(name_parts[0])
        elif len(name_parts) > 1:
            combined = " – ".join(name_parts[:-1])
            p.append(combined + "  ")  # two trailing spaces = hard break
            p.append(name_parts[-1])
        p.append("")

    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(p) + "\n")


def copy_css():
    dst_dir = os.path.join(OUT, "stylesheets")
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copyfile(CSS_SRC, os.path.join(dst_dir, "extra.css"))


def main():
    docs = []
    for idx in glob.glob(os.path.join(EXTRACTS, "*", "index.md")):
        folder = os.path.basename(os.path.dirname(idx))
        docs.append((folder, read_meta(idx)))
    docs.sort(key=lambda d: sort_key(d[0]))

    write_nav(docs)
    write_landing(docs)
    copy_css()

    print(f"wrote nav + landing page for {len(docs)} extracts")


if __name__ == "__main__":
    main()
