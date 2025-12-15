#!/bin/bash
# Filnamn: jbig2_snap_wrapper.sh
# Denna wrapper kör Snap-installerade jbig2enc och returnerar ENDAST relevant utdata.

# Anropar den riktiga binären med alla argument ($@)
# och hoppar över den initiala Snapd-diagnostik (som skrivs till stderr).
/var/lib/snapd/snap/bin/jbig2enc "$@" 2>/dev/null
