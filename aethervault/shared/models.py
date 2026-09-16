# Created: 2026-08-05
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: aethervault/shared/models.py
# Purpose: Data model for a single credential entry.

"""Data model for a single credential entry."""

from typing import Any, Dict


class CredentialEntry:
    """Data class representing a single credential entry with all metadata fields."""

    def __init__(self, **kwargs):
        """Initialize a CredentialEntry from keyword arguments, defaulting missing fields."""
        self.db_id = kwargs.get("db_id")
        self.title = kwargs.get("title", "")
        self.url = kwargs.get("url", "")
        self.username = kwargs.get("username", "")
        self.email = kwargs.get("email", "")
        self.password = kwargs.get("password", "")
        self.phone = kwargs.get("phone", "")
        self.address = kwargs.get("address", "")
        self.category = kwargs.get("category", "")
        self.notes = kwargs.get("notes", "")
        self.tags = kwargs.get("tags", "")
        self.custom_fields = kwargs.get("custom_fields", "")
        self.totp_secret = kwargs.get("totp_secret", "")
        self.recovery_codes = kwargs.get("recovery_codes", "")
        self.entry_uuid = kwargs.get("entry_uuid", "")
        self.deleted = kwargs.get("deleted", 0)
        self.sync_rev = kwargs.get("sync_rev", "")
        self.parent_id = kwargs.get("parent_id", 0)
        self.created_at = kwargs.get("created_at")
        self.modified_at = kwargs.get("modified_at")
        self.time_last_used = kwargs.get("time_last_used", "")
        self.time_password_changed = kwargs.get("time_password_changed", "")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this credential entry to a plain dictionary."""
        return {
            "db_id": self.db_id,
            "title": self.title,
            "url": self.url,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "phone": self.phone,
            "address": self.address,
            "category": self.category,
            "notes": self.notes,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
            "totp_secret": self.totp_secret,
            "recovery_codes": self.recovery_codes,
            "entry_uuid": self.entry_uuid,
            "deleted": self.deleted,
            "sync_rev": self.sync_rev,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "time_last_used": self.time_last_used,
            "time_password_changed": self.time_password_changed,
        }
