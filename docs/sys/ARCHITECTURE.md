# Created: 2026-07-24
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Path: docs/sys/ARCHITECTURE.md
# Purpose: Architecture diagram and description for kissPWM_v6.

## Directory Structure
```
kissPWM_v6/
├── src/
│   ├── __init__.py            # Package init, PROJECT_ROOT constant
│   ├── core_logic.py          # Encryption, hashing, data model, settings
│   ├── db_manager.py          # SQLite CRUD, import/export, backup
│   ├── main.py                # Application entry point (QApplication setup)
│   └── gui/
│       ├── __init__.py
│       ├── app.py             # PySidePWManager — main window and UI logic
│       ├── dialogs.py         # PasswordGeneratorDialog, DocumentationDialog
│       └── theme.py           # Dark and light theme stylesheets
├── main_app_pyside.py         # Thin entry point (delegates to src.main.run)
├── help_doc.md                # Legacy user documentation
├── docs/
│   ├── USER_GUIDE.md          # Consolidated user documentation
│   └── sys/                   # System documentation (PLAN, ARCHITECTURE, etc.)
├── instructions/              # Prompt templates for AI workflow
├── scripts/                   # Utility scripts (build_reference, cost, etc.)
├── assets/                    # Application icon resources
├── .portable                  # Portable mode marker (created at runtime)
├── AGENTS.md                  # Agent instructions (READ ONLY)
├── kiss_pwm_v6.spec           # PyInstaller build spec
├── .gitignore
├── .repomixignore
├── requirements.txt
├── password_manager.db        # Encrypted vault (SQLite)
├── password_manager.db.bak    # Auto-backup
├── .master.key                # Master password hash (PBKDF2)
└── .app_settings.json         # App settings (lockout, theme, etc.)
```

## Architecture Layers

### 1. Data Layer (`src/core_logic.py`, `src/db_manager.py`)
- SQLite database with AES-256 encrypted credential storage
- PBKDF2 key derivation from master password (600K iterations)
- Automatic versioned backups
- CSV import/export with encryption

### 2. Business Logic (`src/gui/app.py`)
- Authentication flow (setup master password → login → encryption key derivation)
- Clipboard management with auto-clear timer (15s)
- Auto-lock on inactivity (configurable 1-30 min)
- Password generation (via dialogs.py)
- Duplicate detection and removal
- System tray icon with quick-lock and minimize-to-tray
- Portable mode detection (.portable marker file)
- Category + tag filtering with dynamic dropdowns
- Password health report (weak/reused/short scan)
- Entry tags (comma-separated) and custom fields (JSON key/value pairs)
- Sort toggle on table columns (Title, Username, Category)
- Double-click to copy, right-click context menu
- Category click-to-filter from table cells
- Favicon auto-fetch from Google service
- Rich text notes with B/I/U formatting toolbar
- One-click timestamped backup

### 3. Presentation Layer (`src/gui/app.py`, `src/gui/dialogs.py`)
- PySide6 (Qt) GUI with QStackedWidget for auth/main views
- QSplitter with credential list (left) and edit form (right)
- Menu bar: File (export/import/backup/restore), Tools (duplicates), Settings (auto-lock, theme), Help
- Dark/light theme toggle in Settings menu

## Data Flow
```
User Input → PySidePWManager (app.py) → DatabaseManager (db_manager.py) → SQLite
                                                ↓
                                        core_logic.py (AES-256 encrypt/decrypt)
```
