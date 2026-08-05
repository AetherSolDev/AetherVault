# Created: 2026-07-27
# Last Edited: 2026-08-05 16:08 CT (America/Chicago)
# Path: docs/sys/AUDIT_REPORT.md
# Purpose: Formal audit findings from alignment_checklist.md evaluation of AetherVault.

# Audit Report: AetherVault

**Date**: 2026-08-05 (post-restructure re-audit + remediation)
**Files Scanned**: 17 source files (aethervault/ incl. core/ + shared/), 6 test files, 6 scripts
**Overall Score**: **A** (F15 + F16 remediated)

## Summary

| Finding Type | Resolved | New This Audit | Remaining |
|--------------|----------|----------------|-----------|
| Structure alignment | 0 | 1 (fixed, C10) | 0 |
| Maps | 0 | 1 (added maps/) | 0 |
| Line length | 0 | 1 (fixed) | 0 |
| Startup integrity check | 0 | 1 (fixed, F15) | 0 |
| Python version floor | 0 | 1 (fixed, F16) | 0 |
| **Total** | **0** | **5** | **0** |

## Re-Audit Findings (2026-08-05)

Fresh scan of 17 source files + 6 test files + 6 scripts against
`alignment_checklist.md` after the `core/`+`shared/` restructure:

| Category | Checks | Pass | Fail | Notes |
|----------|--------|------|------|-------|
| 1. File Structure & Headers | 5 | 5 | 0 | All headers present, correct order, line length ≤100 |
| 2. Imports | 5 | 5 | 0 | AST scan: zero unused imports; grouped stdlib→third→local; absolute imports |
| 3. Error Handling | 4 | 4 | 0 | No bare `except:`, no `except Exception`; specific types only |
| 4. Functions & Structure | 6 | 6 | 0 | No circular imports (verified vs imports.mmd); separation of concerns (core/shared/gui) |
| 5. Database | 4 | 4 | 0 | Parameterized, WAL, Row access, context manager, **integrity check + auto-recovery (F15)** |
| 6. Testing | 4 | 4 | 0 | 74 tests, all passing, core/model/DB/score/duress/form/integrity covered |
| 7. Project Hygiene | 6 | 6 | 0 | No secrets, .gitignore covers internals, venv/, unique package name |
| 8. Documentation | 5 | 5 | 0 | ARCHITECTURE, USER_GUIDE, mmd, maps/ all current |
| 9. Environment | 3 | 3 | 0 | venv active; **requires-python ≥3.10 (F16 fixed)** |
| **Total** | **42** | **42** | **0** | **Score: A** |

### Notable Strengths
- **71 tests passing** in ~5s — encryption, hashing, password gen, settings, DB CRUD, import/export, duplicates, backup, duress, copy-buttons.
- **STRUCTURE.md layout complete**: `core/` (engine, password) + `shared/` (database, models) + `gui/`. Verified `core/` never imports `gui/`.
- **No debug artifacts**: zero `print()` in production (CLI output in `__main__.py` is by design).
- **No lines > 100 chars**, no trailing whitespace, all file headers present.
- **DB discipline**: parameterized queries, `PRAGMA journal_mode=WAL`, context manager, `sqlite3.Row`, whitelist-guarded ALTER TABLE (f-string uses fixed internal set, not user input).
- **Maps added**: `maps/architecture.md`, `maps/imports.mmd`, `maps/database.mmd` — validated against the real import graph (all edges match).
- **No secrets committed**: `.master.key`, DB files, settings, sessions.md, COST.md, project_audit/, scripts/ all gitignored.

### Findings

### P1

1. **F15 — Missing startup integrity check** `[x] Fixed`
   - **File**: `aethervault/shared/database.py` (`_connect()`), `aethervault/gui/app.py` (`__init__`)
   - **Issue**: AGENTS.md Critical Rules require "Run startup integrity checks with automatic recovery." No `PRAGMA integrity_check` (or equivalent) runs at startup or on DB connect. Checklist 5.x implies connection robustness; a corrupted DB would fail cryptically at first query rather than at startup with a recoverable error.
   - **Fix**: `_connect()` now runs `PRAGMA integrity_check`. On failure it notifies via `error_handler` and auto-recovers from the most recent `.db.bak` (copy + re-check). No backup → `conn=None` (safe fail). 3 regression tests added. Verified live: corrupt DB recovered, `secret` intact.

### P3

2. **F16 — `requires-python` is `>=3.9`, checklist prefers 3.10+** `[x] Fixed`
   - **File**: `pyproject.toml`
   - **Issue**: Checklist 9.1 (Environment) wants Python 3.10+. Project supported 3.9+.
   - **Fix**: Raised `requires-python` to `>=3.10`; dropped Python 3.9 from the CI matrix (`ci.yml` now 3.10–3.12); updated USER_GUIDE system requirements.

