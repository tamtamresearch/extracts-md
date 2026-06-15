#!/usr/bin/env python3
"""Convert ISO/CEN/EN 'Extract' .docx files to Markdown for TC204 publishing.

Features:
  * YAML front-matter (standard, name/name_1..n, published/edition/pages, annotation, note)
  * Body from "Introduction" onward, H1 demoted to H2 (Heading n -> level n+1)
  * Embedded figures extracted to <docname>/fig-N.<ext>; vector EMF/WMF figures
    are rejected (convert them to PNG/JPEG inside the .docx and rerun)
  * Word tables -> HTML <table> with colspan/rowspan (merged cells preserved)
  * Czech custom styles mapped (Text normy, Seznam v normě, Poznámka, NadpisTabObr, ...)
"""
import glob
import html as _html
import os
import re
import shutil
import sys

import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table

P_TAG = qn("w:p")
TBL_TAG = qn("w:tbl")

DASH_SPLIT = re.compile(r"\s*[–—]\s*")
CAPTION_RE = re.compile(
    r"Published\s+(?:in\s+)?(?P<year>\d{4})"
    r"(?:\s*\(Edition\s+(?P<edition>\d+)\))?"
    r".*?(?P<pages>\d+)\s+pages",
    re.IGNORECASE,
)
CAPTION_STYLES = {"Caption", "NadpisTabObr"}
LIST_STYLES = {"List Paragraph", "Seznam v normě"}
NOTE_STYLES = set()  # Poznámka removed: authors must use proper styles
CT_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
    "image/tiff": "tif", "image/bmp": "bmp",
    "image/x-emf": "emf", "image/emf": "emf",
    "image/x-wmf": "wmf", "image/wmf": "wmf",
}
VECTOR = {"emf", "wmf"}
MONOSPACE_FONTS = {'courier', 'courier new', 'consolas', 'monaco', 'monospace'}


class VectorFigureError(Exception):
    """Raised when a .docx contains a vector (EMF/WMF) figure.

    These cannot be embedded as raster images; the figure must be converted
    to PNG/JPEG inside the .docx before conversion can proceed.
    """


def clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace(" ", " ").replace(" ", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def yaml_q(s: str) -> str:
    s = re.sub(r"\s+", " ", s.replace("\n", " ")).strip()
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------- metadata ----------

def parse_name_table(table):
    vals = []
    for c in table.rows[0].cells:
        t = clean(c.text)
        if t and t not in vals:
            vals.append(t)
    vals.sort(key=len)
    standard = vals[0]
    raw = re.sub(r"\s*\n\s*", " ", vals[-1])
    parts = [p.strip() for p in DASH_SPLIT.split(raw) if p.strip()]
    name = re.sub(r"\s+", " ", " – ".join(parts))
    return standard, name, parts


# ---------- images ----------


class ImgState:
    def __init__(self, doc, assetdir, docname):
        self.doc = doc
        self.assetdir = assetdir
        self.docname = docname
        self.cache = {}     # rid -> relative path
        self.n = 0

    def save(self, rid):
        if rid in self.cache:
            return self.cache[rid]
        part = self.doc.part.related_parts[rid]
        ext = CT_EXT.get(part.content_type, "png")
        self.n += 1
        base = f"fig-{self.n}"
        if ext in VECTOR:
            raise VectorFigureError(
                f"{self.docname}: figure {base} is a vector image "
                f"({ext.upper()}), which cannot be embedded as a raster image. "
                f"Open the .docx, convert this figure to PNG or JPEG, re-embed "
                f"it, and rerun the conversion."
            )
        os.makedirs(self.assetdir, exist_ok=True)
        # Stage in /tmp (mounts disallow file deletion); copy final file to mount.
        tmp = os.path.join("/tmp", "extract_assets")
        os.makedirs(tmp, exist_ok=True)
        staged = os.path.join(tmp, base + "." + ext)
        with open(staged, "wb") as fh:
            fh.write(part.blob)
        final = os.path.join(self.assetdir, base + "." + ext)
        shutil.copyfile(staged, final)
        rel = f"{base}.{ext}"          # md lives in same folder as figures
        self.cache[rid] = rel
        return rel


def para_blip_rids(el):
    return [b.get(qn("r:embed")) for b in el.findall(".//" + qn("a:blip"))
            if b.get(qn("r:embed"))]


# ---------- tables ----------

def cell_html(tc, imgs: ImgState) -> str:
    chunks = []
    for p in tc.findall(qn("w:p")):
        for rid in para_blip_rids(p):
            chunks.append(f'<img src="{imgs.save(rid)}" alt="">')
        txt = clean("".join(t.text or "" for t in p.iter(qn("w:t"))))
        if txt:
            chunks.append(_html.escape(txt))
    return "<br>".join(chunks)


def table_html(table, imgs: ImgState) -> str:
    trs = table._tbl.findall(qn("w:tr"))
    parsed = []
    for tr in trs:
        col, cells = 0, []
        for tc in tr.findall(qn("w:tc")):
            gs = tc.find(".//" + qn("w:gridSpan"))
            span = int(gs.get(qn("w:val"))) if gs is not None else 1
            vm = tc.find(".//" + qn("w:vMerge"))
            v = (vm.get(qn("w:val")) or "continue") if vm is not None else None
            cells.append({"tc": tc, "col": col, "span": span, "vm": v})
            col += span
        parsed.append(cells)

    nrows = len(parsed)
    for ri, row in enumerate(parsed):
        for c in row:
            if c["vm"] == "continue":
                c["render"] = False
                continue
            c["render"] = True
            rs = 1
            if c["vm"] == "restart":
                for rj in range(ri + 1, nrows):
                    if any(x["col"] == c["col"] and x["vm"] == "continue"
                           for x in parsed[rj]):
                        rs += 1
                    else:
                        break
            c["rowspan"] = rs

    out = ["<table>"]
    for ri, row in enumerate(parsed):
        out.append("  <tr>")
        tag = "th" if ri == 0 else "td"
        for c in row:
            if not c.get("render"):
                continue
            a = ""
            if c["span"] > 1:
                a += f' colspan="{c["span"]}"'
            if c.get("rowspan", 1) > 1:
                a += f' rowspan="{c["rowspan"]}"'
            out.append(f"    <{tag}{a}>{cell_html(c['tc'], imgs)}</{tag}>")
        out.append("  </tr>")
    out.append("</table>")
    return "\n".join(out)


# ---------- list numbering ----------

# Word numbering formats that should render as an *ordered* (numbered) list.
# Everything else (bullet, none, ...) renders as an unordered "-" list.
ORDERED_FMTS = {
    "decimal", "decimalZero",
    "lowerLetter", "upperLetter",
    "lowerRoman", "upperRoman",
    "ordinal", "cardinalText", "ordinalText",
}


def build_numfmt_map(doc):
    """Map (numId, ilvl) -> numFmt for a document's numbering definitions.

    Word stores list numbering indirectly: a paragraph's ``w:numPr`` points at a
    ``w:numId`` which resolves (via ``w:num`` -> ``w:abstractNumId``) to an
    ``w:abstractNum`` carrying per-level ``w:numFmt`` (decimal, bullet, ...).
    Returns an empty dict when the document has no numbering part.
    """
    try:
        numbering = doc.part.numbering_part.element
    except (AttributeError, NotImplementedError, KeyError):
        return {}
    num2ab = {}
    for num in numbering.findall(qn("w:num")):
        ab = num.find(qn("w:abstractNumId"))
        if ab is not None:
            num2ab[num.get(qn("w:numId"))] = ab.get(qn("w:val"))
    ab_fmts = {}  # abstractNumId -> {ilvl: numFmt}
    for ab in numbering.findall(qn("w:abstractNum")):
        aid = ab.get(qn("w:abstractNumId"))
        levels = {}
        for lvl in ab.findall(qn("w:lvl")):
            ilvl = lvl.get(qn("w:ilvl"))
            fmt = lvl.find(qn("w:numFmt"))
            if ilvl is not None and fmt is not None:
                levels[ilvl] = fmt.get(qn("w:val"))
        ab_fmts[aid] = levels
    result = {}
    for num_id, ab_id in num2ab.items():
        for ilvl, fmt in ab_fmts.get(ab_id, {}).items():
            result[(num_id, ilvl)] = fmt
    return result


def list_info(p, numfmt_map):
    """Return (ilvl, ordered) for a list paragraph, or None if not a list.

    ``ilvl`` is the 0-based indent level; ``ordered`` is True for numbered
    lists (decimal, roman, letter, ...) and False for bullets.
    """
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        return None
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return None
    num_id_el = numPr.find(qn("w:numId"))
    ilvl_el = numPr.find(qn("w:ilvl"))
    num_id = num_id_el.get(qn("w:val")) if num_id_el is not None else None
    # A numId of "0" means numbering is explicitly removed for this paragraph.
    if num_id is None or num_id == "0":
        return None
    ilvl = ilvl_el.get(qn("w:val")) if ilvl_el is not None else "0"
    fmt = numfmt_map.get((num_id, ilvl))
    return int(ilvl), fmt in ORDERED_FMTS


# ---------- paragraph rendering ----------

def _extract_run_text(run_elem) -> str:
    """Extract text from a Word run element, handling special elements.
    
    Word stores text in <w:t> elements but uses special elements for:
    - <w:noBreakHyphen /> non-breaking hyphen (-)
    - <w:softHyphen /> soft hyphen (optional line break)
    - <w:tab /> tab character
    """
    text_parts = []
    for elem in run_elem:
        if elem.tag == qn('w:t'):
            if elem.text:
                text_parts.append(elem.text)
        elif elem.tag == qn('w:noBreakHyphen'):
            text_parts.append('-')
        elif elem.tag == qn('w:softHyphen'):
            text_parts.append('\u00AD')  # soft hyphen character
        elif elem.tag == qn('w:tab'):
            text_parts.append('\t')
    return ''.join(text_parts)


def render_paragraph_runs(p) -> str:
    """Convert paragraph runs to Markdown, preserving inline formatting.
    
    Handles hyperlinks by traversing the paragraph's XML structure directly,
    since python-docx's p.runs iterator doesn't include hyperlink text.
    Converts Word hyperlinks to Markdown link syntax: [text](url)
    """
    
    # Extract runs from paragraph XML, including those inside hyperlinks
    all_runs = []
    
    for child in p._element:
        if child.tag == qn('w:hyperlink'):
            # Get the URL from the relationship
            r_id = child.get(qn('r:id'))
            url = None
            if r_id:
                try:
                    rel = p.part.rels[r_id]
                    url = rel.target_ref
                except (KeyError, AttributeError):
                    pass
            
            # Extract all text from runs inside the hyperlink
            link_text_parts = []
            for run_elem in child.findall(qn('w:r')):
                text = _extract_run_text(run_elem)
                if text:
                    link_text_parts.append(text)
            
            link_text = ''.join(link_text_parts)
            if not link_text:
                continue
            
            # Create Markdown link if we have a URL, otherwise just use the text
            if url:
                # Create a special run that's already formatted as a link
                all_runs.append({
                    'text': f'[{link_text}]({url})',
                    'bold': False,
                    'italic': False,
                    'code': False,
                    'is_link': True  # Mark as already formatted
                })
            else:
                # No URL found, treat as regular text
                all_runs.append({
                    'text': link_text,
                    'bold': False,
                    'italic': False,
                    'code': False
                })
        elif child.tag == qn('w:r'):
            # Regular run (not in hyperlink)
            text = _extract_run_text(child)
            if not text:
                continue
            
            # Check formatting properties
            rPr = child.find(qn('w:rPr'))
            bold = rPr is not None and rPr.find(qn('w:b')) is not None
            italic = rPr is not None and rPr.find(qn('w:i')) is not None
            
            # Check for monospace font
            is_code = False
            if rPr is not None:
                font_elem = rPr.find(qn('w:rFonts'))
                if font_elem is not None:
                    font_name = font_elem.get(qn('w:ascii'), '').lower()
                    is_code = font_name in MONOSPACE_FONTS
            
            all_runs.append({
                'text': text,
                'bold': bold,
                'italic': italic,
                'code': is_code
            })
    
    # Merge consecutive runs with identical formatting
    merged_runs = []
    for run in all_runs:
        # Don't merge links - they're already fully formatted
        if run.get('is_link'):
            merged_runs.append(run)
            continue
        
        # Check if we can merge with the previous run
        if merged_runs and \
           not merged_runs[-1].get('is_link') and \
           merged_runs[-1]['bold'] == run['bold'] and \
           merged_runs[-1]['italic'] == run['italic'] and \
           merged_runs[-1]['code'] == run['code']:
            # Merge with previous run
            merged_runs[-1]['text'] += run['text']
        else:
            # New run with different formatting
            merged_runs.append(run)
    
    # Apply Markdown formatting
    chunks = []
    for run in merged_runs:
        text = run['text']
        
        # Skip formatting for links - they're already formatted
        if run.get('is_link'):
            chunks.append(text)
            continue
        
        # Move leading/trailing spaces outside of formatting markers
        # This prevents broken Markdown like "**text **" or "** text**"
        leading_space = ''
        trailing_space = ''
        
        if text and not run['code']:  # Don't strip spaces from code
            if text[0] in ' \t':
                leading_space = text[0]
                text = text[1:]
            if text and text[-1] in ' \t':
                trailing_space = text[-1]
                text = text[:-1]
        
        # Skip empty text after stripping spaces (e.g., a run that's only spaces)
        if not text:
            chunks.append(leading_space + trailing_space)
            continue
        
        # Apply Markdown formatting to the stripped text
        # IMPORTANT: Code takes precedence. If monospace, ignore bold/italic.
        if run['code']:
            text = f"`{text}`"
        elif run['bold'] and run['italic']:
            text = f"***{text}***"
        elif run['bold']:
            text = f"**{text}**"
        elif run['italic']:
            text = f"*{text}*"
        # Underline is ignored (no Markdown equivalent)
        
        # Reassemble with spaces outside formatting
        chunks.append(leading_space + text + trailing_space)
    
    # Join runs and apply standard cleaning
    txt = ''.join(chunks)
    
    # Merge adjacent formatting markers (handles remaining edge cases)
    # Merge adjacent backticks: `foo``bar` → `foobar`
    while '``' in txt:
        txt = txt.replace('``', '')
    
    # Merge adjacent bold markers: **foo****bar** → **foobar**
    while '****' in txt:
        txt = txt.replace('****', '')
    
    txt = clean(txt).replace("\t", " — ")
    return txt


def render_paragraph(p, numfmt_map=None) -> str:
    style = p.style.name or ""
    txt = render_paragraph_runs(p)
    if not txt:
        return ""
    if style.startswith("Heading") or style == "Nadpis":
        m = re.search(r"(\d+)", style)
        level = int(m.group(1)) if m else 1
        return "#" * min(level + 1, 6) + " " + txt
    info = list_info(p, numfmt_map or {})
    if info is not None:
        ilvl, ordered = info
        indent = "    " * ilvl  # 4 spaces per nesting level (Markdown sublist)
        marker = "1." if ordered else "-"
        return f"{indent}{marker} {txt}"
    if style in LIST_STYLES:
        return "- " + txt
    if style in NOTE_STYLES:
        return "> " + txt
    return txt


def _normalize_code_ws(text: str) -> str:
    """Normalize odd Word spaces to ASCII spaces without collapsing/stripping.

    Mirrors the first line of ``clean()`` (nbsp/narrow/figure spaces -> space)
    but, unlike ``clean()``, preserves leading whitespace and run-length so a
    code line keeps its visible indentation. Literal tabs become 4 spaces.
    """
    text = text.replace("\xa0", " ").replace(" ", " ").replace(" ", " ")
    return text.replace("\t", "    ")


def code_line(p, numfmt_map=None):
    """Return the raw text of an all-monospace code paragraph, else ``None``.

    A paragraph qualifies as a code line only when it has at least one
    text-bearing run and *every* text-bearing run uses a monospace font. It is
    excluded if it is a heading, list, or note paragraph (those keep their
    normal rendering). Indentation is preserved (``clean()`` is not applied).

    Mixed prose containing an inline monospace term does **not** qualify, so it
    continues to render as inline ``code`` via ``render_paragraph``.
    """
    style = p.style.name or ""
    if style.startswith("Heading") or style == "Nadpis":
        return None
    if list_info(p, numfmt_map or {}) is not None:
        return None
    if style in LIST_STYLES or style in NOTE_STYLES:
        return None

    saw_text = False
    parts = []
    for child in p._element:
        if child.tag == qn("w:hyperlink"):
            # A hyperlink in the paragraph means it is not a plain code line.
            for run_elem in child.findall(qn("w:r")):
                if _extract_run_text(run_elem).strip():
                    return None
            continue
        if child.tag != qn("w:r"):
            continue
        text = _extract_run_text(child)
        parts.append(text)
        if not text.strip():
            continue  # whitespace-only run doesn't need to be monospace
        rPr = child.find(qn("w:rPr"))
        font_elem = rPr.find(qn("w:rFonts")) if rPr is not None else None
        font_name = font_elem.get(qn("w:ascii"), "").lower() if font_elem is not None else ""
        if font_name not in MONOSPACE_FONTS:
            return None
        saw_text = True

    if not saw_text:
        return None
    return _normalize_code_ws("".join(parts)).rstrip()


# ---------- captions ----------

CAPTION_RE_PREFIX = re.compile(r"^(Figure|Table)\b", re.IGNORECASE)


def _para_centered(p) -> bool:
    """True if the paragraph is centre-aligned (w:jc=center)."""
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        return False
    jc = pPr.find(qn("w:jc"))
    return jc is not None and jc.get(qn("w:val")) == "center"


def _para_all_bold(p) -> bool:
    """True if the paragraph has runs and every run with text is bold."""
    runs = p._p.findall(qn("w:r"))
    saw_text = False
    for r in runs:
        if not _extract_run_text(r).strip():
            continue
        saw_text = True
        rPr = r.find(qn("w:rPr"))
        if rPr is None or rPr.find(qn("w:b")) is None:
            return False
    return saw_text


def is_caption(p) -> bool:
    """Detect a figure/table caption paragraph.

    Requires the text to start with ``Figure N``/``Table N`` AND for the
    paragraph to look like a caption (centred, all-bold, or a caption style).
    This rejects ordinary prose that merely begins with the word "Table".
    """
    txt = clean(p.text)
    if not CAPTION_RE_PREFIX.match(txt):
        return False
    style = p.style.name or ""
    return (
        style in CAPTION_STYLES
        or _para_centered(p)
        or _para_all_bold(p)
    )


def caption_kind(text: str) -> str:
    """Return 'figure' or 'table' from the caption's leading word."""
    return "table" if re.match(r"^Table\b", text.strip(), re.IGNORECASE) else "figure"


def caption_label(text: str) -> str:
    """Short alt text, e.g. 'Figure 1' / 'Table 2', from a caption string."""
    m = re.match(r"^(Figure|Table)\s+([\w.\-]+)", text.strip(), re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return text.strip().split("\u2013")[0].strip()[:40]


def caption_block(text: str, above: bool) -> str:
    """Render a pymdownx generic caption block.

    The block must be placed **immediately after** the object it captions
    (image/table); pymdownx always wraps the *preceding* block in a ``<figure>``.
    ``above=True`` (``| <``) renders the ``<figcaption>`` above the object
    (for tables); otherwise it renders below (for figures). The generic
    ``caption`` type adds no auto-number, so the verbatim docx text is preserved.
    """
    header = "/// caption | <" if above else "/// caption"
    return f"{header}\n{text}\n///"


# ---------- main convert ----------

def convert(path, outdir):
    doc = docx.Document(path)
    docname = os.path.splitext(os.path.basename(path))[0]
    docdir = os.path.join(outdir, docname)
    imgs = ImgState(doc, docdir, docname)
    numfmt_map = build_numfmt_map(doc)

    paras = [p for p in doc.paragraphs if p.text.strip()]
    annotation = clean(paras[1].text) if len(paras) > 1 else ""
    caption = next((clean(p.text) for p in paras
                    if clean(p.text).startswith("Published")), "")
    standard, name, parts = parse_name_table(doc.tables[0])
    note = next((clean(p.text) for p in paras
                 if clean(p.text).startswith("Note:")), "")

    fm = ["---"]
    m = CAPTION_RE.search(caption)
    if m:
        fm.append(f"published: {int(m.group('year'))}")
        if m.group("edition"):
            fm.append(f"edition: {int(m.group('edition'))}")
        fm.append(f"pages: {int(m.group('pages'))}")
    fm.append(f"title: {yaml_q(standard + ' - Extract')}")
    fm.append(f"standard: {yaml_q(standard)}")
    fm.append(f"name: {yaml_q(name)}")
    for i, part in enumerate(parts, 1):
        fm.append(f"name_{i}: {yaml_q(part)}")
    if annotation:
        fm.append(f"annotation: {yaml_q(annotation)}")
    if note:
        fm.append(f"note: {yaml_q(note)}")
    fm.append("---")

    # ordered body blocks
    blocks = []
    in_body = False
    for child in doc.element.body.iterchildren():
        if child.tag == P_TAG:
            p = Paragraph(child, doc)
            if not in_body:
                if p.text.strip().lower().startswith("introduction") \
                        and (p.style.name or "").startswith("Heading"):
                    in_body = True
                else:
                    continue
            blocks.append(("p", p))
        elif child.tag == TBL_TAG:
            if in_body:
                blocks.append(("tbl", Table(child, doc)))

    # Identify caption paragraphs / image-bearing paragraphs up front.
    is_cap = [kind == "p" and is_caption(obj) for kind, obj in blocks]
    has_img = [kind == "p" and bool(para_blip_rids(obj._p))
               for kind, obj in blocks]
    # A caption paragraph that also carries its own image is "self-captioning";
    # it is rendered on its own and must not be claimed by another caption.
    self_cap = [is_cap[i] and has_img[i] for i in range(len(blocks))]

    def _is_object(j):
        """A figure/table object that a *separate* caption can attach to."""
        return (
            0 <= j < len(blocks)
            and not self_cap[j]
            and (blocks[j][0] == "tbl" or (has_img[j] and not is_cap[j]))
        )

    # Assign each (non-self) caption to exactly one owning object.
    #   Figure caption -> the image *before* it.
    #   Table caption  -> the object (table or image) *after* it; else before.
    owner = {}  # caption_index -> object_index
    for i, cap in enumerate(is_cap):
        if not cap or self_cap[i]:
            continue
        kind_cap = caption_kind(clean(blocks[i][1].text))
        order = (i - 1, i + 1) if kind_cap == "figure" else (i + 1, i - 1)
        for j in order:
            if _is_object(j) and j not in owner.values():
                owner[i] = j
                break

    cap_for = {oj: ci for ci, oj in owner.items()}  # object_index -> caption_index

    def _emit_image(rids, ctext):
        """Emit an image (+ optional caption) for a paragraph's blip rids.

        The pymdownx caption block always attaches to the *preceding* block, so
        the caption is emitted **after** the image; ``above`` only controls
        whether the figcaption renders above (tables) or below (figures) the
        image inside the figure.
        """
        above = caption_kind(ctext) == "table" if ctext else False
        label = caption_label(ctext) if ctext else ""
        first = True
        for rid in rids:
            rel = imgs.save(rid)
            img_md = f"![{label if first else ''}]({rel}){{.figure}}"
            lines.append(img_md)
            if first and ctext:
                lines.append(caption_block(ctext, above=above))
            first = False

    lines = []
    code_buf = []  # consecutive monospace code lines awaiting a fenced block

    def flush_code():
        """Emit any buffered code lines as a single fenced code block."""
        if not code_buf:
            return
        # Use a longer fence if any line itself contains a run of backticks.
        fence = "```"
        while any(fence in ln for ln in code_buf):
            fence += "`"
        lines.append(fence + "\n" + "\n".join(code_buf) + "\n" + fence)
        code_buf.clear()

    for i, (kind, obj) in enumerate(blocks):
        if self_cap[i]:
            # Caption text and image live in the same paragraph: render the
            # image with its own caption (table -> above, figure -> below).
            flush_code()
            _emit_image(para_blip_rids(obj._p), clean(obj.text))
            continue

        if is_cap[i]:
            flush_code()
            if i not in owner:
                # Caption with no object: keep it as a standalone caption.
                lines.append(caption_block(clean(obj.text), above=False))
            continue

        ctext = clean(blocks[cap_for[i]][1].text) if i in cap_for else ""

        if kind == "tbl":
            # The caption block attaches to the preceding block, so it must be
            # emitted *after* the table; ``above=True`` (`| <`) renders the
            # figcaption above the table inside the figure.
            flush_code()
            lines.append(table_html(obj, imgs))
            if ctext:
                lines.append(caption_block(ctext, above=True))
            continue

        rids = para_blip_rids(obj._p)
        if rids:
            flush_code()
            _emit_image(rids, ctext)
            continue

        # Group consecutive all-monospace paragraphs into one fenced block.
        cl = code_line(obj, numfmt_map)
        if cl is not None:
            code_buf.append(cl)
            continue

        flush_code()
        md = render_paragraph(obj, numfmt_map)
        if md:
            lines.append(md)

    flush_code()
    body = "\n\n".join(lines)
    os.makedirs(docdir, exist_ok=True)
    out_md = os.path.join(docdir, "index.md")
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(fm) + "\n\n" + body + "\n")
    return docname, imgs.n, sum(1 for k, _ in blocks if k == "tbl")


def scan_doc(path):
    """Inspect a .docx for content that breaks conversion.

    Returns a list of human-readable problem strings (empty if the document
    is convertible). Currently flags vector (EMF/WMF) figures, which the
    converter rejects.
    """
    problems = []
    doc = docx.Document(path)
    for rid, part in doc.part.related_parts.items():
        ext = CT_EXT.get(getattr(part, "content_type", ""), "")
        if ext in VECTOR:
            problems.append(
                f"vector figure ({ext.upper()}) — convert to PNG/JPEG in the .docx"
            )
    return problems


def _docx_inputs(indir):
    for f in sorted(glob.glob(os.path.join(indir, "*.docx"))):
        if os.path.basename(f).startswith("~"):
            continue
        yield f


def check(indir):
    """Scan all input docx and report problems; return number of bad docs.

    Does not abort on the first problem — reports every offending document so
    they can all be fixed in one pass (intended for local development).
    """
    bad = 0
    for f in _docx_inputs(indir):
        name = os.path.basename(f)
        try:
            problems = scan_doc(f)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the scan
            print(f"[ERROR] {name}: could not read ({exc})")
            bad += 1
            continue
        if problems:
            bad += 1
            print(f"[FAIL] {name}")
            for p in problems:
                print(f"        - {p}")
        else:
            print(f"[ok]   {name}")
    if bad:
        print(f"\n{bad} document(s) need attention before conversion.")
    else:
        print("\nAll documents are convertible.")
    return bad


def main():
    args = sys.argv[1:]
    if args and args[0] == "--check":
        indir = args[1] if len(args) > 1 else "input"
        sys.exit(1 if check(indir) else 0)

    indir, outdir = args[0], args[1]
    # Extracts live under <outdir>/extracts/<doc>/ to mirror the production
    # mkdocs site layout (docs/extracts/<doc>/index.md).
    extracts_dir = os.path.join(outdir, "extracts")
    os.makedirs(extracts_dir, exist_ok=True)
    for f in _docx_inputs(indir):
        try:
            name, nimg, ntbl = convert(f, extracts_dir)
        except VectorFigureError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print(
                "Tip: run `mise run check` to list every document that needs "
                "vector figures converted.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"{name:24} figures={nimg} tables={ntbl}")


if __name__ == "__main__":
    main()
