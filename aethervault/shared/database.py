# Created: 2026-08-05
# Last Edited: 2026-08-05 15:52 CT (America/Chicago)
# Path: aethervault/shared/database.py
# Purpose: SQLite database operations for AetherVault credential entries.

"""Database operations for AetherVault credential entries using SQLite."""

import csv
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aethervault.core.engine import (
    decrypt_data,
    derive_encryption_key,
    encrypt_data,
    get_timestamped_backup_path,
    rotate_backups,
)
from aethervault.shared.models import CredentialEntry

COLUMN_ALIASES = {
    "db_id": ["db_id", "id", "entry_id", "entry id"],
    "title": ["title", "name", "item_name", "entry_name", "site name", "login name"],
    "url": ["url", "website", "web site", "login_uri", "login url", "uri"],
    "username": ["username", "user name", "user", "login", "login id", "login_username"],
    "email": ["email", "e-mail", "mail"],
    "password": ["password", "pass", "passwd", "pwd", "login_password"],
    "phone": ["phone", "telephone", "mobile", "phone number"],
    "address": ["address", "addr"],
    "category": ["category", "folder", "group"],
    "notes": ["notes", "note", "comment", "description"],
    "tags": ["tags", "tag", "labels"],
    "custom_fields": ["custom_fields", "custom fields", "custom"],
    "parent_id": ["parent_id", "parent", "folder id"],
    "created_at": [
        "created_at", "time created", "timecreated", "creation time", "created",
    ],
    "modified_at": [
        "modified_at", "time modified", "timemodified", "modification time",
        "modified", "updated",
    ],
    "time_last_used": [
        "time_last_used", "time last used", "timelastused", "last_used",
        "last used",
    ],
    "time_password_changed": [
        "time_password_changed", "time password changed", "timepasswordchanged",
        "password changed", "pass changed",
    ],
}

_BUILT_ALIAS_MAP = {}
for canonical, aliases in COLUMN_ALIASES.items():
    for alias in aliases:
        key = alias.lower().strip()
        _BUILT_ALIAS_MAP[key] = canonical