## Map Health

| Map File | Status | Notes |
|----------|--------|-------|
| `maps/architecture.md` | ✅ OK | Tree matches current `core/`+`shared/`+`gui/` layout; all 12 modules mapped |
| `maps/imports.mmd` | ✅ OK | Every edge validated against real imports; no ghosts, no missing |
| `maps/database.mmd` | ✅ OK | 17/17 schema columns mapped |
| `aethervault/docs/sys/aethervault.mmd` | ✅ OK | Present, describes UI/DB flow accurately |
| `docs/sys/ARCHITECTURE.md` | ✅ OK | Matches restructured layout |

## Remediation Log

| Finding | Date | Action |
|---------|------|--------|
| F1 (god function) | 2026-07-27 | `create_main_content()` 225→24 lines. Extracted CredentialForm (344 lines) and CredentialTable (334 lines). |
| F4 (god function) | 2026-07-27 | `update_list_view()` 67 lines → moved to CredentialTable. 0 lines in app.py. |
| F9 (god function) | 2026-07-27 | `__init__()` 56→50 lines. Waived — acceptable for initialization. |
| F6 (mixed concerns) | 2026-07-27 | Partially fixed. Favicon fetching moved to CredentialTable. Password health scoring stays in app.py pending extraction to engine.py. |
| F8 (WAL mode) | 2026-07-27 | Added `PRAGMA journal_mode=WAL;` to `_connect()` — 1 line. |
| F7 (DB context manager) | 2026-07-27 | Added `__enter__`/`__exit__` to DatabaseManager. |
| F2 (god function) | 2026-07-27 | `show_password_health()` reduced 82→64 lines by extracting `score_password()` to core_logic.py. |
| F3 (god function) | 2026-07-27 | `setup_menu_bar()` 70→6 lines. Extracted into 4 builder methods. Duplicated password scoring eliminated from both password_strength.py and app.py. |

## Post-Duress-Test Verification (2026-08-01)

Live test of the duress wipe on a full copy of the real vault (429 creds):
- Duress password set → entered at login → vault + backups + keys destroyed (data/ → 0 files), fake "Invalid password" dialog + silent exit.
- Manual backup (`~/aethervault-backup-2026-08-01/`) + NAS copy both preserved 429 creds.
- Restore from manual backup → 429 creds, logged in successfully.
- Fixed a real bug found during testing: `QInputDialog.getText()` returns `(text, ok)` in PySide6; the duress setup unpacked them backwards, causing a silent `AttributeError` after the master prompt. Swap fixed + verified with real modal dialogs.
- Cleanup: test dirs removed; manual backup removed after successful restore (NAS remains as long-term copy).

## Audit Log

| Date | Action |
|------|--------|
| 2026-07-27 | Initial audit conducted. Score: C. 12 findings total (9 P1, 3 P2). |
| 2026-07-27 | Session 1: Split app.py into 5 focused files. F1, F4, F9 fixed. F6 partial. |
| 2026-07-27 | Session 2: Import conflict dialog + preview/execute. F2, F3, F7, F8 fixed. |
| 2026-07-27 | Session 3: F10 (prints→logging), F11 (SQL whitelist), F5 (22 tests, 3 test files). All findings closed. Score: C→A. |
| 2026-07-27 | Re-audit (session 11-12): All 12 findings still closed. 42/42 checklist checks pass. 61 tests. Score: A (unchanged). |
| 2026-08-01 | Re-audit (session 16): All 12 prior findings closed. New: F12 (unused imports, P2), F13 (except Exception style, P3). 41/42 checks pass. Score: A−. |
| 2026-08-01 | Remediated F12 + F13: removed all unused imports (AST-verified); narrowed all 22 `except Exception` blocks to specific types. 42/42 checks pass, 61 tests pass. Score: A. |
| 2026-08-01 | Re-audit (session 20): Post-duress-test pass. 42/42 checklist checks pass. 9 functions > 50 lines are pre-existing/UI-builders, none > 75 in logic. 69 tests pass. Score: A. |
| 2026-08-05 | Post-restructure re-audit: STRUCTURE.md layout verified, maps/ added + validated, line-length enforced (PEP 8). 40/42 checks pass. 2 new findings: F15 (startup integrity check, P1), F16 (python floor, P3). 71 tests pass. Score: A−. |
| 2026-08-05 | Remediated F15 + F16: added `PRAGMA integrity_check` + auto-recovery from backup in `DatabaseManager._connect()` (3 regression tests, suite 71→74); raised `requires-python` to 3.10+, dropped 3.9 from CI. 42/42 checks pass, 74 tests pass. Score: A. |

