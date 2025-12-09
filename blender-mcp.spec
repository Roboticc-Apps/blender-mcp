# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Blender MCP
# Bundles the MCP server as a standalone executable for OneController

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all MCP and related package data
datas = []
datas += collect_data_files('mcp')

# Include addon.py in the distribution
datas += [('addon.py', '.')]

# Collect all hidden imports for MCP and dependencies
hiddenimports = []
hiddenimports += collect_submodules('mcp')
hiddenimports += collect_submodules('blender_mcp')
hiddenimports += [
    'asyncio',
    'socket',
    'json',
    'logging',
    'tempfile',
    'contextlib',
    'typing',
    'pathlib',
    'base64',
    'urllib.parse',
    'supabase',
    'tomli',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='blender-mcp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # REQUIRED: Console mode for stdio JSON-RPC communication
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
