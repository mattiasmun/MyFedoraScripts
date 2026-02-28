#!/bin/bash
set -e

INPUT="$1"
[ -z "$INPUT" ] && { echo "Ange PDF-fil"; exit 1; }
[ ! -f "$INPUT" ] && { echo "Filen finns inte"; exit 1; }

BASENAME=$(basename "$INPUT" .pdf)
WORKDIR="${BASENAME}_WORK_$$"

mkdir -p "$WORKDIR/pages" "$WORKDIR/clean"

############################################
# 1️⃣ Ghostscript → 600 dpi PBM
############################################

echo "1️⃣ Renderar 600 dpi PBM…"

gs -dSAFER -dBATCH -dNOPAUSE \
   -sDEVICE=pbmraw \
   -r600 \
   -sOutputFile="$WORKDIR/pages/page_%04d.pbm" \
   "$INPUT"

############################################
# 2️⃣ unpaper (musik-optimerad)
############################################

############################################
# 2️⃣ unpaper (musik-optimerad, parallell)
############################################

echo "2️⃣ Tvättar med unpaper (parallel)…"

export WORKDIR

find "$WORKDIR/pages" -name "*.pbm" | sort | \
parallel -j"$(nproc)" --bar '
  infile={}
  outfile="$WORKDIR/clean/$(basename {})"

  unpaper \
    --overwrite \
    --layout single \
    --deskew-scan-direction left,right \
    --deskew-scan-range 5 \
    --deskew-scan-step 0.1 \
    --border-scan-direction v \
    --border-scan-size 10 \
    --border-scan-threshold 5 \
    --no-blurfilter \
    --no-grayfilter \
    --type pbm \
    "$infile" "$outfile"
'

############################################
# 3️⃣ JBIG2-komprimering
############################################

echo "3️⃣ JBIG2-komprimerar…"

cd "$WORKDIR/clean"
jbig2 -s -p -v -a *.pbm
cd -

############################################
# 4️⃣ Bygg JBIG2 PDF
############################################

echo "4️⃣ Bygger JBIG2 PDF…"

python3 <<EOF
import os
import pikepdf
from pikepdf import Pdf
from PIL import Image

workdir = "$WORKDIR/clean"
output_pdf = os.path.join(workdir, "jbig2.pdf")

out = Pdf.new()

symbols = os.path.join(workdir, "output.sym")
pages = sorted([f for f in os.listdir(workdir) if f.endswith(".0000")])

for pagefile in pages:
    img_path = os.path.join(workdir, pagefile)

    # Läs verklig storlek
    with Image.open(img_path) as im:
        width, height = im.size

    page = out.add_blank_page(page_size=(width, height))

    img_stream = pikepdf.Stream(out, open(img_path,"rb").read())
    globals_stream = pikepdf.Stream(out, open(symbols,"rb").read())

    img_dict = {
        "/Type": "/XObject",
        "/Subtype": "/Image",
        "/Width": width,
        "/Height": height,
        "/ColorSpace": "/DeviceGray",
        "/BitsPerComponent": 1,
        "/Filter": "/JBIG2Decode",
        "/DecodeParms": {"/JBIG2Globals": globals_stream}
    }

    img_obj = out.make_indirect(img_dict)
    page.Resources = {"/XObject": {"/Im0": img_obj}}

    content = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q"
    page.Contents = out.make_stream(content.encode())

out.save(output_pdf)
EOF

echo "4️⃣  Auto-croppar med pdfcropmargins…"

pdfcropmargins \
  -c gb \
  -p 0 \
  -o "$WORKDIR/jbig2_cropped.pdf" \
  "$WORKDIR/jbig2.pdf"

############################################
# 5️⃣ Skala till A5 + 15 mm + booklet-logik
############################################

echo "5️⃣ Skalar till A5 och fixar sidantal…"

python3 <<EOF
import pikepdf
from pikepdf import Pdf, Name, Dictionary

INPUT = "$WORKDIR/jbig2_cropped.pdf"
OUTPUT = "${BASENAME}_PRINT_READY.pdf"

TARGET_W = 420      # A5 bredd i pt
TARGET_H = 595      # A5 höjd i pt

MAX_W = 335         # 15 mm marginal horisontellt
MAX_H = 510         # något större vertikalt utrymme

pdf = Pdf.open(INPUT)
out = Pdf.new()

back_cover = pdf.pages[-1]
content_pages = list(pdf.pages[:-1])

def place_scaled(page):
    llx, lly, urx, ury = map(float, page.MediaBox)

    width  = urx - llx
    height = ury - lly

    # Skydd mot trasiga sidor
    if width <= 0 or height <= 0:
        out.add_blank_page(page_size=(TARGET_W, TARGET_H))
        return

    scale = min(MAX_W / width, MAX_H / height)

    new_page = out.add_blank_page(page_size=(TARGET_W, TARGET_H))

    x_offset = (TARGET_W - width * scale) / 2
    y_offset = (TARGET_H - height * scale) / 2

    xobj = out.copy_foreign(page.as_form_xobject())

    new_page.Resources = new_page.Resources or Dictionary()
    new_page.Resources.XObject = new_page.Resources.get("/XObject", Dictionary())
    new_page.Resources.XObject[Name("/Fm0")] = xobj

    content = f"""
    q
    {scale} 0 0 {scale} {x_offset - llx*scale} {y_offset - lly*scale} cm
    /Fm0 Do
    Q
    """

    new_page.Contents = out.make_stream(content.encode())

# Lägg in innehållssidor
for p in content_pages:
    place_scaled(p)

# Fyll upp till delbart med 4 (före bakgrund)
while (len(out.pages) + 1) % 4 != 0:
    out.add_blank_page(page_size=(TARGET_W, TARGET_H))

# Lägg bakgrund sist
place_scaled(back_cover)

out.save(OUTPUT)
EOF

echo "📏 Verifierar verkliga marginaler…"

python3 <<EOF
import pikepdf
import math

PDF_FILE = "${BASENAME}_PRINT_READY.pdf"

PT_TO_MM = 25.4 / 72.0
TARGET_W = 420
TARGET_H = 595

pdf = pikepdf.open(PDF_FILE)

print("\nSida | Vänster | Höger | Topp | Botten (mm)")
print("-" * 50)

for i, page in enumerate(pdf.pages, start=1):

    llx, lly, urx, ury = map(float, page.MediaBox)
    page_width = urx - llx
    page_height = ury - lly

    # Hitta transformation i content stream
    content = page.Contents.read_bytes().decode("latin1")

    # Leta efter cm-matrisen
    import re
    match = re.search(r"([\d\.]+)\s+0\s+0\s+([\d\.]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+cm", content)

    if not match:
        print(f"{i:4} | Kunde inte analysera")
        continue

    scale_x = float(match.group(1))
    scale_y = float(match.group(2))
    tx = float(match.group(3))
    ty = float(match.group(4))

    # Innehållets bbox
    content_width = page_width / scale_x
    content_height = page_height / scale_y

    left = tx
    bottom = ty
    right = TARGET_W - (tx + content_width * scale_x)
    top = TARGET_H - (ty + content_height * scale_y)

    left_mm = left * PT_TO_MM
    right_mm = right * PT_TO_MM
    top_mm = top * PT_TO_MM
    bottom_mm = bottom * PT_TO_MM

    print(f"{i:4} | {left_mm:7.2f} | {right_mm:7.2f} | {top_mm:7.2f} | {bottom_mm:7.2f}")

pdf.close()
EOF

############################################
# 6️⃣ Städa
############################################

rm -rf "$WORKDIR"

echo "KLAR: ${BASENAME}_PRINT_READY.pdf"
