# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: tests/test_sync_server.py
# Purpose: Tests for the zero-knowledge sync server (tools/sync_server.py).

"""Tests for the AetherVault sync server."""

import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_server():
    spec = importlib.util.spec_from_file_location(
        "sync_server", ROOT / "tools" / "sync_server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def base_url(tmp_path):
    server = _load_server()
    httpd = server.create_server(str(tmp_path), token="secret",
                                 host="127.0.0.1", port=0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _request(method, url, body=None, token="secret"):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health(base_url):
    status, body = _request("GET", f"{base_url}/health", token=None)
    assert status == 200 and body["status"] == "ok"


def test_get_empty_vault(base_url):
    status, body = _request("GET", f"{base_url}/vault")
    assert status == 200
    assert body == {"version": 0, "payload": None}


def test_push_then_pull(base_url):
    status, body = _request("POST", f"{base_url}/vault",
                            {"base_version": 0, "payload": "cipher-1", "device_id": "d1"})
    assert status == 200 and body["version"] == 1

    status, body = _request("GET", f"{base_url}/vault")
    assert status == 200
    assert body["version"] == 1 and body["payload"] == "cipher-1"


def test_stale_push_conflicts(base_url):
    _request("POST", f"{base_url}/vault", {"base_version": 0, "payload": "cipher-1"})
    status, body = _request("POST", f"{base_url}/vault",
                            {"base_version": 0, "payload": "cipher-2"})
    assert status == 409
    assert body["version"] == 1 and body["payload"] == "cipher-1"


def test_auth_required(base_url):
    status, _ = _request("GET", f"{base_url}/vault", token=None)
    assert status == 401
    status, _ = _request("POST", f"{base_url}/vault",
                         {"base_version": 0, "payload": "x"}, token=None)
    assert status == 401


def test_missing_payload_rejected(base_url):
    status, body = _request("POST", f"{base_url}/vault", {"base_version": 0})
    assert status == 400
