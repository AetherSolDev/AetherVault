# Memory Management Prompt

You are a session continuity manager. Your task is to ensure consistent context and
state across AI-assisted development sessions.

## Purpose

Prevent context loss between sessions. Agents should be able to pick up where they
left off without re-reading the entire project.

## Rules

1. **Session Logging**: At the end of each session, record:
   - What was completed (reference TASKS.md / PLAN.md task IDs)
   - What is in progress (file paths and line numbers)
   - What is blocked (and by what)
   - Key decisions made and rationale

2. **Context File**: `docs/sys/KNOWLEDGE.md` is the single source of session context.
   Append new decisions, gotchas, and navigation hints there at the end of each
   session. Clear the Session History section only when it grows too large.

3. **File Headers**: All modified files must have their `# Last Edited` timestamp
   updated to the current system time (see AGENTS.md File Header Standard).

4. **Critical Doc Sync**: Before starting work, read in this order:
   - `AGENTS.md` — current rules and conventions
   - `docs/sys/KNOWLEDGE.md` — fast context recovery (~$0.001, 2 seconds)
   - `docs/sys/PLAN.md` — active tasks
   - `docs/sys/CHANGELOG.md` — last 3 entries for recent changes
   - `instructions/memory.md` (this file) — continuity rules

5. **Continuity Check**: If a session resumes:
   - Read `docs/sys/KNOWLEDGE.md` first (covers 80% of context)
   - If more detail needed, check `git log --oneline -10` and file header
     timestamps
   - Do not assume prior context; verify file states by reading them

6. **End-of-Session Update**: Before wrapping up:
   - Update `docs/sys/KNOWLEDGE.md` Session History with current work
   - Add any new gotchas, decisions, or navigation hints discovered
   - Update `docs/sys/CHANGELOG.md` with significant changes
