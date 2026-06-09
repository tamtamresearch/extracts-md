"""Unit tests for convert_docx.py functions."""
import re

import pytest

from convert_docx import clean, yaml_q, CAPTION_RE


@pytest.mark.unit
def test_clean_whitespace():
    """Test clean() normalizes various whitespace characters."""
    # NBSP (non-breaking space)
    assert clean("hello\xa0world") == "hello world"
    
    # Multiple spaces
    assert clean("hello  world") == "hello world"
    assert clean("hello   world") == "hello world"
    
    # Tabs
    assert clean("hello\tworld") == "hello world"
    
    # Leading/trailing whitespace
    assert clean("  hello world  ") == "hello world"
    
    # Mixed whitespace
    assert clean("  hello\xa0\t  world  ") == "hello world"
    
    # Empty string
    assert clean("") == ""
    
    # Only whitespace
    assert clean("   ") == ""


@pytest.mark.unit
def test_yaml_q_escaping():
    """Test yaml_q() properly escapes YAML strings."""
    # Simple string
    assert yaml_q("hello") == '"hello"'
    
    # String with quotes
    assert yaml_q('say "hello"') == '"say \\"hello\\""'
    
    # String with backslashes
    assert yaml_q(r"path\to\file") == '"path\\\\to\\\\file"'
    
    # String with newlines (should be collapsed)
    assert yaml_q("line1\nline2") == '"line1 line2"'
    
    # String with multiple spaces (should be normalized)
    assert yaml_q("hello   world") == '"hello world"'
    
    # Mixed newlines and spaces
    assert yaml_q("hello\n  world\n  !") == '"hello world !"'
    
    # Empty string
    assert yaml_q("") == '""'


@pytest.mark.unit
def test_caption_re_parsing():
    """Test CAPTION_RE regex matches publication metadata."""
    # Full match with edition
    text1 = "Published in 2025 (Edition 2) by ISO. 123 pages total."
    m1 = CAPTION_RE.search(text1)
    assert m1 is not None
    assert m1.group("year") == "2025"
    assert m1.group("edition") == "2"
    assert m1.group("pages") == "123"
    
    # Without "in"
    text2 = "Published 2024 (Edition 3) with 456 pages."
    m2 = CAPTION_RE.search(text2)
    assert m2 is not None
    assert m2.group("year") == "2024"
    assert m2.group("edition") == "3"
    assert m2.group("pages") == "456"
    
    # Without edition
    text3 = "Published 2023 - total of 789 pages."
    m3 = CAPTION_RE.search(text3)
    assert m3 is not None
    assert m3.group("year") == "2023"
    assert m3.group("edition") is None
    assert m3.group("pages") == "789"
    
    # Case insensitive
    text4 = "PUBLISHED 2022 with 100 PAGES"
    m4 = CAPTION_RE.search(text4)
    assert m4 is not None
    assert m4.group("year") == "2022"
    
    # No match
    text5 = "This document has no publication info"
    m5 = CAPTION_RE.search(text5)
    assert m5 is None


@pytest.mark.unit
def test_caption_re_edge_cases():
    """Test CAPTION_RE edge cases."""
    # Edition with different capitalization
    text = "Published in 2025 (edition 1), 50 pages"
    m = CAPTION_RE.search(text)
    assert m is not None
    assert m.group("edition") == "1"
    
    # Multiple digit years and pages
    text2 = "Published 1999 (Edition 99) spanning 9999 pages"
    m2 = CAPTION_RE.search(text2)
    assert m2 is not None
    assert m2.group("year") == "1999"
    assert m2.group("edition") == "99"
    assert m2.group("pages") == "9999"
