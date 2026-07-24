
#!/usr/bin/env python3
# Created: 2026-07-14 14:30 CT (America/Chicago)
# Last Edited: 2026-07-20 08:44 CT (America/Chicago)
# Path: scripts/create_portable.py
# Purpose: Create portable version and build preparation with versioning

import re
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Configurable — set to your project name
PROJECT_ID = "kissPWM_v6"


def get_current_version():
    """Read the current version from version.py."""
    version_file = Path(__file__).parent.parent / "src" / "shared" / "version.py"
    if not version_file.exists():
        return "2.5.0"
    
    with open(version_file, 'r') as f:
        content = f.read()
    
    match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    return "2.5.0"


def bump_version(version, bump_type="patch"):
    """Bump version number."""
    major, minor, patch = version.split('.')
    if bump_type == "major":
        return f"{int(major) + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{int(minor) + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{int(patch) + 1}"


def update_version_file(bump_type="patch"):
    """Update version.py with new version and build date."""
    version_file = Path(__file__).parent.parent / "src" / "shared" / "version.py"
    
    if not version_file.exists():
        version_file.parent.mkdir(parents=True, exist_ok=True)
        current_version = "2.5.0"
    else:
        current_version = get_current_version()
    
    new_version = bump_version(current_version, bump_type)
    now = datetime.now()
    build_date = now.strftime("%Y-%m-%d")
    build_time = now.strftime("%H:%M CT")
    
    content = f'''# Created: 2026-07-14 13:00 CT (America/Chicago)
# Last Edited: {now.strftime('%Y-%m-%d %H:%M CT (America/Chicago)')}
# Path: src/shared/version.py
# Purpose: Centralized version management for {PROJECT_ID}

# Version format: MAJOR.MINOR.PATCH
# MAJOR: Breaking changes
# MINOR: New features, backward compatible
# PATCH: Bug fixes, backward compatible

VERSION = "{new_version}"
BUILD_DATE = "{build_date}"
BUILD_TIME = "{build_time}"

def get_version_string() -> str:
    """Return the full version string."""
    return f"v{{VERSION}}"

def get_about_text() -> str:
    """Return the about dialog text."""
    return f"""
    <b>{PROJECT_ID} Enterprise</b><br>
    Version: {{VERSION}}<br>
    Build: {{BUILD_DATE}} {{BUILD_TIME}}<br><br>
    Professional task management and enterprise-grade time tracking solution.<br><br>
    &copy; 2026 {PROJECT_ID} Solutions. All rights reserved.
    """
'''
    
    with open(version_file, 'w') as f:
        f.write(content)
    
    print(f"📝 Version bumped: {current_version} → {new_version}")
    return new_version


