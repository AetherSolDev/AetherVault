# Created: 2026-09-16
# Last Edited: 2026-09-16 15:33 CT (America/Chicago)
# Path: tools/build_user_guide.py
# Purpose: Render aethervault/docs/USER_GUIDE.md -> USER_GUIDE.html (single source of truth).

"""Render the Markdown user guide to HTML for the in-app Help menu.

`USER_GUIDE.md` is the single source of truth; `USER_GUIDE.html` is generated from it
so the two can never drift. Run this after editing the Markdown::

    python tools/build_user_guide.py

Requires the optional docs extra::

    pip install -e '.[docs]'
"""

from __future__ import annotations

import pathlib
import re
import sys

try:
    import markdown
except ImportError:  # pragma: no cover - developer tool
    sys.exit("Missing dependency 'markdown'. Install it with: pip install -e '.[docs]'")

ROOT = pathlib.Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "aethervault" / "docs" / "USER_GUIDE.md"
HTML_PATH = ROOT / "aethervault" / "docs" / "USER_GUIDE.html"

# The MD file starts with a project header block; strip it so it isn't rendered.
_HEADER_RE = re.compile(r"^# (Created|Last Edited|Path|Purpose):")

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AetherVault — User Guide</title>
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 960px;
        margin: 40px auto;
        padding: 0 20px;
        line-height: 1.6;
        color: #1a1a1a;
    }
    h1 { border-bottom: 2px solid #0366d6; padding-bottom: 8px; }
    h2 { border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 40px; }
    h3 { margin-top: 24px; }
    code { background: #f6f8fa; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
    pre {
        background: #f6f8fa;
        padding: 16px;
        border-radius: 6px;
        overflow-x: auto;
        white-space: pre;
        font-size: 0.85em;
        line-height: 1.3;
    }
    pre code { padding: 0; background: none; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
    th { background: #f6f8fa; }
    blockquote { border-left: 4px solid #0366d6; margin: 0; padding: 4px 16px; color: #555; }
    hr { border: none; border-top: 1px solid #ddd; margin: 32px 0; }
    @media (max-width: 768px) {
        pre { font-size: 0.7em; padding: 10px; }
    }
</style>

</head>
<body>
{body}
</body>
</html>
"""


def strip_header(markdown_text: str) -> str:
    """Remove the leading ``# Created/Last Edited/Path/Purpose`` header block."""
    lines = markdown_text.splitlines()
    while lines and (not lines[0].strip() or _HEADER_RE.match(lines[0])):
        lines.pop(0)
    return "\n".join(lines)


def render(markdown_text: str) -> str:
    """Render Markdown text (minus the header block) to a full HTML document."""
    body = markdown.markdown(
        strip_header(markdown_text),
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
    )
    # .replace, not .format — the CSS contains literal braces.
    return _TEMPLATE.replace("{body}", body)


def main() -> int:
    html = render(MD_PATH.read_text(encoding="utf-8"))
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_PATH.relative_to(ROOT)} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
