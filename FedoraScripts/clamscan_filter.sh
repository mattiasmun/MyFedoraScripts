#!/bin/bash
# Detta skript fungerar som en mellanhand mellan FiltaQuilla och ClamAV.
# Det anropar clamscan och returnerar en statuskod.

# --------------------------
# VARIABLER
# --------------------------
# Sökväg till den mapp FiltaQuilla skickar (med bilagor)
BILAGA_DIR="$1"
# Sökväg till din karantänmapp (använder $HOME för portabilitet)
KARANTAN_DIR="$HOME/.clamtk/quarantine" 
# Sökväg till Clamscan binärfil
CLAMSCAN_BIN="/usr/bin/clamscan"

# Kontrollera att sökvägen till bilagan skickades
if [ -z "$BILAGA_DIR" ]; then
    exit 0 # Ingen sökväg skickades, avsluta som rent
fi

# --------------------------
# 1. KÖR CLAMSCAN
# --------------------------
# Argument:
# --no-summary: Håll utdata ren
# -r: Skanna rekursivt (för bilagor inuti bilagor/temporära mappar)
# --move: Flytta den infekterade filen direkt till karantän
"$CLAMSCAN_BIN" --no-summary -r --move="$KARANTAN_DIR" "$BILAGA_DIR"

# Fånga exit-koden från clamscan.
CLAMSCAN_STATUS=$?

# --------------------------
# 2. HANTERA RESULTAT
# --------------------------

if [ "$CLAMSCAN_STATUS" -eq 0 ]; then
    # Exit code 0: Rent. Låt meddelandet passera.
    exit 0
elif [ "$CLAMSCAN_STATUS" -eq 1 ]; then
    # Exit code 1: Virushot hittades OCH flyttades.
    # Vi returnerar en icke-noll-kod för att signalera att något hände.
    # FiltaQuilla kommer att tolka detta som "Lyckades Inte" (Failed/Not Succeeded).
    # Vi kan nu använda en sekundär åtgärd i filtret, t.ex. lägga till en tagg.
    exit 10
else
    # Andra fel (t.ex. fil hittades inte, databasfel)
    exit 99
fi
