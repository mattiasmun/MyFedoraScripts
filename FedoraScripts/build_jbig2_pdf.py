#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path
import tempfile


def run(cmd):
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_pdf")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_pdf = Path(args.output_pdf)

    pbm_files = sorted(input_dir.glob("*.pbm"))
    if not pbm_files:
        sys.exit("❌ No PBM files found")

    print("Found pages:")
    for p in pbm_files:
        print(" ", p.name)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        prefix = tmpdir / "output"

        # 1️⃣ Kör jbig2 på ALLA sidor samtidigt
        cmd = [
            "jbig2",
            "-s",          # symbol mode
            "-a",          # auto threshold
            "-p",          # PDF-compatible segments
            "-t", "0.80",  # bra balans för noter
            "-v",
            "-b", str(prefix)
        ] + [str(p) for p in pbm_files]

        run(cmd)

        # 2️⃣ Bygg PDF via jbig2topdf.py
        cmd = [
            "/usr/local/bin/jbig2topdf.py",
            str(prefix)
        ]

        print("Building PDF with jbig2topdf.py...")

        with open(output_pdf, "wb") as f:
            subprocess.run(cmd, stdout=f, check=True)

    print("✅ PDF created:", output_pdf)


if __name__ == "__main__":
    main()
