"""Unit tests for frontmatter_preprocessor.py functions."""
import pytest

from frontmatter_preprocessor import _field, transform


@pytest.mark.unit
def test_field_extraction():
    """Test _field() extracts YAML fields correctly."""
    fm = """published: 2025
edition: 2
pages: 123
title: "ISO 12345 - Extract"
standard: "ISO 12345"
name: "Intelligent transport systems"
"""
    
    # Unquoted values
    assert _field(fm, "published") == "2025"
    assert _field(fm, "edition") == "2"
    assert _field(fm, "pages") == "123"
    
    # Quoted values
    assert _field(fm, "title") == "ISO 12345 - Extract"
    assert _field(fm, "standard") == "ISO 12345"
    assert _field(fm, "name") == "Intelligent transport systems"
    
    # Missing field
    assert _field(fm, "nonexistent") == ""


@pytest.mark.unit
def test_transform_strips_frontmatter():
    """Test transform() removes YAML front-matter."""
    input_md = """---
title: "Test"
---

## Content

Body text.
"""
    
    output = transform(input_md)
    assert "---" not in output
    assert "title:" not in output


@pytest.mark.unit
def test_transform_injects_title():
    """Test transform() injects H1 from name field."""
    input_md = """---
name: "Example Standard"
standard: "ISO 12345"
---

## Content
"""
    
    output = transform(input_md)
    assert output.startswith("# Example Standard")


@pytest.mark.unit
def test_transform_metadata_line():
    """Test transform() formats metadata line correctly."""
    # With all fields
    input1 = """---
standard: "ISO 12345"
published: 2025
edition: 2
pages: 100
name: "Test"
---

Body
"""
    
    output1 = transform(input1)
    assert "**ISO 12345**" in output1
    assert "Published 2025 (Edition 2)" in output1
    assert "100 pages" in output1
    assert " · " in output1  # Separator
    
    # Without edition
    input2 = """---
standard: "ISO 99999"
published: 2024
pages: 50
name: "Test"
---

Body
"""
    
    output2 = transform(input2)
    assert "**ISO 99999**" in output2
    assert "Published 2024" in output2
    assert "(Edition" not in output2
    assert "50 pages" in output2


@pytest.mark.unit
def test_transform_annotation():
    """Test transform() italicizes annotation."""
    input_md = """---
name: "Test"
annotation: "This is informative only."
---

Body
"""
    
    output = transform(input_md)
    assert "*This is informative only.*" in output


@pytest.mark.unit
def test_transform_no_frontmatter():
    """Test transform() leaves content unchanged when no front-matter."""
    input_md = """# Regular Markdown

No front-matter here.
"""
    
    output = transform(input_md)
    assert output == input_md


@pytest.mark.unit
def test_transform_empty_content():
    """Test transform() handles empty content."""
    output = transform("")
    assert output == ""


@pytest.mark.unit
def test_transform_preserves_body():
    """Test transform() preserves all body content."""
    input_md = """---
name: "Test"
standard: "ISO 12345"
---

## Introduction

This is paragraph 1.

This is paragraph 2.

### Subsection

- List item 1
- List item 2

> A quote

```code
block
```
"""
    
    output = transform(input_md)
    
    # All body content preserved
    assert "## Introduction" in output
    assert "This is paragraph 1." in output
    assert "This is paragraph 2." in output
    assert "### Subsection" in output
    assert "- List item 1" in output
    assert "> A quote" in output
    assert "```code" in output
