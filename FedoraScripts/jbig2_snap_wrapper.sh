#!/bin/bash
# Filnamn: jbig2_snap_wrapper.sh
# Fixar biblioteksfelen genom att lägga till Snaps bibliotekssökväg.

# 1. Definiera de nödvändiga bibliotekssökvägarna:
SNAP_LIB_PATH="/var/lib/snapd/snap/jbig2enc/44/usr/lib"
# Anta att PNG-biblioteket ligger här (justera sökvägen vid behov):
SNAP_PNG_PATH="/var/lib/snapd/snap/jbig2enc/44/usr/lib/x86_64-linux-gnu" 

# 2. Uppdatera LD_LIBRARY_PATH FÖR DETTA KOMMANDO
# Lägger till båda sökvägarna i början av befintlig LD_LIBRARY_PATH.
LD_LIBRARY_PATH="$SNAP_LIB_PATH:$SNAP_PNG_PATH:$LD_LIBRARY_PATH" exec /snap/jbig2enc/44/bin/jbig2 "$@"
