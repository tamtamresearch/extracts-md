"""Pre-flight tests: validate environment before running conversion tests."""
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


def test_no_libreoffice_dependency():
    """The converter must no longer depend on LibreOffice/soffice."""
    import convert_docx

    assert not hasattr(convert_docx, "find_soffice"), \
        "find_soffice() should have been removed (no LibreOffice dependency)"
    assert "subprocess" not in dir(convert_docx), \
        "subprocess import should have been removed (no LibreOffice dependency)"
