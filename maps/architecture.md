# Created: 2026-08-05
# Last Edited: 2026-08-05 15:56 CT (America/Chicago)
# Path: maps/architecture.md
# Purpose: Directory tree and component responsibilities — the source-of-truth architecture map.

# Architecture Map

> Maps are the source of truth. If code contradicts this map, fix the code.
> This map lives at the repo root per `project_audit/mapping_convention.md`.

## Directory Tree

```
AetherVault/
├── .github/
│   └── workflows/
│       ├── build.yml            # Cross-platform exe builds + release asset upload
│       └── ci.yml               # pytest on push/PR (Python 3.9–3.12)
├── aethervault/                 # Top-level package (named after the project)
│   ├── __init__.py            # Package init, PROJECT_ROOT, VERSION, portable mode
│   ├── __main__.py            # ENTRY POINT → python -m aethervault (--version, --debug, --upgrade, --foreground)
│   ├── core/                  # Business logic — no UI imports
│   │   ├── __init__.py
│   │   ├── engine.py          # Encryption, hashing, key derivation, backup/wipe, settings
│   │   └── password.py        # score_password, generate_strong_password
│   ├── shared/                # Cross-cutting — database + models
│   │   ├── __init__.py
│   │   ├── database.py        # DatabaseManager — SQLite CRUD, import/export, backup, WAL
│   │   └── models.py          # CredentialEntry data model
│   ├── gui/                   # UI layer — imports core/shared, never the reverse
│   │   ├── app.py             # PySidePWManager — coordinator (auth, menus, CRUD, tray, clipboard)
│   │   ├── click_to_copy_filter.py
│   │   ├── conflict_dialog.py
│   │   ├── credential_form.py
│   │   ├── credential_table.py
│   │   ├── dialogs.py
│   │   ├── password_strength.py
│   │   └── theme.py
│   ├── assets/                # aethersol.ico, aethersol_logo.png, main.png
│   └── docs/
│       ├── USER_GUIDE.md/.html
│       └── sys/               # Internal docs (gitignored, consolidated into REFERENCE.md)
├── data/                      # Runtime data (gitignored) — aethervault.db, .master.key, etc.
├── maps/                      # THIS directory — architecture maps (source of truth)
├── tests/                     # pytest suite (71 tests)
├── scripts/                   # Admin/build scripts (gitignored)
├── instructions/              # Prompt templates + examples (gitignored)
├── pyproject.toml
├── requirements.txt
├── MANIFEST.in
└── aethervault.spec           # PyInstaller build spec
```

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `aethervault/core/engine.py` | AES-256 encrypt/decrypt, PBKDF2 key derivation, password hashing/verify, backup rotation, vault wipe, settings JSON I/O, path constants |
| `aethervault/core/password.py` | Password strength scoring, cryptographically secure password generation |
| `aethervault/shared/database.py` | All SQL queries, connection mgmt (WAL), CSV import/export/conflict-resolution, pre-op backups |
| `aethervault/shared/models.py` | `CredentialEntry` data class + serialization |
| `aethervault/gui/` | User interface, event handling, clipboard mgmt, theme |
| `aethervault/__main__.py` | QApplication bootstrap, auto-detach, CLI switches |

## Key Relationships

- `gui/` imports `core/` + `shared/` (via the coordinator and widgets)
- `shared/database.py` imports `core/engine.py` (encrypt/decrypt) + `shared/models.py`
- `core/` NEVER imports `gui/` — business logic stays UI-free
- `core/engine.py` and `gui/dialogs.py` import only `aethervault` (PROJECT_ROOT constants)

## Related Docs

- Full mermaid/ASCII diagram: `aethervault/docs/sys/aethervault.mmd` + `aethervault.txt`
- Import graph: `maps/imports.mmd`
- DB schema: `maps/database.mmd`
