# Created: 2026-09-16
# Last Edited: 2026-09-16 18:31 CT (America/Chicago)
# Path: server/README.md
# Purpose: Overview + deploy guide for the AetherVault zero-knowledge sync relay.

# AetherVault Sync Relay

A single-vault, **zero-knowledge** sync relay. It stores only what it cannot read: the
vault's *wrapped* master key + KDF parameters (so a new device can bootstrap), opaque record
payloads, and hashed device tokens. Record merge is last-write-wins by the client's HLC
`rev`.

> **Provenance:** this source was recovered from the `aethervault-relay:latest` image on the
> Protectli router (2026-09-16) and committed here so it is version-controlled. The
> `Dockerfile` was reconstructed from the image build history; `docker-compose.yml` and
> `.env.example` were taken from `/root/vault/aethervault-relay/` (the secret `.env` was not).

## API (v1)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/healthz` | — | health check |
| `POST` | `/v1/vault` | `X-Enroll-Secret` | create the vault (wrapped key + KDF params) |
| `POST` | `/v1/enroll` | `X-Enroll-Secret` | enroll a device → `{device_id, token}` |
| `GET` | `/v1/vault/meta` | device token | wrapped master key + KDF params (bootstrap) |
| `GET` | `/v1/changes?since=N` | device token | pull records with `server_rev > N` + `server_rev` |
| `POST` | `/v1/changes` | device token | push records (LWW by `rev`) |
| `GET` | `/v1/devices` | device token | list enrolled devices |
| `DELETE` | `/v1/devices/{id}` | device token | revoke a device (not yourself) |

A record is `{uuid, vault_id, device_id, rev, deleted, deleted_at, updated_at, payload}` —
`payload` is opaque ciphertext; `rev` is the client's HLC string.

## Configuration (env)

| Var | Default | Notes |
|-----|---------|-------|
| `AETHERVAULT_HOST` | `127.0.0.1` | bind address (use the Tailscale IP) |
| `AETHERVAULT_PORT` | `8787` | |
| `AETHERVAULT_DATA_DIR` | `/data` | relay SQLite lives here |
| `AETHERVAULT_DB_PATH` | `<data>/relay.db` | |
| `AETHERVAULT_ENROLL_SECRET` | _(empty)_ | enrollment disabled if unset |
| `AETHERVAULT_MAX_PAYLOAD_BYTES` | `262144` | per-record payload cap |
| `AETHERVAULT_MAX_RECORDS_PER_PUSH` | `1000` | |

## Deploy

```sh
cp .env.example .env        # then set TAILSCALE_IP + AETHERVAULT_ENROLL_SECRET
chmod 600 .env
docker compose up -d --build
curl -s "http://$TAILSCALE_IP:8787/healthz"   # {"status":"ok"}
```

Host networking binds the relay to the **Tailscale IP only** — nothing is exposed on the LAN.
