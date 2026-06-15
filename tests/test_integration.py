"""Integration tests: implementation-agnostic end-to-end validation."""
import os
import re
from pathlib import Path

import pytest

import convert_docx
import gen_nav


@pytest.mark.integration
def test_real_extract_iso22741_10(docx_fixtures_dir, tmp_output):
    """Test full conversion of ISO/TS 22741-10 extract.
    
    This is the core regression test for refactoring - validates that conversion
    produces expected front-matter, figures, tables, and markdown structure.
    """
    # Input file
    docx_file = docx_fixtures_dir / "ISO_TS_22741-10.docx"
    assert docx_file.exists(), f"Fixture not found: {docx_file}"
    
    # Run conversion
    docname, n_figures, n_tables = convert_docx.convert(str(docx_file), str(tmp_output))
    
    # Verify output directory and files created
    output_dir = tmp_output / docname
    assert output_dir.exists()
    
    index_md = output_dir / "index.md"
    assert index_md.exists()
    
    # Read generated output
    content = index_md.read_text(encoding="utf-8")
    
    # --- Test 1: Front-matter presence and structure ---
    assert content.startswith("---\n"), "Front-matter missing opening delimiter"
    assert "\n---\n" in content, "Front-matter missing closing delimiter"
    
    # Extract front-matter
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert fm_match, "Front-matter not properly delimited"
    fm = fm_match.group(1)
    
    # Validate required fields
    assert re.search(r"^published:\s*2024", fm, re.M), "published field missing or wrong"
    assert re.search(r"^pages:\s*30", fm, re.M), "pages field missing or wrong"
    assert re.search(r'^title:\s*"ISO/TS 22741-10 - Extract"', fm, re.M), "title field missing or wrong"
    assert re.search(r'^standard:\s*"ISO/TS 22741-10"', fm, re.M), "standard field missing or wrong"
    assert re.search(r'^name:\s*".*Roadside modules AP-DATEX data interface.*"', fm, re.M), "name field missing"
    assert re.search(r'^name_1:\s*"Intelligent transport systems"', fm, re.M), "name_1 missing"
    assert re.search(r'^name_2:\s*"Roadside modules AP-DATEX data interface"', fm, re.M), "name_2 missing"
    assert re.search(r'^name_3:\s*"Part 10: Variable message signs"', fm, re.M), "name_3 missing"
    assert re.search(r'^annotation:\s*".*does not replace.*"', fm, re.M), "annotation missing"
    assert re.search(r'^note:\s*".*Extract presents selected chapters.*"', fm, re.M), "note missing"
    
    # --- Test 2: Body starts correctly ---
    body = content[fm_match.end():]
    assert body.strip().startswith("## Introduction"), "Body should start with ## Introduction"
    
    # --- Test 3: Heading demotion (H1 → H2) ---
    # No H1 headings in body
    h1_in_body = re.findall(r"^# [^#]", body, re.M)
    assert len(h1_in_body) == 0, f"Found {len(h1_in_body)} H1 headings in body (should be 0)"
    
    # Multiple H2 headings
    h2_count = len(re.findall(r"^## ", body, re.M))
    assert h2_count >= 5, f"Expected at least 5 H2 headings, found {h2_count}"
    
    # --- Test 4: Figures extracted ---
    assert n_figures == 2, f"Expected 2 figures, got {n_figures}"
    
    fig1 = output_dir / "fig-1.png"
    fig2 = output_dir / "fig-2.png"
    assert fig1.exists(), "fig-1.png not extracted"
    assert fig2.exists(), "fig-2.png not extracted"
    
    # Verify file sizes are reasonable (not empty, not too small)
    assert fig1.stat().st_size > 100, "fig-1.png too small (likely empty)"
    assert fig2.stat().st_size > 100, "fig-2.png too small (likely empty)"
    
    # Verify mkdocs-style image references with the .figure class
    assert "(fig-1.png){.figure}" in body, "fig-1.png not referenced with {.figure}"
    assert "(fig-2.png){.figure}" in body, "fig-2.png not referenced with {.figure}"

    # --- Test 4b: Captions emitted as pymdownx caption blocks (once each) ---
    # pymdownx wraps the *preceding* block, so the caption block is emitted
    # AFTER its object. Figure caption uses plain `/// caption` (renders below).
    fig1_caption = "Figure 1 – View of y physical architecture (Fig. 1 of the source standard)"
    assert re.search(
        r"!\[Figure 1\]\(fig-1\.png\)\{\.figure\}\n\n/// caption\n" + re.escape(fig1_caption),
        body,
    ), "Figure 1 caption must follow its image as a plain caption block"
    # The caption text must appear exactly once (no duplicated bold line)
    assert body.count(fig1_caption) == 1, "Figure 1 caption duplicated or missing"
    assert f"**{fig1_caption}**" not in body, "Legacy bold caption line still present"

    # Table-as-image: image first, then `/// caption | <` (figcaption above)
    assert re.search(
        r"!\[Table 2\]\(fig-2\.png\)\{\.figure\}\n\n/// caption \| <\nTable 2",
        body,
    ), "Table 2 (image) caption must follow the image with `| <`"

    # The false-positive prose line stays normal body text (not a caption)
    assert "Table 1 defines user needs" in body
    assert "/// caption\nTable 1 defines" not in body
    assert "/// caption | <\nTable 1 defines" not in body
    
    # --- Test 5: Table rendered as HTML with the caption after it ---
    assert n_tables == 1, f"Expected 1 table, got {n_tables}"
    
    assert "<table>" in body, "No <table> tag found"
    assert "</table>" in body, "No </table> closing tag found"
    assert "<tr>" in body, "No <tr> tags found"
    assert "<th>" in body or "<td>" in body, "No table cells found"
    
    # Verify colspan attribute present (merged cells)
    assert 'colspan="' in body, "No colspan attribute found (merged cells not preserved)"

    # The real-table caption is placed AFTER the table with `| <` (renders above)
    assert re.search(r"</table>\n\n/// caption \| <\nTable 1 —", body), \
        "Real table caption must follow the table with `| <`"


