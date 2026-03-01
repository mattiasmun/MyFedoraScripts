#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path
import pikepdf
from pikepdf import Name, Dictionary

if len(sys.argv) != 3:
    print("Usage: build_jbig2_pdf.py <pages_dir> <output_pdf>")
    sys.exit(1)

PAGES_DIR = Path(sys.argv[1])
OUTPUT_PDF = sys.argv[2]

TARGET_W = 420   # A5 width in points
TARGET_H = 595   # A5 height in points

pbms = sorted(PAGES_DIR.glob("*.pbm"))
if not pbms:
    print("❌ Inga PBM-filer hittades")
    sys.exit(1)

# ==========================================================
# 1️⃣ Kör jbig2 (utan -p)
# ==========================================================

tmp_base = PAGES_DIR / "output"

cmd = [
    "jbig2",
    "-s", "-a", "-p",
    "-t", "0.80",
    "-b", str(tmp_base)
] + [str(p) for p in pbms]

print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)

# Kontrollera att jbig2 skapade filer
sym_file = Path(str(tmp_base) + ".sym")
page_files = [Path(str(tmp_base) + f".{i:04d}") for i in range(len(pbms))]

if not sym_file.exists() or not all(p.exists() for p in page_files):
    print("❌ jbig2 skapade inte förväntade filer")
    sys.exit(1)

# ==========================================================
# 2️⃣ Bygg PDF via jbig2topdf.py (helt robust)
# ==========================================================

raw_pdf_path = PAGES_DIR / "jbig2_raw.pdf"

cmd = [
    "/usr/local/bin/jbig2topdf.py",
    str(sym_file)
] + [str(p) for p in page_files]

print("Running:", " ".join(cmd))

with open(raw_pdf_path, "wb") as f:
    process = subprocess.Popen(
        cmd,
        stdout=f,
        stderr=subprocess.PIPE
    )
    _, stderr = process.communicate()

if process.returncode != 0:
    print("❌ jbig2topdf misslyckades:")
    print(stderr.decode())
    sys.exit(1)

if not raw_pdf_path.exists() or raw_pdf_path.stat().st_size == 0:
    print("❌ jbig2topdf skapade ingen giltig PDF")
    sys.exit(1)

# ==========================================================
# 3️⃣ Skala korrekt till A5
# ==========================================================

src_pdf = pikepdf.Pdf.open(raw_pdf_path)
out_pdf = pikepdf.Pdf.new()

for page in src_pdf.pages:

    # Hämta bild-XObject
    xobj = next(iter(page.Resources.XObject.values()))
    width = int(xobj.Width)
    height = int(xobj.Height)

    scale_x = TARGET_W / width
    scale_y = TARGET_H / height

    new_page = out_pdf.add_blank_page(page_size=(TARGET_W, TARGET_H))

    xobj_ref = out_pdf.copy_foreign(xobj)

    new_page.Resources = Dictionary({
        Name("/XObject"): Dictionary({
            Name("/Im0"): xobj_ref
        })
    })

    content = f"""
q
{scale_x} 0 0 {scale_y} 0 0 cm
/Im0 Do
Q
"""
    new_page.Contents = out_pdf.make_stream(content.encode())

out_pdf.save(OUTPUT_PDF)

print("✅ PDF created:", OUTPUT_PDF)
