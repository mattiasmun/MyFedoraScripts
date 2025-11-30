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

# Sökväg till Clamscan binärfil
CLAMSCAN_BIN="/usr/bin/clamscan"

# Loggfilens sökväg (vi lägger den i .clamtk/log/)
LOGG_FIL="$HOME/.clamtk/log/clamscan_filter.log"

# --------------------------
# 0. FÖRBEREDELSER
# --------------------------
# Skapa karantän- och loggmappar om de inte redan finns.
mkdir -p "$KARANTAN_DIR"
mkdir -p "$HOME/.clamtk/log"

# Lägg till tidsstämpel i loggen
echo "--- Skanning startad: $(date) ---" >> "$LOGG_FIL"

# --------------------------
# 0.5. KONTROLLERA INNEHÅLL
# --------------------------
# Säkerställ att om det inte finns några filer i mappen, avslutas skriptet.
# 'shopt -s nullglob' ser till att '*.+' blir en tom sträng om det inte finns matchningar.
shopt -s nullglob
files=("$SPARAD_BILAGA_DIR"/*)
shopt -u nullglob

if [ ${#files[@]} -eq 0 ]; then
    echo "Skanning klar: Ingen bilaga hittades i mappen. Avslutas." >> "$LOGG_FIL"
    exit 0
fi

# --------------------------
# 1. KÖR CLAMSCAN MED LOGGNING
# --------------------------
# Argument:
# -r: Skanna rekursivt
# --move: Flytta den infekterade filen direkt till karantän
# --log: Skriver alla meddelanden till loggfilen
"$CLAMSCAN_BIN" -r --move="$KARANTAN_DIR" --log="$LOGG_FIL" "$SPARAD_BILAGA_DIR"

# Fånga exit-koden från clamscan.
CLAMSCAN_STATUS=$?

# --------------------------
# 2. HANTERA RESULTAT & RENSNING
# --------------------------

if [ "$CLAMSCAN_STATUS" -eq 0 ]; then
    # Exit code 0: Rent. Inga hot hittades.
    echo "Skanning klar: Rent." >> "$LOGG_FIL"
    # Rensa den temporära sparade bilagemappen.
    rm -rf "$SPARAD_BILAGA_DIR"/*
    exit 0
elif [ "$CLAMSCAN_STATUS" -eq 1 ]; then
    # Exit code 1: Virushot hittades OCH flyttades till karantän.
    echo "Skanning klar: VIRUS HITTAT och flyttat till karantän: $KARANTAN_DIR" >> "$LOGG_FIL"
    # Rensa den nu tomma sparade bilagemappen.
    rm -rf "$SPARAD_BILAGA_DIR"/*
    exit 10
else
    # Andra fel.
    echo "Skanning klar: FEL UPPSTOD (Exit Code $CLAMSCAN_STATUS). Kontrollera ClamAV-databasen." >> "$LOGG_FIL"
    # Låt mappen vara kvar för felsökning vid fel.
    exit 99
fi
