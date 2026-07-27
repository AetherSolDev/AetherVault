# Created: 2026-07-24
# Last Edited: 2026-07-27 13:47 CT (America/Chicago)
# Path: docs/sys/CHANGELOG.md
# Purpose: Changelog tracking all significant project changes for AetherVault.

# Changelog

## [6.1.0] — 2026-07-27

### Added
- **Version bump criteria** documented in AGENTS.md — SemVer from conventional commit types
- **Import conflict system** — `preview_import()` scans for title+username collisions; `execute_import()` with per-entry resolution (Keep Vault / Use Import) or bulk import and review later
- **`score_password()`** extracted to `core_logic.py` — single source of truth for password strength scoring
- **Test suite** — 22 tests across 3 files (`test_score_password`, `test_credential_entry`, `test_db_manager`) with pytest fixtures
- **`tests/conftest.py`** — shared temp database and sample entry fixtures
- **`docs/sys/AUDIT_REPORT.md`** — formal audit trail with 12 findings, all resolved

### Changed
- **God file split**: `app.py` 1627→968 lines. Extracted `CredentialForm` (344), `CredentialTable` (334), `ClickToCopyFilter` (24), `PasswordStrengthBar` (46)
- **`setup_menu_bar()`** 70→6 lines — extracted into 4 builder methods
- **`CredentialEntry.__init__()`** — all string fields default to `""` instead of `None`
- **`import_from_csv()`** — now uses column alias mapping for browser CSV compatibility (73 aliases, 17 fields)
- **`handle_import()`** — preview-first flow with conflict detection
- **`_connect()`** — added `PRAGMA journal_mode=WAL`
- **`DatabaseManager`** — added `__enter__`/`__exit__` context manager protocol
- **`resource_path()`** — uses `PROJECT_ROOT` instead of `os.path.abspath(".")`
- **`CredentialTable`** — added `time_last_used` and `time_password_changed` columns
- **`New_Project_init/AGENTS.md`** — added versioning section, updated safety.md with NAS mount check and trash directory

### Fixed
- **All 12 audit findings** resolved (score C→A)
- Duplicate password scoring logic eliminated (was in 2 places, now one `score_password()`)
- `print()` calls in `core_logic.py` replaced with `logging`
- ALTER TABLE SQL now uses whitelist guard instead of raw f-string
- `show_password_health()` reduced 82→64 lines via `score_password()` reuse

## 2026-07-24 (session 3)

### Added
- Project scaffolding with template system (AGENTS.md, docs/, instructions/, scripts/)
- System documentation: PLAN, ARCHITECTURE, KNOWLEDGE, TASKS, BUGS, COST, mermaid diagram
- `.repomixignore` for AI context management
- Template instructions for bug tracking, changelog, tasks, cost tracking
- `src/` package structure with proper module separation
- `src/gui/dialogs.py` — extracted PasswordGeneratorDialog and DocumentationDialog
- `src/gui/theme.py` — dark and light mode stylesheets
- `src/main.py` — clean application entry point
- `src/__init__.py` — PROJECT_ROOT constant for portable data paths
- `assets/` directory for application icon
- Dark/light theme toggle in Settings menu (persistent across sessions)
- In-app help now loads from consolidated `docs/USER_GUIDE.md`

### Changed
- Customized AGENTS.md for AetherLock (paths, critical files, database schema)
- Updated USER_GUIDE.md with actual application features and documentation
- Refactored monolithic `main_app_pyside.py` (~1250 lines) into `src/` package (7 files)
- Updated `aetherlock.spec` to use `src/main.py` as entry point and bundle `docs/`
- `main_app_pyside.py` is now a thin wrapper around `src.main.run()`
- Updated `.gitignore` to exclude app data files and both `kiss/` and `venv/` dirs
- Updated `requirements.txt` with actual runtime dependencies
- **C3**: Created `venv/` symlink → `kiss/` for standardized virtual env name

### Added
- **A3**: Portable mode detection and config — `.portable` marker file, toggle in Settings menu, status bar indicator
- **A2**: System tray icon with quick-lock — tray menu (Show Window, Lock Vault, Quit), minimize-to-tray on close

### Fixed
- **F0**: `resource_path()` missing `sys` import — added `import sys` at module level
- **F1**: `find_and_remove_duplicates()` backup call ordering — moved `create_pre_op_backup()` after docstring
- **F2**: Created `assets/` directory (icon optionally placed there, gracefully handled)

