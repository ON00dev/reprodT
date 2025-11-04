# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['source\\reprodT.py'],
    pathex=[],
    binaries=[],
    datas=[('source/ffmpeg-win', 'ffmpeg-win'), ('source/ffmpeg-mac', 'ffmpeg-mac'), ('source/ffmpeg-linux', 'ffmpeg-linux'), ('source/settings.json', '.')],
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
    name='reprodT',
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
    version='pyinstaller.version.txt',
    icon=['assets\\logo.ico'],
)
