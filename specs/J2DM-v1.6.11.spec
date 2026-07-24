# -*- mode: python ; coding: utf-8 -*-

import os

# Spec files live in specs/, one level below the repo root. PyInstaller
# resolves relative paths in this file against the spec file's own
# directory (SPECPATH), not the caller's cwd, so anchor everything to
# the repo root explicitly.
ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

a = Analysis(
    [os.path.join(ROOT, 'convert_jeol_to_dm.py')],
    pathex=[],
    binaries=[],
    datas=[(os.path.join(ROOT, 'templates'), 'templates'), (os.path.join(ROOT, 'THIRD_PARTY_NOTICES.txt'), '.')],
    hiddenimports=['windnd'],
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
    name='J2DM-v1.6.11',
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
    icon=os.path.join(ROOT, 'assets', 'J2DM.ico'),
)
