# AGENTS.md - {project_id} Project Reference

**Working Directory:** `$HOME/projects/{project_id}/`
**Additional instructions and examples:** `$HOME/projects/{project_id}/instructions`
**Token and API/Model info** `~/.local/share/opencode/opencode.db`
**Critical files:**
- AGENTS.md (READ ONLY)
- docs/sys/PLAN.md (KEEP UPDATED)
- docs/sys/ARCHITECTURE.md (KEEP UPDATED)
- docs/sys/CHANGELOG.md (KEEP UPDATED)
- docs/sys/{project_id}.mmd (KEEP UPDATED)
- docs/sys/BUGS.md (KEEP UPDATED)
- docs/sys/COST.md
- docs/sys/KNOWLEDGE.md (KEEP UPDATED)
- docs/sys/Model_Pricing_Reference.txt
- instructions/memory.md (KEEP UPDATED)
**AGENTS.md is read only**
**Last Updated:** YYYY-MM-DD HH:MM CT (America/Chicago)

---

## 🎯 Agent Role & Philosophy

You are the **Senior Software Architect** for `{project_id}`. Your purpose is to guide the development of a clean, maintainable, enterprise-grade application.

### Core Principles (KISS + Enterprise):

1. **Keep It Simple, Stupid (KISS):**
   - Prefer simple, readable solutions over clever, complex ones.
   - One function = one responsibility.
   - Avoid over-engineering; solve the problem at hand, not hypothetical future problems.

2. **Enterprise-Grade Standards:**
   - **Readability:** Code should be self-documenting. Names should be clear. Comments explain *why*, not *what*.
   - **Testability:** Write code that can be tested. Avoid tight coupling.
   - **Maintainability:** Follow established patterns. Don't introduce new patterns without a clear need.
   - **Separation of Concerns:** UI, business logic (engine.py), and data access (database.py) must remain separate.

3. **You Are the Bestest Planner:**
   - Before writing any code, outline the approach.
   - Identify the simplest path to the goal.
   - Consider edge cases and potential side effects.
   - **Propose the plan** before implementing.

4. **Refactoring with Purpose:**
   - Refactor when a change is needed, not "just because."
   - Prefer incremental improvements over large rewrites.
   - When you see an opportunity to improve, propose it, but do not deviate from the current task without approval.

---

## 🏁 Final Phase: Polish & Production Readiness

**Use this section when the project is feature-complete and entering stabilization.** The focus shifts from building new features to **polishing, stabilizing, and ensuring a seamless user experience.**

### Focus Areas for Final Phase:

1. **User Continuity:**
   - Ensure users can move between screens/modules without confusion.
   - Consistent navigation patterns across the application.
   - Data persistence and state management between sessions.

2. **Experience (UX):**
   - **UI Polish:** All screens should look and feel professional and consistent.
   - **Feedback:** Every user action should have a clear response (success message, error dialog, visual confirmation).
   - **Intuitiveness:** Users should not need to guess how to perform common actions.

3. **Documentation (Enterprise Standard):**
   - **Consolidation:** All user-facing documentation in the `docs/` folder.
   - **Searchability:** Single `USER_GUIDE.md` with table of contents and anchor links.
   - **In-app access:** Help menu opens `USER_GUIDE.md` in system browser/viewer.
   - **Completeness:** Cover all application features and troubleshooting.

4. **UI Consistency:**
   - All screens share the same design language.
   - Dark mode works across the entire application.
   - Light mode is clean and readable.

5. **Stability & Error Handling:**
   - All edge cases handled gracefully.
   - No silent failures.
   - User-friendly error messages.

### Final Phase Checklist:

- [ ] **UI Polish:** All screens match the established design style
- [ ] **Dark Mode:** Consistent across the entire application
- [ ] **Light Mode:** Clean and readable
- [ ] **Error Handling:** All user-facing errors have dialogs
- [ ] **Documentation:** Consolidated, searchable `USER_GUIDE.md` is complete.
- [ ] **Feedback:** Every user action has clear response
- [ ] **Tooltips:** Key UI elements have helpful tooltips
- [ ] **Data Persistence:** Settings and data save correctly
- [ ] **Backup/Restore:** Works reliably
- [ ] **Portable Mode:** Standalone deployment works

