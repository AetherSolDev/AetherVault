# Created: 2026-09-16
# Last Edited: 2026-09-16 18:31 CT (America/Chicago)
# Path: tools/SYNC.md
# Purpose: Client guide for AetherVault sync (the relay lives in server/).

# AetherVault Sync — client guide

Sync uses the **zero-knowledge relay** under [`server/`](../server/) (FastAPI, deployed on the
Protectli router, Tailscale-only). See [`server/README.md`](../server/README.md) for the relay
API and deployment.

## How it works

- Each entry is a **record** with a stable `uuid`, a hybrid-logical-clock `rev`, a `deleted`
  tombstone, and an opaque `payload` (the entry fields, encrypted).
- A random 32-byte **data key** encrypts payloads. It is wrapped with a KEK derived from the
  master password + the relay's KDF salt, and stored on the relay — so the relay is
  zero-knowledge and a password change only re-wraps the key.
- A new device **enrolls** with the enrollment secret, fetches `/v1/vault/meta`, derives the
  KEK from the password, and unwraps the data key.
- Sync is **pull → merge → push**: `GET /v1/changes?since=N` returns records newer than the
  last cursor; local and remote records merge by `uuid`, **last-writer-wins** on `rev`;
  local changes push with `POST /v1/changes`.

## First device (creates the relay vault)

```sh
export AETHERVAULT_ENROLL_SECRET="<the relay's enroll secret>"
aethervault-cli --vault-dir ~/vault sync-setup --server http://openwrt:8787 --device-name laptop
```

## Additional devices

```sh
aethervault-cli --vault-dir ~/vault sync-enroll --server http://openwrt:8787 --device-name phone
```

## Day to day

```sh
aethervault-cli --vault-dir ~/vault sync            # pull + merge + push
aethervault-cli --vault-dir ~/vault sync-devices    # list enrolled devices
aethervault-cli --vault-dir ~/vault sync-revoke <id># revoke a lost device
```

Python:

```python
from aethervault.sdk import Vault
with Vault().unlock("master-password") as vault:
    print(vault.sync())          # {"pulled": 2, "pushed": 1, "server_rev": 42}
```

## Duress

Entering the **duress password** on a synced client wipes only that device's local files
(including `<db>.sync.json`) and **never pushes**. The relay and every other device are
untouched. To also revoke the lost device, run `sync-revoke <device_id>` from another device.

## Config

Per-vault state lives in `<vault.db>.sync.json` (`relay_url`, `vault_id`, `device_id`,
`token`, `last_server_rev`, `hlc_last`). Delete it to detach a device without wiping.
