# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: tests/test_sync_integration.py
# Purpose: End-to-end sync tests (two vaults + a live in-process sync server).

"""End-to-end sync tests: SDK clients against a live in-process sync server."""

import importlib.util
import threading
from pathlib import Path

import pytest

from aethervault.core.sync import SyncError
from aethervault.sdk import Vault

ROOT = Path(__file__).resolve().parent.parent
MASTER_PW = "sync-master-password-123"
TOKEN = "test-sync-token"


def _load_server():
    spec = importlib.util.spec_from_file_location(
        "sync_server_it", ROOT / "tools" / "sync_server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server_url(tmp_path):
    server = _load_server()
    httpd = server.create_server(str(tmp_path / "srv"), token=TOKEN,
                                 host="127.0.0.1", port=0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _vault(tmp_path, name):
    return Vault.create(MASTER_PW, str(tmp_path / f"{name}.db"),
                        str(tmp_path / f".{name}.key"))


def test_two_vaults_merge_both_directions(server_url, tmp_path):
    a = _vault(tmp_path, "a")
    b = _vault(tmp_path, "b")
    try:
        a.add(title="GitHub", username="octocat", password="p1")
        assert a.sync(server_url, token=TOKEN, device_id="a")["entries"] == 1

        assert b.sync(server_url, token=TOKEN, device_id="b")["entries"] == 1
        assert [e.title for e in b.list_entries()] == ["GitHub"]

        b.add(title="Bank", password="p2")
        b.sync(server_url, token=TOKEN, device_id="b")
        a.sync(server_url, token=TOKEN, device_id="a")
        assert {e.title for e in a.list_entries()} == {"GitHub", "Bank"}
    finally:
        a.lock()
        b.lock()


def test_delete_propagates_as_tombstone(server_url, tmp_path):
    a = _vault(tmp_path, "a")
    b = _vault(tmp_path, "b")
    try:
        entry_id = a.add(title="Temp", password="p")
        a.sync(server_url, token=TOKEN)
        b.sync(server_url, token=TOKEN)
        assert len(b.list_entries()) == 1

        a.delete(entry_id)
        a.sync(server_url, token=TOKEN)
        b.sync(server_url, token=TOKEN)
        assert b.list_entries() == []
    finally:
        a.lock()
        b.lock()


def test_wrong_token_is_rejected(server_url, tmp_path):
    a = _vault(tmp_path, "a")
    try:
        a.add(title="X", password="p")
        with pytest.raises(SyncError):
            a.sync(server_url, token="wrong-token")
    finally:
        a.lock()


def test_unreachable_server_raises(tmp_path):
    a = _vault(tmp_path, "a")
    try:
        with pytest.raises(SyncError):
            a.sync("http://127.0.0.1:1", token=TOKEN)
    finally:
        a.lock()
