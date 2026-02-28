#!/bin/bash
set -e

INPUT="$1"
[ -z "$INPUT" ] && { echo "Ange PDF-fil"; exit 1; }
[ ! -f "$INPUT" ] && { echo "Filen finns inte: $INPUT"; exit 1; }

BASENAME=$(basename "$INPUT" .pdf)
CROPPED="${BASENAME}_CROPPED.pdf"
OUTPUT="${BASENAME}_MATRIX_MARGIN.pdf"

echo "1️⃣  Tar bort vitkant automatiskt..."
pdfcropmargins -c gb -p 0 -o "$CROPPED" "$INPUT"

echo "2️⃣  Skalar och placerar på A5..."

python3 <<EOF
import pikepdf
from pikepdf import Pdf, Name, Dictionary

INPUT = "$CROPPED"
OUTPUT = "$OUTPUT"

TARGET_W = 420
TARGET_H = 595
MAX_W = 335
MAX_H = 510

pdf = Pdf.open(INPUT)
out = Pdf.new()

for page_number, page in enumerate(pdf.pages, start=1):
    try:
        llx, lly, urx, ury = map(float, page.MediaBox)
        width = urx - llx
        height = ury - lly

        if width <= 0 or height <= 0:
            print(f"⚠️  Sida {page_number} är tom → ersätter med blank A5")
            out.add_blank_page(page_size=(TARGET_W, TARGET_H))
            continue

        scale = min(MAX_W / width, MAX_H / height)

        new_page = out.add_blank_page(page_size=(TARGET_W, TARGET_H))

        x_offset = (TARGET_W - width * scale) / 2
        y_offset = (TARGET_H - height * scale) / 2

        # 🔥 KORREKT sätt
        xobj = out.copy_foreign(
            pikepdf.Page(page).as_form_xobject()
        )

        new_page.Resources = new_page.Resources or Dictionary()
        new_page.Resources.XObject = new_page.Resources.get("/XObject", Dictionary())
        new_page.Resources.XObject[Name("/Fm0")] = xobj

        content = f"""
        q
        {scale} 0 0 {scale} {x_offset - llx*scale} {y_offset - lly*scale} cm
        /Fm0 Do
        Q
        """

        new_page.Contents = out.make_stream(content.encode("utf-8"))

    except Exception as e:
        print(f"⚠️  Sida {page_number} kraschade → ersätter med blank A5")
        out.add_blank_page(page_size=(TARGET_W, TARGET_H))

out.save(OUTPUT)
EOF

rm "$CROPPED"

echo "KLAR: $OUTPUT"
