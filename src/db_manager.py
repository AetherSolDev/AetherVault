# Created: 2025-12-04
# Last Edited: 2026-07-24 00:37 CT (America/Chicago)
# Path: src/db_manager.py
# Purpose: SQLite database operations for credential entries.

import csv
import os
import shutil
import sqlite3
import time
from typing import Any, Dict, List, Optional

from src.core_logic import (
    CredentialEntry,
    decrypt_data,
    derive_encryption_key,
    encrypt_data,
    get_timestamped_backup_path,
)


class DatabaseManager:
    """Handles all SQLite database operations for credential entries."""

    def __init__(self, db_path: str, error_handler):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.error_handler = error_handler
        self.encryption_key: bytes = b""
        self._connect()
        self._create_table()

    def set_encryption_key(self, master_password_hash: str):
        try:
            self.encryption_key = derive_encryption_key(master_password_hash)
        except Exception as e:
            self.error_handler(
                "Encryption Error", f"Failed to derive encryption key: {e}"
            )
            self.encryption_key = b""

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Could not connect to database: {e}")

    def _create_table(self):
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
            modified_at TEXT NOT NULL
        )
        """
        try:
            self.cursor.execute(sql)
            self.conn.commit()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error creating table: {e}")
        for col in ["tags", "custom_fields"]:
            try:
                self.cursor.execute(f"ALTER TABLE credentials ADD COLUMN {col} TEXT DEFAULT ''")
                self.conn.commit()
            except sqlite3.OperationalError:
                pass

    def load_all_credentials(self) -> List[CredentialEntry]:
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
        except Exception as e:
            self.error_handler(
                "Decryption Error", f"Decryption failed (wrong key?): {e}"
            )
        return credentials

    def save_credential(self, entry: CredentialEntry) -> Optional[int]:
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
        INSERT INTO credentials (title, url, username, email, password, phone, address, category, notes, tags, custom_fields, parent_id, created_at, modified_at)
        VALUES (:title, :url, :username, :email, :password, :phone, :address, :category, :notes, :tags, :custom_fields, :parent_id, :created_at, :modified_at)
        """
        try:
            self.cursor.execute(sql, entry_dict)
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error saving credential: {e}")
            return None

    def update_credential(self, entry: CredentialEntry):
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
            parent_id = :parent_id, modified_at = :modified_at
        WHERE db_id = :db_id
        """
        try:
            self.cursor.execute(sql, entry_dict)
            self.conn.commit()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error updating credential: {e}")

    def delete_credential(self, db_id: int):
        if not self.conn:
            return
        sql = "DELETE FROM credentials WHERE db_id = ?"
        try:
            self.cursor.execute(sql, (db_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Error deleting credential: {e}")

    def create_pre_op_backup(self, operation: str) -> Optional[str]:
        if not os.path.exists(self.db_path):
            return None
        try:
            if self.conn:
                self.conn.close()
            backup_path = get_timestamped_backup_path()
            shutil.copyfile(self.db_path, backup_path)
            self._connect()
            return backup_path
        except Exception as e:
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

        cursor = self.conn.cursor()
        deleted_count = 0
        try:
            cursor.execute("""
                SELECT MIN(db_id)
                FROM credentials
                GROUP BY title, username
                HAVING COUNT(*) > 1
            """)
            ids_to_keep = {row[0] for row in cursor.fetchall()}
            cursor.execute("""
                SELECT db_id
                FROM credentials
                WHERE (title, username) IN (
                    SELECT title, username
                    FROM credentials
                    GROUP BY title, username
                    HAVING COUNT(*) > 1
                )
            """)
            all_duplicate_ids = {row[0] for row in cursor.fetchall()}
            ids_to_delete = all_duplicate_ids - ids_to_keep
            if not ids_to_delete:
                return 0
            placeholders = ",".join("?" * len(ids_to_delete))
            cursor.execute(
                f"""
                DELETE FROM credentials
                WHERE db_id IN ({placeholders})
            """,
                tuple(ids_to_delete),
            )
            deleted_count = cursor.rowcount
            self.conn.commit()
            return deleted_count
        except sqlite3.Error as e:
            self.error_handler("Database Error", f"Failed to remove duplicates: {e}")
            return 0

    def export_to_csv(self, file_path: str, credentials: List[CredentialEntry]) -> int:
        if not credentials:
            self.error_handler("Export Warning", "No credentials to export.")
            return 0
        fieldnames = [
            "db_id", "title", "url", "username", "email", "password",
            "phone", "address", "category", "notes", "tags", "custom_fields",
            "parent_id", "created_at", "modified_at",
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
        except Exception as e:
            self.error_handler("Export Error", f"Failed to write to CSV: {e}")
            raise

    def import_from_csv(self, file_path: str) -> int:
        self.create_pre_op_backup("Import")
        imported_count = 0
        valid_keys = [
            "db_id", "title", "url", "username", "email", "password",
            "phone", "address", "category", "notes", "tags", "custom_fields",
        ]
        try:
            with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    entry_data = {k: row.get(k) or "" for k in valid_keys}
                    if not entry_data.get("title") or not entry_data.get("password"):
                        continue
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
        except Exception as e:
            self.error_handler("Import Error", f"Failed to read/parse CSV: {e}")
            raise
