# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/lmj/projects/ai-project/qixiaofu-bid-crawler/app.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/lmj/projects/ai-project/qixiaofu-bid-crawler/web/templates', 'web/templates'), ('/Users/lmj/projects/ai-project/qixiaofu-bid-crawler/web/static', 'web/static'), ('/Users/lmj/projects/ai-project/qixiaofu-bid-crawler/config.json', '.')],
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
    name='qixiaofu-bid-crawler-macos',
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
)
