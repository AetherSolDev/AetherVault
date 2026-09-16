# Created: 2026-09-16
# Last Edited: 2026-09-16 12:36 CT (America/Chicago)
# Path: server/app.py
# Purpose: Zero-knowledge FastAPI sync relay for AetherVault (Phase 2).

"""Zero-knowledge sync relay for AetherVault.

The relay stores only what it cannot read: the vault's *wrapped* key + KDF
parameters (so a new device can bootstrap), opaque record payloads, and hashed
device tokens. Record merge is last-write-wins by the client's HLC revision.

Run with::

    uvicorn app:create_app --factory --host 127.0.0.1 --port 8787

The enrollment secret (``AETHERVAULT_ENROLL_SECRET``) authorizes creating the
vault and enrolling devices; each device then gets its own revocable token.
"""

from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from . import auth, db
from .config import Settings


class VaultCreate(BaseModel):
    vault_id: str
    format_version: int
    kdf_algorithm: str
    kdf_iterations: int
    kdf_salt: str
    wrapped_master: str


class EnrollRequest(BaseModel):
    device_name: str = ""


class SyncRecord(BaseModel):
    uuid: str
    vault_id: str = ""
    device_id: str = ""
    rev: str
    deleted: bool = False
    deleted_at: str = ""
    updated_at: str = ""
    payload: str


class PushRequest(BaseModel):
    records: List[SyncRecord]


def _validate_record(record: SyncRecord, settings: Settings) -> None:
    if not record.uuid or not record.rev or not record.payload:
        raise HTTPException(422, "record is missing uuid, rev, or payload")
    if len(record.payload) > settings.max_payload_bytes:
        raise HTTPException(413, "record payload exceeds the size limit")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the FastAPI app (factory so tests can inject settings)."""
    settings = settings or Settings.from_env()
    db.init_db(settings.db_path)

    app = FastAPI(title="AetherVault Sync Relay", version="1")

    def get_conn():
        conn = db.connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def require_device(
        authorization: str = Header(default=""), conn=Depends(get_conn)
    ) -> Dict[str, object]:
        token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        if not token:
            raise HTTPException(401, "missing device token")
        device = db.get_device_by_token(conn, auth.hash_token(token))
        if device is None:
            raise HTTPException(401, "invalid device token")
        db.touch_device(conn, device["device_id"])
        return dict(device)

    def require_enroll_secret(x_enroll_secret: str = Header(default="")) -> None:
        if not settings.enrollment_enabled:
            raise HTTPException(503, "enrollment is disabled on this relay")
        if not auth.secret_matches(x_enroll_secret, settings.enroll_secret):
            raise HTTPException(401, "invalid enrollment secret")

    @app.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/vault", status_code=201)
    def create_vault(
        body: VaultCreate,
        conn=Depends(get_conn),
        _=Depends(require_enroll_secret),
    ) -> Dict[str, str]:
        if db.get_vault(conn) is not None:
            raise HTTPException(409, "a vault already exists on this relay")
        db.create_vault(
            conn,
            body.vault_id,
            body.format_version,
            body.kdf_algorithm,
            body.kdf_iterations,
            body.kdf_salt,
            body.wrapped_master,
        )
        return {"vault_id": body.vault_id}

    @app.post("/v1/enroll")
    def enroll(
        body: EnrollRequest,
        conn=Depends(get_conn),
        _=Depends(require_enroll_secret),
    ) -> Dict[str, str]:
        vault = db.get_vault(conn)
        if vault is None:
            raise HTTPException(409, "no vault exists on this relay yet")
        token = auth.new_token()
        device_id = db.create_device(
            conn, vault["vault_id"], body.device_name, auth.hash_token(token)
        )
        return {"device_id": device_id, "token": token, "vault_id": vault["vault_id"]}

    @app.get("/v1/vault/meta")
    def vault_meta(
        device=Depends(require_device), conn=Depends(get_conn)
    ) -> Dict[str, object]:
        vault = db.get_vault(conn)
        if vault is None:
            raise HTTPException(404, "no vault")
        return {
            "vault_id": vault["vault_id"],
            "format_version": vault["format_version"],
            "kdf_algorithm": vault["kdf_algorithm"],
            "kdf_iterations": vault["kdf_iterations"],
            "kdf_salt": vault["kdf_salt"],
            "wrapped_master": vault["wrapped_master"],
        }

    @app.get("/v1/changes")
    def pull(
        since: int = Query(0, ge=0),
        device=Depends(require_device),
        conn=Depends(get_conn),
    ) -> Dict[str, object]:
        records, server_rev = db.pull_records(conn, device["vault_id"], since)
        return {"records": records, "server_rev": server_rev}

    @app.post("/v1/changes")
    def push(
        body: PushRequest,
        device=Depends(require_device),
        conn=Depends(get_conn),
    ) -> Dict[str, int]:
        if len(body.records) > settings.max_records_per_push:
            raise HTTPException(413, "too many records in one push")
        for record in body.records:
            _validate_record(record, settings)
        applied, server_rev = db.push_records(
            conn, device["vault_id"], [record.model_dump() for record in body.records]
        )
        return {"applied": applied, "server_rev": server_rev}

    @app.get("/v1/devices")
    def devices(
        device=Depends(require_device), conn=Depends(get_conn)
    ) -> Dict[str, object]:
        return {"devices": db.list_devices(conn, device["vault_id"])}

    @app.delete("/v1/devices/{device_id}")
    def revoke(
        device_id: str,
        device=Depends(require_device),
        conn=Depends(get_conn),
    ) -> Dict[str, str]:
        if device_id == device["device_id"]:
            raise HTTPException(400, "cannot revoke the calling device")
        if not db.delete_device(conn, device["vault_id"], device_id):
            raise HTTPException(404, "unknown device")
        return {"revoked": device_id}

    return app
