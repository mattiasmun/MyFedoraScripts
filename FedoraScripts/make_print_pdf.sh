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

mkdir -p "$WORKDIR/pages" "$WORKDIR/clean" "$WORKDIR/jbig2"

trap "rm -rf '$WORKDIR'" EXIT

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
# 2️⃣ unpaper parallellt
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
# 3️⃣ JBIG2 parallell (auto-optimerad)
############################################

echo "3️⃣ JBIG2-komprimerar (auto-optimerad)…"

cd "$WORKDIR/clean"

FILES=($(ls *.pbm | sort))
TOTAL=${#FILES[@]}
CPU=$(nproc)

# Räkna blocksize dynamiskt
if [ "$TOTAL" -le 40 ]; then
  BLOCKSIZE=$TOTAL
else
  BLOCKS=$(( CPU * 2 ))
  BLOCKSIZE=$(( TOTAL / BLOCKS ))

  # Säkerhetsgränser
  if [ "$BLOCKSIZE" -lt 10 ]; then BLOCKSIZE=10; fi
  if [ "$BLOCKSIZE" -gt 40 ]; then BLOCKSIZE=40; fi
fi

echo "📊 Sidor: $TOTAL | CPU: $CPU | Blocksize: $BLOCKSIZE"

BLOCKS=$(( (TOTAL + BLOCKSIZE - 1) / BLOCKSIZE ))

export WORKDIR BLOCKSIZE TOTAL
export FILES

parallel -j"$CPU" --bar '
  block={#}
  start=$(( (block-1)*BLOCKSIZE ))
  end=$(( start+BLOCKSIZE-1 ))

  files=()
  for i in $(seq $start $end); do
    if [ $i -lt '"$TOTAL"' ]; then
      files+=("'"${FILES[$i]}"'")
    fi
  done

  if [ ${#files[@]} -gt 0 ]; then
    jbig2 -s -p -v -a -b "$WORKDIR/jbig2/block_${block}" "${files[@]}"
  fi
' ::: $(seq 1 $BLOCKS)

cd -

############################################
# 4️⃣ Bygg PDF från alla block
############################################

echo "4️⃣ Bygger JBIG2 PDF…"

python3 <<EOF
import os
import pikepdf
from pikepdf import Pdf
from PIL import Image

workdir = "$WORKDIR/jbig2"
output_pdf = os.path.join("$WORKDIR", "jbig2.pdf")

out = Pdf.new()

blocks = sorted([f for f in os.listdir(workdir) if f.endswith(".sym")])

for block in blocks:
    base = block.replace(".sym","")
    sym_path = os.path.join(workdir, block)
    globals_stream = pikepdf.Stream(out, open(sym_path,"rb").read())

    pagefiles = sorted([f for f in os.listdir(workdir) if f.startswith(base) and f.endswith(".0000")])

    for pagefile in pagefiles:
        img_path = os.path.join(workdir, pagefile)

        with Image.open(img_path) as im:
            width, height = im.size

        page = out.add_blank_page(page_size=(width, height))

        img_stream = pikepdf.Stream(out, open(img_path,"rb").read())

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

############################################
# 5️⃣ Auto-crop
############################################

echo "5️⃣ Auto-croppar…"

pdfcropmargins -c gb -p 0 \
  -o "$WORKDIR/jbig2_cropped.pdf" \
  "$WORKDIR/jbig2.pdf"

############################################
# 6️⃣ A5 + 15mm + booklet
############################################

echo "6️⃣ Skalar till A5 + fixar sidantal…"

python3 <<EOF
import pikepdf
from pikepdf import Pdf, Name, Dictionary

INPUT = "$WORKDIR/jbig2_cropped.pdf"
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
