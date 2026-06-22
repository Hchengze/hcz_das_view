# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the HCZ DAS View GUI.

Run from the repository root:

    python -m PyInstaller packaging/hcz_das_view.spec --clean --noconfirm
"""

from pathlib import Path


block_cipher = None
repo_root = Path.cwd()

a = Analysis(
    [str(repo_root / "das_view" / "gui" / "app.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "matplotlib.backends.backend_qt5agg",
        "h5py",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "old_code",
        "validation_outputs",
        "outputs",
        "tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hcz-das-view",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="hcz-das-view",
)
