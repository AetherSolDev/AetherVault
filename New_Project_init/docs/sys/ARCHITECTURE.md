# Created: YYYY-MM-DD
# Last Edited: YYYY-MM-DD HH:MM CT (America/Chicago)
# Path: templates/docs/sys/ARCHITECTURE.md
# Purpose: Architecture diagram for the project.

## Directory Structure
```
src/
├── core/
│   ├── engine.py
│   └── settings.py
├── gui/
│   ├── main_window.py
│   ├── tracker_tab.py
│   ├── widgets/
│   │   ├── overview.py
│   │   ├── billable_hours.py
│   │   ├── settings_widget.py
│   │   ├── analytics_tab.py
│   │   └── unified_task_editor.py
│   └── dialogs/
│       ├── task_dialog.py
│       ├── project_dialog.py
│       └── project_tasks_dialog.py
└── shared/
    ├── database.py
    ├── models.py
    ├── utils.py
    ├── signals.py
    ├── theme.py
    └── error_handler.py
```