def fix_windows_paths(file_path: Path) -> None:
    """
    Fix file paths for Windows compatibility.
    Converts Linux-style paths to Windows-style paths in the file.
    """
    if not file_path.exists():
        return
    
    print(f"🔧 Fixing Windows paths in: {file_path.name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    # Fix specific Windows path issues - simple replacements only
    # Ensure get_base_path() and get_data_path() work on Windows
    if "def get_base_path()" in content:
        # Make sure it uses .resolve() for absolute paths
        if ".resolve()" not in content:
            content = content.replace(
                "return Path(sys.executable).parent",
                "return Path(sys.executable).parent.resolve()"
            )
            content = content.replace(
                "return Path(__file__).parent",
                "return Path(__file__).parent.resolve()"
            )
            changes_made = True
    
    # Add Windows crash handler to main.py if not already present
    if file_path.name == "main.py" and "def setup_crash_handler" not in content and "def setup_windows_crash_handler" not in content:
        crash_handler = '''
def setup_crash_handler():
    """Set up crash handling for Windows."""
    if sys.platform == 'win32':
        # Create a crash log directory
        crash_dir = Path(os.path.dirname(sys.executable)) / "crash_logs"
        crash_dir.mkdir(parents=True, exist_ok=True)
        
        def crash_handler(exc_type, exc_value, exc_tb):
            error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            crash_file = crash_dir / f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            with open(crash_file, 'w') as f:
                f.write(error_msg)
            try:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "{PROJECT_ID} Crash", 
                    f"The application crashed. Please send this file to support:\n{crash_file}")
            except ImportError:
                pass
        
        sys.excepthook = crash_handler

# Call this at the very beginning
setup_crash_handler()
'''
        # Find the main block and insert before it
        if "if __name__ == \"__main__\":" in content:
            content = content.replace(
                "if __name__ == \"__main__\":",
                f"{crash_handler}\n\nif __name__ == \"__main__\":"
            )
            changes_made = True
    
    # Write back if changes were made
    if changes_made or content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Fixed Windows paths in: {file_path.name}")


def fix_all_windows_paths(build_dir: Path) -> None:
    """Fix Windows paths in all Python files in the build directory."""
    print("\n🔧 Fixing Windows paths in build directory...")
    
    # Files to fix
    files_to_fix = [
        build_dir / "main.py",
        build_dir / "src" / "gui" / "main_window.py",
        build_dir / "src" / "shared" / "utils.py",
        build_dir / "src" / "shared" / "database.py",
        build_dir / "src" / "gui" / "widgets" / "tracker_tab.py",
        build_dir / "src" / "gui" / "widgets" / "unified_task_editor.py",
        build_dir / "src" / "gui" / "widgets" / "overview.py",
        build_dir / "src" / "gui" / "widgets" / "billable_hours.py",
    ]
    
    for file_path in files_to_fix:
        if file_path.exists():
            fix_windows_paths(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")


def create_portable():
    """Create a simple portable version of {PROJECT_ID}."""
    
    # Bump version for the portable release
    version = update_version_file("patch")
    
    project_root = Path(__file__).parent.parent
    portable_root = project_root / "{PROJECT_ID}Portable"
    
    print("=" * 60)
    print(f"🔵 {PROJECT_ID} Portable Creator - v{version}")
    print("=" * 60)
    print(f"📁 Target: {portable_root}")
    print("=" * 60)
    
    # Remove existing
    if portable_root.exists():
        print(f"🗑️  Removing existing {portable_root}")
        shutil.rmtree(portable_root)
    
    # Create structure
    print("\n📁 Creating directory structure...")
    app_dir = portable_root / "App" / "{PROJECT_ID}"
    data_dir = portable_root / "Data"
    docs_dir = portable_root / "Docs"
    assets_dir = portable_root / "App" / "{PROJECT_ID}" / "assets"
    
    app_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (data_dir / "backups").mkdir(exist_ok=True)
    (app_dir / "updates").mkdir(exist_ok=True)
    print("✅ Created directories")
    
    # Copy docs
    print("\n📄 Copying documentation...")
    docs_source = project_root / "docs"
    if docs_source.exists():
        for doc in docs_source.glob("*.md"):
            shutil.copy2(doc, docs_dir / doc.name)
            print(f"✅ Copied {doc.name}")
    else:
        print("⚠️  docs/ not found")
    
    # Copy assets (icon)
    print("\n📄 Copying assets...")
    assets_source = project_root / "assets"
    if assets_source.exists():
        for asset in assets_source.glob("*"):
            if asset.is_file():
                shutil.copy2(asset, assets_dir / asset.name)
                print(f"✅ Copied {asset.name}")
    else:
        print("⚠️  assets/ not found")
    
    # Create launcher with version
    print("\n📄 Creating launcher...")
    batch_content = f"""@echo off
:: {PROJECT_ID} Portable Launcher
:: Version: {version}

cd /d "%~dp0App\\{PROJECT_ID}"
start {PROJECT_ID}.exe
cd /d "%~dp0"
exit
"""
    with open(portable_root / "Start {PROJECT_ID}.bat", "w") as f:
        f.write(batch_content)
    print("✅ Created Start {PROJECT_ID}.bat")
    
    # Create README with version
    readme_content = f"""{PROJECT_ID} Portable
=================
Version: {version}
Built: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}

📁 Structure:
- App/{PROJECT_ID}/{PROJECT_ID}.exe  ← The main program
- App/{PROJECT_ID}/updates/        ← Place updates here
- App/{PROJECT_ID}/assets/         ← Application assets (icon)
- Data/                          ← Your data (database, backups)
- Docs/                          ← Documentation

🚀 To Run:
Double-click "Start {PROJECT_ID}.bat"

📦 To Update:
1. Copy new src/ folder to App/{PROJECT_ID}/updates/
2. Run the app - update applies automatically!

💾 Data Location:
- Data/{project_id}.db  ← Your database
- Data/backups/       ← Automatic backups

For help, see the Docs/ folder.
"""
    with open(portable_root / "README.txt", "w") as f:
        f.write(readme_content)
    print("✅ Created README.txt")
    
    print("\n" + "=" * 60)
    print(f"✅ PORTABLE VERSION {version} CREATED!")
    print("=" * 60)
    print(f"📁 Location: {portable_root}")
    print("\n📂 Next Steps:")
    print("1. Build {PROJECT_ID}.exe (use option 2)")
    print("2. Copy {PROJECT_ID}.exe to App/{PROJECT_ID}/")
    print("3. Copy the folder to her USB drive")
    print("=" * 60)


def prepare_build():
    """Prepare a clean build folder for PyInstaller on Windows."""
    
    # Bump version for the build
    version = update_version_file("patch")
    
    project_root = Path(__file__).parent.parent
    build_dir = project_root / "{PROJECT_ID}Build"
    
    print("=" * 60)
    print(f"🔵 {PROJECT_ID} Build Preparer - v{version}")
    print("=" * 60)
    print(f"📁 Target: {build_dir}")
    print("=" * 60)
    
    # Remove existing FIRST
    if build_dir.exists():
        print(f"🗑️  Removing existing {build_dir}")
        shutil.rmtree(build_dir)
    
    # Create build directory FIRST
    print(f"📁 Creating {build_dir}")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Exclude patterns
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.db",
        "*.db-shm",
        "*.db-wal",
        "*.log",
        "*.csv",
        "*.xlsx",
        "test.py",
        "theme_old.py",
        "backups",
        "logs",
        "tests",
        "scripts",
        "*.spec",
    ]
    
    # Copy main.py
    print("\n📄 Copying main.py...")
    shutil.copy2(project_root / "main.py", build_dir / "main.py")
    print("✅ Copied main.py")
    
    # Copy src/
    print("\n📁 Copying src/...")
    shutil.copytree(
        project_root / "src",
        build_dir / "src",
        ignore=shutil.ignore_patterns(*exclude_patterns)
    )
    print("✅ Copied src/")
    
    # Copy docs/
    print("\n📄 Copying docs/...")
    docs_source = project_root / "docs"
    docs_dest = build_dir / "docs"
    if docs_source.exists():
        shutil.copytree(
            docs_source, 
            docs_dest, 
            ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
        )
        print("✅ Copied docs/")
    else:
        print("⚠️  docs/ not found")
    
    # Copy assets/ (for the icon)
    print("\n📄 Copying assets/...")
    assets_source = project_root / "assets"
    assets_dest = build_dir / "assets"
    if assets_source.exists():
        shutil.copytree(
            assets_source, 
            assets_dest, 
            ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
        )
        print("✅ Copied assets/")
    else:
        print("⚠️  assets/ not found - icon may not work")
    
    # Copy requirements.txt
    print("\n📄 Copying requirements.txt...")
    shutil.copy2(project_root / "requirements.txt", build_dir / "requirements.txt")
    print("✅ Copied requirements.txt")
    
    # Create requirements-build.txt (minimal dependencies)
    print("\n📄 Creating requirements-build.txt...")
    req_build_content = """# Created: 2026-07-16
# Path: requirements-build.txt
# Purpose: Minimal dependencies for {PROJECT_ID} portable build

# Core GUI - REQUIRED
PySide6

# Excel export - REQUIRED (openpyxl handles .xlsx without pandas)
openpyxl

# PyInstaller - REQUIRED for building the EXE
pyinstaller
"""
    with open(build_dir / "requirements-build.txt", "w") as f:
        f.write(req_build_content)
    print("✅ Created requirements-build.txt")
    
    # FIX WINDOWS PATHS - This is the key addition!
    fix_all_windows_paths(build_dir)
    
    # Create build.bat with version and icon support
    print("\n📄 Creating build.bat...")
    build_bat = f"""@echo off
:: {PROJECT_ID} Build Script for Windows
:: Version: {version}
:: Generated: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}

echo ========================================
echo Building {PROJECT_ID} Portable v{version}
echo ========================================
echo.

:: Install dependencies if needed (use requirements-build.txt for minimal build deps)
echo Installing dependencies...
pip install -r requirements-build.txt
echo.

:: Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del *.spec

:: Build the executable with icon and docs
echo Building {PROJECT_ID}.exe...
pyinstaller --onefile --windowed --name {PROJECT_ID} --icon=assets/kiss_icon.ico --add-data "docs;docs" --add-data "assets;assets" main.py

echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo Version: {version}
echo EXE location: dist\\{PROJECT_ID}.exe
echo.
pause
"""
    with open(build_dir / "build.bat", "w") as f:
        f.write(build_bat)
    print("✅ Created build.bat")
    
    # Create README for the build folder
    readme = f"""# {PROJECT_ID} Build Folder
Version: {version}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}

## What's Here
- main.py              - Entry point with update logic
- src/                 - Complete source code (v{version})
- docs/                - Documentation files
- assets/              - Application assets (icon)
- requirements.txt     - Python dependencies
- requirements-build.txt - Minimal dependencies (recommended)
- build.bat            - Windows build script

## How to Build on Windows
1. Copy this entire folder to your Windows machine
2. (Optional) Replace requirements.txt with requirements-build.txt for smaller EXE
3. Open Command Prompt in this folder
4. Run: `build.bat`
5. Find {PROJECT_ID}.exe in the `dist/` folder

## After Build
Copy {PROJECT_ID}.exe and the assets/ folder to:
`{PROJECT_ID}Portable/App/{PROJECT_ID}/`

The docs/ folder should be copied to:
`{PROJECT_ID}Portable/Docs/`
"""
    with open(build_dir / "README.txt", "w") as f:
        f.write(readme)
    print("✅ Created README.txt")
    
    # Show size
    total_size = 0
    for path in build_dir.rglob("*"):
        if path.is_file():
            total_size += path.stat().st_size
    print(f"\n📊 Total size: {total_size / 1024 / 1024:.2f} MB")
    
    print("\n" + "=" * 60)
    print(f"✅ BUILD FOLDER v{version} CREATED!")
    print("=" * 60)
    print(f"📁 Location: {build_dir}")
    print("\n📂 Next Steps:")
    print("1. Copy the entire folder to your Windows VM")
    print("2. On Windows, open Command Prompt in the folder")
    print("3. (Recommended) Replace requirements.txt with requirements-build.txt")
    print("4. Run: build.bat")
    print("5. Copy dist/{PROJECT_ID}.exe to {PROJECT_ID}Portable/App/{PROJECT_ID}/")
    print("6. Copy docs/ to {PROJECT_ID}Portable/Docs/")
    print("7. Copy assets/ to {PROJECT_ID}Portable/App/{PROJECT_ID}/assets/")
    print("=" * 60)


def create_update():
    """Create an update package with version bump."""
    
    # Bump version for the update
    version = update_version_file("patch")
    
    project_root = Path(__file__).parent.parent
    update_dir = project_root / f"{PROJECT_ID}Update_v{version}"
    
    print("\n" + "=" * 60)
    print(f"🔵 Creating Update Package - v{version}")
    print("=" * 60)
    
    if update_dir.exists():
        shutil.rmtree(update_dir)
    
    update_dir.mkdir()
    update_src = update_dir / "src"
    
    shutil.copytree(
        project_root / "src",
        update_src,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "*.db",
            "*.log",
            "*.csv",
            "*.xlsx",
            "test.py",
            "theme_old.py",
        )
    )
    
    # Also include docs in updates
    update_docs = update_dir / "docs"
    docs_source = project_root / "docs"
    if docs_source.exists():
        shutil.copytree(
            docs_source, 
            update_docs,
            ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
        )
        print("✅ Copied docs to update package")
    
    # Also include assets in updates
    update_assets = update_dir / "assets"
    assets_source = project_root / "assets"
    if assets_source.exists():
        shutil.copytree(
            assets_source, 
            update_assets,
            ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
        )
        print("✅ Copied assets to update package")
    
    # Fix Windows paths in the update
    fix_all_windows_paths(update_dir)
    
    readme = f"""# {PROJECT_ID} Update - v{version}

## What's New
- Version: {version}
- Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}

## How to Apply
1. Copy the `src/` folder to: `App/{PROJECT_ID}/updates/`
2. (Optional) Copy `docs/` to: `Docs/` (if documentation changed)
3. (Optional) Copy `assets/` to: `App/{PROJECT_ID}/assets/` (if icon changed)
4. Run the app - it will auto-update!
5. Check Help → About to verify version {version}

## Changes in This Update
- Unified versioning system - version now matches main application
- Consolidated documentation
- Version {version}
"""
    with open(update_dir / "UPDATE_README.txt", "w") as f:
        f.write(readme)
    
    print(f"✅ Update package created: {update_dir}")
    print(f"📁 Version: {version}")
    print("📁 Copy the contents to her USB drive")
    print("📁 She should copy 'src/' to App/{PROJECT_ID}/updates/")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("{PROJECT_ID} Portable Tool")
    print("=" * 60)
    print("1. Create portable folder structure")
    print("2. Prepare build folder for Windows")
    print("3. Create update package")
    print("4. Exit")
    print("=" * 60)
    
    choice = input("Select option (1-4): ").strip()
    
    if choice == "1":
        create_portable()
    elif choice == "2":
        prepare_build()
    elif choice == "3":
        create_update()
    else:
        print("Exiting...")
        sys.exit(0)

