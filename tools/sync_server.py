# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: tools/sync_server.py
# Purpose: Zero-knowledge sync server for AetherVault (stdlib only, runs in Docker).

"""Zero-knowledge sync server for AetherVault.

The server stores an **opaque ciphertext blob** and a version counter — it never sees the
master password, the key, or any plaintext. Clients pull the blob, merge locally, and push
with optimistic concurrency (``base_version``); a stale push gets a ``409`` with the current
version so the client can re-merge.

Endpoints (all JSON):

* ``GET  /health`` → ``{"status": "ok"}``
* ``GET  /vault``  → ``{"version": N, "payload": "<ciphertext or null>"}``
* ``POST /vault``  ``{"base_version": N, "payload": "<ciphertext>", "device_id": "..."}``
                    → ``{"version": N+1}`` or ``409`` with the current version + payload

Auth: if ``AETHERVAULT_SYNC_TOKEN`` (or ``--token``) is set, every ``/vault`` request must
send ``Authorization: Bearer <token>``. On a Tailscale network the WireGuard tunnel already
encrypts transport; on a plain LAN, put it behind TLS or keep it on a trusted network.

Run:  ``python tools/sync_server.py --data /data --port 8787``
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN_ENV = "AETHERVAULT_SYNC_TOKEN"
DATA_ENV = "AETHERVAULT_SYNC_DATA"
DEFAULT_PORT = 8787


class VaultStore:
    """A single encrypted blob + version, persisted to ``data_dir``."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.payload_path = os.path.join(data_dir, "vault.bin")
        self.meta_path = os.path.join(data_dir, "meta.json")
        self.lock = threading.Lock()
        self.version = 0
        self.updated_at = None
        self.devices: dict = {}
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.meta_path):
            return
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        self.version = int(meta.get("version", 0))
        self.updated_at = meta.get("updated_at")
        self.devices = meta.get("devices", {})

    def _read_payload(self):
        if not os.path.exists(self.payload_path):
            return None
        with open(self.payload_path, "r", encoding="utf-8") as f:
            return f.read()

    def _save_meta(self) -> None:
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {"version": self.version, "updated_at": self.updated_at,
                 "devices": self.devices},
                f,
            )

    def get(self):
        """Return ``(version, payload_or_None)``."""
        with self.lock:
            return self.version, self._read_payload()

    def put(self, base_version: int, payload: str, device_id: str = ""):
        """Store ``payload`` if ``base_version`` matches. Returns ``(ok, version, payload)``."""
        with self.lock:
            if base_version != self.version:
                return False, self.version, self._read_payload()
            with open(self.payload_path, "w", encoding="utf-8") as f:
                f.write(payload)
            self.version += 1
            self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if device_id:
                self.devices[device_id] = self.updated_at
            self._save_meta()
            return True, self.version, payload


def make_handler(store: VaultStore, token: str):
    """Build a request handler bound to ``store`` and optional bearer ``token``."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "AetherVaultSync/1"

        def _authorized(self) -> bool:
            if not token:
                return True
            return self.headers.get("Authorization", "") == f"Bearer {token}"

        def _json(self, code: int, obj) -> None:
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 (http.server API)
            if self.path == "/health":
                return self._json(200, {"status": "ok"})
            if self.path == "/vault":
                if not self._authorized():
                    return self._json(401, {"error": "unauthorized"})
                version, payload = store.get()
                return self._json(200, {"version": version, "payload": payload})
            return self._json(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802 (http.server API)
            if self.path != "/vault":
                return self._json(404, {"error": "not found"})
            if not self._authorized():
                return self._json(401, {"error": "unauthorized"})
            length = int(self.headers.get("Content-Length", 0) or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "invalid JSON"})
            if not isinstance(body.get("payload"), str) or not body["payload"]:
                return self._json(400, {"error": "missing payload"})
            ok, version, payload = store.put(
                int(body.get("base_version", 0)),
                body["payload"],
                str(body.get("device_id", "")),
            )
            if not ok:
                return self._json(409, {
                    "error": "version conflict", "version": version, "payload": payload,
                })
            return self._json(200, {"version": version})

        def log_message(self, *args):  # keep the container logs quiet
            pass

    return Handler


def create_server(data_dir: str, token: str = "", host: str = "0.0.0.0",
                  port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Create (but do not start) the sync HTTP server."""
    return ThreadingHTTPServer((host, port), make_handler(VaultStore(data_dir), token))


def main() -> int:
    parser = argparse.ArgumentParser(description="AetherVault zero-knowledge sync server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data", default=os.environ.get(DATA_ENV, "./sync-data"))
    parser.add_argument("--token", default=os.environ.get(TOKEN_ENV, ""))
    args = parser.parse_args()

    httpd = create_server(args.data, args.token, args.host, args.port)
    auth = "on" if args.token else "OFF (set AETHERVAULT_SYNC_TOKEN!)"
    print(f"AetherVault sync server listening on {args.host}:{args.port} "
          f"(data={args.data}, auth={auth})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
