#!/usr/bin/env python3
# Created: 2026-07-21
# Last Edited: 2026-07-21 10:50 CT (America/Chicago)
# Path: scripts/update_cost.py
# Purpose: Query opencode.db for new sessions and append to COST.md.

"""
Append new sessions from opencode.db to docs/sys/COST.md.

Reads the existing COST.md, finds new sessions in the shared DB since
the last logged session, and appends them to the Cost Breakdown table.
Updates the summary total at the top.

Usage:
    python scripts/update_cost.py
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path


OPENDCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def get_project_id(project_root: Path) -> str | None:
    """Find the opencode project ID matching this project directory."""
    if not OPENDCODE_DB.exists():
        return None
    conn = sqlite3.connect(str(OPENDCODE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    project_name = project_root.name
    cursor.execute(
        "SELECT id FROM project WHERE name = ? ORDER BY time_created DESC LIMIT 1",
        (project_name,),
    )
    row = cursor.fetchone()
    if row:
        conn.close()
        return row["id"]
    cursor.execute(
        "SELECT id FROM project WHERE worktree LIKE ? ORDER BY time_created DESC LIMIT 1",
        (f"%/{project_name}%",),
    )
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None


def last_logged_date(cost_path: Path) -> str:
    """Read the last date in the Cost Breakdown table."""
    if not cost_path.exists():
        return "2000-01-01"
    text = cost_path.read_text()
    # Find all dates in the breakdown table (lines starting with | YYYY-MM-DD)
    dates = re.findall(r"^\| (\d{4}-\d{2}-\d{2}) ", text, re.MULTILINE)
    return dates[-1] if dates else "2000-01-01"


def clean_model(model: str) -> str:
    """Extract human-readable model name."""
    if not model or model == "unknown":
        return "unknown"
    if model.startswith("{"):
        import json
        try:
            return json.loads(model).get("id", model)
        except json.JSONDecodeError:
            pass
    return model.split("/")[-1] if "/" in model else model


def fetch_new_sessions(project_id: str, since_date: str) -> list[dict]:
    """Fetch sessions after the given date."""
    conn = sqlite3.connect(str(OPENDCODE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """SELECT slug, title, model, cost,
                  tokens_input, tokens_output, time_created
           FROM session
           WHERE project_id = ? AND time_created > ?
           ORDER BY time_created ASC""",
        (project_id, _date_to_ts(since_date)),
    )
    rows = cursor.fetchall()
    conn.close()
    sessions = []
    for row in rows:
        created = datetime.fromtimestamp(row["time_created"] / 1000)
        sessions.append({
            "date": created.strftime("%Y-%m-%d"),
            "title": (row["title"] or row["slug"]).split(" - ")[0],
            "model": clean_model(row["model"]),
            "tokens_in": row["tokens_input"],
            "tokens_out": row["tokens_output"],
            "cost": row["cost"],
        })
    return sessions


def _date_to_ts(date_str: str) -> int:
    """Convert YYYY-MM-DD to epoch milliseconds."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp() * 1000)


def parse_breakdown_table(text: str) -> list[dict]:
    """Parse existing breakdown rows into dicts for recalculating totals."""
    rows = []
    for line in text.split("\n"):
        m = re.match(
            r"^\| (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+?) \| ([\d,]+) \| ([\d,]+) \| \$(.+?) \|$",
            line,
        )
        if m:
            cost_str = m.group(6).replace(",", "")
            rows.append({
                "date": m.group(1),
                "title": m.group(2),
                "model": m.group(3),
                "tokens_in": int(m.group(4).replace(",", "")),
                "tokens_out": int(m.group(5).replace(",", "")),
                "cost": float(cost_str),
            })
    return rows


def append_sessions(cost_path: Path, new_sessions: list[dict], project_name: str = "Project"):
    text = cost_path.read_text()
    existing = parse_breakdown_table(text)
    existing_keys = {(r["date"], r["title"], r["tokens_in"], r["tokens_out"]) for r in existing}

    # Filter out sessions already in the table
    truly_new = []
    for s in new_sessions:
        key = (s["date"], s["title"], s["tokens_in"], s["tokens_out"])
        if key not in existing_keys:
            truly_new.append(s)
            existing_keys.add(key)

    if not truly_new:
        total_cost = sum(r["cost"] for r in existing)
        print(f"   No new sessions to append. Total cost: ${total_cost:.2f}")
        return

    all_rows = existing + truly_new

    # Update summary total
    total_cost = sum(r["cost"] for r in all_rows)
    total_tokens_in = sum(r["tokens_in"] for r in all_rows)
    total_tokens_out = sum(r["tokens_out"] for r in all_rows)
    first_date = all_rows[0]["date"]
    last_date = all_rows[-1]["date"]
    days = (datetime.strptime(last_date, "%Y-%m-%d") - datetime.strptime(first_date, "%Y-%m-%d")).days + 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M CT (America/Chicago)")

    # Build new file
    lines = [
        f"# Created: YYYY-MM-DD",
        f"# Last Edited: {now}",
        f"# Path: docs/sys/COST.md",
        f"# Purpose: Track project costs — summary and per-session breakdown.",
        "",
        "> Summary updated manually. Run `python scripts/update_cost.py` to append new sessions.",
        "",
        f"## {project_name} Project Cost",
        "",
        "| Date | Timeline | Model | Cost |",
        "|------|----------|-------|------|",
        f"| {last_date} | {first_date} ({days} days) | multi-model | ${total_cost:.2f} |",
        "",
        "## Cost Breakdown",
        "",
        "| Date | Session | Model | Tokens In | Tokens Out | Cost |",
        "|------|---------|-------|-----------|------------|------|",
    ]

    for r in all_rows:
        cost_str = f"${r['cost']:.2f}" if r["cost"] else "$0.00"
        lines.append(
            f"| {r['date']} | {r['title']} | {r['model']} "
            f"| {r['tokens_in']:,} | {r['tokens_out']:,} | {cost_str} |"
        )
    lines.append("")

    cost_path.write_text("\n".join(lines))

    if new_sessions:
        print(f"✅ Appended {len(new_sessions)} new session(s)")
    else:
        print("   No new sessions since last logged date.")
    print(f"   Total cost: ${total_cost:.2f}")


def main():
    project_root = Path(__file__).parent.parent.resolve()
    project_name = project_root.name
    cost_path = project_root / "docs" / "sys" / "COST.md"

    if not OPENDCODE_DB.exists():
        print(f"❌ opencode.db not found at {OPENDCODE_DB}")
        return

    project_id = get_project_id(project_root)
    if not project_id:
        print(f"❌ Could not find project '{project_name}' in opencode.db")
        return

    since = last_logged_date(cost_path)
    print(f"🔍 Checking for new sessions since {since}...")
    new_sessions = fetch_new_sessions(project_id, since)

    if not new_sessions:
        print("   No new sessions found in DB.")
        return

    append_sessions(cost_path, new_sessions, project_name)


if __name__ == "__main__":
    main()
