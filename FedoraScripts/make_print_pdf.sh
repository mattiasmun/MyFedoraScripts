#!/bin/bash
set -e

INPUT="$1"
[ -z "$INPUT" ] && { echo "Ange PDF-fil"; exit 1; }
[ ! -f "$INPUT" ] && { echo "Filen finns inte"; exit 1; }

BASENAME=$(basename "$INPUT" .pdf)
WORKDIR="${BASENAME}_WORK_$$"
mkdir -p "$WORKDIR/pages" "$WORKDIR/clean"

############################################
# 1️⃣ Rendera till 600 dpi mono
############################################

echo "1️⃣ Renderar 600 dpi mono..."

gs -dSAFER -dBATCH -dNOPAUSE \
   -sDEVICE=pngmono \
   -r600 \
   -sOutputFile="$WORKDIR/pages/page_%04d.png" \
   "$INPUT"

############################################
# 2️⃣ Tvätta med unpaper
############################################

echo "2️⃣ Tvättar med unpaper..."

for f in "$WORKDIR"/pages/*.png; do
  unpaper \
    --overwrite \
    --layout single \
    --threshold 0.55 \
    --deskew-scan-range 5 \
    --deskew-scan-step 0.1 \
    --no-noisefilter \
    --no-blurfilter \
    "$f" "$WORKDIR/clean/$(basename "$f")"
done

############################################
# 3️⃣ JBIG2 komprimering
############################################

echo "3️⃣ JBIG2-komprimerar..."

cd "$WORKDIR/clean"
jbig2 -s -p -v -a page_*.png
cd -

############################################
# 4️⃣ Bygg PDF från JBIG2
############################################

echo "4️⃣ Bygger JBIG2 PDF..."

python3 <<EOF
import os
import pikepdf
from pikepdf import Pdf

workdir = "$WORKDIR/clean"
output_jbig = "$WORKDIR/jbig2.pdf"

out = Pdf.new()

symbols = os.path.join(workdir, "output.sym")

pages = sorted([f for f in os.listdir(workdir) if f.endswith(".0000")])

for pagefile in pages:
    img_path = os.path.join(workdir, pagefile)

    page = out.add_blank_page(page_size=(420,595))

    img = pikepdf.Stream(out, open(img_path,"rb").read())
    img_dict = {
        "/Type": "/XObject",
        "/Subtype": "/Image",
        "/Width": 2480,
        "/Height": 3508,
        "/ColorSpace": "/DeviceGray",
        "/BitsPerComponent": 1,
        "/Filter": "/JBIG2Decode",
        "/DecodeParms": {"/JBIG2Globals": pikepdf.Stream(out, open(symbols,"rb").read())}
    }

    img_obj = out.make_indirect(img_dict)
    page.Resources = {"/XObject": {"/Im0": img_obj}}

    page.Contents = out.make_stream(b"q 420 0 0 595 0 0 cm /Im0 Do Q")

out.save(output_jbig)
EOF

############################################
# 5️⃣ Skala till A5 + 15 mm
############################################

echo "5️⃣ Skalar till A5..."

python3 <<EOF
import pikepdf
from pikepdf import Pdf, Name, Dictionary

INPUT = "$WORKDIR/jbig2.pdf"
OUTPUT = "${BASENAME}_PRINT_READY.pdf"

TARGET_W = 420
TARGET_H = 595
MAX_W = 335
MAX_H = 510

pdf = Pdf.open(INPUT)
out = Pdf.new()

# sista sidan = bakgrund
back_cover = pdf.pages[-1]
content_pages = list(pdf.pages[:-1])

def place(page):
    llx,lly,urx,ury = map(float,page.MediaBox)
    w = urx-llx
    h = ury-lly
    scale = min(MAX_W/w, MAX_H/h)

    new_page = out.add_blank_page(page_size=(TARGET_W,TARGET_H))

    x_offset = (TARGET_W - w*scale)/2
    y_offset = (TARGET_H - h*scale)/2

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

for p in content_pages:
    place(p)

while (len(out.pages)+1) % 4 != 0:
    out.add_blank_page(page_size=(TARGET_W,TARGET_H))

place(back_cover)

out.save(OUTPUT)
EOF

############################################
# 6️⃣ Städa
############################################

rm -rf "$WORKDIR"

echo "KLAR: ${BASENAME}_PRINT_READY.pdf"
