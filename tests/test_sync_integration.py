# Created: 2026-09-16
# Last Edited: 2026-09-16 18:31 CT (America/Chicago)
# Path: tests/test_sync_integration.py
# Purpose: End-to-end sync tests against a live in-process relay (server/).

"""End-to-end sync tests: SDK clients against a live relay process."""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from aethervault.core.sync import RelayError
from aethervault.sdk import Vault

ROOT = Path(__file__).resolve().parent.parent
MASTER_PW = "sync-master-password-123"
ENROLL_SECRET = "test-enroll-secret"


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def relay(tmp_path):
    port = _free_port()
    env = {
        **os.environ,
        "AETHERVAULT_DATA_DIR": str(tmp_path),
        "AETHERVAULT_DB_PATH": str(tmp_path / "relay.db"),
        "AETHERVAULT_ENROLL_SECRET": ENROLL_SECRET,
        "AETHERVAULT_HOST": "127.0.0.1",
        "AETHERVAULT_PORT": str(port),
        "PYTHONPATH": str(ROOT / "server"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:create_app", "--factory",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT / "server"), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            with urllib.request.urlopen(url + "/healthz", timeout=1) as resp:
                if resp.status == 200:
                    break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("relay did not start")

    yield url
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _vault(tmp_path, name):
    return Vault.create(MASTER_PW, str(tmp_path / f"{name}.db"),
                        str(tmp_path / f".{name}.key"))


def test_setup_enroll_and_merge_both_directions(relay, tmp_path):
    a = _vault(tmp_path, "a")
    b = _vault(tmp_path, "b")
    try:
        a.add(title="GitHub", username="octocat", password="p1")
        result = a.setup_sync(relay, ENROLL_SECRET, "laptop")
        assert result["pushed"] == 1

        result = b.enroll_sync(relay, ENROLL_SECRET, "phone")
        assert result["pulled"] == 1
        assert [e.title for e in b.list_entries()] == ["GitHub"]

        b.add(title="Bank", password="p2")
        b.sync()
        a.sync()
        assert {e.title for e in a.list_entries()} == {"GitHub", "Bank"}
    finally:
        a.lock()
        b.lock()


def test_delete_propagates_as_tombstone(relay, tmp_path):
    a = _vault(tmp_path, "a")
    b = _vault(tmp_path, "b")
    try:
        entry_id = a.add(title="Temp", password="p")
        a.setup_sync(relay, ENROLL_SECRET)
        b.enroll_sync(relay, ENROLL_SECRET)
        assert len(b.list_entries()) == 1

        a.delete(entry_id)
        a.sync()
        b.sync()
        assert b.list_entries() == []
    finally:
        a.lock()
        b.lock()


def test_devices_list_and_revoke(relay, tmp_path):
    a = _vault(tmp_path, "a")
    b = _vault(tmp_path, "b")
    try:
        a.setup_sync(relay, ENROLL_SECRET, "laptop")
        b.enroll_sync(relay, ENROLL_SECRET, "phone")
        devices = a.sync_devices()
        assert len(devices) == 2

        phone = next(d for d in devices if d["name"] == "phone")
        a.sync_revoke(phone["device_id"])
        assert len(a.sync_devices()) == 1
    finally:
        a.lock()
        b.lock()


def test_wrong_enroll_secret_rejected(relay, tmp_path):
    a = _vault(tmp_path, "a")
    try:
        with pytest.raises(RelayError):
            a.setup_sync(relay, "wrong-secret")
    finally:
        a.lock()


def test_sync_without_config_raises(tmp_path):
    a = _vault(tmp_path, "a")
    try:
        with pytest.raises(Exception):
            a.sync()
    finally:
        a.lock()
