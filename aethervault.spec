# -*- mode: python ; coding: utf-8 -*-
# Created: 2026-07-24
# Last Edited: 2026-08-01 01:55 CT (America/Chicago)
# Path: aethervault.spec
# Purpose: PyInstaller build spec for AetherVault standalone executable.

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
    a.binaries,
    a.datas,
    [],
    name='aethervault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
