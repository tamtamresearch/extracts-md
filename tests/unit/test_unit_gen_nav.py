"""Unit tests for gen_nav.py functions."""
import pytest

from gen_nav import field, sort_key


@pytest.mark.unit
def test_field_extraction():
    """Test field() extracts YAML fields correctly."""
    fm = """published: 2025
edition: 2
pages: 123
title: "ISO 12345 - Extract"
standard: "ISO 12345"
name: "Intelligent transport systems"
"""
    
    # Unquoted values
    assert field(fm, "published") == "2025"
    assert field(fm, "edition") == "2"
    assert field(fm, "pages") == "123"
    
    # Quoted values
    assert field(fm, "title") == "ISO 12345 - Extract"
    assert field(fm, "standard") == "ISO 12345"
    assert field(fm, "name") == "Intelligent transport systems"
    
    # Missing field
    assert field(fm, "nonexistent") == ""


@pytest.mark.unit
def test_field_multiline_value():
    """Test field() handles values with special characters."""
    fm = """title: "Test – with en-dash"
name: "Line with \\"escaped\\" quotes"
empty: ""
"""
    
    assert field(fm, "title") == "Test – with en-dash"
    assert field(fm, "name") == 'Line with \\"escaped\\" quotes'
    assert field(fm, "empty") == ""


@pytest.mark.unit
def test_sort_key_natural_ordering():
    """Test sort_key() produces natural sort order."""
    # Basic numeric sorting
    folders = ["ISO_15622", "ISO_1234", "ISO_99999"]
    sorted_folders = sorted(folders, key=sort_key)
    assert sorted_folders == ["ISO_1234", "ISO_15622", "ISO_99999"]
    
    # With hyphens (parts)
    folders2 = ["ISO_22726-1", "ISO_22726-10", "ISO_22726-2"]
    sorted_folders2 = sorted(folders2, key=sort_key)
    assert sorted_folders2 == ["ISO_22726-1", "ISO_22726-2", "ISO_22726-10"]
    
    # Mixed prefixes
    folders3 = ["EN_ISO_12855", "ISO_15622", "CEN_TS_16157-13"]
    sorted_folders3 = sorted(folders3, key=sort_key)
    assert sorted_folders3 == ["CEN_TS_16157-13", "EN_ISO_12855", "ISO_15622"]
    
    # TS prefix
    folders4 = ["ISO_TS_19091", "ISO_TS_22726-1", "ISO_14823-1"]
    sorted_folders4 = sorted(folders4, key=sort_key)
    assert sorted_folders4 == ["ISO_14823-1", "ISO_TS_19091", "ISO_TS_22726-1"]


@pytest.mark.unit
def test_sort_key_case_insensitive():
    """Test sort_key() is case insensitive."""
    folders = ["iso_100", "ISO_50", "Iso_75"]
    sorted_folders = sorted(folders, key=sort_key)
    # All should sort by number regardless of case
    assert sorted_folders == ["ISO_50", "Iso_75", "iso_100"]
