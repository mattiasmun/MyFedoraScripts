#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path
import pikepdf
from pikepdf import Name, Dictionary

PAGES_DIR = Path(sys.argv[1])
OUTPUT_PDF = sys.argv[2]

TARGET_W = 420
TARGET_H = 595

pbms = sorted(PAGES_DIR.glob("*.pbm"))
if not pbms:
    print("Inga PBM-filer hittades")
    sys.exit(1)

# Kör jbig2
tmp_base = PAGES_DIR / "output"

cmd = [
    "jbig2",
    "-s", "-a", "-p",
    "-t", "0.80",
    "-b", str(tmp_base)
] + [str(p) for p in pbms]

print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)

pdf = pikepdf.Pdf.new()

for i, pbm in enumerate(pbms):
    page_pdf = pikepdf.Pdf.open(f"{tmp_base}.{i:04d}")
    img_page = page_pdf.pages[0]

    # Hämta bilddimensioner
    xobj = next(iter(img_page.Resources.XObject.values()))
    width = int(xobj.Width)
    height = int(xobj.Height)

    scale_x = TARGET_W / width
    scale_y = TARGET_H / height

    new_page = pdf.add_blank_page(page_size=(TARGET_W, TARGET_H))

    xobj_ref = pdf.copy_foreign(xobj)

    new_page.Resources = new_page.Resources or Dictionary()
    new_page.Resources.XObject = Dictionary({Name("/Im0"): xobj_ref})

    content = f"""
q
{scale_x} 0 0 {scale_y} 0 0 cm
/Im0 Do
Q
"""
    new_page.Contents = pdf.make_stream(content.encode())

pdf.save(OUTPUT_PDF)
print("✅ PDF created:", OUTPUT_PDF)
