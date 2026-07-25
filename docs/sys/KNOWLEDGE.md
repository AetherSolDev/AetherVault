# Created: 2026-07-24
# Last Edited: 2026-07-25 18:12 CT (America/Chicago)
# Path: docs/sys/KNOWLEDGE.md
# Purpose: Curated project knowledge for fast AI context recovery on AetherVault.

> Read this first on session resume. Covers 80% of what you need to be
> productive without reading the full codebase. Updated every session.

---

## Architecture TL;DR

PySide6 desktop password manager. Single-window app with auth screen (setup/login)
and main split-pane view (credential list + edit form). SQLite backend with AES-256
encryption via `cryptography` library. Master password hashed with PBKDF2-SHA256.

## Critical Files Map

| File | Responsibility |
|------|---------------|
| `core_logic.py` | Encryption (Fernet/AES-256), password hashing, `CredentialEntry` model, settings JSON I/O |
| `db_manager.py` | SQLite CRUD for credentials, CSV import/export, duplicate removal, pre-op backup |
| `src/gui/app.py` | PySide6 GUI — auth flow, credential list/edit, clipboard mgmt, auto-lock, menus, system tray, health report, favicon fetch |
| `src/gui/dialogs.py` | PasswordGeneratorDialog, DocumentationDialog |
| `src/gui/theme.py` | Dark/light mode stylesheets, QPalette |
| `src/main.py` | QApplication entry point |
| `docs/USER_GUIDE.md` | User-facing documentation (opened from Help menu) |
| `aethervault.spec` | PyInstaller spec for building standalone `.exe` |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| PySide6 (Qt) over Tkinter | Mature widget set, cross-platform, professional look |
| SQLite + AES-256 | Portable single-file vault, no server needed |
| PBKDF2 (600K iterations) | Industry-standard key derivation, OWASP recommended |
| QStackedWidget for views | Reliable view swapping between auth and main content |
| Single monolithic file | Legacy decision — scheduled for refactor into src/ package |

## Gotchas

- `WindowDeactivate` now resets activity timer (does NOT immediately lock) — fixed in session 4
- `sectionClicked` sort signal connected once in `create_main_content`, not on every `update_list_view`
- Password strength bar row is tracked independently via `row` counter to avoid grid cell collision
- Custom fields stored as JSON array of `{"field": "...", "value": "..."}` objects in `custom_fields` TEXT column
- Tags stored as comma-separated string in `tags` TEXT column — both columns auto-migrated on startup
- `handle_backup()` uses `get_timestamped_backup_path()` for unique filenames, shows success in status bar (no dialog)
- `.master.key` stores the hash, not the raw password — safe, but file deletion = permanent lockout
- Virtual env: `venv/` is a symlink → `kiss/`; both names resolve
- Portable mode: create `.portable` file in app directory to keep all data local
- System tray: close minimizes to tray; use File → Quit or tray → Quit to fully exit

## Code Patterns

- Database methods use `try/except` with `error_handler` callback (lambda wiring to QMessageBox)
- All passwords encrypted at rest, decrypted in memory during session
- `CredentialEntry.to_dict()` used for serialization
- `row_factory = sqlite3.Row` for named column access
- Lambda closures with default args for button callbacks: `lambda checked, entry=line_edit: ...`

## Navigation Hints

- **Need to change encryption?** → `core_logic.py` (encrypt_data, decrypt_data, derive_encryption_key)
- **Need to add a DB operation?** → `db_manager.py` (DatabaseManager class)
- **Need to change UI layout?** → `src/gui/app.py` (PySidePWManager class)
- **Need to add a menu item?** → `src/gui/app.py` (setup_menu_bar method)
- **Need to change backup behavior?** → `db_manager.py` (create_pre_op_backup, _auto_backup_db)

## Session History Summary

- **2026-07-24 (session 1)**: Initial project audit. Set up project scaffolding with New_Project_init template system. Created AGENTS.md, docs/sys/, USER_GUIDE.md, instructions/, scripts/, .repomixignore. Identified 3 bugs and 5 planned changes.
- **2026-07-24 (session 2)**: Fixed F0 (missing sys import), F1 (backup call order), F2 (assets dir). Refactored monolithic main_app_pyside.py (~1250 lines) into src/ package (7 files). Added dark/light theme support. Updated PyInstaller spec, .gitignore, requirements.txt.
- **2026-07-24 (session 3)**: Added system tray icon with quick-lock (A2). Added portable mode detection (A3). Created venv/ symlink (C3).
- **2026-07-24 (session 4)**: Category+tag filters, password health report, entry tags, custom fields, sort toggle, double-click copy, context menu, click-to-filter, favicon fetch, rich text notes, one-click backup. Fixed auto-lock timer bypass, strength bar grid collision, quit-to-tray bug, header clipping, RuntimeWarning. UI polish: QComboBox height matching, right-aligned labels, proportional form stretching, splitter sizing.
- **2026-07-24 (session 5)**: Added docstrings to all 129 modules/classes/functions. GitHub Actions CI for Win+macOS builds. Help opens in browser. Cleaned up `.gitignore` and untracked `AGENTS.md`, `aetherlock.spec`, `.repomixignore`, `venv`.
- **2026-07-25 (session 6)**: Renamed project from AetherLock to AetherVault to align with GitHub repo name. Created `pyproject.toml` for `pip install -e .` with CLI entry point `aethervault`. Updated all 30+ files with correct naming. Rebuilt REFERENCE docs. Installed system-wide via `pip install --user --break-system-packages -e .`.
