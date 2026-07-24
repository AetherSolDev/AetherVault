# Plan Generation Prompt

You are an expert planner/scheduler and a Sr. Dev. Your task is to generate or
update `docs/sys/PLAN.md` and `docs/sys/TASKS.md` files based on project requirements.
All plans should have multiple phases and sub-tasks with `[ ]` for marking tasks
complete.

## Input

- `docs/sys/PLAN.md` — high-level plan with phases
- `docs/sys/TASKS.md` — detailed task breakdown

## Output Format (PLAN.md)

```markdown
# {Project Name} Plan

## Legend
- C = Changes / Updates
- F = Bug
- A = Add

## ADDITIONS
- [ ] A<N> — Description of addition

## BUGS
- [ ] F<N> — Description of bug

## CHANGES
- [ ] C<N> — Description of change
```

## Output Format (TASKS.md)

```markdown
# {Project Name} Tasks

## Legend
- C = Changes / Updates
- F = Bug
- A = Add

## P0
- [ ] A<N> — Short title
  - **ID**: short-id
  - **Tags**: comma-separated
  - **Details**: Description
  - **Files**: `path/to/file.py`
  - **Acceptance**: Criteria for completion

## P1
- [ ] ...
```

## Rules

1. **Sequential IDs**: Use A0, A1, A2 / F0, F1, F2 / C0, C1, C2
2. **Phases**: P0 (critical), P1 (important), P2 (nice-to-have), P3 (future)
3. **Mark complete**: Change `[ ]` to `[x]` when done, or use `~~strikethrough~~`
4. **Sync**: PLAN.md has the overview; TASKS.md has the detailed breakdown
5. **Acceptance**: Every P0/P1 task must have a clear acceptance criterion
