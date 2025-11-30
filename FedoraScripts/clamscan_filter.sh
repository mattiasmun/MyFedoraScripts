#!/bin/bash
# Detta skript fungerar som en mellanhand mellan FiltaQuilla och ClamAV.
# Det skannar den fixa sökvägen där Thunderbird/FiltaQuilla sparar bilagorna.

# --------------------------
# VARIABLER
# --------------------------
# Sökväg till den mapp Thunderbird/FiltaQuilla sparar bilagorna.
SPARAD_BILAGA_DIR="$HOME/.clamtk/attachment"

# Sökväg till din karantänmapp (där infekterade filer flyttas)
KARANTAN_DIR="$HOME/.clamtk/quarantine" 

# Byt till clamdscan för snabbare skanning via daemonen.
CLAMSCAN_BIN="/usr/bin/clamdscan"

# Loggfilens sökväg (vi lägger den i .clamtk/log/)
LOGG_FIL="$HOME/.clamtk/log/clamscan_filter.log"

# --------------------------
# 0. FÖRBEREDELSER
# --------------------------
# Tvinga Bash att starta i hemmakatalogen för att säkra att $HOME är korrekt.
cd "$HOME"

# Skapa karantän- och loggmappar om de inte redan finns.
mkdir -p "$KARANTAN_DIR"
mkdir -p "$HOME/.clamtk/log"

# Lägg till tidsstämpel och miljövärden i loggen
echo "--- Skanning startad: $(date) ---" >> "$LOGG_FIL"
echo "VERKTYG: clamdscan" >> "$LOGG_FIL"
echo "Kontrollerad \$HOME: $HOME" >> "$LOGG_FIL"
echo "Skanningskatalog: $SPARAD_BILAGA_DIR" >> "$LOGG_FIL"
echo "Karantänkatalog: $KARANTAN_DIR" >> "$LOGG_FIL"


# --------------------------
# 0.5. KONTROLLERA INNEHÅLL
# --------------------------
# Säkerställ att om det inte finns några filer i mappen, avslutas skriptet.
shopt -s nullglob
files=("$SPARAD_BILAGA_DIR"/*)
shopt -u nullglob

if [ ${#files[@]} -eq 0 ]; then
    echo "Skanning klar: Ingen bilaga hittades i mappen. Avslutas. (Exit Code 0)" >> "$LOGG_FIL"
    exit 0
fi

# --------------------------
# 1. KÖR CLAMDSCA MED FLYTT TILL KARANTÄN
# --------------------------
# --move: Flyttar infekterade filer till karantän (detta är clamdscans inbyggda flagga)
# -r: Skanna rekursivt
"$CLAMSCAN_BIN" --move="$KARANTAN_DIR" -r --no-summary "$SPARAD_BILAGA_DIR" >> "$LOGG_FIL" 2>&1

# Fånga exit-koden från clamdscan.
CLAMSCAN_STATUS=$?

# --------------------------
# 2. HANTERA RESULTAT & RENSNING
# --------------------------

if [ "$CLAMSCAN_STATUS" -eq 0 ]; then
    # Exit code 0: Rent. Inga hot hittades.
    echo "Skanning klar: Rent. (Exit Code 0)" >> "$LOGG_FIL"
    # Rensa den temporära sparade bilagemappen.
    rm -rf "$SPARAD_BILAGA_DIR"/*
    exit 0
elif [ "$CLAMSCAN_STATUS" -eq 1 ]; then
    # Exit code 1: Virushot hittades OCH flyttades till karantän.
    echo "Skanning klar: VIRUS HITTAT och flyttat till karantän. (Exit Code 1)" >> "$LOGG_FIL"
    # Rensa den nu tomma sparade bilagemappen.
    rm -rf "$SPARAD_BILAGA_DIR"/*
    exit 10 # Använder 10 för att indikera VIRUS
else
    # Andra fel. Logga felkoden för diagnostik.
    echo "Skanning klar: FEL UPPSTOD (Exit Code $CLAMSCAN_STATUS)." >> "$LOGG_FIL"
    echo "Felet kan bero på: clamd@scan.service är inte igång, nätverksfel eller att clamdscan inte hittade något att skanna." >> "$LOGG_FIL"
    # Låt mappen vara kvar för felsökning vid fel.
    exit 99
fi
