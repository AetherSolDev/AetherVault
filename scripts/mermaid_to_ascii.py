#!/usr/bin/env python3
# Created: 2026-07-21
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Path: scripts/mermaid_to_ascii.py
# Purpose: Extract mermaid code from .mmd file, generate ASCII flowchart, recombine.

"""
Mermaid → ASCII Pipeline

Usage:
    python scripts/mermaid_to_ascii.py docs/sys/{project_id}.mmd

Requires:
    pip install termaid

Workflow:
    1. Reads the combined .mmd file
    2. Extracts the mermaid code blocks (inside ```mermaid fences)
    3. Runs termaid --ascii to generate ASCII art from each block
    4. Combines ASCII sections with the original header and mermaid code
    5. Writes the updated file
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_mermaid_blocks(content: str) -> list[tuple[str, int, int]]:
    """Extract mermaid code blocks from ```mermaid ... ``` fences.

    Returns list of (code, start_line, end_line).
    """
    blocks = []
    pattern = re.compile(r"^```mermaid\s*$", re.MULTILINE)
    lines = content.split("\n")
    for match in pattern.finditer(content):
        start = match.start()
        start_line = content[:start].count("\n")
        end_line = start_line
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip() == "```":
                end_line = i
                break
        code = "\n".join(lines[start_line + 1 : end_line])
        blocks.append((code, start_line, end_line))
    return blocks


def run_termaid(mermaid_code: str) -> str:
    """Run termaid --ascii on clean mermaid code and return ASCII output."""
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False)
        tmp.write(mermaid_code)
        tmp_path = tmp.name
        tmp.close()
        result = subprocess.run(
            ["termaid", "--ascii", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        os.unlink(tmp_path)
        if result.returncode != 0:
            print(f"⚠️ termaid stderr: {result.stderr}", file=sys.stderr)
            return ""
        return result.stdout
    except FileNotFoundError:
        print(
            "❌ termaid not found. Install with: pip install termaid",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️ termaid timed out after 30s", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="Generate ASCII flowchart from mermaid .mmd file"
    )
    parser.add_argument("mmd_file", type=str, help="Path to the .mmd file")
    args = parser.parse_args()

    mmd_path = Path(args.mmd_file)
    if not mmd_path.exists():
        print(f"❌ File not found: {mmd_path}", file=sys.stderr)
        sys.exit(1)

    content = mmd_path.read_text()
    blocks = extract_mermaid_blocks(content)

    if not blocks:
        print(
            "❌ No mermaid code blocks found. Looking for: ```mermaid ... ``` fences.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"📐 Found {len(blocks)} mermaid code block(s)")
    ascii_results = []

    for i, (code, start_line, end_line) in enumerate(blocks):
        print(f"🔄 Generating ASCII for block {i+1} ({len(code)} chars)...")
        ascii_art = run_termaid(code)
        if ascii_art:
            ascii_results.append((ascii_art, start_line, end_line))
        else:
            print(f"⚠️  Block {i+1}: no ASCII output generated.")

    if not ascii_results:
        print("⚠️ No ASCII output generated for any block. File unchanged.", file=sys.stderr)
        sys.exit(1)

    # Split content at each block boundary and rebuild with ASCII art inserted
    lines = content.split("\n")
    new_lines = list(lines)

    # Insert ASCII output before the ```mermaid opening fence for each block
    # Process in reverse order so line numbers stay valid
    for ascii_art, start_line, end_line in reversed(ascii_results):
        ascii_lines = ascii_art.strip("\n").split("\n")
        # Insert a separator line, then ASCII art, then another separator
        insert = [""] + ascii_lines + [""]
        new_lines[start_line:start_line] = insert

    new_content = "\n".join(new_lines)

    mmd_path.write_text(new_content)
    print(f"✅ Updated {mmd_path}")
    print("📊 ASCII flowchart generated successfully via termaid.")


if __name__ == "__main__":
    main()
