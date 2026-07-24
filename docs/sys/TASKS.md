# Created: 2026-07-24
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Path: docs/sys/TASKS.md
# Purpose: Detailed task breakdown for kissPWM_v6.

# kissPWM_v6 Tasks

## Legend
- C = Changes / Updates
- F = Bug
- A = Add

## P0 — Critical (security/stability)

- [x] F0 — Fix `resource_path()` missing `sys` import
  - **ID**: fix-resource-path
  - **Tags**: bug, gui, packaging
  - **Details**: `sys._MEIPASS` referenced but `sys` not imported at module level in `main_app_pyside.py`
  - **Files**: `main_app_pyside.py`
  - **Acceptance**: `resource_path()` works in both dev and PyInstaller builds without NameError

- [x] F1 — Fix `find_and_remove_duplicates()` backup call ordering
  - **ID**: fix-backup-order
  - **Tags**: bug, database
  - **Details**: `create_pre_op_backup()` called before docstring, making backup timing non-obvious and potentially mistimed
  - **Files**: `db_manager.py`
  - **Acceptance**: Backup is called at the correct point in the method body, not before the docstring

- [x] C0 — Refactor `main_app_pyside.py` into `src/` package structure
  - **ID**: refactor-src
  - **Tags**: refactor, architecture
  - **Details**: Split monolithic ~1250-line file into separate modules: engine.py (business logic), clipboard.py, gui/main_window.py, gui/dialogs/, data/database.py, data/encryption.py
  - **Files**: `main_app_pyside.py`, `core_logic.py`, `db_manager.py`
  - **Acceptance**: App launches and functions identically. Each module has single responsibility. No circular imports.

- [x] C1 — Update all file headers with standard format
  - **ID**: file-headers
  - **Tags**: chore, documentation
  - **Details**: Add `# Created`, `# Last Edited`, `# Path`, `# Purpose` headers to all Python files
  - **Files**: `core_logic.py`, `db_manager.py`, `main_app_pyside.py`
  - **Acceptance**: Every source file has proper header matching AGENTS.md standard

## P1 — Important (UX/Polish)

- [x] A2 — Add dark/light theme support
  - **ID**: theme-support
  - **Tags**: feature, gui
  - **Details**: Add theme toggle with dark and light mode, persistent setting
  - **Files**: `src/gui/app.py`, `src/gui/theme.py`
  - **Acceptance**: Full app respects dark/light theme, toggle in menu, persists across sessions

- [x] F2 — Create `assets/` directory with app icon
  - **ID**: fix-icon
  - **Tags**: bug, gui
  - **Details**: `assets/kiss_icon.ico` referenced but no directory exists
  - **Files**: `assets/`, `src/gui/app.py`
  - **Acceptance**: App icon displays correctly in title bar and taskbar

- [x] C2 — Replace `help_doc.md` with `docs/USER_GUIDE.md`
  - **ID**: help-to-userguide
  - **Tags**: change, documentation
  - **Details**: Update `DocumentationDialog` to load from `docs/USER_GUIDE.md` instead of `help_doc.md`
  - **Files**: `main_app_pyside.py`, `help_doc.md`, `docs/USER_GUIDE.md`
  - **Acceptance**: Help menu opens consolidated user guide

## P2 — Nice-to-have

- [x] C3 — Rename virtual env from `kiss/` to `venv/`
  - **ID**: fix-venv-name
  - **Tags**: chore, devx
  - **Details**: Standardize virtual environment name per template convention
  - **Files**: `.gitignore`
  - **Acceptance**: `venv/` is the active virtual environment

- [x] A2 — Add system tray icon with quick-lock
  - **ID**: tray-icon
  - **Tags**: feature, gui
  - **Details**: Minimize to tray, quick-lock from tray context menu
  - **Files**: `src/gui/app.py`
  - **Acceptance**: App minimizes to tray, tray menu has Lock and Quit options

- [x] A3 — Add portable mode detection and config
  - **ID**: portable-mode
  - **Tags**: feature, config
  - **Details**: `.portable` marker file keeps all data in app directory; toggle in Settings menu
  - **Files**: `src/__init__.py`, `src/gui/app.py`
  - **Acceptance**: Toggle in Settings, status bar shows [Portable] when active

- [x] A4 — Category filter + tag filter dropdowns
  - **ID**: filter-dropdowns
  - **Tags**: feature, ui
  - **Details**: QComboBox filters for category and tags next to search bar
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Filters populate dynamically, combine with search text

- [x] A5 — Password health report dialog
  - **ID**: password-health
  - **Tags**: feature, tools
  - **Details**: Scans all entries for weak/reused/short passwords, shows in dialog with table
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Tools → Password Health shows summary + detail table

- [x] A6 — Entry tags
  - **ID**: entry-tags
  - **Tags**: feature, database
  - **Details**: `tags TEXT` column auto-migrated, QLineEdit in form with comma-separated values
  - **Files**: `src/core_logic.py`, `src/db_manager.py`, `src/gui/app.py`
  - **Acceptance**: Tags save/load correctly, filter by tag works

- [x] A7 — Custom fields
  - **ID**: custom-fields
  - **Tags**: feature, database
  - **Details**: `custom_fields TEXT` column (JSON array), QTableWidget with add/remove in form
  - **Files**: `src/core_logic.py`, `src/db_manager.py`, `src/gui/app.py`
  - **Acceptance**: Custom fields save/load correctly as JSON

- [x] A8 — Sort toggle on Title/Username/Category
  - **ID**: sort-toggle
  - **Tags**: feature, ui
  - **Details**: Click column header to sort ascending, click again to toggle
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Columns sort correctly in both directions

- [x] A9 — Double-click to copy from table
  - **ID**: double-click-copy
  - **Tags**: feature, ui
  - **Details**: Double-click any cell to copy value to clipboard with 15s auto-clear
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Double-click copies cell text, status bar shows confirmation

- [x] A10 — Right-click context menu
  - **ID**: context-menu
  - **Tags**: feature, ui
  - **Details**: Right-click row for Copy Username, Copy Password, Edit, Delete
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Context menu actions work correctly

- [x] A11 — Category click-to-filter
  - **ID**: click-to-filter
  - **Tags**: feature, ui
  - **Details**: Single-click category cell auto-sets category filter dropdown
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Clicking category cell updates filter

- [x] A12 — Favicon auto-fetch
  - **ID**: favicon-fetch
  - **Tags**: feature, ui
  - **Details**: Tools → Fetch Favicons downloads 16×16 icons via Google service, displays in Title column
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Favicons appear next to titles after fetch

- [x] A13 — Rich text notes
  - **ID**: rich-notes
  - **Tags**: feature, ui
  - **Details**: B/I/U formatting toolbar, stored as HTML
  - **Files**: `src/gui/app.py`
  - **Acceptance**: Notes save formatting, display correctly on reload

- [x] A14 — One-click timestamped backup
  - **ID**: one-click-backup
  - **Tags**: feature, ui
  - **Details**: Status bar message instead of modal dialog, unique filenames with timestamps
  - **Files**: `src/gui/app.py`
  - **Acceptance**: File → Backup saves to `kiss_vault_YYYY.MM.DD_HHMMSS.db.bak`

## P3 — Future

- [ ] Browser extension integration
- [ ] Cloud sync (optional, opt-in)
- [ ] Auto-type / fill hotkey