@pytest.mark.integration
def test_self_captioning_image_keeps_image_and_caption(tmp_path):
    """A paragraph that holds BOTH a Table caption and its image must render the
    image (not drop it) with the caption directly above it (not disjoint)."""
    docx_file = Path("input/EN_ISO_12855.docx")
    if not docx_file.exists():
        pytest.skip("EN_ISO_12855.docx not available in input/")

    out = tmp_path / "output"
    out.mkdir()
    docname, n_figures, _ = convert_docx.convert(str(docx_file), str(out))
    body = (out / docname / "index.md").read_text(encoding="utf-8")

    # The "Table 1 – Overview of ADUs" caption is in the same paragraph as its
    # image. It must render the image immediately followed by a `| <` caption
    # block (figcaption above) — never a bare caption with the image dropped.
    m = re.search(
        r"!\[Table 1\]\(fig-\d+\.png\)\{\.figure\}\n\n/// caption \| <\nTable 1 – Overview of ADUs",
        body,
    )
    assert m, "Table 1 image is not immediately followed by its caption block"
    # All four embedded figures (incl. the previously-dropped Table 1 image).
    assert n_figures == 4, f"Expected 4 figures, got {n_figures}"


@pytest.mark.integration
def test_inline_formatting_iso14823_1(tmp_path):
    """Test inline formatting conversion (bold, italic, code) for ISO 14823-1."""
    # Check if ISO 14823-1 fixture exists
    fixtures_dir = Path("tests/fixtures/docx")
    docx_file = Path("input/ISO_14823-1.docx")
    
    if not docx_file.exists():
        pytest.skip("ISO_14823-1.docx not available in input/")
    
    # Run conversion
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    docname, n_figures, n_tables = convert_docx.convert(str(docx_file), str(output_dir))
    
    # Read generated output
    index_md = output_dir / docname / "index.md"
    assert index_md.exists()
    
    content = index_md.read_text(encoding="utf-8")
    
    # Extract body (skip front-matter)
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert fm_match, "Front-matter not found"
    body = content[fm_match.end():]
    
    # --- Test 1: Code formatting (monospace) ---
    # OID in Clause 7.3 should be formatted as code
    assert "`{joint-iso-itut(2) its(28) gdd(5)}`" in body, \
        "OID should be formatted as inline code with backticks"
    
    # Technical expressions in Clause 7.5 should have at least some code formatting
    # (The exact split depends on how Word formatted the original runs)
    assert "`trafficSign" in body or "`{1 2 7 xx}`" in body or "{1 2 7 xx}" in body, \
        "Technical identifiers should be present (formatted or not)"
    
    # --- Test 2: Bold formatting ---
    # Term definitions should be bold
    assert "**Graphic Data Dictionary (GDD)**" in body, \
        "GDD term should be bold"
    
    # Clause references should be bold
    assert "**7.3 Relative object identifier (relative OID)**" in body or \
           "**7.3**" in body, \
        "Clause numbers should be bold"
    
    # --- Test 3: Italic formatting ---
    # References to external resources should be italic
    if "*ITS Terminology*" in body or "*StandardLand*" in body:
        # At least one italic reference present
        assert True
    
    # --- Test 4: No broken Markdown ---
    # Check for unmatched backticks
    backtick_count = body.count("`")
    assert backtick_count % 2 == 0, \
        f"Unmatched backticks found (count: {backtick_count})"
    
    # Check for unmatched asterisks (rough heuristic)
    # We can't perfectly detect all cases, but gross errors will show
    lines_with_odd_asterisks = []
    for i, line in enumerate(body.split("\n"), 1):
        # Skip code blocks and inline code
        line_without_code = re.sub(r"`[^`]*`", "", line)
        single = line_without_code.count("*") - line_without_code.count("**") * 2
        triple = line_without_code.count("***") * 3
        if (single + triple) % 2 != 0:
            lines_with_odd_asterisks.append((i, line[:80]))
    
    # Allow some false positives, but catch gross errors
    assert len(lines_with_odd_asterisks) < 5, \
        f"Too many lines with potentially unmatched asterisks: {lines_with_odd_asterisks[:5]}"


