# Created: 2026-09-16
# Last Edited: 2026-09-16 15:23 CT (America/Chicago)
# Path: tests/test_user_guide.py
# Purpose: Guard against USER_GUIDE.html drifting from USER_GUIDE.md.

"""Tests that the generated user-guide HTML matches its Markdown source."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("markdown", reason="docs extra (markdown) not installed")

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "build_user_guide.py"
MD_PATH = ROOT / "aethervault" / "docs" / "USER_GUIDE.md"
HTML_PATH = ROOT / "aethervault" / "docs" / "USER_GUIDE.html"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_user_guide", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_html_is_up_to_date():
    """USER_GUIDE.html must equal a fresh render of USER_GUIDE.md."""
    builder = _load_builder()
    expected = builder.render(MD_PATH.read_text(encoding="utf-8"))
    actual = HTML_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "USER_GUIDE.html is stale — run: python scripts/build_user_guide.py"
    )


def test_header_block_is_stripped():
    builder = _load_builder()
    html = builder.render(MD_PATH.read_text(encoding="utf-8"))
    body = html.split("<body>", 1)[1]
    assert 'id="last-edited-' not in body
    assert "AetherVault — User Guide" in body
