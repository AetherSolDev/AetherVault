# Created: 2026-07-27
# Last Edited: 2026-07-27 17:27 CT (America/Chicago)
# Path: safety.md
# Purpose: Backup strategy — automatic local + NAS snapshots on every git commit/push.

# Safety: Multi-Tier Backup Strategy

## Architecture

```
git commit
  ├──► origin (GitHub)     — public subset (respects .gitignore)
  └──► ~/recover/{project}/ — full snapshot (.gitignore stripped, keeps last 5)

git push
  ├──► origin (GitHub)
  └──► /mnt/nas/planb/projects/{project}/ — full rsync mirror
```

No cron, no tarball rotation, no extra commands. Every `git commit` and `git push`
you type automatically triggers the safety layer via a `git()` override in `.zshrc`.

---

## How It Works

### The `git()` Override

A shell function wraps `git commit` and `git push` to add the safety steps.
All other git commands pass through unchanged.

```zsh
git() {
    if [[ "$1" == "commit" && "$*" != *"--help"* && "$*" != *"--amend"* ]]; then
        command git "$@"
        local rc=$?
        (( rc == 0 )) && _safety_after_commit
        return $rc
    fi
    if [[ "$1" == "push" ]]; then
        command git "$@"
        local rc=$?
        (( rc == 0 )) && _safety_after_push
        return $rc
    fi
    command git "$@"
}
```

The project name is inferred from `git rev-parse --show-toplevel` — no manual
configuration needed. Works in any repo under `$HOME/projects/`.

### Recovery Snapshot (`git commit` extra step)

Every successful commit triggers:

```zsh
_safety_after_commit() {
    local project
    project=$(basename "$(git rev-parse --show-toplevel)" 2>/dev/null) || return
    local recover="$HOME/recover/$project"
    local stamp
    stamp=$(date '+%Y-%m-%d_%H-%M-%S')

    mkdir -p "$recover"

    rsync -a \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='node_modules' \
        "$src/" "$recover/$stamp/" || {
        echo "  ⚠ Recover rsync failed"
        rm -rf "$recover/$stamp"
        return
    }

    git -C "$recover/$stamp" init -q
    git -C "$recover/$stamp" add . 2>&1 | head -5
    git -C "$recover/$stamp" commit -q -m "Recovery $stamp"

    # Rotate: keep 5 most recent
    ls -dt "$recover"/*/ 2>/dev/null | tail -n +6 | xargs -r rm -rf
    echo "  ✔ Recover snapshot saved ($stamp)"
}
```

What this captures that GitHub doesn't:
- `.env` files, API keys, secrets
- `COST.md`, internal tracking docs
- Local config overrides

### NAS Backup (`git push` extra step)

Every successful push triggers:

```zsh
_safety_after_push() {
    local project
    project=$(basename "$(git rev-parse --show-toplevel)" 2>/dev/null) || return
    local dest="/mnt/nas/planb/projects"

    if ! mountpoint -q "/mnt/nas" 2>/dev/null; then
        echo "  ⚠ NAS not mounted — backup skipped"
        return
    fi

    mkdir -p "$dest"

    rsync -a --backup --backup-dir="$dest/$project/.trash/$(date '+%Y-%m-%d_%H-%M-%S')" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='node_modules' \
        "$(git rev-parse --show-toplevel)/" "$dest/$project/" || {
        echo "  ⚠ NAS rsync failed"
    }
}
```

The NAS copy includes everything (no `.gitignore` filtering). The full project
with secrets, cost tracking, and config is always backed up.

---

## Restore Instructions

### From Local Recovery (`~/recover/`)

```bash
# List available snapshots for a project
ls ~/recover/my_project/

# Restore a specific snapshot to a temp location
cp -a ~/recover/my_project/2026-07-27_14-30-00 /tmp/restored

# Or restore the most recent
cp -a "$(ls -dt ~/recover/my_project/*/ | head -1)" /tmp/restored
```

### From TrueNAS

