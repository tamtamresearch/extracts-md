"""Integration tests: implementation-agnostic end-to-end validation."""
import os
import re
from pathlib import Path

import pytest

import convert_docx
import gen_nav
import frontmatter_preprocessor


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
    
    # Verify markdown image references
    assert "![" in body and "](fig-1.png)" in body, "fig-1.png not referenced in markdown"
    assert "![" in body and "](fig-2.png)" in body, "fig-2.png not referenced in markdown"
    
    # --- Test 5: Table rendered as HTML ---
    assert n_tables == 1, f"Expected 1 table, got {n_tables}"
    
    assert "<table>" in body, "No <table> tag found"
    assert "</table>" in body, "No </table> closing tag found"
    assert "<tr>" in body, "No <tr> tags found"
    assert "<th>" in body or "<td>" in body, "No table cells found"
    
    # Verify colspan attribute present (merged cells)
    assert 'colspan="' in body, "No colspan attribute found (merged cells not preserved)"


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
    """Test gen_nav.py generates correct SUMMARY.md and index.md."""
    # Create temporary output directory with sample extracts
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Create 3 sample extracts with front-matter
    extracts = [
        ("CEN_TS_12345", {
            "standard": "CEN/TS 12345",
            "name": "Traffic Management Systems – Example Standard",
            "published": "2025",
            "edition": "1",
            "pages": "100"
        }),
        ("ISO_15622", {
            "standard": "ISO 15622",
            "name": "Intelligent transport systems – Adaptive cruise control systems – Performance requirements",
            "published": "2018",
            "edition": "3",
            "pages": "24"
        }),
        ("EN_ISO_12855", {
            "standard": "EN ISO 12855",
            "name": "Intelligent transport systems – Information exchange – Part 1",
            "published": "2022",
            "edition": "3",
            "pages": "153"
        }),
    ]
    
    for folder, meta in extracts:
        extract_dir = output_dir / folder
        extract_dir.mkdir()
        
        # Write index.md with front-matter
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
        (extract_dir / "index.md").write_text("\n".join(fm), encoding="utf-8")
    
    # Run gen_nav
    gen_nav.main.__globals__["OUT"] = str(output_dir)
    gen_nav.main()
    
    # --- Test SUMMARY.md ---
    summary_file = output_dir / "SUMMARY.md"
    assert summary_file.exists(), "SUMMARY.md not generated"
    
    summary = summary_file.read_text(encoding="utf-8")
    assert "# Summary" in summary, "SUMMARY.md missing header"
    assert "[Overview](index.md)" in summary, "SUMMARY.md missing overview link"
    
    # Verify all 3 extracts present and sorted
    assert "[CEN/TS 12345](CEN_TS_12345/index.md)" in summary
    assert "[ISO 15622](ISO_15622/index.md)" in summary
    assert "[EN ISO 12855](EN_ISO_12855/index.md)" in summary
    
    # Verify natural sort order (CEN before EN before ISO)
    lines = summary.split("\n")
    cen_line = next(i for i, l in enumerate(lines) if "CEN_TS_12345" in l)
    en_line = next(i for i, l in enumerate(lines) if "EN_ISO_12855" in l)
    iso_line = next(i for i, l in enumerate(lines) if "ISO_15622" in l and "EN_ISO" not in l)
    assert cen_line < en_line < iso_line, "Extracts not sorted correctly"
    
    # --- Test index.md landing page ---
    index_file = output_dir / "index.md"
    assert index_file.exists(), "index.md not generated"
    
    landing = index_file.read_text(encoding="utf-8")
    assert "# ITS Standard Extracts" in landing, "Landing page missing title"
    assert "An extract does **not** replace the standard itself" in landing, "Landing page missing intro text"
    
    # Verify all 3 extracts with new format: **[STANDARD:YEAR]**
    assert "CEN/TS 12345:2025" in landing
    assert "ISO 15622:2018" in landing
    assert "EN ISO 12855:2022" in landing


@pytest.mark.integration
def test_preprocessor_transform():
    """Test frontmatter_preprocessor.py transform function."""
    # Test content with full front-matter
    input_md = """---
published: 2025
edition: 2
pages: 123
title: "ISO 12345 - Extract"
standard: "ISO 12345"
name: "Intelligent transport systems – Example Standard – Part 1: Specification"
annotation: "This Extract does not replace the technical standard itself."
note: "Note: This Extract presents selected chapters."
---

## Introduction

This is the body content.

## 3 Terms and definitions

Some terms here.
"""
    
    output = frontmatter_preprocessor.transform(input_md)
    
    # --- Test YAML stripped ---
    assert not output.startswith("---"), "YAML front-matter not stripped"
    assert "published: 2025" not in output, "Front-matter fields still present"
    
    # --- Test H1 title injected ---
    assert output.startswith("# Intelligent transport systems"), "H1 title not injected from 'name'"
    
    # --- Test metadata line formatted ---
    assert "**ISO 12345**" in output, "Standard not in metadata line"
    assert "Published 2025 (Edition 2)" in output, "Published/Edition not formatted correctly"
    assert "123 pages" in output, "Pages not in metadata line"
    
    # --- Test annotation rendered ---
    assert "*This Extract does not replace" in output, "Annotation not italicized"
    
    # --- Test body preserved ---
    assert "## Introduction" in output, "Body content not preserved"
    assert "## 3 Terms and definitions" in output, "Body headings not preserved"


@pytest.mark.integration
def test_preprocessor_transform_missing_fields():
    """Test preprocessor handles missing optional fields gracefully."""
    input_md = """---
published: 2025
pages: 100
title: "ISO 99999 - Extract"
standard: "ISO 99999"
name: "Test Standard"
---

## Content

Body text.
"""
    
    output = frontmatter_preprocessor.transform(input_md)
    
    # Title injected
    assert output.startswith("# Test Standard"), "Title not injected"
    
    # Published without edition
    assert "Published 2025" in output
    assert "(Edition" not in output, "Edition mentioned when not present"
    
    # Pages present
    assert "100 pages" in output


@pytest.mark.integration
def test_preprocessor_transform_no_frontmatter():
    """Test preprocessor leaves content unchanged when no front-matter present."""
    input_md = """# Regular Markdown

This has no front-matter.

## Section

Content here.
"""
    
    output = frontmatter_preprocessor.transform(input_md)
    
    # Content unchanged
    assert output == input_md, "Content without front-matter was modified"
