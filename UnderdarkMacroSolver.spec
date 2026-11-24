# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [
    ('assets', 'assets'),
]

# 샘플 이미지가 존재하면 번들에 포함
for sample_file in ['화면캡처.png', '화면캡처 성공.png', '캠프화면.png', '던전선택화면.png', '게임진행화면.png', '게임오버화면.png', '획득보상화면.png', '캠프화면_960_960.png', '던전선택화면_960_960.png', '게임진행화면_960_960.png', '게임오버화면_960_960.png', '심연의모래구멍.png', '언더다크튕김.png', '비밀번호해제못함.png', '일반_810스테이지_던전선택2.png', '일반_810스테이지_보스등장2.png']:
    if os.path.exists(sample_file):
        datas.append((sample_file, '.'))

binaries = []
hiddenimports = []

# adbutils의 내장 바이너리(adb.exe 등) 및 데이터 자동 수집
adb_ret = collect_all('adbutils')
datas += adb_ret[0]
binaries += adb_ret[1]
hiddenimports += adb_ret[2]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='UnderdarkMacroSolver',
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
    icon='assets/icon.ico',
)