## 2026-07-24 (session 4)

### Added
- **Category filter** dropdown (QComboBox next to search) with dynamic population from credentials
- **Tag filter** dropdown — parses comma-separated tags, filters entries
- **Tag field** (`tags` TEXT column, auto-migrated) on the edit form
- **Custom fields** (`custom_fields` TEXT column, JSON array) with add/remove table UI
- **Password health report** (Tools menu) — scans weak/reused/short passwords with detail table
- **Sort toggle** — click Title/Username/Category column headers to sort ascending/descending
- **Double-click table cell to copy** — copies value to clipboard with 15s auto-clear
- **Right-click context menu** on table (Copy Username, Copy Password, Edit, Delete)
- **Category click-to-filter** — single-click a category cell to auto-set filter dropdown
- **Favicon auto-fetch** (Tools menu) — downloads 16×16 favicons from Google service, caches in-memory, displays in Title column
- **Rich text notes** — B/I/U formatting toolbar, stored as HTML
- **One-click backup** — status bar message instead of modal dialog, timestamped filenames

### Changed
- Auto-lock: `WindowDeactivate` now resets activity timer instead of immediately locking
- Table columns: increased default sizes (Title 220, Username 160, Category 140), minimum section 100px
- QComboBox styling: matched 30px height to QLineEdit in both themes
- Form labels right-aligned, grid vertical spacing set to 4px
- Splitter: equal initial sizes [500, 500], form panel capped at 700px max width
- Custom fields table: removed max-height cap, added stretch factor (1:2 with form grid)
- Sort signal moved to `create_main_content` (connected once, not on every refresh)

### Fixed
- Password strength bar: hidden by Email QLineEdit in same grid cell — fixed with independent row counter
- File → Quit minimized to tray instead of quitting — now calls `_quit_application()` directly
- Header text clipping in credential table — added `setFixedHeight(50)` on horizontal header
- `sectionClicked.disconnect()` RuntimeWarning — moved connection to table creation

## 2026-07-25 (session 6)

### Changed
- **Rebrand**: Renamed project from `AetherLock` to `AetherVault` to align with GitHub repo name `brandonmunoz1975-ops/AetherVault`
- **Package**: Created `pyproject.toml` for `pip install -e .` with CLI entry point `aethervault`
- **Renamed files**: `aetherlock.py` → `aethervault.py`, `aetherlock.spec` → `aethervault.spec`, `assets/aetherlock.ico` → `assets/aethervault.ico`, `docs/sys/aetherlock.mmd` → `docs/sys/aethervault.mmd`
- **Updated** all 30+ source files, docs, and config to use `AetherVault` naming
- **Rebuilt** REFERENCE.md, REFERENCE.html, and USER_GUIDE.html from updated sources

## 2026-07-26 (session 7)

### Changed
- **Cleanup**: Removed `docs/sys/COST.md` and `docs/sys/KNOWLEDGE.md` from git tracking (keep local only)
- **Docs**: Updated all documentation to reference `src/data/aethervault.db` instead of `password_manager.db`
- **README**: Added `assets/main.png` screenshot, updated project tree and data storage table
- **USER_GUIDE**: Rebranded from "KISS Python Password Manager" to "AetherVault", fixed install instructions
- **Git**: Added `password_manager.db` to `.gitignore`

### Removed
- Deleted stale files: root `password_manager.db`, `src/data/aetherlock.db`, `src/data/aetherlock.db.bak`, `src/data/kiss_vault_*.db.bak`

## 2026-07-24 (session 5)

### Added
- Docstrings added to all modules, classes, and functions across 9 source files (~129 items)
- GitHub Actions CI workflow (`.github/workflows/build.yml`) — builds Windows + macOS executables on release
- Help menu now opens `USER_GUIDE.html` in system browser via `QDesktopServices`

### Changed
- Cleaned up `.gitignore`: added `.repomixignore`, `aetherlock.spec`, `AetherVault/`
- Removed from tracking: `AGENTS.md`, `aetherlock.spec`, `.repomixignore`, `venv` symlink
- Updated all doc references from `main_app_pyside.py` to `aetherlock.py` / `src/gui/app.py`
