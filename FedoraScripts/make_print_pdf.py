#!/usr/bin/env python3
"""Create an ultra-fast print-ready PDF from an input PDF using dynamic sizing and DPI."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def get_pdf_dimensions_and_dpi(pdf_path: Path) -> int:
    """Hämtar den första sidans storlek och räknar ut en hög bitonal DPI."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True
        )
        match = re.search(r"Page size:\s+([\d.]+)\s+x\s+([\d.]+)", result.stdout)
        if match:
            width = float(match.group(1))
            height = float(match.group(2))

            area = width * height
            if area <= 0:
                return 1200

            calculated_dpi = round(1200.0 * ((501157 / area) ** 0.5))
            return max(600, min(1800, calculated_dpi))
    except Exception as e:
        print(f"⚠️ Kunde inte läsa PDF-info ({e}), använder standard 1200 DPI.")

    return 1200


def main() -> int:
    if len(sys.argv) < 2:
        print("Ange PDF-fil")
        return 1

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.is_file():
        print("Filen finns inte")
        return 1

    dpi = get_pdf_dimensions_and_dpi(input_path)
    print(f"🧠 Beräknad smart upplösning: {dpi} DPI (dynamisk per sida)")

    base_name = input_path.stem
    ramdisk = Path("/dev/shm")

    if ramdisk.is_dir():
        workdir = Path(tempfile.mkdtemp(prefix=f"{base_name}_WORK_", dir=str(ramdisk)))
        print(f"⚡ Använder RAM-disk: {workdir}")
    else:
        workdir = Path(tempfile.mkdtemp(prefix=f"{base_name}_WORK_"))
        print("⚠️  RAM-disk saknas, använder disk")

    pages_dir = workdir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"1️⃣ Renderar till 1-bit PBM ({dpi} dpi, helt dynamiska sidstorlekar)…")
        subprocess.run(
            [
                "gs",
                "-sDEVICE=pbmraw",
                f"-r{dpi}",
                "-dBATCH",
                "-dNOPAUSE",
                f"-sOutputFile={pages_dir / 'page_%04d.pbm'}",
                str(input_path),
            ],
            check=True,
        )

        print("2️⃣ Bygger JBIG2 PDF…")
        script_dir = Path(__file__).resolve().parent
        output_pdf = Path.cwd() / f"{base_name}_ULTRA_FAST_PRINT_READY.pdf"

        # Vi skickar nu med DPI till byggskriptet istället för statiska mått
        subprocess.run(
            [
                sys.executable,
                str(script_dir / "build_jbig2_pdf.py"),
                str(pages_dir),
                str(output_pdf),
                str(dpi),
            ],
            check=True,
        )

        print(f"🏁 KLAR: {output_pdf.name}")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
