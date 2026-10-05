# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Gather data files
datas = [
    ('app/assets', 'app/assets'),
    ('icon.ico', '.'),
    ('clock_config.example.json', '.'),
]

# Include yt-dlp.exe if present
if os.path.exists('app/bin/yt-dlp.exe'):
    datas.append(('app/bin/yt-dlp.exe', 'app/bin'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.colorchooser',
        'winsound',
        'urllib.request',
        'urllib.parse',
        'ssl',
        'json',
        'wave',
        'struct',
        'math',
        'random',
        'threading',
        'subprocess',
        'datetime',
        'time',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FloatingClock',
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
    icon='icon.ico',
)
