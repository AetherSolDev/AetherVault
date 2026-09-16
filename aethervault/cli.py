# Created: 2026-09-16
# Last Edited: 2026-09-16 14:11 CT (America/Chicago)
# Path: aethervault/cli.py
# Purpose: Headless command-line interface to a vault (no GUI/PySide6 dependency).

"""Command-line interface for AetherVault.

A headless front-end over :class:`aethervault.sdk.Vault` for terminals — and for
environments where the Qt GUI cannot run (e.g. Termux on Android). It never
imports PySide6, so it starts instantly and works anywhere ``cryptography`` is
available.

Run it as a module (no install needed)::

    python -m aethervault.cli list
    python -m aethervault.cli search github --json
    python -m aethervault.cli show 3 --field password

Or via the console script ``aethervault-cli`` (installed with the package).

Master-password sources, in order: ``--master-password-stdin``, the
``AETHERVAULT_MASTER_PASSWORD`` environment variable, then an interactive
``getpass`` prompt.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from aethervault import VERSION
from aethervault.core.engine import DB_PATH, MASTER_KEY_FILE
from aethervault.core.password import generate_strong_password
from aethervault.sdk import Vault, VaultError
from aethervault.shared.models import CredentialEntry

PROG = "aethervault-cli"
DEFAULT_PASSWORD_LENGTH = 18
MASTER_PASSWORD_ENV = "AETHERVAULT_MASTER_PASSWORD"

#: Credential fields exposed as ``--flag`` on ``add`` / ``update``.
_FIELD_FLAGS = (
    "title", "url", "username", "email", "phone",
    "address", "category", "notes", "tags", "custom_fields",
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _resolve_paths(args: argparse.Namespace) -> Tuple[str, str]:
    """Resolve the vault database + master key paths from CLI options."""
    db_path = args.db or DB_PATH
    key_file = args.key or MASTER_KEY_FILE
    if args.vault_dir:
        db_path = args.db or os.path.join(args.vault_dir, "aethervault.db")
        key_file = args.key or os.path.join(args.vault_dir, ".master.key")
    return db_path, key_file


def _master_password(args: argparse.Namespace) -> str:
    """Obtain the master password from stdin, the environment, or a prompt."""
    if getattr(args, "master_password_stdin", False):
        return sys.stdin.readline().rstrip("\n")
    env_value = os.environ.get(MASTER_PASSWORD_ENV)
    if env_value:
        return env_value
    return getpass.getpass("Master password: ")


def _new_master_password(args: argparse.Namespace) -> str:
    """Obtain and confirm a new master password for ``init``."""
    env_value = os.environ.get(MASTER_PASSWORD_ENV)
    if env_value:
        return env_value
    first = getpass.getpass("New master password: ")
    second = getpass.getpass("Confirm new master password: ")
    if first != second:
        raise VaultError("Passwords do not match.")
    return first


def _entry_password(args: argparse.Namespace) -> str:
    """Resolve a credential password from --generate, --password, or a prompt."""
    if args.generate is not None:
        return generate_strong_password(length=args.generate)
    if args.password is not None:
        return args.password
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise VaultError("Passwords do not match.")
    return first


def _open_vault(args: argparse.Namespace) -> Vault:
    """Open and unlock the vault described by the CLI options."""
    db_path, key_file = _resolve_paths(args)
    return Vault(db_path, key_file).unlock(_master_password(args))


def _entry_dict(entry: CredentialEntry, show_password: bool = False) -> Dict[str, Any]:
    """Serialize an entry, masking the password unless explicitly requested."""
    data = entry.to_dict()
    if not show_password and data.get("password"):
        data["password"] = "*" * 8
    return data


def _print_table(headers: List[str], rows: List[List[Any]]) -> None:
    """Print a simple fixed-width text table."""
    if not rows:
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))


def _print_entry(entry: CredentialEntry, show_password: bool = False) -> None:
    """Print a single entry as aligned ``Field: value`` lines."""
    data = _entry_dict(entry, show_password)
    for key, value in data.items():
        if value in (None, ""):
            continue
        print(f"{key.replace('_', ' ').title():<20}: {value}")


def _filter_entries(entries: List[CredentialEntry], args: argparse.Namespace) -> List[CredentialEntry]:
    """Apply ``--category`` / ``--tag`` filters to a list of entries."""
    result = entries
    if getattr(args, "category", None):
        wanted = args.category.strip().lower()
        result = [e for e in result if e.category.strip().lower() == wanted]
    if getattr(args, "tag", None):
        wanted = args.tag.strip().lower()
        result = [e for e in result if wanted in [t.strip().lower() for t in e.tags.split(",")]]
    return result


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_init(args: argparse.Namespace) -> int:
    db_path, key_file = _resolve_paths(args)
    if os.path.exists(key_file):
        raise VaultError(f"A vault already exists at {key_file}.")
    vault = Vault.create(_new_master_password(args), db_path, key_file)
    vault.lock()
    print(f"Vault created: {db_path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    with _open_vault(args) as vault:
        entries = _filter_entries(vault.list_entries(), args)
    if args.json:
        print(json.dumps([_entry_dict(e, args.show_password) for e in entries],
                         indent=2, default=str))
        return 0
    _print_table(
        ["ID", "Title", "Username", "Category", "URL"],
        [[e.db_id, e.title, e.username, e.category, e.url] for e in entries],
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    with _open_vault(args) as vault:
        entries = _filter_entries(vault.search(args.query), args)
    if args.json:
        print(json.dumps([_entry_dict(e, args.show_password) for e in entries],
                         indent=2, default=str))
        return 0
    _print_table(
        ["ID", "Title", "Username", "Category", "URL"],
        [[e.db_id, e.title, e.username, e.category, e.url] for e in entries],
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    with _open_vault(args) as vault:
        entry = vault.get(args.id)
        if args.field:
            if not hasattr(entry, args.field):
                raise VaultError(f"Unknown field: {args.field}")
            value = getattr(entry, args.field)
            print(value if value is not None else "")
            return 0
        if args.json:
            print(json.dumps(_entry_dict(entry, args.show_password), indent=2, default=str))
        else:
            _print_entry(entry, args.show_password)
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    fields = {name: getattr(args, name) for name in _FIELD_FLAGS
              if getattr(args, name) is not None}
    fields["password"] = _entry_password(args)
    with _open_vault(args) as vault:
        new_id = vault.add(**fields)
    if args.json:
        print(json.dumps({"db_id": new_id}))
    else:
        print(f"Added entry {new_id}: {fields.get('title', '')}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    fields = {name: getattr(args, name) for name in _FIELD_FLAGS
              if getattr(args, name) is not None}
    if args.generate is not None:
        fields["password"] = generate_strong_password(length=args.generate)
    elif args.password is not None:
        fields["password"] = args.password
    if not fields:
        raise VaultError("No fields to update. Pass at least one field flag.")
    with _open_vault(args) as vault:
        vault.update(args.id, **fields)
    if args.json:
        print(json.dumps({"db_id": args.id, "updated": sorted(fields)}))
    else:
        print(f"Updated entry {args.id}: {', '.join(sorted(fields))}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    if not args.yes:
        if not sys.stdin.isatty():
            raise VaultError("Refusing to delete without --yes in a non-interactive shell.")
        answer = input(f"Delete entry {args.id}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return 0
    with _open_vault(args) as vault:
        vault.delete(args.id)
    print(f"Deleted entry {args.id}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    with _open_vault(args) as vault:
        count = vault.export_csv(args.path)
    print(f"Exported {count} entries to {args.path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    with _open_vault(args) as vault:
        count = vault.import_csv(args.path)
    print(f"Imported {count} entries from {args.path}")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    with _open_vault(args) as vault:
        path = vault.backup()
    if path:
        print(f"Backup written: {path}")
    else:
        print("No backup created (vault database missing?).", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

def _add_field_flags(parser: argparse.ArgumentParser, include_password: bool = True) -> None:
    parser.add_argument("--title", help="Entry title")
    parser.add_argument("--url", help="Website URL")
    parser.add_argument("--username", help="Username / login")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--phone", help="Phone number")
    parser.add_argument("--address", help="Address")
    parser.add_argument("--category", help="Category / folder")
    parser.add_argument("--notes", help="Plain-text notes")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--custom_fields", help="Custom fields as a JSON string")
    if include_password:
        parser.add_argument("--password", help="Password (prompted if omitted)")
        parser.add_argument(
            "--generate", nargs="?", type=int, const=DEFAULT_PASSWORD_LENGTH,
            metavar="LEN", help=f"Generate a random password (default {DEFAULT_PASSWORD_LENGTH})",
        )


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--show-password", action="store_true",
                        help="Include plaintext passwords in output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="AetherVault command-line interface (headless, no GUI).",
    )
    parser.add_argument("--version", "-v", action="store_true", help="Show version and exit")
    parser.add_argument("--db", help="Path to the vault database (default: app data dir)")
    parser.add_argument("--key", help="Path to the master key file (default: app data dir)")
    parser.add_argument("--vault-dir", metavar="DIR",
                        help="Directory holding aethervault.db + .master.key")
    parser.add_argument("--master-password-stdin", action="store_true",
                        help="Read the master password from stdin")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_init = sub.add_parser("init", help="Create a new vault")
    p_init.set_defaults(func=cmd_init)

    p_list = sub.add_parser("list", help="List all entries")
    p_list.add_argument("--category", help="Filter by category")
    p_list.add_argument("--tag", help="Filter by tag")
    _add_output_flags(p_list)
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser("search", help="Search entries")
    p_search.add_argument("query", help="Case-insensitive substring query")
    p_search.add_argument("--category", help="Filter by category")
    p_search.add_argument("--tag", help="Filter by tag")
    _add_output_flags(p_search)
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", help="Show one entry")
    p_show.add_argument("id", type=int, help="Entry db_id")
    p_show.add_argument("--field", help="Print only this field's raw value")
    _add_output_flags(p_show)
    p_show.set_defaults(func=cmd_show)

    p_add = sub.add_parser("add", help="Add an entry")
    _add_field_flags(p_add)
    _add_output_flags(p_add)
    p_add.set_defaults(func=cmd_add)

    p_update = sub.add_parser("update", help="Update an entry")
    p_update.add_argument("id", type=int, help="Entry db_id")
    _add_field_flags(p_update)
    _add_output_flags(p_update)
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="Delete an entry")
    p_delete.add_argument("id", type=int, help="Entry db_id")
    p_delete.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p_delete.set_defaults(func=cmd_delete)

    p_export = sub.add_parser("export", help="Export all entries to CSV")
    p_export.add_argument("path", help="Destination CSV path")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="Import entries from CSV")
    p_import.add_argument("path", help="Source CSV path")
    p_import.set_defaults(func=cmd_import)

    p_backup = sub.add_parser("backup", help="Create a timestamped vault backup")
    p_backup.set_defaults(func=cmd_backup)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"AetherVault v{VERSION} (CLI)")
        return 0
    if not getattr(args, "command", None):
        parser.print_help()
        return 2

    try:
        return args.func(args)
    except VaultError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Aborted.", file=sys.stderr)
        return 130


def run() -> None:
    """Console-script wrapper: run :func:`main` and exit with its status."""
    sys.exit(main())


if __name__ == "__main__":
    run()
