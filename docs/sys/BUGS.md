# Created: 2026-07-24
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Path: docs/sys/BUGS.md
# Purpose: Bug tracker for the kissPWM_v6 project.

# kissPWM_v6 Bug Tracker

## F0 — `resource_path()` references `sys._MEIPASS` without module-level `sys` import

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, gui, packaging
- **Description**: `resource_path()` in `main_app_pyside.py:58` uses `sys._MEIPASS` to resolve bundled asset paths in PyInstaller builds, but `sys` is only imported at the `__main__` block (line 1233), not at module level. This will cause a `NameError` in frozen builds.
- **Root Cause**: `import sys` is at line 1233 (`if __name__ == "__main__"` block) instead of the top of the file.
- **Fix**: Add `import sys` to the top-level imports in `main_app_pyside.py`.
- **Files**: `main_app_pyside.py`

## F1 — `find_and_remove_duplicates()` calls backup before docstring

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, database
- **Description**: In `db_manager.py:244`, `self.create_pre_op_backup("Duplicate Removal")` is called on the line immediately after `def find_and_remove_duplicates(self):`, before the docstring and actual logic. While Python still executes this correctly (the docstring is a no-op string literal), the intent is confusing — the backup call looks like it belongs to the previous method or is misplaced.
- **Root Cause**: The `create_pre_op_backup` call was placed between the method signature and the docstring during a refactor, making the execution order non-obvious.
- **Fix**: Move `self.create_pre_op_backup("Duplicate Removal")` to after the docstring, at line ~256.
- **Files**: `db_manager.py`

## F2 — `assets/kiss_icon.ico` referenced but `assets/` directory does not exist

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, gui
- **Description**: `main_app_pyside.py:252` attempts to load an icon from `assets/kiss_icon.ico`, but no `assets/` directory exists in the project. The error is silently caught and logged to console only.
- **Root Cause**: Icon file was planned but never created/committed.
- **Fix**: Create `assets/` directory with a valid `.ico` (or `.png`) application icon, or remove the icon reference. Update `kiss_pwm_v6.spec` to bundle `assets/` if not already done.
- **Files**: `assets/kiss_icon.ico` (missing), `main_app_pyside.py`, `kiss_pwm_v6.spec`

## F3 — Auto-lock triggers immediately on WindowDeactivate

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, security, ui
- **Description**: `_check_focus_lock()` called `lock_application()` immediately on `WindowDeactivate`, bypassing the configured lockout timeout. Switching to another window (e.g., terminal) would lock the vault instantly regardless of the 3-minute setting.
- **Root Cause**: `eventFilter` called `_check_focus_lock()` on `WindowDeactivate`, which locked immediately if lockout was not set to "Never".
- **Fix**: Changed `WindowDeactivate` handler to call `reset_activity_timer()` instead of `_check_focus_lock()`. The configured timeout is now respected.
- **Files**: `src/gui/app.py`

## F4 — Password strength bar hidden by Email QLineEdit in grid cell

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, ui
- **Description**: The `PasswordStrengthBar` was placed at grid row 4 column 1, but the Email QLineEdit was also at row 4 column 1 (due to `enumerate` indices). The QLineEdit overwrote the progress bar, making it invisible.
- **Root Cause**: Using `enumerate` for grid rows with an extra row inserted for the strength bar caused a cell collision.
- **Fix**: Replaced `enumerate` with an independent `row` counter that increments past the strength bar row (row += 1 inside the password block).
- **Files**: `src/gui/app.py`

## F5 — File → Quit minimizes to tray instead of quitting

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, ui
- **Description**: File → Quit called `self.close()` which triggered `closeEvent` → minimize to tray. There was no way to actually quit the application from the menu.
- **Root Cause**: `closeEvent` always minimized to tray when tray icon was visible.
- **Fix**: Created `_quit_application()` that hides tray, runs cleanup, and calls `QApplication.quit()`. Both File → Quit and tray → Quit use this method.
- **Files**: `src/gui/app.py`

## F6 — Header text clipped in credential table

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, ui
- **Description**: The horizontal header text in the credential table was partially visible, with words cut off at the edges. Increasing column widths or reducing padding didn't fully resolve it.
- **Root Cause**: The QHeaderView section height was determined by content and padding, but the minimum size wasn't enough for the bold 11pt font with 4px padding.
- **Fix**: Added `horizontalHeader().setFixedHeight(50)` to force adequate header height.
- **Files**: `src/gui/app.py`

## F7 — `sectionClicked.disconnect()` RuntimeWarning on every table refresh

- **Status**: Fixed
- **Fixed**: 2026-07-24
- **Found**: 2026-07-24
- **Tags**: bug, performance
- **Description**: Every call to `update_list_view()` tried to disconnect and reconnect the `sectionClicked` signal, producing a RuntimeWarning: "Failed to disconnect (None) from signal".
- **Root Cause**: Signal connection/disconnection happened in `update_list_view` (called on every credential change) instead of during table creation.
- **Fix**: Moved `h.sectionClicked.connect(self._handle_sort)` to `create_main_content` where the table is created once.
- **Files**: `src/gui/app.py`
