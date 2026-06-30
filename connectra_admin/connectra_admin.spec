# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


python_root = Path(sys.base_prefix)
python_dlls = python_root / 'DLLs'
ssl_binaries = [
    (str(python_dlls / '_ssl.pyd'), '.'),
    (str(python_dlls / '_socket.pyd'), '.'),
    (str(python_dlls / 'libssl-3-x64.dll'), '.'),
    (str(python_dlls / 'libcrypto-3-x64.dll'), '.'),
]


a = Analysis(
    ['main.py'],
    pathex=['..'],
    binaries=ssl_binaries,
    datas=[],
    hiddenimports=['_hashlib', 'ssl', '_ssl'],
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
    name='connectra_admin',
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