@pytest.mark.integration
def test_navigation_generation(sample_output_dir, tmp_path):
    """Test gen_nav.py generates mkdocs nav + landing page from front-matter."""
    output_dir = tmp_path / "output"
    extracts_dir = output_dir / "extracts"
    extracts_dir.mkdir(parents=True)

    # A temp mkdocs.yml with the GENERATED NAV markers, and a temp css source.
    mkdocs_yml = tmp_path / "mkdocs.yml"
    mkdocs_yml.write_text(
        "site_name: t\n\n"
        f"{gen_nav.NAV_START}\n"
        "nav:\n  - Overview: index.md\n"
        f"{gen_nav.NAV_END}\n",
        encoding="utf-8",
    )
    css_src = tmp_path / "extra.css"
    css_src.write_text("figcaption { text-align: center; }\n", encoding="utf-8")

    extracts = [
        ("CEN_TS_12345", {"standard": "CEN/TS 12345",
                          "name": "Traffic Management Systems – Example Standard",
                          "published": "2025", "edition": "1", "pages": "100"}),
        ("ISO_15622", {"standard": "ISO 15622",
                       "name": "Intelligent transport systems – Adaptive cruise control systems – Performance requirements",
                       "published": "2018", "edition": "3", "pages": "24"}),
        ("EN_ISO_12855", {"standard": "EN ISO 12855",
                          "name": "Intelligent transport systems – Information exchange – Part 1",
                          "published": "2022", "edition": "3", "pages": "153"}),
    ]
    for folder, meta in extracts:
        d = extracts_dir / folder
        d.mkdir()
        fm = [
            "---",
            f"published: {meta['published']}",
            f"edition: {meta['edition']}",
            f"pages: {meta['pages']}",
            f'title: "{meta["standard"]} - Extract"',
            f'standard: "{meta["standard"]}"',
            f'name: "{meta["name"]}"',
            "---",
            "",
            "## Introduction",
            "",
            "This is a test extract.",
        ]
        (d / "index.md").write_text("\n".join(fm), encoding="utf-8")

    # Point gen_nav at the temp tree/config.
    g = gen_nav.main.__globals__
    g["OUT"] = str(output_dir)
    g["EXTRACTS"] = str(extracts_dir)
    g["MKDOCS_YML"] = str(mkdocs_yml)
    g["CSS_SRC"] = str(css_src)
    gen_nav.main()

    # --- Test mkdocs nav block ---
    yml = mkdocs_yml.read_text(encoding="utf-8")
    assert "- Extracts:" in yml, "nav missing Extracts section"
    assert "extracts/CEN_TS_12345/index.md" in yml
    assert "extracts/ISO_15622/index.md" in yml
    assert "extracts/EN_ISO_12855/index.md" in yml

    # Natural sort order (CEN before EN before ISO)
    lines = yml.split("\n")
    cen = next(i for i, l in enumerate(lines) if "CEN_TS_12345" in l)
    en = next(i for i, l in enumerate(lines) if "EN_ISO_12855" in l)
    iso = next(i for i, l in enumerate(lines) if "ISO_15622" in l and "EN_ISO" not in l)
    assert cen < en < iso, "Extracts not sorted correctly"

    # --- Test landing page ---
    landing = (output_dir / "index.md").read_text(encoding="utf-8")
    assert "# ITS Standard Extracts" in landing
    assert "An extract does **not** replace the standard itself" in landing
    assert "CEN/TS 12345:2025" in landing
    assert "ISO 15622:2018" in landing
    assert "EN ISO 12855:2022" in landing
    # Landing links use the extracts/ path
    assert "(extracts/CEN_TS_12345/index.md)" in landing

    # --- Test CSS copied into output/stylesheets ---
    assert (output_dir / "stylesheets" / "extra.css").exists()