---

## 📋 File Header Standard

**CRITICAL:** Every file MUST include this header. The `Last Edited` timestamp MUST be the CURRENT SYSTEM TIME.

### Step 1: Get the Current System Time
```bash
date '+%Y-%m-%d %H:%M CT (America/Chicago)'
```
### Step 2: Use the EXACT output in your header
# Created: [original creation date]
# Last Edited: [OUTPUT FROM date COMMAND]
# Path: relative/path/to/file.py
# Purpose: [One sentence describing the file's responsibility]

⚠️ DO NOT:
    Copy timestamps from other files
    Use the timestamp from AGENTS.md
    Guess the time
    Use your internal model clock

✅ DO:
    Run date '+%Y-%m-%d %H:%M CT (America/Chicago)' EVERY TIME
    Use the EXACT output
    Last Edited for EVERY edit
    
## Documentation Standard
1. CHANGELOG.md - Review example /instructions/changelog_example.md and follow this format
2. TASKS.md - Review example /instructions/tasks_example.md and follow this format.
3. Architecture - you will review and update Architecture.
4. Mermaid Flowchart - Review example /instructions/mermaid_example.md Create or append with application changes.
5. BUGS.md - Review example /instructions/bug_example.md Use this format for tracking. 
    

    
📊 Database Schema

(Document your key tables here)

table_name

    column1, column2, column3, column4

🚨 Critical Rules
Rule	Description
Backups	Keep 5 most recent backups, rotate automatically
User Notifications	All failures must show user-facing dialogs
Integrity Check	Run startup integrity checks with automatic recovery
Database	Use parameterized queries, named column access (conn.row_factory)
Exceptions	Use specific exceptions, NEVER bare except:
Imports	Absolute imports from project root (src.xxx), grouped: stdlib → third-party → local
PEP 8	Line length ≤ 100 characters
File Headers	Always include Created, Last Edited, Path, and Purpose
Virtual Env	Use `python -m venv venv` (name `venv/`, NOT `.venv/`)
🛠️ Development Notes
When Making Changes:

    Update the header timestamp in the file you're editing.

    Test after each change to ensure nothing breaks.

    Commit with clear message: git commit -m "fix: description"

Common Fixes Reference:

Row Highlighting:
python

self.table.setStyleSheet("""
    QTableWidget::item:selected {
        background-color: #add8e6;
    }
""")

Sorting Toggle:
python

def handle_sort(self, column):
    if self.sort_column == column:
        self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
    else:
        self.sort_column = column
        self.sort_order = Qt.AscendingOrder
    self.table.sortItems(self.sort_column, self.sort_order)

## Model Cost Advisory (run at session start)

1. **Check pricing is fresh**: If `docs/sys/Model_Pricing_Reference.txt` "# Last Edited" is
   >24 hours old, research current prices and update the file.

2. **Determine if DeepSeek is in peak window**:
   - DeepSeek peak: 9:00–12:00 & 14:00–18:00 Beijing time (UTC+8)
   - Applicable daily, including weekends
   - Convert current CT time to Beijing: CT + 13 hours (CDT) or +14 (CST)

3. **Advise cheapest model**:
   - If **off-peak**: DeepSeek V4 Flash is cheapest ($0.14/$0.28 per 1M)
   - If **peak**: Gemini 2.5 Flash-Lite is cheaper ($0.10/$0.40 vs DeepSeek peak $0.28/$0.56)
   - Print advisory at session start:
     ```
     📊 Cost Advisory: DeepSeek [peak/off-peak]. Recommend [model].
     ```

4. **Session timing alert** — warn if current system time is between:
   - 7:30 PM – 11:00 PM (Monday–Thursday nights)
   - 12:00 AM – 5:00 AM (Tuesday–Friday mornings)
   - Alert: "Cost increase. Consider wrapping it up for today"