class DatabaseManager:
    """Handles all SQLite database operations for credential entries."""

    def __init__(self, db_path: str, error_handler):
        """Initialize database connection and create table if not exists."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.error_handler = error_handler
        self.encryption_key: bytes = b""
        self._connect()
        self._create_table()

    def set_encryption_key(self, master_password_hash: str):
        """Derive and store the encryption key from the master password hash."""
        try:
            self.encryption_key = derive_encryption_key(master_password_hash)
        except ValueError as e:
            self.error_handler(
                "Encryption Error", f"Failed to derive encryption key: {e}"
            )
            self.encryption_key = b""

    def _connect(self):
        """Establish connection to the SQLite database."""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA journal_mode=WAL;")
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Could not connect to database: {e}")

    def __enter__(self):
        """Context manager entry — returns self for use in 'with' blocks."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit — close the connection if open."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def _create_table(self):
        """Create the credentials table if not present, with migration for new columns."""
        if not self.conn:
            return
        sql = """
        CREATE TABLE IF NOT EXISTS credentials (
            db_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            username TEXT,
            email TEXT,
            password TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            category TEXT,
            notes TEXT,
            tags TEXT DEFAULT '',
            custom_fields TEXT DEFAULT '',
            parent_id INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            time_last_used TEXT DEFAULT '',
            time_password_changed TEXT DEFAULT ''
        )
        """
        try:
            self.cursor.execute(sql)
            self.conn.commit()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error creating table: {e}")
        known_columns = {"tags", "custom_fields", "time_last_used", "time_password_changed"}
        for col in known_columns:
            try:
                self.cursor.execute(f"ALTER TABLE credentials ADD COLUMN {col} TEXT DEFAULT ''")
                self.conn.commit()
            except sqlite3.OperationalError:
                pass

    def load_all_credentials(self) -> List[CredentialEntry]:
        """Load and decrypt all credentials, returning a list of CredentialEntry objects."""
        if not self.conn:
            return []
        if not self.encryption_key:
            return []
        sql = "SELECT * FROM credentials ORDER BY title COLLATE NOCASE ASC"
        credentials = []
        try:
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            for row in rows:
                entry_data = dict(row)
                decrypted_password = decrypt_data(row["password"], self.encryption_key)
                entry_data["password"] = decrypted_password
                credentials.append(CredentialEntry(**entry_data))
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error loading credentials: {e}")
        except (TypeError, ValueError) as e:
            self.error_handler(
                "Decryption Error", f"Decryption failed (wrong key?): {e}"
            )
        return credentials

    def save_credential(self, entry: CredentialEntry) -> Optional[int]:
        """Encrypt and insert a new credential. Returns the new row ID or None."""
        if not self.conn:
            return None
        if not self.encryption_key:
            self.error_handler("Security Error", "Cannot save, encryption key not set.")
            return None
        entry_dict = entry.to_dict()
        entry_dict["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        entry_dict["modified_at"] = entry_dict["created_at"]
        entry_dict["password"] = encrypt_data(
            entry_dict["password"], self.encryption_key
        )
        sql = """
        INSERT INTO credentials (
            title, url, username, email, password, phone, address, category,
            notes, tags, custom_fields, parent_id, created_at, modified_at,
            time_last_used, time_password_changed
        )
        VALUES (
            :title, :url, :username, :email, :password, :phone, :address,
            :category, :notes, :tags, :custom_fields, :parent_id, :created_at,
            :modified_at, :time_last_used, :time_password_changed
        )
        """
        try:
            self.cursor.execute(sql, entry_dict)
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error saving credential: {e}")
            return None

    def update_credential(self, entry: CredentialEntry):
        """Encrypt and update an existing credential identified by db_id."""
        if not self.conn:
            return
        if not entry.db_id:
            self.error_handler(
                "Update Error", "Attempted to update entry without a database ID."
            )
            return
        if not self.encryption_key:
            self.error_handler(
                "Security Error", "Cannot update, encryption key not set."
            )
            return
        entry_dict = entry.to_dict()
        entry_dict["modified_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        entry_dict["password"] = encrypt_data(
            entry_dict["password"], self.encryption_key
        )
        sql = """
        UPDATE credentials SET
            title = :title, url = :url, username = :username, email = :email, password = :password,
            phone = :phone, address = :address, category = :category, notes = :notes,
            tags = :tags, custom_fields = :custom_fields,
            parent_id = :parent_id, modified_at = :modified_at,
            time_last_used = :time_last_used, time_password_changed = :time_password_changed
        WHERE db_id = :db_id
        """
        try:
            self.cursor.execute(sql, entry_dict)
            self.conn.commit()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error updating credential: {e}")

    def delete_credential(self, db_id: int):
        """Delete a credential from the database by its db_id."""
        if not self.conn:
            return
        sql = "DELETE FROM credentials WHERE db_id = ?"
        try:
            self.cursor.execute(sql, (db_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error deleting credential: {e}")

    def create_pre_op_backup(self, operation: str) -> Optional[str]:
        """Create a timestamped backup before a destructive operation.
        Returns the backup path or None."""
        if not os.path.exists(self.db_path):
            return None
        try:
            if self.conn:
                self.conn.close()
            backup_path = get_timestamped_backup_path()
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copyfile(self.db_path, backup_path)
            rotate_backups()
            self._connect()
            return backup_path
        except OSError as e:
            self.error_handler(
                "Backup Error", f"Failed to create pre-{operation} backup: {e}"
            )
            self._connect()
            return None

    def find_and_remove_duplicates(self) -> int:
        """
        Finds and deletes duplicate entries based on (title, username),
        keeping only the oldest entry (lowest db_id).
        Returns the number of deleted records.
        """
        if not self.conn:
            self.error_handler("Database Error", "Connection not established.")
            return 0

        self.create_pre_op_backup("Duplicate Removal")

        deleted_count = 0
        try:
            self.cursor.execute(
                """
                DELETE FROM credentials
                WHERE db_id NOT IN (
                    SELECT MIN(db_id)
                    FROM credentials
                    GROUP BY title, username
                )
            """
            )
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            return deleted_count
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Failed to remove duplicates: {e}")
            return 0

    def export_to_csv(self, file_path: str, credentials: List[CredentialEntry]) -> int:
        """Export a list of credentials to a CSV file. Returns the number of rows written."""
        if not credentials:
            self.error_handler("Export Warning", "No credentials to export.")
            return 0
        fieldnames = [
            "db_id", "title", "url", "username", "email", "password",
            "phone", "address", "category", "notes", "tags", "custom_fields",
            "parent_id", "created_at", "modified_at",
            "time_last_used", "time_password_changed",
        ]
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                count = 0
                for entry in credentials:
                    writer.writerow(entry.to_dict())
                    count += 1
            return count
        except (OSError, csv.Error, ValueError) as e:
            self.error_handler("Export Error", f"Failed to write to CSV: {e}")
            raise

    @staticmethod
    def _build_column_map(csv_headers: List[str]) -> Dict[str, str]:
        """Map CSV column headers to canonical field names using known aliases."""
        col_map = {}
        for header in csv_headers:
            normalized = header.lower().strip().replace("  ", " ")
            canonical = _BUILT_ALIAS_MAP.get(normalized)
            if canonical:
                col_map[canonical] = header
        return col_map

    def import_from_csv(self, file_path: str) -> int:
        """Import credentials from a CSV file, inserting or updating as needed.
        Handles varying column names across browsers via alias mapping.
        Returns the count of imported entries."""
        if not self.encryption_key:
            raise RuntimeError("Encryption key not set. Please unlock the vault first.")
        self.create_pre_op_backup("Import")
        imported_count = 0
        required = {"title", "password"}
        try:
            with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    self.error_handler("Import Error", "CSV file has no headers.")
                    return 0
                col_map = self._build_column_map(reader.fieldnames)
                if not required.issubset(col_map):
                    missing = required - set(col_map)
                    self.error_handler(
                        "Import Error",
                        f"CSV missing required columns: {', '.join(sorted(missing))}. "
                        f"Found headers: {', '.join(reader.fieldnames)}",
                    )
                    return 0
                for row in reader:
                    entry_data = {}
                    for canonical, header in col_map.items():
                        entry_data[canonical] = row.get(header) or ""
                    entry = CredentialEntry(**entry_data)
                    try:
                        db_id = int(entry_data.get("db_id") or 0)
                    except ValueError:
                        db_id = 0
                    entry.db_id = db_id
                    if entry.db_id and entry.db_id > 0:
                        self.update_credential(entry)
                        imported_count += 1
                    else:
                        if self.save_credential(entry) is not None:
                            imported_count += 1
            return imported_count
        except FileNotFoundError:
            self.error_handler("Import Error", f"File not found: {file_path}")
            raise
        except (OSError, csv.Error, ValueError) as e:
            self.error_handler("Import Error", f"Failed to read/parse CSV: {e}")
            raise

    def preview_import(self, file_path: str) -> Dict:
        """Scan a CSV and identify conflicts with existing (title, username) pairs.
        Returns {'total_rows': int, 'conflicts': list, 'non_conflict_count': int}.
        Each conflict: {'vault': dict, 'import': dict} with decrypted vault data."""
        if not self.encryption_key:
            raise RuntimeError("Encryption key not set. Please unlock the vault first.")
        existing = self.load_all_credentials()
        existing_by_key = {}
        for e in existing:
            key = (e.title.lower().strip(), e.username.lower().strip())
            existing_by_key[key] = e

        required = {"title", "password"}
        conflicts = []
        non_conflict_count = 0
        try:
            with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    return {"total_rows": 0, "conflicts": [], "non_conflict_count": 0}
                col_map = self._build_column_map(reader.fieldnames)
                if not required.issubset(col_map):
                    return {"total_rows": 0, "conflicts": [], "non_conflict_count": 0}
                for row in reader:
                    entry_data = {}
                    for canonical, header in col_map.items():
                        entry_data[canonical] = row.get(header) or ""
                    key = (
                        entry_data.get("title", "").lower().strip(),
                        entry_data.get("username", "").lower().strip(),
                    )
                    if key in existing_by_key:
                        conflicts.append({
                            "vault": existing_by_key[key].to_dict(),
                            "import": entry_data,
                        })
                    else:
                        non_conflict_count += 1
            return {
                "total_rows": non_conflict_count + len(conflicts),
                "conflicts": conflicts,
                "non_conflict_count": non_conflict_count,
            }
        except FileNotFoundError:
            self.error_handler("Import Error", f"File not found: {file_path}")
            raise
        except (OSError, csv.Error, ValueError) as e:
            self.error_handler("Import Error", f"Failed to preview CSV: {e}")
            raise

    def execute_import(self, file_path: str,
                       conflict_decisions: Dict[Tuple[str, str], str]) -> int:
        """Execute CSV import with per-conflict resolution decisions.
        conflict_decisions: {(title_lower, username_lower): 'keep_vault'|'replace'}
        Keys omitted from conflict_decisions are inserted as new entries.
        Returns count of imported/updated entries."""
        if not self.encryption_key:
            raise RuntimeError("Encryption key not set. Please unlock the vault first.")
        self.create_pre_op_backup("Import")
        imported_count = 0
        required = {"title", "password"}

        existing = self.load_all_credentials()
        existing_by_key = {}
        for e in existing:
            key = (e.title.lower().strip(), e.username.lower().strip())
            existing_by_key[key] = e

        try:
            with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    return 0
                col_map = self._build_column_map(reader.fieldnames)
                if not required.issubset(col_map):
                    return 0
                for row in reader:
                    entry_data = {}
                    for canonical, header in col_map.items():
                        entry_data[canonical] = row.get(header) or ""
                    key = (
                        entry_data.get("title", "").lower().strip(),
                        entry_data.get("username", "").lower().strip(),
                    )
                    if key in conflict_decisions:
                        decision = conflict_decisions[key]
                        if decision == "keep_vault":
                            continue
                        elif decision == "replace":
                            vault_entry = existing_by_key[key]
                            entry = CredentialEntry(**entry_data)
                            entry.db_id = vault_entry.db_id
                            entry.created_at = vault_entry.created_at
                            self.update_credential(entry)
                            imported_count += 1
                    else:
                        entry = CredentialEntry(**entry_data)
                        if self.save_credential(entry) is not None:
                            imported_count += 1
            return imported_count
        except FileNotFoundError:
            self.error_handler("Import Error", f"File not found: {file_path}")
            raise
        except (OSError, csv.Error, ValueError) as e:
            self.error_handler("Import Error", f"Failed to execute import: {e}")
            raise
