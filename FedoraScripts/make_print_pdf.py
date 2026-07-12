#!/usr/bin/env python3
"""Create an ultra-fast print-ready PDF from an input PDF using dynamic sizing and DPI."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def get_pdf_dimensions_and_dpi(pdf_path: Path) -> tuple[float, float, int]:
    """Hämtar den första sidans storlek och räknar ut en hög bitonal DPI."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True
        )
        # Sök efter "Page size:      595.276 x 841.89 pts (A4)"
        match = re.search(r"Page size:\s+([\d.]+)\s+x\s+([\d.]+)", result.stdout)
        if match:
            width = float(match.group(1))
            height = float(match.group(2))

            area = width * height
            if area <= 0:
                return 595.0, 842.0, 1200  # Fallback till 1200 DPI

            # Höjd upplösning anpassad för bitonal (1-bit) rendering.
            # En standard A4 (ca 501 157 pt²) ger nu ~1200 DPI.
            # Mindre sidor (A5) skalar upp mot ~1700 DPI, större (A3) landar runt ~850 DPI.
            calculated_dpi = round(1200.0 * ((501157 / area) ** 0.5))

            # Sätter ett tak på 1800 DPI för att inte spränga RAM-minnet vid extremt små format,
            # och ett golv på 600 DPI för att garantera bitonal skärpa på stora ritningar.
            dpi = max(600, min(1800, calculated_dpi))

            return width, height, dpi
    except Exception as e:
        print(f"⚠️ Kunde inte läsa PDF-info ({e}), använder standard 1200 DPI för säkerhets skull.")

    return 595.0, 842.0, 1200


def main() -> int:
    if len(sys.argv) < 2:
        print("Ange PDF-fil")
        return 1

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.is_file():
        print("Filen finns inte")
        return 1

    # Vi hämtar mått (för loggning och fallback) samt den smarta upplösningen
    width, height, dpi = get_pdf_dimensions_and_dpi(input_path)
    print(f"📐 Basstorlek: {width}x{height} pt | 🧠 Smart upplösning: {dpi} DPI")

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
        # Genom att ta bort -dFIXEDMEDIA tillåter vi Ghostscript att hantera
        # varierande sidstorlekar och stående/liggande format helt automatiskt per sida!
        print(f"1️⃣ Renderar till 1-bit PBM ({dpi} dpi, dynamisk sidstorlek)…")
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

        subprocess.run(
            [
                sys.executable,
                str(script_dir / "build_jbig2_pdf.py"),
                str(pages_dir),
                str(output_pdf),
                str(width),
                str(height),
            ],
            check=True,
        )

        print(f"🏁 KLAR: {output_pdf.name}")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
