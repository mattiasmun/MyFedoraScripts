#!/bin/bash
# Detta skript fungerar som en mellanhand mellan FiltaQuilla och ClamAV.
# Det skannar en FIXXAD SÖKVÄG där Thunderbird/FiltaQuilla sparar bilagorna.

# --------------------------
# VARIABLER
# --------------------------
# Sökväg till den mapp Thunderbird/FiltaQuilla sparar bilagorna.
SPARAD_BILAGA_DIR="$HOME/.clamtk/attachment"

# Sökväg till din karantänmapp (där infekterade filer flyttas)
KARANTAN_DIR="$HOME/.clamtk/quarantine" 

# Sökväg till Clamscan binärfil
CLAMSCAN_BIN="/usr/bin/clamscan"

# --------------------------
# 1. KÖR CLAMSCAN MOT DEN FIXA SÖKVÄGEN
# --------------------------
# Argument:
# --no-summary: Håll utdata ren
# -r: Skanna rekursivt
# --move: Flytta den infekterade filen direkt till karantän
# Sökväg: Vi skannar den sparade mappen direkt.
"$CLAMSCAN_BIN" --no-summary -r --move="$KARANTAN_DIR" "$SPARAD_BILAGA_DIR"

# Fånga exit-koden från clamscan.
CLAMSCAN_STATUS=$?

# --------------------------
# 2. HANTERA RESULTAT
# --------------------------

if [ "$CLAMSCAN_STATUS" -eq 0 ]; then
    # Exit code 0: Rent. Inga hot hittades i den sparade mappen.
    # Rensa den temporära sparade bilagemappen.
    rm -rf "$SPARAD_BILAGA_DIR"/*
    exit 0
elif [ "$CLAMSCAN_STATUS" -eq 1 ]; then
    # Exit code 1: Virushot hittades OCH flyttades till karantän.
    # Även om hotet är borta, returnerar vi 10 för att indikera att något HÄNDE.
    # Rensa den nu tomma sparade bilagemappen.
    rm -rf "$SPARAD_BILAGA_DIR"/*
    exit 10
else
    # Andra fel (t.ex. databasfel, sökvägsproblem)
    # Låt mappen vara kvar för felsökning.
    exit 99
fi
