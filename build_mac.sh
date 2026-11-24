#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[Setup] Creating Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Convert assets/icon.png to macOS .icns icon using built-in sips/iconutil
ICON_ARGS=""
if [ -f "assets/icon.png" ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
    echo "[Build] Generating macOS app icon (.icns)..."
    ICONSET_DIR="build/AppIcon.iconset"
    rm -rf "$ICONSET_DIR"
    mkdir -p "$ICONSET_DIR"
    sips -z 16 16     assets/icon.png --out "$ICONSET_DIR/icon_16x16.png"      >/dev/null
    sips -z 32 32     assets/icon.png --out "$ICONSET_DIR/icon_16x16@2x.png"   >/dev/null
    sips -z 32 32     assets/icon.png --out "$ICONSET_DIR/icon_32x32.png"      >/dev/null
    sips -z 64 64     assets/icon.png --out "$ICONSET_DIR/icon_32x32@2x.png"   >/dev/null
    sips -z 128 128   assets/icon.png --out "$ICONSET_DIR/icon_128x128.png"    >/dev/null
    sips -z 256 256   assets/icon.png --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
    sips -z 256 256   assets/icon.png --out "$ICONSET_DIR/icon_256x256.png"    >/dev/null
    sips -z 512 512   assets/icon.png --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
    iconutil -c icns "$ICONSET_DIR" -o build/icon.icns
    ICON_ARGS="--icon build/icon.icns"
fi

echo "[Build] Building dist/UnderdarkMacroSolver.app..."
python3 -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onedir \
    --name "UnderdarkMacroSolver" \
    --add-data "assets:assets" \
    --collect-all adbutils \
    $ICON_ARGS \
    main.py

# Clear macOS quarantine flag if set
xattr -cr dist/UnderdarkMacroSolver.app 2>/dev/null || true

echo ""
echo "[Done] Build complete: dist/UnderdarkMacroSolver.app"
echo "Finder에서 dist/UnderdarkMacroSolver.app을 더블클릭하거나 응용 프로그램 폴더로 옮겨 실행하세요."
