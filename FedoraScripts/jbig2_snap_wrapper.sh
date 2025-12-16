#!/bin/bash
# Filnamn: jbig2_snap_wrapper.sh
# Fixar 'liblept.so.5' felet genom att lägga till Snaps bibliotekssökväg.

# 1. Definiera den korrekta bibliotekssökvägen inuti Snap-paketet
SNAP_LIB_PATH="/var/lib/snapd/snap/jbig2enc/44/usr/lib"

# 2. Uppdatera LD_LIBRARY_PATH FÖR DETTA KOMMANDO
# Lägger till den nya sökvägen i början av befintlig LD_LIBRARY_PATH.
# Kör sedan den riktiga jbig2enc binären.
LD_LIBRARY_PATH="$SNAP_LIB_PATH:$LD_LIBRARY_PATH" exec /snap/jbig2enc/44/bin/jbig2 "$@"