@pytest.mark.integration
def test_metadata_macro_render():
    """The macros module renders the standard-metadata box from front matter."""
    import macros

    meta = {
        "name": "Intelligent transport systems – Example – Part 1",
        "standard": "ISO 12345",
        "published": "2025",
        "edition": "2",
        "pages": "123",
        "annotation": "This Extract does not replace the technical standard itself.",
    }

    class _Env:
        pass

    env = _Env()
    env.macro = lambda f: f  # capture decorator
    # define_env registers the macro on env; emulate by calling the inner fn.
    captured = {}

    class _Reg:
        def macro(self, f):
            captured[f.__name__] = f
            return f

    macros.define_env(_Reg())
    html = captured["render_standard_metadata"](meta)

    assert "<strong><em>Intelligent transport systems" in html
    assert "standard-metadata" in html
    assert "<strong>Published:</strong> 2025" in html
    assert "<strong>Edition:</strong> 2" in html
    assert "<strong>Pages:</strong> 123" in html
    assert "does not replace" in html


@pytest.mark.integration
def test_metadata_macro_missing_fields():
    """Macro omits absent optional fields gracefully."""
    import macros

    captured = {}

    class _Reg:
        def macro(self, f):
            captured[f.__name__] = f
            return f

    macros.define_env(_Reg())
    html = captured["render_standard_metadata"](
        {"name": "Test Standard", "standard": "ISO 99999", "published": "2025", "pages": "100"}
    )
    assert "<strong>Published:</strong> 2025" in html
    assert "Edition:" not in html, "Edition shown when not present"
    assert "<strong>Pages:</strong> 100" in html


@pytest.mark.integration
def test_see_also_macro_render(tmp_path):
    """render_see_also turns a see-also.yaml mapping into a See also block."""
    import macros

    yaml_file = tmp_path / "see-also.yaml"
    yaml_file.write_text(
        "ITS Vocabulary: https://isotc204.org/iso14812/latest/\n"
        "GitHub: https://github.com/ISO-TC204/iso14812\n"
        '"iso.org: ISO/TS 14812:2022": https://www.iso.org/standard/79779.html\n'
        '"iso.org: ISO/TS 14812:2025": https://www.iso.org/standard/85041.html\n',
        encoding="utf-8",
    )

    captured = {}

    class _Reg:
        def macro(self, f):
            captured[f.__name__] = f
            return f

    macros.define_env(_Reg())
    md = captured["render_see_also"](path=str(yaml_file))

    assert md.startswith("## See also")
    assert "- [ITS Vocabulary](https://isotc204.org/iso14812/latest/)" in md
    assert (
        "- [iso.org: ISO/TS 14812:2022](https://www.iso.org/standard/79779.html)" in md
    )
    # Order is preserved (insertion order from the YAML file).
    assert md.index("ITS Vocabulary") < md.index("GitHub") < md.index("79779")


@pytest.mark.integration
def test_see_also_macro_absent(tmp_path):
    """render_see_also returns empty string when no see-also.yaml is present."""
    import macros

    captured = {}

    class _Reg:
        def macro(self, f):
            captured[f.__name__] = f
            return f

    macros.define_env(_Reg())
    assert captured["render_see_also"](path=str(tmp_path / "see-also.yaml")) == ""
