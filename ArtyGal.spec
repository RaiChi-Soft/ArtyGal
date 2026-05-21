# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('rich._unicode_data')


a = Analysis(
    ['galgame.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PIL', 'numpy', 'pandas', 'matplotlib', 'matplotlib_inline', 'IPython', 'ipywidgets', 'ipykernel', 'jupyter_client', 'notebook', 'comm', 'traitlets', 'pytest', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy', 'zmq', 'cryptography', 'bcrypt', 'nacl', 'psutil', 'scipy', 'setuptools', 'pkg_resources'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    name='ArtyGal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\400HBI\\490EPN\\EX40AHE\\2026052101_ArtyGal\\resources\\artygal.ico'],
)
