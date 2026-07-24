#!/usr/bin/env python3
# Created: 2026-07-21
# Last Edited: 2026-07-21 10:50 CT (America/Chicago)
# Path: scripts/mermaid_to_ascii.py
# Purpose: Extract mermaid code from .mmd file, generate ASCII flowchart, recombine.

"""
Mermaid → ASCII Pipeline

Usage:
    python scripts/mermaid_to_ascii.py docs/sys/{project_id}.mmd

Requires:
    pip install mermaidx

Workflow:
    1. Reads the combined .mmd file
    2. Extracts the mermaid code block (classDiagram/flowchart section)
    3. Runs mermaidx to generate ASCII art
    4. Replaces the ASCII section in the file
    5. Preserves the mermaid code section unchanged
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_mermaid_section(content: str) -> tuple[int, int, str]:
    """Find the mermaid code section in the combined file.

    Scans for classDiagram, flowchart, sequenceDiagram, or stateDiagram-v2
    as the start of the mermaid code block. Returns (start_line, end_line, code).
    """
    lines = content.split("\n")
    mermaid_start = None
    mermaid_end = None

    markers = [
        "classDiagram",
        "flowchart", "graph ",
        "sequenceDiagram",
        "stateDiagram-v2",
        "gantt",
        "pie ",
        "erDiagram",
    ]

    for i, line in enumerate(lines):
        stripped = line.strip()
        for marker in markers:
            if stripped.startswith(marker):
                if mermaid_start is None:
                    mermaid_start = i
                mermaid_end = i + 1
                break

    if mermaid_start is None:
        return -1, -1, ""

    mermaid_code = "\n".join(lines[mermaid_start:mermaid_end])
    return mermaid_start, mermaid_end, mermaid_code


def run_mermaidx(mermaid_code: str) -> str:
    """Run mermaidx on the mermaid code and return the ASCII output."""
    try:
        result = subprocess.run(
            ["mermaidx"],
            input=mermaid_code,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"⚠️ mermaidx stderr: {result.stderr}", file=sys.stderr)
            return ""
        return result.stdout
    except FileNotFoundError:
        print(
            "❌ mermaidx not found. Install with: pip install mermaidx",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️ mermaidx timed out after 30s", file=sys.stderr)
        return ""


def combine_file(
    ascii_art: str, mermaid_code: str, header_lines: list[str]
) -> str:
    """Combine header, ASCII art, and mermaid code back into one file."""
    parts = []
    if header_lines:
        parts.append("\n".join(header_lines))
    parts.append("")
    parts.append(ascii_art.strip())
    parts.append("")
    parts.append(mermaid_code.strip())
    parts.append("")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Generate ASCII flowchart from mermaid .mmd file"
    )
    parser.add_argument("mmd_file", type=str, help="Path to the .mmd file")
    parser.add_argument(
        "--inplace",
        action="store_true",
        default=True,
        help="Update the file in-place (default: True)",
    )
    args = parser.parse_args()

    mmd_path = Path(args.mmd_file)
    if not mmd_path.exists():
        print(f"❌ File not found: {mmd_path}", file=sys.stderr)
        sys.exit(1)

    content = mmd_path.read_text()

    # Extract header (everything before the ASCII/mermaid content)
    lines = content.split("\n")
    header_lines = []
    mermaid_start = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("classDiagram") or stripped.startswith(
            "flowchart"
        ) or stripped.startswith("graph "):
            mermaid_start = i
            break
        if stripped and not stripped.startswith(
            "#"
        ):
            # First non-header, non-blank content — might be ASCII art
            if not header_lines or not stripped.startswith("┌") and not stripped.startswith("│"):
                pass

    # Find the mermaid section
    mermaid_start_line, mermaid_end_line, mermaid_code = find_mermaid_section(
        content
    )

    if mermaid_start_line < 0:
        print(
            "❌ No mermaid code section found. Looking for: classDiagram, flowchart, etc.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"📐 Found mermaid code ({len(mermaid_code)} chars)")
    print("🔄 Generating ASCII flowchart via mermaidx...")

    ascii_art = run_mermaidx(mermaid_code)

    if not ascii_art:
        print("⚠️ No ASCII output generated. File unchanged.", file=sys.stderr)
        sys.exit(1)

    # Extract comment header (lines before mermaid that start with #)
    before_mermaid = content.split(mermaid_code)[0]
    header = [
        l for l in before_mermaid.split("\n") if l.strip().startswith("#")
    ]

    # Recombine
    new_content = combine_file(ascii_art, mermaid_code, header)

    if args.inplace:
        mmd_path.write_text(new_content)
        print(f"✅ Updated {mmd_path}")
    else:
        out_path = mmd_path.with_suffix(".txt")
        out_path.write_text(new_content)
        print(f"✅ Wrote ASCII-only output to {out_path}")

    print("📊 ASCII flowchart generated successfully.")


if __name__ == "__main__":
    main()
