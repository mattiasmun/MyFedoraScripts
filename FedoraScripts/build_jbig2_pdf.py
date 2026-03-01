#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path
import argparse

import pikepdf
from pikepdf import Pdf, Name, Dictionary, Array


# ==========================
# Argument
# ==========================

parser = argparse.ArgumentParser(description="Stable JBIG2 multipage PDF builder")
parser.add_argument("input_dir", help="Directory with PBM files")
parser.add_argument("output_pdf", help="Output PDF filename")
parser.add_argument("--dpi", type=int, default=600)

args = parser.parse_args()

INPUT_DIR = Path(args.input_dir)
OUTPUT_PDF = Path(args.output_pdf)
DPI = args.dpi

if not INPUT_DIR.exists():
    sys.exit("Input directory does not exist")

pbm_files = sorted(INPUT_DIR.glob("*.pbm"))

if not pbm_files:
    sys.exit("No PBM files found")

print("Found pages:")
for f in pbm_files:
    print("  ", f.name)

# ==========================
# Kör jbig2 per sida
# ==========================

print("\nRunning jbig2enc (auto mode)...")

page_modes = {}

for index, pbm in enumerate(pbm_files, start=1):
    base = pbm.stem
    output_file = INPUT_DIR / f"{base}.0000"

    if index == 1:  # exempel: kolumnsida
        args = ["jbig2", "-p", pbm.name]
    else:
        args = ["jbig2", "-s", "-p", pbm.name]

    with open(output_file, "wb") as out:
        subprocess.run(
            args,
            cwd=INPUT_DIR,
            stdout=out,
            check=True
        )

# ==========================
# Bygg PDF
# ==========================

pdf = Pdf.new()

def read_pbm_size(path):
    with open(path, "rb") as f:
        f.readline()  # P4
        while True:
            line = f.readline()
            if not line.startswith(b"#"):
                w, h = map(int, line.split())
                return w, h

for pbm in pbm_files:
    base = pbm.stem
    sym_file = INPUT_DIR / f"{base}.sym"

    if sym_file.exists():
        mode = "symbol"
    else:
        mode = "generic"

    jb2_file = INPUT_DIR / f"{base}.0000"

    width, height = read_pbm_size(pbm)

    with open(jb2_file, "rb") as f:
        image_stream = pdf.make_stream(f.read())

    image_stream["/Type"] = Name("/XObject")
    image_stream["/Subtype"] = Name("/Image")
    image_stream["/Width"] = width
    image_stream["/Height"] = height
    image_stream["/ColorSpace"] = Name("/DeviceGray")
    image_stream["/BitsPerComponent"] = 1
    image_stream["/Filter"] = Name("/JBIG2Decode")

    if mode == "symbol":
        sym_file = INPUT_DIR / f"{base}.sym"
        with open(sym_file, "rb") as f:
            globals_stream = pdf.make_stream(f.read())

        globals_stream = pdf.make_indirect(globals_stream)

        image_stream["/DecodeParms"] = Dictionary({
            "/JBIG2Globals": globals_stream
        })

    image_stream = pdf.make_indirect(image_stream)

    width_pt = width * 72 / DPI
    height_pt = height * 72 / DPI

    page = pdf.add_blank_page(page_size=(width_pt, height_pt))

    page.Resources = Dictionary({
        "/XObject": Dictionary({
            "/Im0": image_stream
        })
    })

    content = f"q {width_pt} 0 0 {height_pt} 0 0 cm /Im0 Do Q"
    page.Contents = pdf.make_stream(content.encode())

pdf.save(OUTPUT_PDF)
pdf.close()

print("\nPDF created:", OUTPUT_PDF)
