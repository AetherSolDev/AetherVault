# Created: 2026-07-24
# Last Edited: 2026-08-05 16:08 CT (America/Chicago)
# Path: docs/USER_GUIDE.md
# Purpose: User-facing handbook for AetherVault.

# AetherVault — User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Features](#features)
5. [Configuration](#configuration)
6. [Data Management](#data-management)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Getting Started

AetherVault is a portable, local password vault that stores your credentials in an encrypted SQLite database. All passwords are encrypted with AES-256 using a key derived from your master password. The application runs on Windows, Linux, and macOS.

### Key Benefits
- **Portable** — single file database, easy to back up and move
- **Secure** — AES-256 encryption, PBKDF2 key derivation, auto-lock on inactivity
- **Self-contained** — no cloud, no servers, no subscriptions

## Installation

### System Requirements
- **OS**: Windows 10+, Linux (any modern distro), macOS 12+
- **Python**: 3.10+
- **Dependencies**: PySide6, cryptography

### Setup from Source

```bash
git clone https://github.com/AetherSolDev/AetherVault.git
cd AetherVault
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
aethervault
```

### CLI Reference

| Command | Description |
|---------|-------------|
| `aethervault` | Launch GUI (auto-detaches from terminal on Unix) |
| `aethervault --version` | Show installed version |
| `aethervault --debug` | Launch with debug logging to terminal |
| `aethervault --upgrade` / `-u` | Check for updates and auto-upgrade via git pull or pip |
| `aethervault --foreground` / `-f` | Keep terminal attached (for debugging) |

### Standalone Executable
A pre-built executable is available (see Releases). No Python installation required.

## Quick Start

### First Run (Setting Up)

1. Launch the application.
2. You will be greeted with the **Setup Master Password** screen.
3. Enter a strong master password (minimum 8 characters).
4. Click **Set Master Password**.
5. You will be redirected to the login screen. Enter your new password to unlock the vault.

### Daily Use

1. Launch the application.
2. Enter your master password and click **Login**.
3. The main interface shows your credential list (left) and the edit form (right).
4. Click **Add New** to create a new entry, or select an existing entry to view/edit.

## Features

### Credential Management
- Add, edit, and delete credential entries
- Fields: Title, URL, Username, Email, Password, Phone, Address, Category, Notes
- Search/filter by title, username, URL, category, or notes

### Strong Password Generator
- Configurable length (8–64 characters)
- Toggle character sets: lowercase, uppercase, digits, symbols
- One-click "Use Password" inserts into the form

### Auto-Lock Security
- Configurable inactivity timeout (1, 3, 5, 10, 30 minutes, or Never)
- Application locks automatically after inactivity
- Clipboard is cleared on lock

### Clipboard Security
- Copy buttons for password, username, and URL
- Clipboard auto-clears after 15 seconds
- Clipboard cleared on application lock

### Data Management
- **Auto-Backup**: Automatic backup on save and application shutdown
- **Manual Backup**: `File > Backup Vault`
- **Restore**: `File > Restore Vault` — select a `.db` backup file
- **Export**: `File > Export Vault (CSV)` — unencrypted plain text
- **Import**: `File > Import Vault (CSV)` — add/update from CSV

### Duplicate Removal
- `Tools > Find and Remove Duplicates`
- Removes entries with duplicate Title + Username (keeps oldest)
- Creates a timestamped backup before removal for safety

## Configuration

### Auto-Lock Settings
- Access via `Settings > Auto-Lock` menu
- Options: After 1, 3, 5, 10, 30 minutes, or Never
- Setting persists across sessions in `.app_settings.json`

### Duress Password (optional)
- Configured via `Settings > Duress Password...` (requires your master password)
- If the duress password is entered at the login screen, the vault **and all
  backups are permanently destroyed** and the app exits.
- From an observer's point of view it looks like a normal failed login.
- **Warning:** there is no recovery — data is gone for good. Use only under
  physical coercion.

### Data File Locations
All files are stored in the application directory:

| File | Purpose |
|------|---------|
| `data/aethervault.db` | Encrypted vault (SQLite) |
| `data/aethervault.db.bak` | Auto-generated backup files |
| `data/.master.key` | Master password hash (PBKDF2) |
| `data/.duress.key` | Duress password hash (PBKDF2, optional) |
| `data/.app_settings.json` | Application settings (unencrypted) |

## Troubleshooting

### "Icon file not found" warning in console
The app icon is optional. The application will run fine without it. To resolve, place an icon file in an `assets/` directory next to the executable.

### Can't open the vault after restore
Restore requires the same master password that was used when the backup was created. If you've changed your master password since the backup, the old backup won't work.

### App locks too quickly / too slowly
Adjust the auto-lock timeout in `Settings > Auto-Lock`. The default is 3 minutes.

## FAQ

- **Can I recover a forgotten master password?** No. The master password is not stored; only a one-way hash is saved. Without the original password, your vault is permanently inaccessible.
- **Is my data secure?** Yes. All passwords are encrypted with AES-256 (Fernet). The encryption key is derived from your master password using PBKDF2 with 600,000 iterations.
- **Can I use the same database on multiple computers?** Yes. Copy the `data/aethervault.db` file to another computer with the application installed. Use the same master password to unlock it.
- **How do I migrate from another password manager?** Export your data to CSV and import it via `File > Import Vault (CSV)`. The CSV must have columns: title, username, password, url, email, phone, address, category, notes.
