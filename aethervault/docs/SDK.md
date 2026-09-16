# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: docs/SDK.md
# Purpose: Reference for the headless SDK (aethervault.sdk) and CLI (aethervault.cli).

# AetherVault SDK & CLI

AetherVault ships two headless front-ends that operate on the same encrypted vault as
the desktop GUI:

- **`aethervault.sdk`** — a Python client (`Vault`) for scripts and applications.
- **`aethervault.cli`** — a command-line interface built on the SDK.

Neither imports PySide6/Qt, so both run anywhere `cryptography` is available — including
servers, CI, and **Termux on Android**.

---

## Table of Contents

1. [Installation](#installation)
2. [CLI quick start](#cli-quick-start)
3. [CLI reference](#cli-reference)
4. [Python SDK reference](#python-sdk-reference)
5. [Security notes](#security-notes)
6. [Phone / Termux](#phone--termux)
7. [Troubleshooting](#troubleshooting)

---

## Installation

The core package depends only on `cryptography`. The GUI is an optional extra.

```bash
pip install aethervault-py          # headless: SDK + CLI (no Qt)
pip install 'aethervault-py[gui]'   # desktop app (adds PySide6)
```

From a source checkout:

```bash
pip install -e .          # headless
pip install -e '.[gui]'   # with the desktop GUI
```

You can always run the CLI as a module without the console script:

```bash
python -m aethervault.cli --help
```

---

## CLI quick start

```bash
# Create a vault in the default app data dir, then add an entry
aethervault-cli init
aethervault-cli add --title GitHub --username octocat --generate 24 --tags dev

# List, search, and pull a single field for scripting
aethervault-cli list
aethervault-cli search github --json
aethervault-cli show 1 --field password
```

The master password is read from `--master-password-stdin`, the
`AETHERVAULT_MASTER_PASSWORD` environment variable, or an interactive prompt (in that
order).

---

## CLI reference

### Global options

| Option | Description |
|--------|-------------|
| `--vault-dir DIR` | Directory holding `aethervault.db` + `.master.key` (default: the app data dir) |
| `--db PATH` | Explicit database path (overrides `--vault-dir`) |
| `--key PATH` | Explicit master-key path (overrides `--vault-dir`) |
| `--master-password-stdin` | Read the master password from stdin |
| `--version`, `-v` | Print the version and exit |

### Commands

| Command | Description |
|---------|-------------|
| `init` | Create a new vault (prompts for a master password) |
| `list [--category C] [--tag T] [--json] [--compact] [--show-password]` | List all entries |
| `search QUERY [--category C] [--tag T] [--json] [--compact] [--show-password]` | Substring search |
| `show ID [--field FIELD] [--json] [--show-password]` | Show one entry (or one raw field) |
| `add --title T [--password P \| --generate [LEN]] [fields...] [--json]` | Add an entry |
| `update ID [fields...] [--password P \| --generate [LEN]] [--json]` | Update fields on an entry |
| `delete ID [--yes]` | Delete an entry |
| `totp ID [--json]` | Print the current TOTP code for an entry |
| `sync` | Pull + merge + push with the configured relay |
| `sync-setup --server URL --enroll-secret S` | Create the relay vault + enroll this device (first device) |
| `sync-enroll --server URL --enroll-secret S` | Enroll this device into an existing relay vault |
| `sync-devices` | List devices enrolled on the relay |
| `sync-revoke DEVICE_ID` | Revoke a device on the relay |
| `export PATH` | Export all entries to CSV |
| `import PATH` | Import entries from CSV |
| `backup` | Create a timestamped backup beside the vault |

`fields...` are any of: `--url --username --email --phone --address --category --notes
--tags --custom_fields --totp-secret --recovery-codes`.

> **Narrow terminals (phones).** `list`/`search` auto-switch between a table (wide) and a
> one-line-per-entry compact view (narrow, under 72 columns) using the terminal width
> (`$COLUMNS`). Force either with `--compact` (or `--json` for scripts). This makes the CLI
> readable in a portrait Termux window as well as a landscape desktop terminal.

> `--totp-secret` accepts either a bare base32 secret or a full `otpauth://` URI
> (non-default `digits`/`period`/`algorithm` are honoured). TOTP secrets and recovery
> codes are masked in output unless `--show-password` is given, and are never written to
> CSV exports.

### Examples

```bash
# Add with a generated password and read it back
aethervault-cli add --title AWS --generate 32
aethervault-cli show 2 --field password

# Machine-readable output
aethervault-cli list --json | jq '.[].title'

# Work on a synced vault folder (e.g. on a phone)
aethervault-cli --vault-dir ~/storage/shared/AetherVault list

# Add a TOTP secret and print the current 2FA code
aethervault-cli add --title GitHub --password '…' --totp-secret JBSWY3DPEHPK3PXP
aethervault-cli totp 1

# Non-interactive master password (CI)
AETHERVAULT_MASTER_PASSWORD=… aethervault-cli list --json
```

Passwords are masked in output by default. `show --field password` prints the raw value;
`--show-password` reveals the password column in `list`/`search`/`show`.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (bad password, missing entry, I/O failure) |
| `2` | Usage error (no command given) |
| `130` | Interrupted (Ctrl-C) |

---

## Python SDK reference

```python
from aethervault.sdk import Vault

with Vault().unlock("master-password") as vault:
    for entry in vault.search("github"):
        print(entry.title, entry.username)
```

`Vault` opens the same on-disk vault as the desktop app
(`data/aethervault.db` + `data/.master.key`). Pass `db_path` / `key_file` to target a
different vault.

### Lifecycle

| Method | Description |
|--------|-------------|
| `Vault(db_path=None, key_file=None)` | Point at a vault (defaults to the app data dir) |
| `Vault.create(password, db_path=None, key_file=None)` | Create a new vault; returns it unlocked |
| `unlock(password)` | Verify the password and open the vault; returns `self` |
| `lock()` | Close the connection and drop the derived key |
| `with Vault(...) as vault:` | Locks automatically on exit |
| `is_locked` | `True` when no usable connection is open |

### Reads

| Method | Returns |
|--------|---------|
| `list_entries()` | `List[CredentialEntry]`, sorted by title |
| `search(query)` | Entries matching `query` (case-insensitive substring across title/url/username/email/category/tags/notes) |
| `get(db_id)` | The entry with `db_id` |
| `find(title=None, username=None)` | First exact (case-insensitive) match, or `None` |
| `totp_code(db_id)` | Current RFC 6238 TOTP code for an entry (raises `VaultError` if none) |

### Writes

| Method | Description |
|--------|-------------|
| `add(**fields)` | Insert a new entry (`title` required); returns the new `db_id` |
| `update(db_id, **fields)` | Apply the given fields; returns the updated entry |
| `delete(db_id)` | Delete the entry |

### Maintenance

| Method | Description |
|--------|-------------|
| `backup()` | Create a timestamped backup beside the vault; returns its path |
| `export_csv(path)` | Export all entries to CSV; returns the row count |
| `import_csv(path)` | Import entries from CSV; returns the count inserted |
| `sync(server_url, token="", device_id="")` | Pull-merge-push with the configured relay; returns `{"pulled", "pushed", "server_rev"}` |
| `setup_sync(relay_url, enroll_secret, device_name="")` | Create the relay vault + enroll this device |
| `enroll_sync(relay_url, enroll_secret, device_name="")` | Enroll this device into an existing relay vault |
| `sync_devices()` / `sync_revoke(device_id)` | List / revoke relay devices |

### Exceptions

All SDK errors derive from `VaultError`:

| Exception | Raised when |
|-----------|-------------|
| `VaultNotFoundError` | The master key file does not exist |
| `AuthenticationError` | The master password is missing or wrong |
| `VaultLockedError` | A read/write is attempted on a locked vault |
| `EntryNotFoundError` | The requested `db_id` does not exist |
| `VaultError` | Base class (unknown field, bad backup, I/O failure, …) |

### Entry fields

`CredentialEntry` exposes: `db_id`, `title`, `url`, `username`, `email`, `password`,
`phone`, `address`, `category`, `notes`, `tags`, `custom_fields`, `totp_secret`,
`recovery_codes`, `parent_id`, `created_at`, `modified_at`, `time_last_used`,
`time_password_changed`, plus `to_dict()`.

---

## Security notes

- **Encryption is unchanged.** Passwords (and TOTP secrets) are encrypted at rest with
  AES-256/Fernet; the key is derived from the stored master-password hash exactly as the
  GUI does. Plaintext is only held in memory while a `Vault` is unlocked.
- **Duress is local-only.** The CLI honours the duress password by default: it wipes **only
  that vault's local files**, returns the same `Invalid master password` error, and exits. It
  never syncs, so the hub and every other device are unaffected. Disable it for automation
  with `--no-duress` (or `Vault.unlock(..., allow_duress_wipe=False)`, the SDK default).
- **CSV export is plaintext.** `export`/`export_csv` write decrypted passwords. Treat the
  output file as sensitive and delete it when done.
- **Keep the master key file safe.** `data/.master.key` stores the master-password hash;
  deleting it is a permanent lockout.
- **Backups are encrypted.** `.db.bak` files are copies of the encrypted database and are
  written beside the vault.

---

## Phone / Termux

The headless install works on Android via [Termux](https://termux.dev/):

```bash
pkg install python
pip install aethervault-py
aethervault-cli --help
```

Point the CLI at a vault you sync to shared storage:

```bash
aethervault-cli --vault-dir ~/storage/shared/AetherVault list
```

> On Termux, `cryptography` is usually available as a prebuilt package
> (`pkg install python-cryptography`) — install that first if `pip` tries to build it.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `AetherVault GUI requires PySide6…` | You ran `aethervault` on a headless install. Use `aethervault-cli`, or install the GUI extra: `pip install 'aethervault-py[gui]'`. |
| `error: Invalid master password.` | Wrong password. (If you set a duress password, the SDK/CLI will also reject it — by design.) |
| `error: Vault is locked.` | Call `unlock()` first (or use the context manager). |
| `error: No master key file at …` | The vault doesn't exist at that path. Run `init`, or fix `--vault-dir`. |
| Backups appearing in an unexpected folder | Fixed in v6.7.x (F20): backups are written **beside** the vault. Ensure you're on a current version. |
| `No module named 'PySide6'` when importing the GUI | Expected on a headless install; use the SDK/CLI or install the `gui` extra. |
