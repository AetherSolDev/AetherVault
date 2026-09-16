# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: tools/SYNC.md
# Purpose: Deploy + design guide for the AetherVault zero-knowledge sync server.

# AetherVault Sync

A small **zero-knowledge** sync hub you run yourself — on an OpenWrt router, NAS, or any
Docker host — reachable over your LAN or Tailscale. Clients (desktop/phone) pull the
encrypted blob, **merge locally**, and push with optimistic concurrency. The server never
sees your master password, key, or plaintext.

```
 desktop ─┐                         ┌─ pull / merge / push (HTTPS or Tailscale)
 phone ───┼── Tailscale / LAN ──►  │  aethervault-sync (Docker)
 other ───┘                         └─ stores ONE opaque ciphertext blob + version
```

## Why not Syncthing the vault file

- The vault is SQLite in **WAL mode**; copying/syncing `aethervault.db` without its `-wal`
  file mid-transaction yields a corrupt DB.
- Two devices editing between syncs produce **divergent databases** that can't be merged.
- **Duress would propagate**: wiping one device deletes the files everywhere.

The sync server avoids all three: clients exchange an **encrypted entry payload** and merge
per entry (see below).

## Deploy (OpenWrt / Docker)

```sh
# on the router / Docker host
git clone https://github.com/AetherSolDev/AetherVault.git
cd AetherVault/tools

export AETHERVAULT_SYNC_TOKEN="$(openssl rand -hex 32)"   # save this — clients need it
docker compose -f docker-compose.sync.yml up -d --build
```

The service listens on `8787`. Reach it over:

- **Tailscale** (recommended): `http://openwrt:8787` or `http://100.84.231.97:8787`
  (WireGuard already encrypts transport; no certs needed).
- **LAN**: `http://<router-ip>:8787` — fine on a trusted network. For untrusted networks put
  it behind a TLS reverse proxy (Caddy/nginx).

Quick check:

```sh
curl http://openwrt:8787/health                 # {"status":"ok"}
curl -H "Authorization: Bearer $AETHERVAULT_SYNC_TOKEN" http://openwrt:8787/vault
```

## Client usage

All devices must use the **same master password** (the sync key is derived from it).

```sh
export AETHERVAULT_SYNC_TOKEN="<the token you generated>"

# desktop
aethervault-cli sync --server http://openwrt:8787 --device-id laptop

# phone (Termux)
aethervault-cli sync --server http://openwrt:8787 --device-id phone
```

Or from Python:

```python
from aethervault.sdk import Vault
with Vault().unlock("master-password") as vault:
    print(vault.sync("http://openwrt:8787", token="...", device_id="laptop"))
    # {"version": 3, "entries": 12}
```

Sync is **pull → merge → push**: safe to run repeatedly; a `409` is handled internally by
re-pulling and re-merging.

## Security model

- **Zero-knowledge:** the payload is encrypted on the client with a key derived from the
  master-password hash (PBKDF2, separate salt from the local vault key). The server only
  stores ciphertext + a version counter.
- **Auth:** a bearer token (`AETHERVAULT_SYNC_TOKEN`). Tailscale additionally restricts who
  can even reach the port.
- **Transport:** Tailscale (encrypted) or TLS via reverse proxy.
- The server can be destroyed/replaced freely — clients hold the only key.

## Duress semantics

Entering the **duress password on a synced client wipes only the local copy and detaches
from sync** — it never pushes. The hub and every other device stay intact, so the legitimate
owner can recover with the real master password. (This matches the existing rule that duress
leaves the remote *backup folder* untouched.)

## Merge model

Each entry has a stable `entry_uuid`. On sync, a client:

1. decrypts the server payload,
2. **unions** local + remote entries by `entry_uuid`,
3. resolves each conflict **last-writer-wins** on `modified_at` (a deletion tombstone wins a
   tie so entries aren't resurrected),
4. writes the merged result back locally,
5. pushes it with `base_version`; a `409` means someone else pushed first — re-pull, re-merge,
   retry.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `401 unauthorized` | Token mismatch — set the same `AETHERVAULT_SYNC_TOKEN` on client and server. |
| `409 version conflict` | Normal under concurrency; the client re-pulls and re-merges. |
| Can't reach `:8787` | Check Tailscale (`tailscale status`), firewall, and that the container is up (`docker logs aethervault-sync`). |
| Lost the token | Set a new one and update every client; the blob is unaffected. |
