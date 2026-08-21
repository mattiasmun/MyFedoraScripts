#!/usr/bin/env bash
set -euo pipefail

USER_BIN="$HOME/.local/bin"
USER_SITE=$(python3 -m site --user-site)

if [ ! -d "$USER_SITE" ]; then
    echo "Ingen user-site-katalog hittades."
    exit 0
fi

echo "Söker efter CLI-verktyg i $USER_SITE..."

# Skapa temporära filer för lista över paket
USER_PACKAGES=$(mktemp)
python3 -c "import pkg_resources; print('\n'.join([p.project_name for p in pkg_resources.find_distributions('$USER_SITE')]))" > "$USER_PACKAGES"

MIGRATED=()

while IFS= read -r pkg; do
    [ -z "$pkg" ] && continue

    # Hitta executable-filer kopplade till paketet via metadata (dist-info/egg-info)
    DIST_INFO=$(find "$USER_SITE" -maxdepth 1 -iname "${pkg//-/_}-*.dist-info" -o -iname "${pkg}-*.dist-info" | head -n 1)
    
    HAS_BIN=0
    if [ -n "$DIST_INFO" ] && [ -f "$DIST_INFO/entry_points.txt" ]; then
        if grep -q "\[console_scripts\]" "$DIST_INFO/entry_points.txt"; then
            HAS_BIN=1
        fi
    fi

    # Om paketet har CLI-skript, migrera det
    if [ "$HAS_BIN" -eq 1 ]; then
        echo "----------------------------------------"
        echo "Hittade CLI-verktyg: $pkg"
        
        # Installera med uv tool
        if uv tool install "$pkg" --force; then
            MIGRATED+=("$pkg")
        else
            echo "Kunde inte installera $pkg med uv tool. Hoppar över avinstallation."
        fi
    fi
done < "$USER_PACKAGES"

rm -f "$USER_PACKAGES"

# Avinstallera migrerade paket från pip --user
if [ ${#MIGRATED[@]} -gt 0 ]; then
    echo "----------------------------------------"
    echo "Rensar gamla paket från pip --user..."
    python3 -m pip uninstall -y "${MIGRATED[@]}"
    echo "----------------------------------------"
    echo "Migreringen klar! Följande verktyg hanteras nu av uv tool:"
    printf ' - %s\n' "${MIGRATED[@]}"
else
    echo "Inga CLI-verktyg hittades att migrera."
fi
