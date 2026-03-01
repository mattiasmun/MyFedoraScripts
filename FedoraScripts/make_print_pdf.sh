#!/bin/bash
set -e

INPUT="$1"
[ -z "$INPUT" ] && { echo "Ange PDF-fil"; exit 1; }
[ ! -f "$INPUT" ] && { echo "Filen finns inte"; exit 1; }

BASENAME=$(basename "$INPUT" .pdf)

############################################
# RAM-disk
############################################

if [ -d /dev/shm ]; then
  WORKDIR="/dev/shm/${BASENAME}_WORK_$$"
  echo "⚡ Använder RAM-disk: $WORKDIR"
else
  WORKDIR="${BASENAME}_WORK_$$"
  echo "⚠️  RAM-disk saknas, använder disk"
fi

mkdir -p "$WORKDIR/pages"
trap "rm -rf '$WORKDIR'" EXIT

############################################
# 1️⃣ Ghostscript → 1-bit PBM (A5 fixed)
############################################

echo "1️⃣ Renderar till 1-bit PBM (A5 fixed mediabox, 400 dpi)…"

gs \
  -sDEVICE=pbmraw \
  -r400 \
  -dBATCH \
  -dNOPAUSE \
  -dFIXEDMEDIA \
  -dDEVICEWIDTHPOINTS=420 \
  -dDEVICEHEIGHTPOINTS=595 \
  -sOutputFile="$WORKDIR/pages/page_%04d.pbm" \
  "$INPUT"

############################################
# 2️⃣ Bygg JBIG2 PDF
############################################

echo "2️⃣ Bygger JBIG2 PDF…"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_PDF="${BASENAME}_ULTRA_FAST_PRINT_READY.pdf"

python3 "$SCRIPT_DIR/build_jbig2_pdf.py" \
    "$WORKDIR/pages" \
    "$OUTPUT_PDF"

echo "🏁 KLAR: $OUTPUT_PDF"
