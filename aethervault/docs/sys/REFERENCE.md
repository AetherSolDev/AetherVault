# docs — Technical Reference

> Auto-generated on 2026-08-06 22:06 CT from docs/sys/
> Source: `scripts/build_reference.py`

## Table of Contents

- [Architecture](#architecture)
- [Project Knowledge](#project-knowledge)
- [Project Plan](#project-plan)
- [Tasks](#tasks)
- [Changelog](#changelog)
- [Bug Tracker](#bug-tracker)
- [Development Costs](#development-costs)
- [Model Pricing Reference](#model-pricing-reference)
- [Diagram (aethervault)](#diagram-(aethervault))
- [Audit Report](#audit-report)
- [Future Dev Ideas](#future-dev-ideas)
- [Sessions](#sessions)

---

---

## Architecture

## Directory Structure
```
AetherVault/
├── .github/
│   └── workflows/
│       ├── build.yml            # Cross-platform exe builds + release asset upload
│       └── ci.yml               # pytest on push/PR (Python 3.10–3.12)
├── aethervault/
│   ├── __init__.py            # Package init, PROJECT_ROOT, VERSION, portable mode
│   ├── core/                  # Business logic — no UI imports
│   │   ├── __init__.py
│   │   ├── engine.py          # Encryption, hashing, key derivation, backup/wipe, settings
│   │   └── password.py        # score_password, generate_strong_password
│   ├── shared/                # Cross-cutting — database, models
│   │   ├── __init__.py
│   │   ├── database.py        # DatabaseManager — SQLite CRUD, import/export/preview, backup, WAL
│   │   └── models.py          # CredentialEntry data model
│   ├── __main__.py            # Application entry point (QApplication setup, auto-detach on Unix, --foreground)
│   ├── assets/                # App icon (aethersol.ico), logo, screenshots
│   ├── docs/
│   │   ├── USER_GUIDE.md      # User-facing documentation
│   │   ├── USER_GUIDE.html
│   │   └── sys/               # System documentation (PLAN, TASKS, CHANGELOG, sessions.md, etc.)
│   └── gui/
│       ├── __init__.py
│       ├── app.py             # PySidePWManager — coordinator (auth, menus, CRUD, import/export, tray)
│       ├── click_to_copy_filter.py  # ClickToCopyFilter event filter
│       ├── conflict_dialog.py       # ImportConflictDialog for per-entry conflict resolution
│       ├── credential_form.py       # CredentialForm — right panel (fields, notes, custom fields, save/cancel)
│       ├── credential_table.py      # CredentialTable — left panel (search, filters, table, context menu)
│       ├── dialogs.py         # PasswordGeneratorDialog, DocumentationDialog
│       ├── password_strength.py     # PasswordStrengthBar widget
│       └── theme.py           # Dark and light theme stylesheets
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures (temp_db, temp_db_no_key, sample_entry)
│   ├── test_core_logic.py     # Encryption, hashing, password gen, settings (24 tests)
│   ├── test_score_password.py # score_password unit tests (10 tests)
│   ├── test_credential_entry.py # CredentialEntry model (5 tests)
│   └── test_db_manager.py     # CRUD, import/export, duplicates, backup, key guards (22 tests)
├── data/                      # Runtime data (gitignored)
│   ├── aethervault.db         # Encrypted vault (SQLite)
│   ├── aethervault.db.bak     # Auto-backup
│   ├── .master.key            # Master password hash (PBKDF2)
│   └── .app_settings.json     # App settings (lockout, theme, etc.)
├── .gitignore
├── .repomixignore
├── pyproject.toml
├── requirements.txt
├── MANIFEST.in
└── aethervault.spec           # PyInstaller build spec
```

## Architecture Layers

### 1. Data Layer (`aethervault/core/engine.py`, `aethervault/shared/database.py`)
- SQLite database with AES-256 encrypted credential storage, WAL journal mode
- PBKDF2 key derivation from master password (600K iterations)
- Automatic timestamped backups + pre-op backups (backup before import/duplicate removal)
- CSV import with column alias mapping (73 aliases across 17 fields) + conflict preview/execute
- `__enter__`/`__exit__` context manager protocol

### 2. Coordinator (`aethervault/gui/app.py`)
- Authentication flow (setup master password → login → encryption key derivation)
- Clipboard management with auto-clear timer (15s) and form auto-clear on password copy
- Auto-lock on inactivity (configurable 1-30 min)
- Password generation (via PasswordGeneratorDialog)
- Duplicate detection via `db_manager.find_and_remove_duplicates()`
- System tray icon with quick-lock and minimize-to-tray
- Import/export/backup/restore with conflict resolution workflow
- Password health report (weak/reused/short scan)
- Theme toggle (light/dark)
- Portable mode detection

### 3. Presentation Layer (`aethervault/gui/`)
- **CredentialTable** — left panel: search, category/tag filters, sortable table, right-click context menu, favicon fetch
- **CredentialForm** — right panel: 8 editable fields, rich text notes, custom fields table, strength bar, save/cancel
- **ImportConflictDialog** — conflict review with per-entry radio buttons, bulk actions
- PySide6 (Qt) GUI with QStackedWidget for auth/main views
- QSplitter layout for list + form
- Dark/light themes

## Data Flow
```
User Input → PySidePWManager (app.py) → CredentialTable / CredentialForm
                                            ↓ signals
                                    PySidePWManager (coordinator)
                                            ↓
                                    DatabaseManager (shared/database.py) → SQLite
                                            ↓
                                    core/engine.py (AES-256 encrypt/decrypt)
```

## CI/CD Pipeline

```
Push to main / PR            → ci.yml → pytest (Python 3.10–3.12)     → gate
Publish Release / manual run → build.yml → PyInstaller onefile per OS →
    ├── ubuntu-latest   → aethervault-linux-x86_64
    ├── windows-latest  → aethervault-windows-x86_64.exe
    ├── macos-15-intel  → aethervault-macos-x86_64
    └── macos-latest    → aethervault-macos-arm64
                                            ↓ (on release: published)
                                    softprops/action-gh-release
                                            ↓
                        Assets attached to Release → /releases/latest/download
```

- `build.yml` requires `permissions: contents: write` so the `GITHUB_TOKEN` can upload release assets.
- The spec (`aethervault.spec`) is a shared single-file EXE build (no `COLLECT`); each OS produces one binary.
- Linux builds install Qt/X11 system deps (`libegl1`, `libgl1`, `libxcb-*`) so the xcb platform plugin is self-contained.
- macOS ships two binaries (arm64 + x86_64) because `cffi` has no universal2 wheel; the retired `macos-13` runner is replaced by `macos-15-intel`.

---

## Project Knowledge

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
| `aethervault/core/engine.py` | Encryption (Fernet/AES-256), password hashing/verification, key derivation, backup/wipe, settings JSON I/O, path constants |
| `aethervault/core/password.py` | `score_password()`, `generate_strong_password()` |
| `aethervault/shared/database.py` | DatabaseManager — SQLite CRUD, CSV import/export/preview/execute, column alias mapping (73 aliases), `preview_import()`/`execute_import()`, duplicate removal, pre-op backup, WAL mode, context manager |
| `aethervault/shared/models.py` | `CredentialEntry` data model |
| `aethervault/gui/app.py` | PySidePWManager coordinator — auth flow, menus, CRUD orchestration, import/export/backup, system tray, auto-lock, clipboard, theme toggle, health report |
| `aethervault/gui/credential_table.py` | CredentialTable — left panel: search, category/tag filters, sortable table, double-click copy, context menu, favicon fetch |
| `aethervault/gui/credential_form.py` | CredentialForm — right panel: 8 editable fields, rich text notes, custom fields table, password strength bar, save/cancel |
| `aethervault/gui/conflict_dialog.py` | ImportConflictDialog — conflict review with per-entry radio buttons, bulk actions |
| `aethervault/gui/click_to_copy_filter.py` | ClickToCopyFilter event filter |
| `aethervault/gui/password_strength.py` | PasswordStrengthBar widget (uses `score_password()`) |
| `aethervault/gui/dialogs.py` | PasswordGeneratorDialog, DocumentationDialog |
| `aethervault/gui/theme.py` | Dark/light mode stylesheets, QPalette |
| `aethervault/__main__.py` | QApplication entry point (auto-detach, --foreground flag) |
| `tests/` | 71 pytest tests across 6 files + shared fixtures |
| `aethervault/docs/USER_GUIDE.md` | User-facing documentation (opened from Help menu) |
| `aethervault.spec` | PyInstaller spec for building standalone executables |
| `.github/workflows/build.yml` | CI builds + release-uploads single-file exe for Win/Linux/macOS (Intel + ARM) |
| `.github/workflows/ci.yml` | Runs pytest on push/PR across Python 3.10–3.12 |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| PySide6 (Qt) over Tkinter | Mature widget set, cross-platform, professional look |
| SQLite + AES-256 | Portable single-file vault, no server needed |
| PBKDF2 (600K iterations) | Industry-standard key derivation, OWASP recommended |
| QStackedWidget for views | Reliable view swapping between auth and main content |
| `core/` + `shared/` layout | STRUCTURE.md standard: `core/` = business logic (no UI), `shared/` = database + models. GUI imports both, never the reverse. Completed 2026-08-05 |

## Gotchas

- **All text `open()` calls must pass `encoding="utf-8"`** — Windows defaults to cp1252 and
  crashes on non-ASCII bytes (AetherTime hit this). Binary mode (`r+b`) must NOT pass `encoding`.
- **Frozen data dir is platform-aware** — `aethervault/__init__.py` `_frozen_data_root()`:
  Windows/macOS single-file exe → `data/` next to the exe; Linux AppImage →
  `~/.local/share/AetherVault`; unwritable app dir → per-user fallback. Do NOT revert to
  `os.getcwd()` — Finder/LaunchServices don't reliably set cwd and AppImage mounts are ephemeral.
- `WindowDeactivate` now resets activity timer (does NOT immediately lock) — fixed in session 4
- `sectionClicked` sort signal connected once in `create_main_content`, not on every `update_list_view`
- Password strength bar row is tracked independently via `row` counter to avoid grid cell collision
- Custom fields stored as JSON array of `{"field": "...", "value": "..."}` objects in `custom_fields` TEXT column
- Tags stored as comma-separated string in `tags` TEXT column — both columns auto-migrated on startup
- `handle_backup()` uses `get_timestamped_backup_path()` for unique filenames, shows success in status bar (no dialog)
- `.master.key` stores the hash, not the raw password — safe, but file deletion = permanent lockout
- Virtual env: `venv/` (the old `kiss/` dir was removed 2026-08-05)
- App icon: `aethervault/assets/aethersol.ico` (window + tray); logo `aethersol_logo.png` (README). Do not reference `aethervault.ico` — renamed.
- Portable mode: create `.portable` file in app directory to keep all data local
- System tray: close minimizes to tray; use File → Quit or tray → Quit to fully exit
- Auto-detach: `main.py` forks on Unix — parent exits, child runs GUI. Debug output goes to `/dev/null`. Use `--foreground` / `-f` to keep terminal attached
- Tag reminder: after bumping version in code, always `git tag -a vX.Y.Z && git push origin vX.Y.Z` — the upgrade check (`--upgrade`) reads GitHub tags, not committed code
- **Pre-op backups write to `data/`** (from `get_timestamped_backup_path()`), which is gitignored and empty on CI. `create_pre_op_backup()` now `os.makedirs()`es the dir first — don't "optimize" it back out
- **`aethervault.spec` must stay tracked** — it was gitignored and CI builds failed with "Spec file not found". If a PyInstaller spec is ever needed, commit it
- **`gh release create vX.Y.Z` reuses an existing local tag** — if a tag already exists (e.g., created days earlier), the release points at that old commit and the release build uses the OLD workflow/spec. Always verify `git rev-parse vX.Y.Z^{commit}` matches intended HEAD before releasing
- **macOS runners (2026-07)**: `macos-13` is retired (jobs queue forever). Use `macos-15-intel` (x86_64) and `macos-latest` (arm64). `universal2` builds fail because `cffi` has no fat wheel — build separate arch binaries instead
- **Ubuntu 24.04 runners**: `libgl1-mesa-glx` no longer exists; use `libgl1` + `libxkbcommon-x11-0` and bundle `libxcb-icccm4`/`libxcb-keysyms1`/`libxcb-shape0` so Qt's xcb platform plugin is self-contained

## Code Patterns

- Database methods use `try/except` with `error_handler` callback (lambda wiring to QMessageBox)
- All passwords encrypted at rest, decrypted in memory during session
- `CredentialEntry.to_dict()` used for serialization
- `row_factory = sqlite3.Row` for named column access
- Lambda closures with default args for button callbacks: `lambda checked, entry=line_edit: ...`

## Namespace Collision Lesson

**Never name your top-level package `src/`.** If you have multiple projects on
the same machine (AetherVault + AetherPod), their editable installs all register
`src` as a Python package — whichever was installed last wins.

**Fix:** Rename `src/` → `{project_name}/` from the start. Update all imports
from `from src.xxx` → `from aethervault.xxx`.

AetherVault was renamed from `src/` → `aethervault/` in v6.1.2 after hitting
this exact bug. Don't repeat it.

## Deployment & Packaging

| Task | Command |
|------|---------|
| Global install | `pip install --user --break-system-packages -e .` |
| Version bump | `aethervault/__init__.py` + `pyproject.toml` → `git tag -a vX.Y.Z` → `git push --tags` |
| Upgrade check | `aethervault/__main__.py` fetches latest tag from GitHub API |
| PyInstaller build (local) | `pyinstaller aethervault.spec` → `dist/aethervault` (single file) |
| CI build (all platforms) | Push to `main`, then Actions → Build → "Run workflow" (`workflow_dispatch`), or publish a Release |
| Publish a Release with binaries | `gh release create vX.Y.Z --generate-notes` → `build.yml` auto-attaches 4 executables on `release: published` |
| Data files location | `aethervault/docs/`, `aethervault/assets/` (inside package for pip compat) |
| **Frozen data dir** | Windows/macOS exe → `data/` next to exe; Linux AppImage → `~/.local/share/AetherVault` (see `_frozen_data_root()` in `__init__.py`) |

**Key rule:** Data files must live inside `aethervault/` to survive a non-editable pip install.

## Navigation Hints

- **Need to change encryption?** → `aethervault/core/engine.py` (encrypt_data, decrypt_data, derive_encryption_key)
- **Need to change password strength/generation?** → `aethervault/core/password.py` (score_password, generate_strong_password)
- **Need to add a DB operation?** → `aethervault/shared/database.py` (DatabaseManager class)
- **Need to change the credential model?** → `aethervault/shared/models.py` (CredentialEntry)
- **Need to change the credential table?** → `aethervault/gui/credential_table.py` (CredentialTable class)
- **Need to change the edit form?** → `aethervault/gui/credential_form.py` (CredentialForm class)
- **Need to change import conflict behavior?** → `aethervault/gui/conflict_dialog.py`, `aethervault/shared/database.py` (preview_import, execute_import)
- **Need to add a menu item?** → `aethervault/gui/app.py` (_build_file_menu, _build_tools_menu, etc.)
- **Need to change backup behavior?** → `aethervault/shared/database.py` (create_pre_op_backup), `aethervault/core/engine.py` (rotate_backups)
- **Need to run tests?** → `venv/bin/python -m pytest tests/ -v`

## Future Features

| Feature | Status | Notes |
|---------|--------|-------|
| **vCard export** | planned | `File > Export Contacts (vCard)` — filter entries with non-empty phone/address, write `.vcf` (vCard 3.0). Covers 99% of real use. hCard/meCard not worth implementing. See session 2026-07-27 for full analysis. |

## Session History Summary

- **2026-08-06 (session 26)**: **v6.4.1 release published.** Tag `v6.4.1` existed locally but no
  GitHub release was created → `Latest` was v6.4.0 and the F16 binaries weren't downloadable.
  Created the release at `v6.4.1` (points at F16 fix `8eb0f54`); `build.yml` auto-attached all 4
  executables. Also manually dispatched Build for artifact-only runs. Workflows: CI (job `test`,
  pytest), Build (4-OS PyInstaller), Publish to PyPI. Noted Node 20 deprecation on
  checkout@v4/setup-python@v5/upload-artifact@v4/gh-release@v2 (non-blocking).

- **2026-08-06 (session 25)**: **Cross-platform hardening (F16) — aligned with AetherTime.** Added
  `encoding="utf-8"` to all text `open()` calls in `core/engine.py` (6) + portable-marker write in
  `__init__.py` (Windows cp1252 crash class). Made frozen `PROJECT_ROOT` platform-aware via
  `_frozen_data_root()`: Windows/macOS single-file exe → `data/` next to exe; Linux AppImage →
  `~/.local/share/AetherVault`; unwritable app dir → per-user fallback. Verified all 3 platform
  branches by simulation. `os.fork()` detach runs before `QApplication` — safe, left unchanged.
  Version 6.4.0 → 6.4.1. 74/74 tests pass; compileall clean; engine round-trip verified.

- **2026-08-05 (session 24)**: **Release v6.4.0 + PyPI + README.** Tagged/released v6.4.0 (4 binaries: Linux, macOS arm64/x86_64, Windows). Published `aethervault-py` 6.4.0 to PyPI via trusted publishing; fixed publish workflow YAML bug (heredoc broke parsing) + CI Qt deps + badge cache-bust. Rewrote README in AetherPod format; captured full-screen demo GIF incl. password health report (dialogs grabbed via `activeWindow().grab()`). Captured format in kit `README_FORMAT.md`. Made `-u` PyPI-aware (`importlib.metadata` → `pip install --upgrade aethervault-py`; source/git keeps git path; exe users redownload). 74 tests pass.
- **2026-08-05 (session 23)**: **Package restructure (C10).** Split `core_logic.py` → `aethervault/core/engine.py` (encryption/hashing/keys/backup/wipe/settings) + `aethervault/core/password.py` (score/gen); `db_manager.py` → `aethervault/shared/database.py` (DatabaseManager); `CredentialEntry` → `aethervault/shared/models.py`. Updated all importers (GUI + 6 test files), deleted old modules, fixed test monkeypatch targets (`aethervault.core.engine.*`). 71 tests pass; app launches. STRUCTURE.md layout now complete.
- **2026-08-05 (session 22)**: **Kit alignment + bug fixes.** Restored `project_kit/` from NAS, compared vs project (gap analysis). Licensing: added "How to Decide: GPL3 vs MIT+EULA" to kit LICENSING.md, moved EULA→instructions/. Brand assets: `aethersol.ico`/`aethersol_logo.png` into `project_kit/assets/` + `instructions/ASSETS.md`. Aligned project: added `sessions.md`, `FUTURE_DEV_IDEAS.md`, `aethervault.txt`, `project_audit/`; synced `instructions/`; updated `AGENTS.md`; removed stale `kiss/`. **Fixed copy/paste bug** (F14): Copy Password button captured the loop variable → copied Category field; fixed with default-arg lambda; 2 regression tests; suite 69→71. Tray/window icon now `aethersol.ico`.
- **2026-07-24 (session 1)**: Initial project audit. Set up project scaffolding with New_Project_init template system. Created AGENTS.md, docs/sys/, USER_GUIDE.md, instructions/, scripts/, .repomixignore. Identified 3 bugs and 5 planned changes.
- **2026-07-24 (session 2)**: Fixed F0 (missing sys import), F1 (backup call order), F2 (assets dir). Refactored monolithic main_app_pyside.py (~1250 lines) into src/ package (7 files). Added dark/light theme support. Updated PyInstaller spec, .gitignore, requirements.txt.
- **2026-07-24 (session 3)**: Added system tray icon with quick-lock (A2). Added portable mode detection (A3). Created venv/ symlink (C3).
- **2026-07-24 (session 4)**: Category+tag filters, password health report, entry tags, custom fields, sort toggle, double-click copy, context menu, click-to-filter, favicon fetch, rich text notes, one-click backup. Fixed auto-lock timer bypass, strength bar grid collision, quit-to-tray bug, header clipping, RuntimeWarning. UI polish: QComboBox height matching, right-aligned labels, proportional form stretching, splitter sizing.
- **2026-07-24 (session 5)**: Added docstrings to all 129 modules/classes/functions. GitHub Actions CI for Win+macOS builds. Help opens in browser. Cleaned up `.gitignore` and untracked `AGENTS.md`, `aetherlock.spec`, `.repomixignore`, `venv`.
- **2026-07-25 (session 6)**: Renamed project from AetherLock to AetherVault to align with GitHub repo name. Created `pyproject.toml` for `pip install -e .` with CLI entry point `aethervault`. Updated all 30+ files with correct naming. Rebuilt REFERENCE docs. Installed system-wide via `pip install --user --break-system-packages -e .`.
- **2026-07-26 (session 7)**: Removed COST.md and KNOWLEDGE.md from git tracking (local-only). Updated all docs to reference `src/data/aethervault.db`. Added README screenshot `assets/main.png`. Cleaned stale files. Pushed to GitHub.
- **2026-07-27 (session 8)**: God file split — `app.py` 1627→968 lines, 4 new extracted files. Version 6.0.0→6.1.0. Added `time_last_used`/`time_password_changed` columns. CSV import with column alias system (73 aliases). Full audit (12/12 findings resolved). `score_password()` extracted, test suite (22 tests). WAL mode, context manager, conflict import dialog, logging instead of print. Documentation: AUDIT_REPORT.md, versioning criteria in AGENTS.md, safety.md fixes (NAS mount check, trash dir, .zshrc guards).
- **2026-07-27 (session 9)**: Import conflict resolution dialog + preview/execute workflow. `src/`→`aethervault/` rename to fix namespace collision between sibling projects. Packaging: docs/assets into `aethervault/`, MANIFEST.in, data-files, README updates. CLI switches (`--version`, `--debug`, `--upgrade`). Template updates to `New_Project_init` (packaging.md, namespace rule in audit checklist and cleanup patterns). Version 6.1.2. Cost: ~$0.35 for this session.
- **2026-07-27 (session 10)**: Auto-detach from terminal on Unix (`os.fork()` + `os.setsid()`). Added `--foreground` / `-f` flag to keep terminal attached for debugging. Updated CLI reference in README and USER_GUIDE. Version 6.2.0.
- **2026-07-27 (session 11)**: Encryption key guard on all import methods (`import_from_csv`, `execute_import`, `preview_import`). Simplified duplicate removal SQL to fix Python 3.14 transaction error. Added 39 tests: `test_core_logic.py` (encryption, hashing, password generation, settings) + extended `test_db_manager.py` (import/export, duplicates, backup, key guards). Updated README, ARCHITECTURE, KNOWLEDGE, USER_GUIDE paths. Test suite: 22→61. Version 6.2.1.
- **2026-07-27 (session 12)**: `--upgrade`/`-u` now auto-performs the upgrade (subprocess git pull + pip install -e . for cloned repos, pip install --upgrade for pip installs). Removed `_print_upgrade_instructions()`, added `_perform_upgrade()` and `_get_pip_command()`. Set `GIT_DISCOVERY_ACROSS_FILESYSTEM=1` in subprocess env for cross-filesystem git discovery. Fixed `.gitignore` to cover `src/data/`. No version bump.
- **2026-07-27 (session 13)**: Re-audit against alignment checklist — 42/42 checks pass, score A. All 12 prior findings still closed. No new issues. Reinstalled package system-wide. Updated all file timestamps to 16:51 CT.
- **2026-07-27 (session 14)**: Fixed `build.yml` workflow (stale `src/main.py` → `aethervault.spec`, added Linux build target). Created `ci.yml` — runs 61 pytest tests on push/PR across Python 3.9-3.12.
- **2026-07-30 (session 15)**: Cross-platform CI/CD delivery. Fixed CI failure (pre-op backup now creates `src/data/` dir). Committed `aethervault.spec` (was gitignored). Reworked `build.yml` — Ubuntu 24.04 Qt/xcb deps, `macos-13`→`macos-15-intel`, separate arm64+x86_64 macOS builds (cffi has no fat wheel), release asset upload. Published v6.2.1 release with 4 binaries; moved stale v6.2.1 tag to current HEAD. README: download table + build badge, fixed image/docs links, removed stray `# test` lines. Removed `safety.md`. Cleaned 9 stale Actions runs. 10 commits, no version bump.
- **2026-08-01 (session 16)**: Audit re-run (score A− → A). Removed all unused imports (AST-verified, zero remaining). Narrowed all 22 `except Exception` blocks to specific types (OSError, ValueError, TypeError, csv.Error, shutil.Error, sqlite3.Error, InvalidToken, RuntimeError). Added `InvalidToken` import to `core_logic.py`, `csv` import to `gui/app.py`. 61 tests pass, no version bump.
- **2026-08-01 (session 17)**: **Repo moved** to `git@github.com:AetherSolDev/AetherVault.git`. Updated remote + all URL refs (`__main__.py` GITHUB_TAGS_API/GIT_REPO_URL/RELEASES_URL, README badges/links, USER_GUIDE.md/html). Workflows already cover all platforms. Marked transfer done in PRE_PUBLIC_CLEANUP.md.
- **2026-08-01 (session 18)**: **Entry point cleanup** — `aethervault/main.py` → `aethervault/__main__.py` (run via `python -m aethervault`), removed root `aethervault.py` shim, fixed pyproject package-data (`src/` → `aethervault/`), updated MANIFEST.in + spec + global install. Reinstalled system-wide; 61 tests pass.
- **2026-08-01 (session 19)**: **Removed `src/`** — moved runtime data `src/data/` → root `data/` (`DATA_DIR = PROJECT_ROOT/data`), deleted stale `aethervault/data/`. Updated .gitignore + docs. Live vault preserved (429 creds).
- **2026-08-01 (session 20)**: **Duress password** (optional) — entered at login → cryptographically wipes vault + backups (`wipe_vault()` in core_logic). Keys deleted first (crypto erasure), then random-overwrite + delete all DB/WAL/SHM/.bak/settings. Fake "Invalid password" dialog then silent exit. Stored as PBKDF2 hash in `data/.duress.key`; checked first with identical cost (no timing tell). Settings → Duress Password to set/clear (needs master pw). Also added `rotate_backups()` (keeps 5 `.bak`). 8 new tests (69 total). Verified live against an isolated copy of the real vault — wipe destroyed all files, real vault (429 creds) untouched. **Released as v6.3.0.**
- **2026-08-01 (session 21)**: **Bug found in live test** — `QInputDialog.getText()` returns `(text, ok)` in PySide6, duress setup unpacked backwards → silent `AttributeError` after master prompt. Fixed + verified with real dialogs. Live duress wipe test on the real vault: wipe destroyed `data/` completely, manual + NAS backups preserved 429 creds, restore worked, logged back in. **Released as v6.3.1 (fix release).**

---

## Project Plan

# AetherVault Plan

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
- [x] A15 — CI/CD build & release pipeline (GitHub Actions)

## BUGS
- [x] F16 — Windows crash risk: bare `open()` without `encoding="utf-8"` + frozen data dir not platform-aware (fixed 2026-08-06)
- [x] F0 — `resource_path()` references `sys._MEIPASS` without `sys` import at module level
- [x] F1 — `find_and_remove_duplicates()` calls backup before docstring (wrong execution order)
- [x] F2 — `assets/kiss_icon.ico` referenced but no `assets/` directory exists
- [x] F3 — Auto-lock triggers immediately on WindowDeactivate (bypasses configured timeout)
- [x] F4 — Password strength bar hidden by Email QLineEdit in same grid cell
- [x] F5 — File → Quit minimizes to tray instead of quitting
- [x] F6 — Header text clipped in credential table
- [x] F7 — `sectionClicked.disconnect()` RuntimeWarning on every table refresh
- [x] F8 — `create_pre_op_backup()` fails on fresh checkouts when `src/data/` is absent

## CHANGES
- [x] C0 — Refactor `main_app_pyside.py`: split UI, controllers, clipboard, backup into separate modules
- [x] C1 — Replace `help_doc.md` with `docs/USER_GUIDE.md` in-app help reference
- [x] C2 — Update all file headers with proper Created/Last Edited/Purpose
- [x] C3 — Standardize virtual env to `venv/` (current is `kiss/`)
- [x] C4 — Move flat `.py` files into `src/` package structure
- [x] C5 — Form layout: right-aligned labels, 4px vertical spacing, proportional stretching
- [x] C6 — QComboBox styling: 30px height matching QLineEdit in both themes
- [x] C7 — Splitter: equal initial sizes, form panel capped at 700px
- [x] C8 — Remove `safety.md` from repository (was NAS-backup strategy doc) — 2026-07-30

## ADDITIONS (session 20) — Duress Password (Option A)
- [x] A16 — Duress password (optional): if entered at login, cryptographically wipes the vault
  - `data/.duress.key` — PBKDF2 hash of duress password (same scheme as master)
  - Checked FIRST in `attempt_login()` (identical PBKDF2 cost ⇒ no timing tell)
  - On match: close DB → delete `.master.key`/`.duress.key` first (crypto erasure) → overwrite+delete `.db`, `.db-wal`, `.db-shm`, `.db.bak`, `aethervault_*.db.bak`, `.app_settings.json`
  - Then show a fake "Invalid password" dialog and exit — indistinguishable from a failed login
  - Settings → Duress Password dialog to set/clear it (requires current master password)
- [x] C9 — Cap `.bak` rotation (keep N most recent, prune the rest) so wipe time stays bounded

---

## Tasks

# AetherVault Tasks

## P0 — Critical (security/stability)

- [x] F16 — Cross-platform hardening (encoding + frozen data dir) — aligned with AetherTime
  - **ID**: fix-cross-platform-hardening
  - **Tags**: bug, cross-platform, windows, macos, packaging
  - **Details**: Added `encoding="utf-8"` to all text `open()` calls in `core/engine.py` (6) +
    portable-marker write in `__init__.py` (Windows cp1252 crash class). Made frozen
    `PROJECT_ROOT` platform-aware via `_frozen_data_root()`: Windows/macOS single-file exe → `data/`
    next to exe; Linux AppImage → `~/.local/share/AetherVault`; unwritable app dir → per-user
    fallback. Verified all 3 branches by simulation. `os.fork()` detach runs before `QApplication`
    (safe, unchanged). Version 6.4.0 → 6.4.1.
  - **Files**: `aethervault/__init__.py`, `aethervault/core/engine.py`, `aethervault/docs/sys/*`
  - **Acceptance**: 74 tests pass; compileall clean; engine round-trip (master/duress/settings) verified.

- [x] R1 — Release v6.4.0 + PyPI publishing + README/GIF
  - **ID**: release-6.4.0-pypi
  - **Tags**: release, ci, docs, packaging
  - **Details**: Bumped to 6.4.0; tagged + released with 4 binaries (Linux, macOS arm64/x86_64, Windows). Published `aethervault-py` to PyPI via trusted publishing (fixed workflow YAML heredoc bug + CI Qt deps + badge cache). Rewrote README in AetherPod format with full-screen demo GIF incl. password health report. Made `-u` PyPI-aware. Captured README format in kit `README_FORMAT.md`.
  - **Files**: `README.md`, `.github/workflows/*`, `aethervault/__main__.py`, `aethervault/assets/screens/*`, `project_kit/instructions/README_FORMAT.md`
  - **Acceptance**: `pip install aethervault-py` → v6.4.0; `aethervault -u` upgrades via PyPI; 4 release binaries attached; 74 tests pass.

- [x] F14 — Copy Password button copies wrong field (late-binding lambda)
  - **ID**: fix-copy-password
  - **Tags**: bug, gui, clipboard
  - **Details**: `credential_form.py` wired the Copy Password button to a lambda capturing the loop variable `line_edit`, which after the form loop points to the last field (`category`). Clicking copied the wrong field (or empty).
  - **Files**: `aethervault/gui/credential_form.py`, `tests/test_credential_form.py`
  - **Acceptance**: Clicking Copy next to Password places the actual decrypted password on the clipboard; 2 regression tests pass.

- [x] A17 — Align repo structure to project_kit template
  - **ID**: template-alignment
  - **Tags**: change, documentation, structure
  - **Details**: Added `sessions.md`, `FUTURE_DEV_IDEAS.md`, `aethervault.txt`, `project_audit/`; synced `instructions/`; updated `AGENTS.md`; replaced tray "K" icon with `aethersol.ico`; removed stale `kiss/`.
  - **Files**: `AGENTS.md`, `aethervault/docs/sys/*`, `aethervault/gui/app.py`, `instructions/*`
  - **Acceptance**: Template files present, tray/window icon shows `aethersol.ico`, tests pass.

- [x] C10 — Restructure `core_logic.py`/`db_manager.py` into `core/` + `shared/`
  - **ID**: package-restructure
  - **Tags**: change, architecture
  - **Details**: Split per STRUCTURE.md — `core/engine.py` (encryption/hashing/keys/backup/wipe/settings), `core/password.py` (score/gen), `shared/database.py` (DatabaseManager), `shared/models.py` (CredentialEntry). Updated all importers (GUI + 6 test files), deleted old modules, fixed test monkeypatch targets.
  - **Files**: `aethervault/core/*`, `aethervault/shared/*`, `aethervault/gui/*`, `tests/*`
  - **Acceptance**: Package layout matches template; 71 tests pass; app launches.

- [x] F15 — Missing startup integrity check (audit finding)
  - **ID**: integrity-check
  - **Tags**: bug, database, security
  - **Details**: AGENTS.md requires startup integrity checks with automatic recovery; none existed. Added `PRAGMA integrity_check` to `DatabaseManager._connect()` with auto-recovery from the latest `.db.bak` (copy + re-check). No backup → `conn=None` safe fail. 3 regression tests.
  - **Files**: `aethervault/shared/database.py`, `tests/test_db_manager.py`
  - **Acceptance**: Corrupt DB recovered from backup; no-backup case fails safely; 74 tests pass.

- [x] F16 — Python floor below checklist standard (audit finding)
  - **ID**: python-floor
  - **Tags**: change, environment
  - **Details**: `requires-python` was `>=3.9`; checklist 9.1 prefers 3.10+. Raised to `>=3.10`, dropped 3.9 from CI matrix, updated USER_GUIDE.
  - **Files**: `pyproject.toml`, `.github/workflows/ci.yml`, `aethervault/docs/USER_GUIDE.md`
  - **Acceptance**: `requires-python >=3.10`; CI tests 3.10–3.12.

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

- [x] F8 — Fix `create_pre_op_backup()` failure on fresh checkouts
  - **ID**: fix-preop-backup-dir
  - **Tags**: bug, database, ci
  - **Details**: `create_pre_op_backup()` wrote to `get_timestamped_backup_path()` (inside `src/data/`), but that dir has no tracked files and is absent in a fresh CI checkout → `shutil.copyfile` raised `FileNotFoundError`, swallowed by the test's error-handler lambda → `assert result is not None` failed on CI (Python 3.10) while passing locally.
  - **Files**: `aethervault/db_manager.py`
  - **Acceptance**: `os.makedirs(os.path.dirname(backup_path), exist_ok=True)` added before `copyfile`; CI green on 3.9–3.12.

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

- [x] A15 — CI/CD build & release pipeline for pre-built executables
  - **ID**: ci-cd-binaries
  - **Tags**: feature, ci, packaging, devx
  - **Details**: `build.yml` builds single-file executables on `ubuntu-latest`, `windows-latest`, `macos-15-intel` (x86_64), and `macos-latest` (arm64), then attaches them to a GitHub Release on `release: published`. Committed `aethervault.spec` (was gitignored). Fixed Ubuntu 24.04 Qt/xcb system deps. Published v6.2.1 with 4 binaries; README download table + build badge.
  - **Files**: `.github/workflows/build.yml`, `aethervault.spec`, `README.md`, `.gitignore`
  - **Acceptance**: All 4 executables build green; release assets downloadable at `/releases/latest/download/`.

- [x] A16 — Duress password (optional, destructive)
  - **ID**: duress-password
  - **Tags**: feature, security
  - **Details**: If the duress password is entered at login, cryptographically destroys the vault and all backups (`wipe_vault()`). Keys deleted first (crypto erasure), then random-overwrite + delete all `.db`, `.db-wal`, `.db-shm`, `.db.bak`, `aethervault_*.db.bak`, `.app_settings.json`. Shows fake "Invalid password" dialog then silent exit. Stored as PBKDF2 hash in `data/.duress.key`; checked first with identical cost (no timing tell). Configured via Settings → Duress Password (requires master password). Verified live: wipe destroyed everything, restore from backup worked (429 creds).
  - **Files**: `aethervault/core_logic.py`, `aethervault/gui/app.py`
  - **Acceptance**: Entering duress at login wipes `data/` completely, exits silently; backup restores the vault.

- [x] C9 — Cap `.bak` backup rotation
  - **ID**: backup-rotation
  - **Tags**: change, database
  - **Details**: `rotate_backups()` keeps the 5 most recent timestamped backups and prunes the rest (pre-op + manual backup paths), keeping duress-wipe time bounded.
  - **Files**: `aethervault/core_logic.py`, `aethervault/db_manager.py`, `aethervault/gui/app.py`
  - **Acceptance**: Only the 5 most recent `aethervault_*.db.bak` files remain after a backup.

## P3 — Future

- [ ] Browser extension integration
- [ ] Cloud sync (optional, opt-in)
- [ ] Auto-type / fill hotkey

---

## Changelog

# Changelog

## [Unreleased] — 2026-08-06 (release operations)

### Added
- **v6.4.1 GitHub release published** — tag `v6.4.1` had no GitHub release, so `Latest` pointed at
  v6.4.0 and the F16 fixes weren't downloadable. Created the release; `build.yml` attached the 4
  executables (Linux x86_64, macOS arm64 + x86_64, Windows x86_64). Manual `workflow_dispatch`
  of Build also verified (artifacts only, no release).

### Notes
- Node 20 actions deprecation (checkout@v4, setup-python@v5, upload-artifact@v4,
  softprops/action-gh-release@v2) — non-blocking; bump on next workflow edit.

## [6.4.1] — 2026-08-06

### Fixed
- **Windows crash risk from bare `open()` calls (F16)** — `.master.key`, `.duress.key`, and
  `.app_settings.json` are now read/written with `encoding="utf-8"` (same class as AetherTime's
  `charmap`/cp1252 crash; Windows defaults to cp1252 and would throw on any non-ASCII byte).
- **Frozen data dir is now platform-aware (F16)** — `PROJECT_ROOT` for a frozen build is no longer
  `os.getcwd()`. Windows/macOS single-file executables keep `data/` next to the exe (deterministic
  regardless of how it's launched); Linux AppImage uses `~/.local/share/AetherVault` (stable path
  vs the ephemeral `/tmp/.mount_*`); unwritable app dirs (e.g. `/Applications`, `Program Files`)
  fall back to a per-user path. Mirrors AetherTime's proven data-dir fix.
- Portable-mode marker write now uses `encoding="utf-8"`.

### Notes
- `os.fork()`/`os.setsid()` detach (Unix) runs before `QApplication` — safe on macOS; effectively
  a no-op on a single-file `.app`. Left unchanged.

## [6.4.0] — 2026-08-05

### Added
- **Startup integrity check (F15, P1)** — `DatabaseManager._connect()` runs `PRAGMA integrity_check`; on failure it notifies the user and auto-recovers from the most recent `.db.bak`. No backup → safe fail. 3 regression tests (suite 71 → 74).
- **PyPI publishing** — `publish-pypi.yml` builds sdist/wheel and uploads via trusted publishing on `v*` tags. Distribution name `aethervault-py` (the name `aethervault` collides with an existing PyPI package).

### Changed
- **Package restructure (C10)** — `core_logic.py` → `aethervault/core/engine.py` + `core/password.py`; `db_manager.py` → `aethervault/shared/database.py`; `CredentialEntry` → `aethervault/shared/models.py`. STRUCTURE.md canonical layout.
- **Python floor 3.10+ (F16)** — `requires-python` `>=3.9` → `>=3.10`; CI matrix dropped 3.9.
- **README** — rewritten in AetherPod format: ASCII banner, badges, demo GIF + screenshot gallery.
- **Internal docs excluded from PyPI package** — `docs/sys/` + `project_audit/` no longer ship in wheel/sdist.

### Fixed
- **Copy Password button copied the Category field** — late-binding lambda; captured with default arg. 2 regression tests.
- **`aethervault -u` for PyPI installs** — previously always ran `pip install --upgrade git+<repo>`, which fails for PyPI users. Now detects install source via `importlib.metadata`: `aethervault-py` present → `pip install --upgrade aethervault-py`; source/git installs keep the git path. Executable (exe) installs can't self-upgrade — documented in README (redownload from Releases).

### Notes
- **v6.4.0 published** — `aethervault-py` 6.4.0 live on PyPI (wheel + sdist) via trusted publishing; 4 release binaries (Linux, macOS arm64/x86_64, Windows). CI + publish workflows fixed (Qt deps, YAML heredoc bug, badge cache).

## [Unreleased] — 2026-08-05 (audit remediation F14 + F15)

### Added
- **Startup integrity check (F14, P1)** — `DatabaseManager._connect()` now runs `PRAGMA integrity_check`. On failure it notifies the user and automatically recovers from the most recent `.db.bak` backup (copy over + re-check). If no backup exists, the connection fails safely (`conn=None`) instead of crashing. 3 regression tests added (`test_recover_from_backup_when_corrupt`, `test_no_backup_fails_safely`, `test_integrity_check_passes_on_valid_db`). Suite: 71 → 74.

### Changed
- **Python floor raised to 3.10+ (F15, P3)** — `pyproject.toml` `requires-python` `>=3.9` → `>=3.10`; CI matrix dropped Python 3.9 (`ci.yml` now 3.10–3.12); USER_GUIDE system requirements updated.

## [Unreleased] — 2026-08-05 (package restructure)

### Changed
- **Package restructure to `core/` + `shared/` (C10)** — split `core_logic.py` → `aethervault/core/engine.py` (encryption, hashing, key derivation, backup/wipe, settings) + `aethervault/core/password.py` (`score_password`, `generate_strong_password`); `db_manager.py` → `aethervault/shared/database.py` (DatabaseManager); `CredentialEntry` → `aethervault/shared/models.py`. Updated all importers (GUI modules + 6 test files) and test monkeypatch targets (`aethervault.core.engine.*`). Deleted old flat modules. Matches STRUCTURE.md canonical layout. 71 tests pass; app launches.

## [Unreleased] — 2026-08-05 (template alignment)

### Fixed
- **Copy Password button copied the Category field instead of the password** — `credential_form.py` used `lambda: self.copy_requested.emit(line_edit.text(), ...)` where `line_edit` was the loop variable, which after the form loop points to the last field (`category`). The classic late-binding closure bug. Fixed by capturing with a default arg: `lambda checked, le=line_edit: ...`. Verified on real X11: clicking Copy now places the actual decrypted password on the clipboard. Added `tests/test_credential_form.py` (2 regression tests). Suite: 69 → 71.

### Changed
- **Tray + window icon** — replaced the hand-drawn "K" placeholder with the packaged `aethersol.ico` (multi-size 16-64px). Updated `app.py`, `MANIFEST.in`; removed unused `QColor`/`QPixmap`/`QPainter` imports.
- **Template alignment (Phase 1-2)** — added `aethervault/docs/sys/sessions.md`, `FUTURE_DEV_IDEAS.md`, `aethervault.txt`; copied `aethervault/project_audit/` (6 files); synced `instructions/` with the kit (`TESTING.md`, `STRUCTURE.md`, `DECISIONS.md`, `LICENSING.md`, `EULA.md`, `packaging.md`, `ASSETS.md`); updated `AGENTS.md` (correct `aethervault/` paths, session keywords, Development Workflow). `kiss/` stale venv removed.
- **Brand assets** — `aethervault.ico` deleted, `aethersol.ico` + `aethersol_logo.png` added; kit `project_kit/assets/` + `instructions/ASSETS.md` created.

## [6.3.1] — 2026-08-01

### Fixed
- **Duress password setup aborted after master prompt** — `QInputDialog.getText()` in PySide6 returns `(text, ok)` (text first, bool second). The duress setup unpacked them as `(ok, text)`, so the master field held a bool and `verify_password()` raised `AttributeError`, silently stopping the flow before the duress prompt. Now the second prompt (or clear) appears correctly. Verified end-to-end with real modal dialogs; live duress wipe test + restore passed.

## [6.3.0] — 2026-08-01

### Added
- **Duress password (optional)** — if entered at the login screen, cryptographically destroys the vault and all backups (`wipe_vault()`): master/duress key files are deleted FIRST (crypto erasure), then all `.db`, `.db-wal`, `.db-shm`, `.db.bak`, `aethervault_*.db.bak`, and `.app_settings.json` are overwritten with random data and removed. After wiping it shows a fake "Invalid password" dialog and exits — indistinguishable from a failed login. Configured via Settings → Duress Password (requires the master password to set/clear). Stored as a PBKDF2 hash in `data/.duress.key`; checked before the master password with identical PBKDF2 cost so timing is indistinguishable.
- **Backup rotation** — `rotate_backups()` keeps the 5 most recent timestamped backups and prunes the rest (pre-op + manual backup paths), keeping wipe time bounded.

### Tests
- 8 new tests (`tests/test_duress.py`): duress hash roundtrip/clear/absent, backup rotation keep/prune, wipe destroys all files including keys, wipe idempotent. Suite now 69 tests. Verified live against an isolated copy of the real vault — wipe destroyed all files, real vault untouched.

## [Unreleased] — 2026-08-01 (session 19)

### Changed
- **Removed `src/` package dir** — runtime data moved from `src/data/` → root `data/` (`DATA_DIR = PROJECT_ROOT/data`). Deleted stale `aethervault/data/` (old backups + `.gitkeep`). Updated `.gitignore` (data/* entries), README, ARCHITECTURE, USER_GUIDE.

## [Unreleased] — 2026-08-01 (session 18)

### Changed
- **Entry point cleanup** — renamed `aethervault/main.py` → `aethervault/__main__.py` so the app runs via `python -m aethervault`; updated `[project.scripts]` (`aethervault.__main__:run`), `aethervault.spec`, and the global install.
- **Removed root `aethervault.py` shim** — legacy pre-package wrapper deleted; single entry point.
- **Fixed package-data bug** — `pyproject.toml` `[tool.setuptools.data-files]` pointed at non-existent `src/docs`/`src/assets`; replaced with correct `aethervault/assets/` + `aethervault/docs/` package-data globs. `MANIFEST.in` paths updated from `src/` → `aethervault/`.
- **`build_reference.py`** — fixed stale `docs/` root path → `aethervault/docs/`; regenerated `REFERENCE.md`/`.html`/`USER_GUIDE.html`.

## [Unreleased] — 2026-08-01 (session 17)

### Changed
- **Repo moved to `AetherSolDev/AetherVault`** — updated git remote and all URL references in `main.py` (upgrade/tags/releases), `README.md` (badges, release links, clone URLs), and `USER_GUIDE.md`/`.html`. Marked transfer checklist complete in `instructions/PRE_PUBLIC_CLEANUP.md`.
- Workflows (`build.yml` + `ci.yml`) already cover Linux, Windows, macOS Intel + ARM — no changes needed.

## [Unreleased] — 2026-08-01 (session 16)

### Changed
- **Unused imports removed** (F12) — `sys`/`List` in `core_logic.py`, `Any` in `db_manager.py`, `QMessageBox` in `main.py`, `json`/`QHBoxLayout`/`PORTABLE_MARKER`/`DocumentationDialog`/`DarkThemeColors`/`ThemeColors` in `gui/app.py`, `Qt` in `conflict_dialog.py`, `QHeaderView` in `credential_form.py`, `Optional`/`QPainter`/`QFont` in `credential_table.py`. AST scan confirms zero unused imports.
- **`except Exception` catch-alls narrowed** (F13) — all 22 instances replaced with specific exception types: `OSError`, `ValueError`, `TypeError`, `csv.Error`, `shutil.Error`, `sqlite3.Error`, `InvalidToken`, `RuntimeError`. Added `InvalidToken` import in `core_logic.py` and `csv` import in `gui/app.py`.
- **Re-audit** — 42/42 checklist checks pass, score back to A. 61 tests pass.

## [Unreleased] — 2026-07-30 (session 15)

### Added
- **GitHub Releases delivery** — `build.yml` builds single-file executables for Windows, Linux, and macOS (Intel + Apple Silicon) and auto-attaches them to the Release on `release: published` (`softprops/action-gh-release`). Manual runs via `workflow_dispatch` still upload workflow artifacts.
- **README quick-download table** — one-click links to the latest binaries via `/releases/latest/download/...`, plus a Build status badge.
- **First release with binaries** — `v6.2.1` published with 4 pre-built executables (Linux 86MB, Windows 54MB, macOS Intel 43MB, macOS ARM 40MB).

### Fixed
- **`create_pre_op_backup()` on fresh checkouts** — now creates the backup directory (`os.makedirs`) before `copyfile`. Previously the write to `src/data/` raised `FileNotFoundError` when that dir was absent (e.g., CI checkout), which the test error-handler lambda swallowed → `test_create_pre_op_backup_creates_file` failed on CI only.
- **`build.yml` Linux system deps** — `libgl1-mesa-glx` no longer exists on Ubuntu 24.04 runners; replaced with `libgl1` + `libxkbcommon-x11-0` and added `libxcb-icccm4` / `libxcb-keysyms1` / `libxcb-shape0` so the Qt xcb libraries bundle into the onefile.
- **macOS build matrix** — `macos-13` runner retired by GitHub (jobs queued forever); switched Intel build to `macos-15-intel`. Dropped the universal2 attempt (cffi ships no fat wheel, PyInstaller refuses single-arch deps) in favor of separate `macos-latest` (arm64) + `macos-15-intel` (x86_64) binaries.

### Changed
- **`aethervault.spec`** — removed from `.gitignore` and committed so CI builds can use it (was untracked, breaking `pyinstaller aethervault.spec` in CI).
- **Removed `safety.md`** from the repository.
- **README** — fixed broken `main.png` path (`src/assets/` → `aethervault/assets/`), corrected USER_GUIDE/REFERENCE links, removed stray `# test` footer lines.
- **Actions hygiene** — deleted 9 stale failed/cancelled workflow runs.

### CI/CD
- **`build.yml`** — matrix: `ubuntu-latest`, `windows-latest`, `macos-15-intel`, `macos-latest`; `contents: write` permission; per-OS asset names (`.exe` on Windows); release upload step.
- **`ci.yml`** — green across Python 3.9–3.12 (61 tests) after the backup-dir fix.

## [6.2.1] — 2026-07-27

### Fixed
- **Encryption key guard** — `import_from_csv()`, `execute_import()`, and `preview_import()` now raise `RuntimeError` upfront if the vault is locked (no encryption key set), instead of firing a flood of per-row error dialogs from `save_credential()` / `update_credential()`.
- **`find_and_remove_duplicates()` SQL** — simplified to a single `DELETE ... WHERE db_id NOT IN (SELECT MIN(db_id)...)` query, fixing a "SQL statements in progress" transaction error on Python 3.14.

### Added
- **Test suite expansion** — 39 new tests across `test_core_logic.py` (24 tests: encryption roundtrip, key derivation, password hashing, password generation, settings persistence) and `test_db_manager.py` (15 tests: `import_from_csv`, export, duplicate removal, backup, and encryption-key-not-set guards for all import methods).

### Changed
- **Documentation** — README tests badge 22→61, project tree paths corrected; KNOWLEDGE.md session history and test count updated; ARCHITECTURE.md paths aligned with `aethervault/` package layout.
- **`--upgrade` / `-u`** — now auto-performs the upgrade (git pull + pip install -e . for cloned repos, pip install --upgrade for pip installs) instead of printing manual instructions. Uses `subprocess.run()` with helpful status output.
- **`GIT_DISCOVERY_ACROSS_FILESYSTEM=1`** — set in subprocess environment to allow git repo discovery across filesystem mounts (FUSE, NFS, etc.).
- **Re-audit** — full alignment checklist pass: 42/42 checks, score A (unchanged). All 12 prior findings remain closed.

### CI/CD
- **`ci.yml`** — new GitHub Actions workflow runs `pytest` on push/PR to `main` across Python 3.9–3.12.
- **`build.yml`** — fixed stale `src/main.py` entry point → uses `aethervault.spec`; added Linux (`ubuntu-latest`) build target.

## [6.2.0] — 2026-07-27

### Added
- **Auto-detach from terminal** — `main.py` forks on Unix to release the terminal so users don't need `aethervault &`. `--foreground` / `-f` flag keeps terminal attached for debugging.

### Changed
- **CLI reference** updated in README and USER_GUIDE with `--foreground` flag

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

---

## Bug Tracker

# AetherVault Bug Tracker

## F16 — Windows crash risk: bare open() + frozen data dir not platform-aware

- **Status**: Fixed
- **Fixed**: 2026-08-06
- **Found**: 2026-08-06 (cross-platform audit, aligned with AetherTime)
- **Priority**: P1
- **Tags**: bug, cross-platform, windows, macos
- **Description**: Two related portability gaps found while aligning AetherVault with
  AetherTime's cross-platform hardening:
  1. **Bare `open()` calls** (no `encoding="utf-8"`) on `.master.key`, `.duress.key`, and
     `.app_settings.json` — the same class as AetherTime's `charmap`/cp1252 Windows crash. If any
     of these files ever contains a non-ASCII byte, Windows (default cp1252) would throw
     `UnicodeDecodeError`/`UnicodeEncodeError`.
  2. **Frozen `PROJECT_ROOT` was `os.getcwd()`** — on a double-clicked macOS/Windows executable,
     `cwd` is not reliably set (Finder/LaunchServices can set it to `/` or leave it undefined), so
     `DATA_DIR = PROJECT_ROOT/data` could land in an unwritable root or an ephemeral location.
     Linux AppImage `--onefile` runs from an ephemeral `/tmp/.mount_*` that can vanish on exit.
- **Root Cause**: `aethervault/core/engine.py` used `open(...)` without `encoding="utf-8"`;
  `aethervault/__init__.py` set `PROJECT_ROOT = os.getcwd()` for all frozen builds.
- **Fix**: Added `encoding="utf-8"` to all 6 text `open()` calls in `engine.py` + the portable
  marker write in `__init__.py` (binary wipe `open(path, "r+b")` unchanged — encoding is invalid
  in binary mode). Added `_frozen_data_root()` in `__init__.py`: Windows/macOS single-file exe →
  data next to the exe; Linux AppImage → `~/.local/share/AetherVault`; unwritable app dir →
  per-user fallback (mirrors AetherTime's proven pattern).
- **Files**: `aethervault/core/engine.py`, `aethervault/__init__.py`

## F15 — No startup integrity check on the vault database

- **Status**: Fixed
- **Fixed**: 2026-08-05
- **Found**: 2026-08-05 (audit)
- **Priority**: P1
- **Tags**: bug, database, security
- **Description**: AGENTS.md Critical Rules require "Run startup integrity checks with automatic recovery," but no `PRAGMA integrity_check` ran at startup or on DB connect. A corrupted DB would fail cryptically on the first query instead of at startup with a recoverable error.
- **Root Cause**: `DatabaseManager._connect()` connected and ran WAL but never verified integrity.
- **Fix**: `_connect()` now runs `PRAGMA integrity_check`. On failure it notifies the user (via `error_handler`) and auto-recovers from the most recent `.db.bak` (copy over + re-check). If no backup exists, `conn=None` so callers fail safely.
- **Tests**: `test_integrity_check_passes_on_valid_db`, `test_recover_from_backup_when_corrupt`, `test_no_backup_fails_safely` (3 tests in `test_db_manager.py`). Suite 71 → 74.
- **Files**: `aethervault/shared/database.py`, `tests/test_db_manager.py`

## F14 — Copy Password button copies the Category field's text

- **Status**: Fixed
- **Fixed**: 2026-08-05
- **Found**: 2026-08-05 (user report: "copy/paste isn't working")
- **Priority**: P0 (password copy silently failed)
- **Tags**: bug, gui, clipboard
- **Environment**: Linux/X11, PySide6
- **Description**: Clicking the "Copy" button next to the Password field copied the text of the *Category* field (or empty) instead of the password. Reproduced on real X11: clipboard ended up empty or stale while the password field visibly held the correct value.
- **Root Cause**: `credential_form.py` wired the button as `lambda: self.copy_requested.emit(line_edit.text(), "password")`, capturing the loop variable `line_edit` by reference. After the form-build loop finishes, `line_edit` is rebound to the last field created (`category`), so the click emits the wrong field's text. Classic Python late-binding closure bug.
- **Fix**: Capture with a default argument: `lambda checked, le=line_edit: self.copy_requested.emit(le.text(), "password")`.
- **Tests**: `tests/test_credential_form.py` — `test_password_copy_button_copies_password_not_last_field`, `test_password_copy_button_not_capturing_category` (2 tests, offscreen Qt). Suite 69 → 71.
- **Files**: `aethervault/gui/credential_form.py`, `tests/test_credential_form.py`

## F0 — `resource_path()` references `sys._MEIPASS` without module-level `sys` import

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, gui, packaging
- **Description**: `resource_path()` in `main_app_pyside.py:58` uses `sys._MEIPASS` to resolve bundled asset paths in PyInstaller builds, but `sys` is only imported at the `__main__` block (line 1233), not at module level. This will cause a `NameError` in frozen builds.
- **Root Cause**: `import sys` is at line 1233 (`if __name__ == "__main__"` block) instead of the top of the file.
- **Fix**: Add `import sys` to the top-level imports in `main_app_pyside.py`.
- **Files**: `main_app_pyside.py`

## F1 — `find_and_remove_duplicates()` calls backup before docstring

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, database
- **Description**: In `db_manager.py:244`, `self.create_pre_op_backup("Duplicate Removal")` is called on the line immediately after `def find_and_remove_duplicates(self):`, before the docstring and actual logic. While Python still executes this correctly (the docstring is a no-op string literal), the intent is confusing — the backup call looks like it belongs to the previous method or is misplaced.
- **Root Cause**: The `create_pre_op_backup` call was placed between the method signature and the docstring during a refactor, making the execution order non-obvious.
- **Fix**: Move `self.create_pre_op_backup("Duplicate Removal")` to after the docstring, at line ~256.
- **Files**: `db_manager.py`

## F2 — `assets/kiss_icon.ico` referenced but `assets/` directory does not exist

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, gui
- **Description**: `main_app_pyside.py:252` attempts to load an icon from `assets/kiss_icon.ico`, but no `assets/` directory exists in the project. The error is silently caught and logged to console only.
- **Root Cause**: Icon file was planned but never created/committed.
- **Fix**: Create `assets/` directory with a valid `.ico` (or `.png`) application icon, or remove the icon reference. Update `aetherlock.spec` to bundle `assets/` if not already done.
- **Files**: `assets/kiss_icon.ico` (missing), `main_app_pyside.py`, `aetherlock.spec`

## F3 — Auto-lock triggers immediately on WindowDeactivate

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, security, ui
- **Description**: `_check_focus_lock()` called `lock_application()` immediately on `WindowDeactivate`, bypassing the configured lockout timeout. Switching to another window (e.g., terminal) would lock the vault instantly regardless of the 3-minute setting.
- **Root Cause**: `eventFilter` called `_check_focus_lock()` on `WindowDeactivate`, which locked immediately if lockout was not set to "Never".
- **Fix**: Changed `WindowDeactivate` handler to call `reset_activity_timer()` instead of `_check_focus_lock()`. The configured timeout is now respected.
- **Files**: `src/gui/app.py`

## F4 — Password strength bar hidden by Email QLineEdit in grid cell

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, ui
- **Description**: The `PasswordStrengthBar` was placed at grid row 4 column 1, but the Email QLineEdit was also at row 4 column 1 (due to `enumerate` indices). The QLineEdit overwrote the progress bar, making it invisible.
- **Root Cause**: Using `enumerate` for grid rows with an extra row inserted for the strength bar caused a cell collision.
- **Fix**: Replaced `enumerate` with an independent `row` counter that increments past the strength bar row (row += 1 inside the password block).
- **Files**: `src/gui/app.py`

## F5 — File → Quit minimizes to tray instead of quitting

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, ui
- **Description**: File → Quit called `self.close()` which triggered `closeEvent` → minimize to tray. There was no way to actually quit the application from the menu.
- **Root Cause**: `closeEvent` always minimized to tray when tray icon was visible.
- **Fix**: Created `_quit_application()` that hides tray, runs cleanup, and calls `QApplication.quit()`. Both File → Quit and tray → Quit use this method.
- **Files**: `src/gui/app.py`

## F6 — Header text clipped in credential table

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, ui
- **Description**: The horizontal header text in the credential table was partially visible, with words cut off at the edges. Increasing column widths or reducing padding didn't fully resolve it.
- **Root Cause**: The QHeaderView section height was determined by content and padding, but the minimum size wasn't enough for the bold 11pt font with 4px padding.
- **Fix**: Added `horizontalHeader().setFixedHeight(50)` to force adequate header height.
- **Files**: `src/gui/app.py`

## F7 — `sectionClicked.disconnect()` RuntimeWarning on every table refresh

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, performance
- **Description**: Every call to `update_list_view()` tried to disconnect and reconnect the `sectionClicked` signal, producing a RuntimeWarning: "Failed to disconnect (None) from signal".
- **Root Cause**: Signal connection/disconnection happened in `update_list_view` (called on every credential change) instead of during table creation.
- **Fix**: Moved `h.sectionClicked.connect(self._handle_sort)` to `create_main_content` where the table is created once.
- **Files**: `src/gui/app.py`

## F8 — `create_pre_op_backup()` fails on fresh checkouts when `src/data/` is absent

- **Status**: Fixed
- **Found**: 2026-07-30
- **Fixed**: 2026-07-30
- **Tags**: bug, database, ci
- **Description**: `test_create_pre_op_backup_creates_file` failed only on CI (Python 3.9–3.12 matrix). The test called `create_pre_op_backup("TestOp")`, which copies the DB to `get_timestamped_backup_path()` — inside `src/data/`. That directory contains no tracked files (gitignored), so the CI checkout lacks it and `shutil.copyfile` raised `FileNotFoundError`. The exception was swallowed by the fixture's `error_handler` lambda (`lambda t, m: None`), so the method returned `None` and `assert result is not None` failed. Locally the dir exists (runtime `.bak` files), which is why it only reproduced on CI.
- **Root Cause**: `create_pre_op_backup()` assumed the backup directory already existed and relied on the global `DATA_DIR` path, not the instance DB path.
- **Fix**: Added `os.makedirs(os.path.dirname(backup_path), exist_ok=True)` before `shutil.copyfile` in `create_pre_op_backup()`.
- **Files**: `aethervault/db_manager.py`

---

## Development Costs

> Summary updated manually. Run `python scripts/update_cost.py` to append new sessions.

## AetherVault Project Cost

| Date | Timeline | Model | Cost |
|------|----------|-------|------|
| 2026-08-06 | 2026-07-24 (14 days) | multi-model | $2.40 |

## Cost Breakdown

| Date | Session | Model | Tokens In | Tokens Out | Cost |
|------|---------|-------|-----------|------------|------|
| 2026-07-24 | Session recall | deepseek-v4-flash | 98,723 | 18,097 | $0.04 |
| 2026-07-24 | Audit docstring coverage (@explore subagent) | deepseek-v4-flash | 34,727 | 3,778 | $0.01 |
| 2026-07-24 | Add docstrings to app.py (@general subagent) | deepseek-v4-flash | 25,118 | 15,237 | $0.01 |
| 2026-07-24 | Add docstrings to core_logic (@general subagent) | deepseek-v4-flash | 7,317 | 2,464 | $0.00 |
| 2026-07-24 | Add docstrings to db_manager (@general subagent) | deepseek-v4-flash | 7,860 | 2,007 | $0.00 |
| 2026-07-24 | Add docstrings to dialogs+theme (@general subagent) | deepseek-v4-flash | 6,009 | 2,305 | $0.00 |
| 2026-07-24 | Add docstrings to small files (@general subagent) | deepseek-v4-flash | 1,587 | 1,758 | $0.00 |
| 2026-07-25 | Recall request | deepseek-v4-flash | 22,988 | 3,831 | $0.01 |
| 2026-07-25 | Recall query | deepseek-v4-flash | 126,654 | 17,150 | $0.03 |
| 2026-08-01 | Run app audit with project_kit | deepseek-v4-flash | 172,419 | 101,844 | $0.32 |
| 2026-08-05 | Project kit vs structure gap analysis | deepseek-v4-flash | 305,168 | 89,784 | $0.21 |
| 2026-08-05 | Project kit vs structure gap analysis | deepseek-v4-flash | 932,461 | 228,694 | $0.87 |
| 2026-08-05 | Project kit vs structure gap analysis | deepseek-v4-flash | 933,794 | 229,896 | $0.88 |
| 2026-08-06 | GitHub CI rebuild failure investigation | deepseek-v4-flash | 42,711 | 3,266 | $0.01 |
| 2026-08-06 | Recall previous context | deepseek-v4-flash | 30,184 | 3,934 | $0.01 |

---

## Model Pricing Reference

```
## Model Pricing Reference (as of 2026-08-06)

> DeepSeek prices verified 2026-08-06 against api-docs.deepseek.com
> (deepseek-v4-flash: $0.14 input / $0.28 output per 1M tokens, cache hit
> $0.0028). Gemini values are from the Google Vertex AI model pricing table.

| Model | Input ($/M tokens) | Output ($/M tokens) |
|---|---|---|
| DeepSeek V4 Flash (cache miss) | $0.14 | $0.28 |
| DeepSeek V4 Flash (cache hit) | $0.0028 | $0.28 |
| DeepSeek V4 Pro (cache miss) | $0.435 | $0.87 |
| DeepSeek V4 Pro (cache hit) | $0.003625 | $0.87 |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 |
| Gemini 2.5 Flash | $0.25 | $1.00 |
| Ollama (local) | $0 (compute only) | $0 |

> ⚠️ DeepSeek announced a near-term overall API price increase — "plan your
> usage accordingly." Watch for updated pricing.

### Peak Hours
- DeepSeek peak: 9:00–12:00 & 14:00–18:00 Beijing time (UTC+8)
- Convert CT to Beijing: CT + 13 hours (CDT) or +14 (CST)

```

---

## Diagram (aethervault)

```
                                  ┌─────────────────────────────────────┐
                                  │         MasterPasswordScreen        │
                                  ├─────────────────────────────────────┤          .master.key
                                  │ Setup new master password           │◄──────── (PBKDF2 hash)
                                  │ Verify & derive encryption key      │
                                  │ Login / Lock screen                 │
                                  └─────────────┬───────────────────────┘
                                                │ on success
                                                ▼
                ┌───────────────────────────────────────────────────────────────────────────┐
                │                              PySidePWManager                              │
                │  ┌──────────────────────────────┐    ┌─────────────────────────────────┐  │
                │  │        QStackedWidget         │    │  QSystemTrayIcon               │  │
                │  │  ├─ Auth View                 │    │  ├─ Show Window                │  │
                │  │  └─ Main Content View         │    │  ├─ Lock Vault                 │  │
                │  │                               │    │  └─ Quit                       │  │
                │  └──────────────────────────────┘    └─────────────────────────────────┘  │
                │                                                                           │
                │  ┌─────────────────────────────────────────────────────────────────────┐  │
                │  │                      QSplitter (Horizontal)                        │  │
                │  │  ┌──────────────────────────────┐  ┌─────────────────────────────┐  │  │
                │  │  │      Credential List (Left)   │  │      Edit Form (Right)      │  │  │
                │  │  ├──────────────────────────────┤  ├─────────────────────────────┤  │  │
                │  │  │ Search [___________]          │  │ Title: [_______________]    │  │  │
                │  │  │ Category [▼ All]  Tag [▼ All] │  │ URL:   [_______________]    │  │  │
                │  │  │ ┌────┬──────┬─────┬──────┐   │  │ Username: [_______________] │  │  │
                │  │  │ │Title│User │ URL │Cat. │   │  │ Password: [_________] [👁] │  │  │
                │  │  │ ├────┼──────┼─────┼──────┤   │  │           [Generate] [Copy]  │  │  │
                │  │  │ │     │      │     │      │   │  │           ████████░░ 80%      │  │  │
                │  │  │ │     │      │     │      │   │  │ Email:  [_______________]    │  │  │
                │  │  │ └────┴──────┴─────┴──────┘   │  │ Phone:  [_______________]    │  │  │
                │  │  │ [Add New] [Edit] [Delete]     │  │ Address:[_______________]    │  │  │
                │  │  │                               │  │ Category:[_______________]    │  │  │
                │  │  │ Sort: click header ▲/▼       │  │ Tags:   [tag1, tag2, tag3]   │  │  │
                │  │  │ Right-click: context menu     │  │ Notes:  [B] [I] [U]         │  │  │
                │  │  │ Double-click: copy cell       │  │          [________________]  │  │  │
                │  │  │ Click category: set filter    │  │          [________________]  │  │  │
                │  │  │ Favicon: ✓ in Title column    │  │ Custom Fields:              │  │  │
                │  │  └──────────────────────────────┘  │  │ ┌───────┬──────────────┐  │  │  │
                │  │                                    │  │ │ Field │ Value        │  │  │  │
                │  │                                    │  │ ├───────┼──────────────┤  │  │  │
                │  │                                    │  │ │ API   │ abc123       │  │  │  │
                │  │                                    │  │ └───────┴──────────────┘  │  │  │
                │  │                                    │  │ [+ Add] [- Remove]        │  │  │
                │  │                                    │  │ [Save] [Cancel]           │  │  │
                │  │                                    │  └─────────────────────────────┘  │  │
                │  └─────────────────────────────────────────────────────────────────────┘  │
                └───────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                ┌───────────────────────────────────────────────────────────────────────────┐
                │                             DatabaseManager                               │
                │  ┌─────────────────────────────────────────────────────────────────────┐  │
                │  │  credentials table                                                    │  │
                │  │  db_id, title, url, username, email, password(encrypted), phone,     │  │
                │  │  address, category, notes, tags, custom_fields, parent_id,           │  │
                │  │  created_at, modified_at                                             │  │
                │  │                                                                      │  │
                │  │  ┌──────────────────────────────────────────────────────────────┐    │  │
                │  │  │  core/engine.py encrypt_data() / decrypt_data() (Fernet/AES) │    │  │
                │  │  │  PBKDF2 key derivation (480K iterations)                     │    │  │
                │  │  │  shared/models.py CredentialEntry data model                  │    │  │
                │  │  └──────────────────────────────────────────────────────────────┘    │  │
                │  └─────────────────────────────────────────────────────────────────────┘  │
                │                                                                           │
                │  ┌─────────────────────────────────────────────────────────────────────┐  │
                │  │  Tools & Features                                                    │  │
                │  │  ├─ CSV Import / Export                                              │  │
                │  │  ├─ Timestamped Auto-Backup (on save, shutdown)                      │  │
                │  │  ├─ Manual Backup (1-click, timestamped filename)                    │  │
                │  │  ├─ Password Health Report (weak/reused/short scan)                  │  │
                │  │  ├─ Fetch Favicons (Google service, cached in-memory)                │  │
                │  │  ├─ Find & Remove Duplicates (title+username match)                  │  │
                │  │  └─ Password Generator (length 8-64, char set options)               │  │
                │  └─────────────────────────────────────────────────────────────────────┘  │
                │                                                                           │
                │  ┌─────────────────────────────────────────────────────────────────────┐  │
                │  │  Configuration                                                        │  │
                │  │  ├─ Theme: Dark / Light (persistent in .app_settings.json)            │  │
                │  │  ├─ Auto-Lock: 1/3/5/10/30 min or Never                             │  │
                │  │  ├─ Clipboard: auto-clear after 15s                                 │  │
                │  │  └─ Portable Mode: data stays in app directory (.portable marker)    │  │
                │  └─────────────────────────────────────────────────────────────────────┘  │
                └───────────────────────────────────────────────────────────────────────────┘

------------------


 +------------------------------------------------------+
 | Auth["Authentication Layer"]                         |
 |                                                      |
 |                                                      |
 | +----------------------+    +----------------------+ |      +----------------------+        +----------------------+
 | |                      |    |                      | |      |                      |        |                      |
 | |     Setup Master     |    |        Login         | |      |         Auth         |        |        Config        |
 | |       Password       |    |                      | |      |                      |        |                      |
 | |                      |    |                      | |      |                      |        |                      |
 | +----------------------+    +----------------------+ |      +----------------------+        +----------------------+
 |             |                           |            |                 |                                |
 |             |                           |            |                 |                                |
 |             |                           |            |                 | +------------------------------+
 |             |                           |            |                 | |
 |             v                           v            |                 v v
 | +----------------------+    +----------------------+ |      +----------------------+
 | |                      |    |                      | |      |                      |
 | |   Hash with PBKDF2   |    |   Verify password    | |      |          UI          |
 | |                      |    |                      | |      |                      |
 | +----------------------+    +----------------------+ |      +----------------------+
 |             |                           |            |                  |
 |             |                           |            |                  |
 |             |                           |            |                  +---------------+
 |             |                           |            |                  |               |
 |             v                           v            |                  v               |
 | +----------------------+    +----------------------+ |      +----------------------+    |
 | |                      |    |                      | |      |                      |    |
 | |    Store hash in     |    |  Derive encryption   | |      |       Filters        |    |
 | |     .master.key      |    |         key          | |      |                      |    |
 | |                      |    |                      | |      |                      |    |
 | +----------------------+    +----------------------+ |      +----------------------+    |
 |                                                      |                 |                |
 +------------------------------------------------------------------------|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------+
 | UI["PySide6 GUI"]                                                      | +--------------+                                                                                                                                                    |
 |                                                                        | |                                                                                                                                                                   |
 |                                                                        v v                                                                                                                                                                   |
 | +----------------------+    +----------------------+        +----------------------+                                                                                                                                                         |
 | |                      |    |                      |        |                      |                                                                                                                                                         |
 | |    QStackedWidget    |    |   System Tray Icon   |        |         Data         |                                                                                                                                                         |
 | |                      |    |                      |        |                      |                                                                                                                                                         |
 | +----------------------+    +----------------------+        +----------------------+                                                                                                                                                         |
 |             |                           |                                                                                                                                                                                                    |
 |             |                           |                                                                                                                                                                                                    |
 |             +---------------------------|-------------------------------+                                                                                                                                                                    |
 |             |                           |                               |                                                                                                                                                                    |
 |             |                           |                               |                                                                                                                                                                    |
 |             |                           |                               |                                                                                                                                                                    |
 |             |                           |                               |                                                                                                                                                                    |
 |             |                           |---------------------------------------------------------------+                                                                                                                                    |
 |             |                           |                               |                               |                                                                                                                                    |
 |             |                           |                               |                               |                                                                                                                                    |
 |             |                           |                               |                               |                                                                                                                                    |
 |             |                           |                               |                               |                                                                                                                                    |
 |             |                           +-----------------------------------------------------------------------------------------------+                                                                                                    |
 |             |                           |                               |                               |                               |                                                                                                    |
 |             |                           |                               |                               |                               |                                                                                                    |
 |             |                           |                               |                               |                               |                                                                                                    |
 |             |                           |                               |                               |                               |                                                                                                    |
 |             |                           |                               |                               |                               |                                                                                                    |
 |             |                           |                               |                               |                               |                                                                                                    |
 |             v                           v                               v                               v                               v                                                                                                    |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+        +----------------------+                                                                                         |
 | |                      |    |                      |        |                      |        |                      |        |                      |                                                                                         |
 | |      Auth View       |    |  Main Content View   |        |      Lock Vault      |        |     Show Window      |        |         Quit         |                                                                                         |
 | |                      |    |                      |        |                      |        |                      |        |                      |                                                                                         |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+        +----------------------+                                                                                         |
 |                                         |                                                                                                                                                                                                    |
 |             +---------------------------+                                                                                                                                                                                                    |
 |             v                                                                                                                                                                                                                                |
 | +----------------------+                                                                                                                                                                                                                     |
 | |                      |                                                                                                                                                                                                                     |
 | |      QSplitter       |                                                                                                                                                                                                                     |
 | |                      |                                                                                                                                                                                                                     |
 | +----------------------+                                                                                                                                                                                                                     |
 |             |                                                                                                                                                                                                                                |
 |             +---------------------------+                                                                                                                                                                                                    |
 |             v                           v                                                                                                                                                                                                    |
 | +----------------------+    +----------------------+                                                                                                                                                                                         |
 | |                      |    |                      |                                                                                                                                                                                         |
 | |   Credential List    |    |      Edit Form       |                                                                                                                                                                                         |
 | |                      |    |                      |                                                                                                                                                                                         |
 | +----------------------+    +----------------------+    +-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+            |
 |             |                           |               |                                                                                                                                                                       |            |
 |             |---------------+           +---------------+---------------------------------------------------------------------------------------------------------------+                                                       |            |
 |             |               |           |                                                                                                                               |                                                       |            |
 |             |               |           |                                                                                                                               |                                                       |            |
 |             |-------------+ |           |-----------------------------------------------------------------------------------------------+                               |                                                       |            |
 |             |             | |           |                                                                                               |                               |                                                       |            |
 |             |             | |           |                                                                                               |                               |                                                       |            |
 |             +----------+  | |           |                                                                                               |                               |                                                       |            |
 |             |          |  | |           |                                                                                               |                               |                                                       |            |
 |             |          |  | |           |                                                                                               |                               |                                                       |            |
 |             |          |  | |           |                                                                                               |                               |                                                       |            |
 |             |          |  | |           |                                                                                               |                               |                                                       |            |
 |             |          |  | |           |                                                                                               |                               |                                                       |            |
 |             |          |  | |           +-----------------------------------------------------------------------------------------------------------------------------------------------------------+                           |            |
 |             |          |  | |                                                                                                           |                               |                           |                           |            |
 |             |          |  | |                                                                                                           |                               |                           |                           |            |
 |             |          |  +---------------------------------------------+                                                               |                               |                           |                           |            |
 |             |          |    |                                           |                                                               |                               |                           |                           |            |
 |             |          |    |                                           |                                                               |                               |                           |                           |            |
 |             |          +--------------------------------------------------------------------------------+                               |                               |                           |                           |            |
 |             v                           v                               v                               v                               v                               v                           v                           v            |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+        +----------------------+        +----------------------+    +----------------------+    +----------------------+ |
 | |                      |    |                      |        |                      |        |                      |        |                      |        |                      |    |                      |    |                      | |
 | |     Sort Toggle      |    |     Context Menu     |        |    Favicon Icons     |        |  Double-Click Copy   |        |  Password Generator  |        |   Rich Text Notes    |    |    Custom Fields     |    |      Tags Field      | |
 | |                      |    |                      |        |                      |        |                      |        |                      |        |                      |    |                      |    |                      | |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+        +----------------------+        +----------------------+    +----------------------+    +----------------------+ |
 |                                                                                                                                                                                                                                              |
 +----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+




 +------------------------------------------------------------------------------------------------------------------------------------------------------+
 | UI2["Filters & Tools"]                                                                                                                               |
 |                                                                                                                                                      |
 |                                                                                                                                                      |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+        +----------------------+ |
 | |                      |    |                      |        |                      |        |                      |        |                      | |
 | |      Search Bar      |    |   Category Filter    |        |      Tag Filter      |        |   Password Health    |        |    Fetch Favicons    | |
 | |                      |    |                      |        |                      |        |        Report        |        |                      | |
 | |                      |    |                      |        |                      |        |                      |        |                      | |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+        +----------------------+ |
 |                                                                                                                                                      |
 +------------------------------------------------------------------------------------------------------------------------------------------------------+




 +--------------------------------------------------------------------------------------+
 | Config["Configuration"]                                                              |
 |                                                                                      |
 |                                                                                      |
 | +----------------------+    +----------------------+        +----------------------+ |
 | |                      |    |                      |        |                      | |
 | |    Portable Mode     |    |   Theme Dark/Light   |        |   Auto-Lock Timer    | |
 | |                      |    |                      |        |                      | |
 | +----------------------+    +----------------------+        +----------------------+ |
 |                                                                                      |
 +--------------------------------------------------------------------------------------+




 +----------------------------------------------------------------------------------------------------------------------+
 | Data["Data Layer"]                                                                                                   |
 |                                                                                                                      |
 |                                                                                                                      |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+ |
 | |                      |    |                      |        |                      |        |                      | |
 | |   SQLite Database    |    |  credentials table   |        |  CSV Import/Export   |        |     Auto Backup      | |
 | |                      |    |                      |        |                      |        |                      | |
 | +----------------------+    +----------------------+        +----------------------+        +----------------------+ |
 |                                         |                                                                            |
 |                                         +-------------------------------+                                            |
 |                                         |                               |                                            |
 |                                         |                               |                                            |
 |             +---------------------------|                               |                                            |
 |             v                           v                               v                                            |
 | +----------------------+    +----------------------+        +----------------------+                                 |
 | |                      |    |                      |        |                      |                                 |
 | |      tags TEXT       |    |  custom_fields TEXT  |        |  AES-256 encrypted   |                                 |
 | |                      |    |                      |        |       password       |                                 |
 | |                      |    |                      |        |                      |                                 |
 | +----------------------+    +----------------------+        +----------------------+                                 |
 |                                                                                                                      |
 +----------------------------------------------------------------------------------------------------------------------+

```mermaid
flowchart TD
    subgraph Auth["Authentication Layer"]
        A1[Setup Master Password] --> A2[Hash with PBKDF2]
        A2 --> A3[Store hash in .master.key]
        A4[Login] --> A5[Verify password]
        A5 --> A6[Derive encryption key]
    end

    subgraph UI["PySide6 GUI"]
        U1[QStackedWidget]
        U1 --> U2[Auth View]
        U1 --> U3[Main Content View]
        U3 --> U4[QSplitter]
        U4 --> U5[Credential List]
        U4 --> U6[Edit Form]
        U6 --> U7[Password Generator]
        U6 --> U8[Rich Text Notes]
        U6 --> U9[Custom Fields]
        U6 --> U10[Tags Field]
        U5 --> U11[Sort Toggle]
        U5 --> U12[Context Menu]
        U5 --> U13[Favicon Icons]
        U5 --> U14[Double-Click Copy]
        U15[System Tray Icon]
        U15 --> U16[Lock Vault]
        U15 --> U17[Show Window]
        U15 --> U18[Quit]
    end

    subgraph UI2["Filters & Tools"]
        F1[Search Bar]
        F2[Category Filter]
        F3[Tag Filter]
        F4[Password Health Report]
        F5[Fetch Favicons]
    end

    subgraph Config["Configuration"]
        P1[Portable Mode]
        P2[Theme Dark/Light]
        P3[Auto-Lock Timer]
    end

    subgraph Data["Data Layer"]
        D1[SQLite Database]
        D2[credentials table]
        D2 --> D3[tags TEXT]
        D2 --> D4[custom_fields TEXT]
        D2 --> D5[AES-256 encrypted password]
        D6[CSV Import/Export]
        D7[Auto Backup]
    end

    Auth --> UI
    UI --> Filters
    Filters --> Data
    UI --> Data
    Config --> UI
```


          +-------------------------------------+
          |           PySidePWManager           |
          +-------------------------------------+
          | -QStackedWidget stacked_widget      |
          | -DatabaseManager db_manager         |
          | -credentials: List[CredentialEntry] |
          | -_favicon_cache: dict               |
          | -sort_column, sort_order            |
          +-------------------------------------+
          | +check_setup_state()                |
          | +attempt_login()                    |
          | +save_credential()                  |
          | +delete_credential()                |
          | +handle_export()                    |
          | +handle_import()                    |
          | +lock_application()                 |
          | +show_password_health()             |
          | +_fetch_favicons()                  |
          | +_handle_sort()                     |
          | +_table_context_menu()              |
          | +_table_cell_double_clicked()       |
          | +_table_cell_clicked()              |
          +-------------------------------------+
                             |
                             |
                             |
                             >
             +-------------------------------+
             |        DatabaseManager        |
             +-------------------------------+
             | -conn: sqlite3.Connection     |
             | -encryption_key: bytes        |
             +-------------------------------+
             | +load_all_credentials()       |
             | +save_credential()            |
             | +update_credential()          |
             | +delete_credential()          |
             | +export_to_csv()              |
             | +import_from_csv()            |
             | +find_and_remove_duplicates() |
             +-------------------------------+
                            | :
                    |-------- :
                    |         :
                    >         ............encrypt/decrypt
  +----------------------------------+            :
  |         CredentialEntry          |            :
  +----------------------------------+            :
  | +db_id, title, url, username     |            >
  | +email, password, phone, address |    +--------------+
  | +category, notes, tags           |    | core/engine |
  | +custom_fields, parent_id        |    +-------------+
  | +created_at, modified_at         |
  +----------------------------------+
  | +to_dict()                       |
  +----------------------------------+

```mermaid
classDiagram
    class PySidePWManager {
        -QStackedWidget stacked_widget
        -DatabaseManager db_manager
        -credentials: List[CredentialEntry]
        -_favicon_cache: dict
        -sort_column, sort_order
        +check_setup_state()
        +attempt_login()
        +save_credential()
        +delete_credential()
        +handle_export()
        +handle_import()
        +lock_application()
        +show_password_health()
        +_fetch_favicons()
        +_handle_sort()
        +_table_context_menu()
        +_table_cell_double_clicked()
        +_table_cell_clicked()
    }

    class DatabaseManager {
        -conn: sqlite3.Connection
        -encryption_key: bytes
        +load_all_credentials()
        +save_credential()
        +update_credential()
        +delete_credential()
        +export_to_csv()
        +import_from_csv()
        +find_and_remove_duplicates()
    }

    class CredentialEntry {
        +db_id, title, url, username
        +email, password, phone, address
        +category, notes, tags
        +custom_fields, parent_id
        +created_at, modified_at
        +to_dict()
    }

    PySidePWManager --> DatabaseManager
    DatabaseManager --> CredentialEntry
    DatabaseManager ..> core/engine : encrypt/decrypt
```

## CI/CD Pipeline

```mermaid
flowchart TD
    GIT[Push to main or Pull Request] --> CI[pytest on Python 3.10 to 3.12]
    REL[Publish GitHub Release] --> BUILD[PyInstaller single file per OS]
    MAN[Manual workflow run] --> BUILD
    CI -->|must pass| BUILD
    BUILD --> LIN[aethervault-linux-x86_64]
    BUILD --> WIN[aethervault-windows-x86_64.exe]
    BUILD --> MACA[AetherVault-arm64.dmg + AetherVault.app.zip]
    BUILD --> MACX[AetherVault-x86_64.dmg + AetherVault.app.zip]
    BUILD --> ATTACH[Attach binaries to the Release]
```

```

---

## Audit Report

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

---

## Future Dev Ideas

> This file is for the project owner only — brainstorming and notes before
> discussing with AI. No structured format required.

## Ideas

- _Add notes here_

---

## Sessions

# Session Log

Append a new entry at the top of the log at the end of every session (see
`save session` protocol in `instructions/memory.md`). This file lives in
`aethervault/docs/sys/` and is NOT tracked by git.

## 2026-08-06 — v6.4.1 release published with binaries

### Completed
- **v6.4.1 release live on GitHub** — created release at tag `v6.4.1`
  (https://github.com/AetherSolDev/AetherVault/releases/tag/v6.4.1). The tag
  existed locally but no GitHub release had been created, so `Latest` pointed at
  v6.4.0 and the F16 fixes weren't downloadable. Release now ships the 4
  binaries: `aethervault-linux-x86_64`, `aethervault-macos-arm64`,
  `aethervault-macos-x86_64`, `aethervault-windows-x86_64.exe` (auto-attached by
  `build.yml` on `release: published`). Tag commit verified = F16 fix commit
  (`8eb0f54`) before publishing.
- **Manual Build dispatch** — `gh workflow run "Build" --ref main` builds the 4
  executables as run artifacts (not attached to a release). Dispatched, all 4
  jobs green. Distinguish from CI (job name `test`, pytest on push/PR).
- **Workflow landscape clarified** — repo has 3 active workflows: CI (pytest,
  job `test`), Build (PyInstaller 4-OS executables, `release: published` +
  `workflow_dispatch`), Publish to PyPI (`v*` tags).
- **Non-blocking warning noted** — Node 20 deprecation on `actions/checkout@v4`,
  `setup-python@v5`, `upload-artifact@v4`, `softprops/action-gh-release@v2`
  (forced to Node 24). Bump to v5/v6/v5 when next editing workflows.

### In Progress
- None — session complete

### Blocked
- None

### Key Decisions
- Created release on `v6.4.1` (F16 fix commit) rather than HEAD — HEAD `e219f8f`
  is only a "Trigger CI re-run" commit with no code change. Binaries build from
  the tag's tree.
- Manual Build dispatches leave binaries as artifacts; only a Release triggers
  auto-attachment to the release page. Use a release for user-facing downloads.

### Cost
- Model(s) used: deepseek-v4-flash (off-peak)
- Tokens — input / output: (run `scripts/update_cost.py`)
- Peak or off-peak: off-peak
- $ cost this session: ~$0.02
- Project total (from COST.md): $2.40

## 2026-08-06 — Cross-platform hardening (F16), aligned with AetherTime

### Completed
- **Windows crash class eliminated (F16)** — added `encoding="utf-8"` to all 6 text `open()`
  calls in `aethervault/core/engine.py` (`.master.key`, `.duress.key`, `.app_settings.json`) +
  portable-marker write in `aethervault/__init__.py`. Windows defaults to cp1252 and crashes on
  non-ASCII bytes (AetherTime hit this exact bug).
- **Frozen data dir platform-aware (F16)** — `_frozen_data_root()` in `aethervault/__init__.py`:
  Windows/macOS single-file exe → `data/` next to the exe (deterministic, vs `os.getcwd()` which
  Finder/LaunchServices don't set reliably); Linux AppImage → `~/.local/share/AetherVault`
  (stable vs ephemeral `/tmp/.mount_*`); unwritable app dir (`/Applications`, Program Files) →
  per-user fallback. Mirrors AetherTime's proven data-dir fix. Verified all 3 branches via
  simulation.
- **Version 6.4.0 → 6.4.1** — `aethervault/__init__.py` + `pyproject.toml`.
- **`os.fork()`/`os.setsid()` detach reviewed** — runs before `QApplication`, safe on macOS,
  effectively a no-op on a single-file `.app`. Left unchanged.
- **Lessons captured in project_kit** — new `instructions/CROSS_PLATFORM.md` (timezone/`tzset`,
  `encoding='utf-8'`, frozen data dir, `os.fork` guard, platform table), `pyproject.toml`
  template, `new_project.md` + `packaging.md` cross-platform steps.

### In Progress
- None — session complete (code committed in AetherVault repo)

### Blocked
- None

### Key Decisions
- Data-dir policy for frozen builds: exe-adjacent on Win/macOS, per-user on Linux, per-user
  fallback if the app dir isn't writable.
- Binary `open(..., "r+b")` (wipe) correctly takes NO `encoding` — only text mode needs it.
- `os.fork()` detach stays (no change): guarded to non-Windows, before Qt init.

## 2026-08-05 — Release v6.4.0, PyPI publishing, README/GIF, upgrade fix

### Completed
- **Release v6.4.0** — integrity check, core/shared restructure, python floor 3.10, PyPI publishing, AetherPod-format README + demo GIF. Tagged + released; 4 binaries attached (Linux, macOS arm64 + x86_64, Windows).
- **PyPI live** — `aethervault-py` 6.4.0 published via trusted publishing (wheel + sdist). Fixed publish workflow YAML bug (heredoc broke parsing → moved to YAML-safe `python -c` inline). Fixed CI (Qt system deps for GUI tests). Badge cache-bust fix (GitHub cached "not found" pre-publish).
- **README/GIF** — rewrote README in AetherPod format (banner, badges, screenshots-first). Captured demo GIF at full-screen: login → vault → entries → edit (strength meter) → search → generator → **health report** (reused + too-short findings). Fixed seed key-derivation bug (used raw pw vs stored hash). Health dialog captured via `activeWindow().grab()` (main-window grab misses dialogs).
- **README format captured in project_kit** — `instructions/README_FORMAT.md` (house style, demo-GIF recipe, dialog-grab gotcha), linked from kit AGENTS.md + new_project.md.
- **`aethervault -u` PyPI-aware** — detects `aethervault-py` dist via importlib.metadata → `pip install --upgrade aethervault-py`; source/git installs keep git path. Binary/exe users must redownload (added README note).

### In Progress
- None — session complete

### Blocked
- None

### Key Decisions
- PyPI distribution name = `aethervault-py` (the name `aethervault` collides with existing `aether-vault` on PyPI)
- `-u` upgrade path branches on install source: PyPI dist / git checkout / git-URL fallback
- Standalone executables cannot self-upgrade — README documents manual redownload
- Trusted publisher claims: project `aethervault-py`, owner `AetherSolDev`, repo `AetherVault`, workflow `publish-pypi.yml`, env `pypi`

### Cost
- Model(s) used: deepseek-v4-flash (off-peak)
- Tokens — input / output: (run `scripts/update_cost.py`)
- Peak or off-peak: off-peak
- $ cost this session: (fill at save session)
- Project total (from COST.md): see COST.md

## 2026-08-05 — Kit alignment, brand assets, copy/paste bug

### Completed
- Restored `project_kit/` from NAS; compared kit vs project structure (gaps documented)
- Licensing: added "How to Decide: GPL3 vs MIT + EULA" to kit LICENSING.md; moved EULA.md → instructions/EULA.md
- Brand assets: copied `aethersol.ico` + `aethersol_logo.png` into `project_kit/assets/`; wrote `instructions/ASSETS.md`
- Phase 0: removed stale `kiss/` venv; baseline 69 tests pass

### In Progress
- Phase 1: adding missing template structure (sessions.md, FUTURE_DEV_IDEAS.md, project_audit/, instructions sync, aethervault.txt)
- Phase 1b: icon & branding (pending)
- Phase 3a/3b: copy/paste bug investigation (pending)

### Blocked
- None

### Key Decisions
- License decision note lives at TOP of LICENSING.md (per-project: MIT+EULA commercial / GPL3 open-source)
- EULA template moved to `instructions/` — the kit root keeps only MIT `LICENSE`
- Asset usage guide lives at `instructions/ASSETS.md` (discoverable from AGENTS.md + new_project.md)
- Tray icon should use the packaged `.ico`, not the hand-drawn "K" placeholder

### Cost
- Model(s) used: deepseek-v4-flash (session start)
- Tokens — input / output: (run `scripts/update_cost.py` at session end)
- Peak or off-peak: off-peak
- $ cost this session: (fill at save session)
- Project total (from COST.md): see COST.md

---

*Generated on 2026-08-06 22:06 CT by `scripts/build_reference.py`*