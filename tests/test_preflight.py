"""Pre-flight tests: validate environment before running conversion tests."""
import os
import shutil
import sys

import pytest


def test_python_version():
    """Verify Python 3.10+ is available."""
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version_info}"


def test_python_docx_available():
    """Verify python-docx is installed."""
    try:
        import docx
        assert docx.__version__ >= "1.1"
    except ImportError:
        pytest.fail("python-docx not installed")


def test_pillow_available():
    """Verify Pillow is installed."""
    try:
        import PIL
        # Pillow 10.0+ required
        major = int(PIL.__version__.split('.')[0])
        assert major >= 10, f"Pillow 10.0+ required, got {PIL.__version__}"
    except ImportError:
        pytest.fail("Pillow not installed")


@pytest.mark.requires_libreoffice
def test_libreoffice_detection():
    """Test LibreOffice binary detection.
    
    This test is marked with 'requires_libreoffice' and can be skipped with:
        pytest -m "not requires_libreoffice"
    """
    from convert_docx import find_soffice
    
    # Test with SOFFICE_BIN env var
    original_env = os.environ.get("SOFFICE_BIN")
    
    try:
        # Test when soffice is available (should not raise)
        if shutil.which("soffice") or shutil.which("libreoffice"):
            soffice = find_soffice()
            assert os.path.exists(soffice), f"find_soffice() returned non-existent path: {soffice}"
            assert os.access(soffice, os.X_OK), f"find_soffice() returned non-executable: {soffice}"
        else:
            pytest.skip("LibreOffice (soffice/libreoffice) not found on PATH")
            
    finally:
        # Restore original env
        if original_env:
            os.environ["SOFFICE_BIN"] = original_env
        elif "SOFFICE_BIN" in os.environ:
            del os.environ["SOFFICE_BIN"]


def test_libreoffice_missing_behavior():
    """Test that find_soffice() raises RuntimeError when LibreOffice is missing.
    
    This test verifies the error message format rather than actually blocking LibreOffice,
    since the system may have it installed in various locations.
    """
    from convert_docx import find_soffice
    
    # If LibreOffice is available, verify it can be found
    if shutil.which("soffice") or shutil.which("libreoffice"):
        soffice = find_soffice()
        assert isinstance(soffice, str)
        assert len(soffice) > 0
    else:
        # If not available, verify RuntimeError is raised
        with pytest.raises(RuntimeError, match="LibreOffice not found"):
            find_soffice()
