#!/usr/bin/env python3
# Created: 2026-07-21
# Last Edited: 2026-07-21 10:50 CT (America/Chicago)
# Path: scripts/build_reference.py
# Purpose: Combine docs/sys/ files into single REFERENCE.md and REFERENCE.html.

"""
Build Project Reference Document

Combines all docs/sys/*.md files into a single REFERENCE.md with a table of
contents. If the `markdown` library is installed, also generates REFERENCE.html.

Usage:
    python scripts/build_reference.py

Output:
    docs/sys/REFERENCE.md
    docs/sys/REFERENCE.html  (if markdown library available)

Dependencies (optional, for HTML):
    pip install markdown
"""

import html as html_module
from pathlib import Path
from datetime import datetime


# Order and display titles for each section
SECTION_ORDER = [
    ("ARCHITECTURE.md", "Architecture"),
    ("KNOWLEDGE.md", "Project Knowledge"),
    ("PLAN.md", "Project Plan"),
    ("TASKS.md", "Tasks"),
    ("CHANGELOG.md", "Changelog"),
    ("BUGS.md", "Bug Tracker"),
    ("COST.md", "Development Costs"),
    ("Model_Pricing_Reference.txt", "Model Pricing Reference"),
]


EXCLUDED = {"REFERENCE.md", "REFERENCE.html"}

def find_extra_md_files(docs_sys: Path, known: set) -> list[tuple[str, str]]:
    """Find any .md and .mmd files not in the defined order."""
    extras = []
    for f in sorted(docs_sys.glob("*.md")):
        if f.name not in known and f.name not in EXCLUDED:
            title = f.stem.replace("_", " ").replace("-", " ").title()
            extras.append((f.name, title))
    return extras


def strip_header(content: str) -> tuple[str, str]:
    """Separate file header comments from body content. Returns (header, body)."""
    lines = content.split("\n")
    header_lines = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("# Created:") or line.strip().startswith("# Last Edited:") or line.strip().startswith("# Path:") or line.strip().startswith("# Purpose:"):
            header_lines.append(line)
        elif header_lines and not line.strip():
            # blank line after header
            body_start = i + 1
            break
        elif not line.strip():
            continue
        elif not line.strip().startswith("#"):
            body_start = i
            break
    return "\n".join(header_lines), "\n".join(lines[body_start:])


def extract_title(content: str) -> str:
    """Extract the first H1 from content."""
    for line in content.split("\n"):
        if line.startswith("# ") and not line.startswith("# Created") and not line.startswith("# Last"):
            return line.lstrip("# ").strip()
    return ""


def build_markdown(docs_sys: Path, output_path: Path):
    """Build the combined REFERENCE.md."""
    sections = []
    seen = set()
    all_toc = []
    total_sections = []

    # Include any .mmd file as the "Diagram" section after the main sections
    mmd_files = sorted(docs_sys.glob("*.mmd"))
    mmd_order = []
    for f in mmd_files:
        mmd_order.append((f.name, f"Diagram ({f.stem})"))

    for filename, title in SECTION_ORDER + mmd_order:
        filepath = docs_sys / filename
        if not filepath.exists():
            continue
        seen.add(filename)
        content = filepath.read_text()
        _, body = strip_header(content)
        if not body.strip():
            continue
        if filename.endswith(".mmd") or filename.endswith(".txt"):
            body = f"```\n{body}\n```"
        else:
            body = body.strip()
        sections.append(f"\n\n---\n\n## {title}\n\n{body}")
        all_toc.append(f"- [{title}](#{title.lower().replace(' ', '-')})")
        total_sections.append((filename, title))

    # Add any extra .md files not in the defined order
    extras = find_extra_md_files(docs_sys, seen)
    for filename, title in extras:
        filepath = docs_sys / filename
        content = filepath.read_text()
        _, body = strip_header(content)
        if not body.strip():
            continue
        sections.append(f"\n\n---\n\n## {title}\n\n{body.strip()}")
        all_toc.append(f"- [{title}](#{title.lower().replace(' ', '-')})")
        total_sections.append((filename, title))

    # Build the combined document
    now = datetime.now().strftime("%Y-%m-%d %H:%M CT")
    combined = f"""# {docs_sys.parent.name} — Technical Reference

> Auto-generated on {now} from docs/sys/
> Source: `scripts/build_reference.py`

## Table of Contents

{chr(10).join(all_toc)}

---"""
    combined += "".join(sections)
    combined += f"\n\n---\n\n*Generated on {now} by `scripts/build_reference.py`*"

    output_path.write_text(combined)
    print(f"✅ Generated {output_path}")
    return total_sections


HTML_CSS = """
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
"""


def md_to_html(md_path: Path, html_path: Path, title: str = None):
    """Convert a Markdown file to a standalone HTML file."""
    try:
        import markdown
    except ImportError:
        print(
            "⚠️  'markdown' library not installed. Skipping HTML generation.\n"
            "   Install with: pip install markdown",
        )
        return

    md_content = md_path.read_text()
    html_body = markdown.markdown(
        md_content,
        extensions=["fenced_code", "tables", "toc"],
    )

    if title is None:
        title = md_path.parent.parent.name

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>{HTML_CSS}
</head>
<body>
{html_body}
</body>
</html>"""

    html_path.write_text(html_content)
    print(f"✅ Generated {html_path}")


def build_html(md_path: Path, html_path: Path):
    """Generate REFERENCE.html from REFERENCE.md using the markdown library."""
    md_to_html(md_path, html_path, f"{md_path.parent.parent.name} — Technical Reference")


def main():
    project_root = Path(__file__).parent.parent
    docs_sys = project_root / "docs" / "sys"

    if not docs_sys.exists():
        print(f"❌ docs/sys/ not found at {docs_sys}", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    md_path = docs_sys / "REFERENCE.md"
    html_path = docs_sys / "REFERENCE.html"

    print(f"📚 Building reference from {docs_sys}/")
    build_markdown(docs_sys, md_path)
    build_html(md_path, html_path)

    # Also generate USER_GUIDE.html for the in-app help / portable build
    userguide_md = project_root / "docs" / "USER_GUIDE.md"
    userguide_html = project_root / "docs" / "USER_GUIDE.html"
    if userguide_md.exists():
        md_to_html(userguide_md, userguide_html, "KISS Password Manager — User Guide")

    print("✅ Reference build complete")


if __name__ == "__main__":
    main()
