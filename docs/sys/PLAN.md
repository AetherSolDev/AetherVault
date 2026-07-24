# Created: 2026-07-24
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Path: docs/sys/PLAN.md
# Purpose: High-level project plan with phases and milestones for kissPWM_v6.

# kissPWM_v6 Plan

## Legend
- C = Changes / Updates
- F = Bug
- A = Add

## ADDITIONS
- [x] A0 — Create `src/` directory, move source files into organized structure
- [x] A1 — Add dark/light theme toggle
- [x] A2 — Add system tray icon with quick-lock
- [x] A3 — Add portable mode detection and config
- [x] A4 — Category filter + tag filter dropdowns
- [x] A5 — Password health report dialog
- [x] A6 — Entry tags (DB column + form field + filter)
- [x] A7 — Custom fields (DB column + JSON + add/remove table)
- [x] A8 — Sort toggle on Title/Username/Category columns
- [x] A9 — Double-click to copy from table
- [x] A10 — Right-click context menu (Copy, Edit, Delete)
- [x] A11 — Category click-to-filter from table
- [x] A12 — Favicon auto-fetch (Google service)
- [x] A13 — Rich text notes with formatting toolbar
- [x] A14 — One-click timestamped backup

## BUGS
- [x] F0 — `resource_path()` references `sys._MEIPASS` without `sys` import at module level
- [x] F1 — `find_and_remove_duplicates()` calls backup before docstring (wrong execution order)
- [x] F2 — `assets/kiss_icon.ico` referenced but no `assets/` directory exists
- [x] F3 — Auto-lock triggers immediately on WindowDeactivate (bypasses configured timeout)
- [x] F4 — Password strength bar hidden by Email QLineEdit in same grid cell
- [x] F5 — File → Quit minimizes to tray instead of quitting
- [x] F6 — Header text clipped in credential table
- [x] F7 — `sectionClicked.disconnect()` RuntimeWarning on every table refresh

## CHANGES
- [x] C0 — Refactor `main_app_pyside.py`: split UI, controllers, clipboard, backup into separate modules
- [x] C1 — Replace `help_doc.md` with `docs/USER_GUIDE.md` in-app help reference
- [x] C2 — Update all file headers with proper Created/Last Edited/Purpose
- [x] C3 — Standardize virtual env to `venv/` (current is `kiss/`)
- [x] C4 — Move flat `.py` files into `src/` package structure
- [x] C5 — Form layout: right-aligned labels, 4px vertical spacing, proportional stretching
- [x] C6 — QComboBox styling: 30px height matching QLineEdit in both themes
- [x] C7 — Splitter: equal initial sizes, form panel capped at 700px
