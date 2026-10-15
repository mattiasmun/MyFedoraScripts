#!/usr/bin/env bash
#
# Clear Shader Cache for Men of War II (AppID: 1128860)

set -euo pipefail

APP_ID="1128860"
STEAM_DIR="${HOME}/.local/share/Steam"

echo "=== Rensar Shader Cache för Men of War II ==="

# 1. Kontrollera om Steam körs
if pgrep -x "steam" > /dev/null; then
    echo "⚠️  Steam körs för närvarande. Stäng av Steam helt och försök igen."
    exit 1
fi

# 2. Ta bort Steams centrala shadercache
CACHE_DIR="${STEAM_DIR}/steamapps/shadercache/${APP_ID}"
if [ -d "${CACHE_DIR}" ]; then
    rm -rf "${CACHE_DIR}"
    echo "✔ Raderade Steams shadercache: ${CACHE_DIR}"
else
    echo "ℹ Hittade ingen huvud-shadercache att radera."
fi

# 3. Ta bort shaderhitcache i userdata
echo "🔍 Söker efter shaderhitcache i userdata..."
find "${STEAM_DIR}/userdata" -type f -name "${APP_ID}_pbuf" -print -delete 2>/dev/null || true
echo "✔ Shaderhitcache rensad."

# 4. Ta bort spelets interna GEM Engine shadercache i Proton-prefixet
PREFIX_CACHE="${STEAM_DIR}/steamapps/compatdata/${APP_ID}/pfx/drive_c/users/steamuser/AppData/Local/my games/men of war ii/profiles/shader_cache"
if [ -d "${PREFIX_CACHE}" ]; then
    rm -rf "${PREFIX_CACHE}"
    echo "✔ Raderade spelets interna shader_cache i Proton-prefixet."
else
    echo "ℹ Hittade ingen intern shader_cache i Proton-prefixet."
fi

echo "=== Klart! Nya shaders byggs upp nästa gång spelet startas. ==="
