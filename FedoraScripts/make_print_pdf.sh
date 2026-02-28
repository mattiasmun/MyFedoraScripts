#!/bin/bash
set -e

# -----------------------------------------
# Kontroll
# -----------------------------------------

INPUT="$1"
[ -z "$INPUT" ] && { echo "Ange PDF-fil"; exit 1; }
[ ! -f "$INPUT" ] && { echo "Filen finns inte: $INPUT"; exit 1; }

BASENAME=$(basename "$INPUT" .pdf)
WORKDIR="${BASENAME}_PRINTPRO_$$"
mkdir "$WORKDIR"

# Marginaler i punkter (15mm ~ 42.5pt)
MARGIN=42.5
# A5-punkter
WIDTH=420
HEIGHT=595

echo "Splitting $INPUT → $WORKDIR ..."
pdfcpu split "$INPUT" "$WORKDIR"

# -----------------------------------------
# Analys + exakt skalning per sida
# -----------------------------------------

for f in "$WORKDIR"/*.pdf; do
    echo "Analyserar $f ..."

    python3 <<EOF
import pdfplumber, os, subprocess

f = "$f"
WORKDIR = "$WORKDIR"
MARGIN = $MARGIN
WIDTH = $WIDTH
HEIGHT = $HEIGHT
OUTFILE = os.path.join(WORKDIR, "scaled.pdf")

with pdfplumber.open(f) as pdf:
    page = pdf.pages[0]
    # bounding box på innehållet
    bbox = page.bbox  # (x0, top, x1, bottom)
    content_width = bbox[2] - bbox[0]
    content_height = bbox[3] - bbox[1]

# Beräkna skalning så innehållet får korrekt marginal
scale_x = (WIDTH - 2*MARGIN) / content_width
scale_y = (HEIGHT - 2*MARGIN) / content_height
scale = min(scale_x, scale_y)

# Translation för att placera innehållet med marginal
tx = MARGIN - bbox[0]*scale
ty = MARGIN - bbox[1]*scale

# Ghostscript: skalning + translation
subprocess.run([
    "gs", "-dSAFER", "-dBATCH", "-dNOPAUSE",
    "-sDEVICE=pdfwrite",
    "-sOutputFile={}".format(OUTFILE),
    "-dFIXEDMEDIA",
    "-dDEVICEWIDTHPOINTS={}".format(WIDTH),
    "-dDEVICEHEIGHTPOINTS={}".format(HEIGHT),
    "-c","<</Install {{ {} {} translate {} {} scale }}>> setpagedevice".format(tx, ty, scale, scale),
    "-f", f
], check=True)

if os.path.isfile(OUTFILE):
    os.rename(OUTFILE, f)
EOF

done

# -----------------------------------------
# Lägg till ledande nollor på filnamn
# -----------------------------------------
cd "$WORKDIR"
COUNT=1
for f in *.pdf; do
    NEW=$(printf "%03d.pdf" $COUNT)
    mv "$f" "$NEW"
    ((COUNT++))
done
cd -

# -----------------------------------------
# Slå ihop tillbaka till en PDF med korrekt ordning
# -----------------------------------------
OUTPUT="${BASENAME}_MATRIX_MARGIN.pdf"
echo "Slår ihop alla sidor → $OUTPUT"
pdfcpu merge -sort "$OUTPUT" "$WORKDIR"/*.pdf

# Rensa upp
rm -rf "$WORKDIR"

echo "KLAR: $OUTPUT"