```bash
# List available project backups
ls /mnt/nas/planb/projects/

# Restore a full project
rsync -a /mnt/nas/planb/projects/my_project/ ~/projects/my_project/
```

### Full Machine Recovery

If setting up a new machine:

```bash
# 1. Clone public repos from GitHub
cd ~/projects
git clone git@github.com:user/my_project.git

# 2. Copy full backup from NAS (overlays secrets, config, cost data)
rsync -a /mnt/nas/planb/projects/my_project/ ~/projects/my_project/

# 3. Or recover from local snapshot if NAS unavailable
cp -a ~/recover/my_project/*/ ~/projects/my_project/
```

---

## .zshrc Configuration

Add to the end of `~/.zshrc`:

```zsh
# ── Safety: auto-backup on git commit/push ──

_safety_after_commit() {
    local project stamp src recover
    project=$(basename "$(git rev-parse --show-toplevel)" 2>/dev/null) || return
    stamp=$(date '+%Y-%m-%d_%H-%M-%S')
    src=$(git rev-parse --show-toplevel) || return
    recover="$HOME/recover/$project"

    mkdir -p "$recover"

    rsync -a \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='node_modules' \
        "$src/" "$recover/$stamp/" || {
        echo "  ⚠ Recover rsync failed"
        rm -rf "$recover/$stamp"
        return
    }

    git -C "$recover/$stamp" init -q
    git -C "$recover/$stamp" add . 2>&1 | head -5
    git -C "$recover/$stamp" commit -q -m "Recovery $stamp"

    ls -dt "$recover"/*/ 2>/dev/null | tail -n +6 | xargs -r rm -rf
    echo "  ✔ Recover snapshot saved ($stamp)"
}

_safety_after_push() {
    local project dest
    project=$(basename "$(git rev-parse --show-toplevel)" 2>/dev/null) || return
    dest="/mnt/nas/planb/projects"

    if ! mountpoint -q "/mnt/nas" 2>/dev/null; then
        echo "  ⚠ NAS not mounted — backup skipped"
        return
    fi

    mkdir -p "$dest"

    rsync -a --backup --backup-dir="$dest/$project/.trash/$(date '+%Y-%m-%d_%H-%M-%S')" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='node_modules' \
        "$(git rev-parse --show-toplevel)/" "$dest/$project/" || {
        echo "  ⚠ NAS rsync failed"
    }

    echo "  ✔ NAS backup saved ($dest/$project/)"
}

git() {
    if [[ "$1" == "commit" && "$*" != *"--help"* && "$*" != *"--amend"* ]]; then
        command git "$@"
        local rc=$?
        (( rc == 0 )) && _safety_after_commit
        return $rc
    fi
    if [[ "$1" == "push" ]]; then
        command git "$@"
        local rc=$?
        (( rc == 0 )) && _safety_after_push
        return $rc
    fi
    command git "$@"
}
```

Paste this at the end of `~/.zshrc`. Test with a dummy repo before trusting it
with real work.

---

## Files & Directories

| Path | Purpose | Retention |
|------|---------|-----------|
| `~/recover/{project}/` | Full project snapshots with git history | 5 most recent |
| `/mnt/nas/planb/projects/{project}/` | NAS copy (full, no .gitignore) | Indefinite |
| `/mnt/nas/planb/projects/{project}/.trash/` | Deleted files from previous pushes (rsync --backup) | Kept per-push timestamped |
| `~/projects/{project}/.git/` | GitHub-facing repo | Public |

## Rules

1. **Secrets always backed up** — `.env`, API keys, tokens, certs are in the
   recovery + NAS snapshots even though `.gitignore` hides them from GitHub
2. **Recovery is local** — `~/recover/` lives on your laptop SSD. NAS is
   off-site protection
3. **No silent failures** — Both functions echo status. If the NAS is
   unreachable the push succeeds but the backup visibly skips with a warning
4. **No cron, no tarballs** — Everything is event-driven off `git commit` / `git push`
