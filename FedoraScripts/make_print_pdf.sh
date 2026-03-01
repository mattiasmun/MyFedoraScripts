#!/bin/bash
set -e

DEBUG=1   # sätt till 0 för tyst läge

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

mkdir -p "$WORKDIR/pages" "$WORKDIR/jbig2"

trap "rm -rf '$WORKDIR'" EXIT

############################################
# 1️⃣ Ghostscript → 600 dpi PBM
############################################

echo "1️⃣ Renderar till 1-bit PBM (A5 fixed mediabox, 400 dpi)…"

gs \
  -sDEVICE=pbmraw \
  -r400 \
  -dBATCH \
  -dNOPAUSE \
  -dFIXEDMEDIA \
  -dPDFFitPage \
  -dNOUseCropBox \
  -dNOUseTrimBox \
  -dNOUseBleedBox \
  -dTextAlphaBits=1 \
  -dGraphicsAlphaBits=1 \
  -dDEVICEWIDTHPOINTS=420 \
  -dDEVICEHEIGHTPOINTS=595 \
  -sOutputFile="$WORKDIR/pages/page_%04d.pbm" \
  "$INPUT_PDF"

echo "2️⃣ Intelligent trim av PBM…"

python3 <<EOF
import numpy as np
from pathlib import Path
import sys

DEBUG = ${DEBUG}

PAGES = Path("$WORKDIR/pages")
DPI = 400
MARGIN_MM = 3
margin_px = int(MARGIN_MM * DPI / 25.4)

for pbm in sorted(PAGES.glob("*.pbm")):
    with open(pbm, "rb") as f:
        magic = f.readline()
        while True:
            line = f.readline()
            if not line.startswith(b"#"):
                w, h = map(int, line.split())
                break
        data = f.read()

    row_bytes = (w + 7) // 8
    expected_size = row_bytes * h

    if DEBUG:
        print(f"\n--- {pbm.name} ---")
        print("Original size:", w, "x", h)
        print("Expected bytes:", expected_size, "Actual:", len(data))

    if len(data) != expected_size:
        print("⚠ Byte size mismatch → skip trim")
        continue

    img = np.frombuffer(data, dtype=np.uint8)
    img = np.unpackbits(img, bitorder="big")
    img = img.reshape(h, row_bytes * 8)[:, :w]

    black_pixels = np.sum(img == 0)

    if DEBUG:
        print("Black pixels:", black_pixels)

    if black_pixels == 0:
        print("⚠ No black pixels → skip")
        continue

    ys, xs = np.where(img == 0)

    min_x = max(xs.min() - margin_px, 0)
    max_x = min(xs.max() + margin_px, w-1)
    min_y = max(ys.min() - margin_px, 0)
    max_y = min(ys.max() + margin_px, h-1)

    new_w = max_x - min_x + 1
    new_h = max_y - min_y + 1

    if DEBUG:
        print("Crop box:", min_x, min_y, max_x, max_y)
        print("New size:", new_w, "x", new_h)

    cropped = img[min_y:max_y+1, min_x:max_x+1]

    padded_w = ((new_w + 7) // 8) * 8
    padded = np.pad(cropped, ((0,0),(0,padded_w-new_w)), constant_values=1)

    packed = np.packbits(padded, bitorder="big")

    with open(pbm, "wb") as f:
        f.write(b"P4\n")
        f.write(f"{new_w} {new_h}\n".encode())
        f.write(packed.tobytes())

EOF

############################################
# 4️⃣ Bygg JBIG2 PDF
############################################

echo "4️⃣ Bygger JBIG2 PDF…"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_PDF="$WORKDIR/jbig2.pdf"

if ! python3 "$SCRIPT_DIR/build_jbig2_pdf.py" \
        "$WORKDIR/pages" \
        "$OUTPUT_PDF"; then
    echo "❌ Fel vid PDF-generering"
    exit 1
fi

echo "✅ PDF klar"

############################################
# 6️⃣ A5 + 15mm + booklet
############################################

echo "6️⃣ Skalar till A5 + fixar sidantal…"

python3 <<EOF
import pikepdf
from pikepdf import Pdf, Name, Dictionary

INPUT = "$OUTPUT_PDF"
OUTPUT = "${BASENAME}_ULTRA_FAST_PRINT_READY.pdf"

TARGET_W = 420
TARGET_H = 595
MAX_W = 335
MAX_H = 510

pdf = Pdf.open(INPUT)
out = Pdf.new()

back_cover = pdf.pages[-1]
content_pages = list(pdf.pages[:-1])

def place_scaled(page):
    llx, lly, urx, ury = map(float, page.MediaBox)
    if urx - llx <= 0 or ury - lly <= 0:
        page.MediaBox = [0, 0, 1, 1]
    width = urx - llx
    height = ury - lly

    if width <= 0 or height <= 0:
        out.add_blank_page(page_size=(TARGET_W, TARGET_H))
        return

    scale = min(MAX_W/width, MAX_H/height)

    new_page = out.add_blank_page(page_size=(TARGET_W, TARGET_H))

    x_offset = (TARGET_W - width*scale)/2
    y_offset = (TARGET_H - height*scale)/2

    xobj = out.copy_foreign(page.as_form_xobject())

    new_page.Resources = new_page.Resources or Dictionary()
    new_page.Resources.XObject = new_page.Resources.get("/XObject", Dictionary())
    new_page.Resources.XObject[Name("/Fm0")] = xobj

    content = f"q {scale} 0 0 {scale} {x_offset - llx*scale} {y_offset - lly*scale} cm /Fm0 Do Q"
    new_page.Contents = out.make_stream(content.encode())

for p in content_pages:
    place_scaled(p)

while (len(out.pages)+1) % 4 != 0:
    out.add_blank_page(page_size=(TARGET_W, TARGET_H))

place_scaled(back_cover)

out.save(OUTPUT)
EOF

echo "🏁 KLAR: ${BASENAME}_ULTRA_FAST_PRINT_READY.pdf"
