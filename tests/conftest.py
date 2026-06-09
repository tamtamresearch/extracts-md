"""Shared pytest fixtures for the test suite."""
import os
import shutil
import sys
from pathlib import Path

import pytest

# Add project root to Python path so we can import convert_docx, gen_nav, etc.
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def docx_fixtures_dir(fixtures_dir):
    """Return path to DOCX fixtures directory."""
    return fixtures_dir / "docx"


@pytest.fixture
def sample_output_dir(fixtures_dir):
    """Return path to sample output directory for gen_nav tests."""
    return fixtures_dir / "sample_output"


@pytest.fixture
def tmp_output(tmp_path):
    """Return a temporary output directory for conversion tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_libreoffice: mark test as requiring LibreOffice"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as implementation-agnostic integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as implementation-specific unit test"
    )
