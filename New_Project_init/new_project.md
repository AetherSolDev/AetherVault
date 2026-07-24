# Created: 2026-07-21
# Last Edited: 2026-07-21 10:50 CT (America/Chicago)
# Path: templates/new_project.md
# Purpose: New project initialization checklist. Use ONCE at project start.

# New Project Setup Checklist

## 1. Repository Initialization

- [ ] Create project directory
- [ ] Initialize git: `git init`
- [ ] Create `.gitignore` (copy from templates/.gitignore)
- [ ] Create `.repomixignore` (copy from templates/.repomixignore)
- [ ] Create initial commit: `git add . && git commit -m "init: initial project structure"`
- [ ] (Optional) Create remote repo and push

## 2. Copy Template Structure

```bash
# Copy the template system into your new project
cp -r /path/to/templates/AGENTS.md ./AGENTS.md
cp -r /path/to/templates/instructions/ ./instructions/
cp -r /path/to/templates/docs/ ./docs/
cp -r /path/to/templates/scripts/ ./scripts/
```

- [ ] AGENTS.md — master guide copied and customized
- [ ] instructions/ — prompt templates copied
- [ ] docs/ — user guide and doc skeletons copied
- [ ] scripts/ — utility scripts copied

## 3. Customize AGENTS.md

- [ ] Replace all `{project_id}` placeholders with your directory name (e.g., `my_project`)
- [ ] Search for any remaining hardcoded paths and replace with `$HOME/projects/{project_id}/` convention
- [ ] Update critical file list to match your project
- [ ] Update Database Schema section if applicable
- [ ] Update High Cost Alert timezone if different from CT
- [ ] Remove or update Critical Rules that are project-specific

## 4. Initialize Project Files

- [ ] Create `docs/sys/PLAN.md` with initial phases
- [ ] Create `docs/sys/TASKS.md` with initial tasks
- [ ] Create `docs/sys/CHANGELOG.md` with first entry
- [ ] Create `docs/sys/ARCHITECTURE.md` with your project structure
- [ ] Create `docs/sys/KNOWLEDGE.md` with architecture TL;DR, critical files, key decisions
- [ ] Create `docs/sys/{project_id}.mmd` for mermaid diagram
- [ ] Create `docs/sys/BUGS.md` (empty tracker)
- [ ] Update `docs/sys/COST.md` with your pricing details
- [ ] Update `docs/sys/Model_Pricing_Reference.txt` with current rates
- [ ] Write `docs/USER_GUIDE.md` with features, installation, troubleshooting
- [ ] Build combined reference: `python scripts/build_reference.py`

## 5. Development Environment

- [ ] Install template tooling: `pip install -r requirements.txt` (only `mermaidx` if needed)
- [ ] Add your project-specific dependencies (e.g., `PySide6`, `flask`, `fastapi`) to `requirements.txt`
- [ ] Set up virtual environment: `python -m venv venv`
- [ ] Verify `.repomixignore` exists for AI context management
- [ ] Run initial lint/typecheck to establish baseline

## 6. First Commit

```bash
git add .
git commit -m "init: project scaffolding with template system"
```

## Post-Setup

After this checklist is complete, `templates/new_project.md` has served its purpose.
Refer to `AGENTS.md` and `instructions/` for ongoing development guidance.

### Session Resumption Protocol

When resuming after a gap (days/months):
1. Read `docs/sys/REFERENCE.md` or `docs/sys/REFERENCE.html` — full project overview
2. Read `docs/sys/KNOWLEDGE.md` — fastest context recovery
3. Read `AGENTS.md` for current rules
4. Read last 3 entries of `docs/sys/CHANGELOG.md` for recent changes
5. Only then read specific source files if needed

### Regenerate Reference

After any significant change to `docs/sys/`:
```bash
python scripts/build_reference.py
```
