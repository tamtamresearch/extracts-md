#!/usr/bin/env python3
"""mdBook preprocessor: strip YAML front-matter from each chapter and inject a
title header (H1 + metadata line + annotation) so the pages render cleanly.

Standard library only — no third-party deps required on the build machine.

Configured in book.toml:
    [preprocessor.frontmatter]
    command = "python3 frontmatter_preprocessor.py"
"""
import json
import re
import sys

FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)


def _field(fm: str, key: str) -> str:
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm, re.M)
    return m.group(1) if m else ""


def transform(content: str) -> str:
    m = FM_RE.match(content)
    if not m:
        return content
    fm, body = m.group(1), content[m.end():]
    name = _field(fm, "name")
    std = _field(fm, "standard")
    pub = _field(fm, "published")
    ed = _field(fm, "edition")
    pg = _field(fm, "pages")
    ann = _field(fm, "annotation")

    head = [f"# {name or std or 'Extract'}"]
    meta = []
    if std:
        meta.append(f"**{std}**")
    if pub:
        meta.append(f"Published {pub}" + (f" (Edition {ed})" if ed else ""))
    if pg:
        meta.append(f"{pg} pages")
    if meta:
        head.append(" · ".join(meta))
    if ann:
        head.append(f"*{ann}*")
    return "\n\n".join(head) + "\n\n" + body


def walk(items):
    for it in items:
        ch = it.get("Chapter") if isinstance(it, dict) else None
        if not ch:
            continue
        if ch.get("content"):
            ch["content"] = transform(ch["content"])
        if ch.get("sub_items"):
            walk(ch["sub_items"])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)                     # support every renderer
    _context, book = json.load(sys.stdin)
    walk(book["sections"])
    json.dump(book, sys.stdout)


if __name__ == "__main__":
    main()
