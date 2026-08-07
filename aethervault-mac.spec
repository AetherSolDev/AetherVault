# -*- mode: python ; coding: utf-8 -*-
# Created: 2026-08-06
# Last Edited: 2026-08-06 22:38 CT (America/Chicago)
# Path: aethervault-mac.spec
# Purpose: PyInstaller spec for building the macOS .app bundle (onedir + BUNDLE).

import re

# Parse the version from aethervault/__init__.py instead of importing it —
# PyInstaller's spec exec doesn't guarantee the package is importable.
with open("aethervault/__init__.py", "r", encoding="utf-8") as _f:
    _version = re.search(r'__version__ = "([^"]+)"', _f.read()).group(1)

a = Analysis(
    ['aethervault/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('aethervault/assets', 'assets'), ('aethervault/docs', 'docs'), ('README.md', '.'), ('LICENSE', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='aethervault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='aethervault',
)

app = BUNDLE(
    coll,
    name='AetherVault.app',
    icon=None,
    bundle_identifier='com.aethersol.aethervault',
    info_plist={
        'CFBundleShortVersionString': _version,
        'CFBundleVersion': _version,
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
)
