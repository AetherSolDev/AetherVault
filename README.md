# AetherLock

A local, portable, encrypted password vault.

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://pypi.org/project/PySide6/)
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey)]()
[![Code style: black](https://img.shields.io/badge/code%20style-PEP%208-000000.svg)]()

---

## Overview

AetherLock is a desktop application that stores your credentials in an encrypted local SQLite database. No cloud, no servers, no subscriptions — your data stays on your machine, encrypted with AES-256.

### Features

- **AES-256 encryption** via Fernet (cryptography library), key derived with PBKDF2-SHA256 (480K iterations)
- **Master password** authentication with setup/login flow
- **Credential management** — add, edit, delete, search, sort, filter
- **Password generator** — configurable length (8–64), character sets
- **Password strength meter** — real-time scoring as you type
- **Password health report** — scan for weak, reused, or short passwords
- **Category & tag filters** — dynamic dropdowns, category click-to-filter
- **Custom fields** — add key/value pairs to any entry (JSON-backed)
- **Rich text notes** — bold/italic/underline formatting toolbar
- **Favicon auto-fetch** — downloads site icons from Google's service
- **System tray** — minimize to tray, quick-lock from tray menu
- **Dark/light theme** — toggle in Settings, persistent across sessions
- **Auto-lock** — configurable 1/3/5/10/30 minutes or never
- **Clipboard auto-clear** — copied passwords clear after 15 seconds
- **One-click backup** — timestamped filenames, no confirmation dialog
- **CSV import/export** — bulk add or migrate data
- **Duplicate detection** — find and remove entries with matching title+username
- **Portable mode** — all data stays in the app directory (`.portable` marker)
- **Right-click context menu** — copy username/password, edit, delete
- **Sortable columns** — click Title/Username/Category to sort ascending/descending

## Installation

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/AetherLock.git
cd AetherLock

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python aetherlock.py
```

### Build Standalone Executable

```bash
pip install pyinstaller
pyinstaller aetherlock.spec
# Output in dist/aetherlock/
```

## Usage

1. **First launch** — Set a master password (minimum 8 characters)
2. **Login** — Enter your master password to unlock the vault
3. **Add entries** — Click "Add New" and fill in the form
4. **Generate passwords** — Click "Generate" next to the password field
5. **Copy to clipboard** — Double-click a table cell or click "Copy" buttons
6. **Organize** — Use categories and tags to group entries
7. **Backup** — File → Backup Vault (or auto-backup on save/shutdown)

## Data Storage

| File | Purpose |
|------|---------|
| `password_manager.db` | Encrypted SQLite vault |
| `.master.key` | PBKDF2 hash of master password |
| `.app_settings.json` | Theme, auto-lock, and app preferences |
| `.portable` | Marker file for portable mode |

## Security

- Passwords are **never stored in plain text** — encrypted with AES-256 via Fernet
- Master password is **never stored** — only the PBKDF2-SHA256 hash (600K iterations)
- Encryption key is derived from the master password hash (480K iterations)
- Clipboard is **auto-cleared** after 15 seconds
- Auto-lock on **inactivity** or window focus loss
- SQLite with **parameterized queries** (no SQL injection)

## Documentation

Full user guide: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
Technical reference: [`docs/sys/REFERENCE.html`](docs/sys/REFERENCE.html)

## Project Structure

```
AetherLock/
├── src/
│   ├── __init__.py          # Version, PROJECT_ROOT, portable mode
│   ├── core_logic.py        # Encryption, hashing, data model, settings
│   ├── db_manager.py        # SQLite CRUD, import/export, backup
│   ├── main.py              # Application entry point
│   └── gui/
│       ├── app.py           # Main window and UI logic
│       ├── dialogs.py       # Password generator, documentation viewer
│       └── theme.py         # Dark/light mode stylesheets
├── docs/
│   ├── USER_GUIDE.md        # User documentation
│   ├── USER_GUIDE.html      # HTML version for in-app help
│   └── sys/                 # System documentation
├── scripts/                 # Utility scripts
├── assets/                  # Application icon (optional)
├── aetherlock.py            # Application entry point
├── requirements.txt
└── aetherlock.spec         # PyInstaller build spec
```

## Tech Stack

- **Python 3.12+** — core language
- **PySide6 (Qt)** — GUI framework
- **SQLite 3** — local database
- **cryptography** — Fernet AES-256 encryption
- **PBKDF2-SHA256** — key derivation (480K–600K iterations)

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

## Contributing

Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/your-username/AetherLock/issues).
