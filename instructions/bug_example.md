# Bug Tracker Prompt

You are an expert bug tracker. Your task is to create or update `docs/sys/BUGS.md`
with structured bug entries following the format below.

## Bug Entry Format

Each bug gets its own `##` section with the following fields:

```markdown
## F<N> — Brief title

- **Status**: Open | Fixed | In Progress
- **Found**: YYYY-MM-DD
- **Fixed**: YYYY-MM-DD (if applicable)
- **Tags**: comma-separated keywords
- **Description**: Clear explanation of the bug, steps to reproduce
- **Root Cause**: What caused the bug at the code level
- **Fix**: What change resolved it
- **Files**: `path/to/file.py`, `path/to/another.py`
```

## Rules

1. **Sequential IDs**: Use F0, F1, F2, ... — never reuse an ID
2. **Status**: Only `Open`, `Fixed`, or `In Progress`
3. **Fixed date**: Only include when status is `Fixed`
4. **Tags**: Reuse existing tags from the project (e.g., `gui`, `database`, `core`)
5. **Root Cause**: Be specific — what function, what assumption was wrong
6. **Files**: Use backtick-wrapped relative paths from project root

## Example

```markdown
## F0 — Calendar does not show Sunday in Unified Entry Editor

- **Status**: Fixed
- **Found**: 2026-07-20
- **Fixed**: 2026-07-20
- **Tags**: gui, calendar
- **Description**: The QDateTimeEdit calendar popup uses the locale default
  first day of week (Monday), so Sunday is not visible as the first column.
- **Root Cause**: `setCalendarPopup(True)` was called but
  `setFirstDayOfWeek(Qt.Sunday)` was never set on the calendar widget.
- **Fix**: Added `self.due_date_edit.calendarWidget().setFirstDayOfWeek(Qt.Sunday)`
  after `setCalendarPopup(True)`.
- **Files**: `src/gui/widgets/unified_task_editor.py`
```

## Documentation
- Update `docs/sys/CHANGELOG.md` with a ### Fixed section for each bug fixed.
