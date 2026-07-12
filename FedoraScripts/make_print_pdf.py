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
    """Hämtar sidstorlek i points från pdfinfo och räknar ut en smart DPI."""
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
            
            # Smart DPI-beräkning baserat på sidans area
            # A4 är ca 501 157 points² -> ger ~424 DPI
            # A5 är ca 250 578 points² -> ger ~600 DPI
            # A3 är ca 1 002 314 points² -> ger ~300 DPI
            area = width * height
            if area <= 0:
                return 595.0, 842.0, 424  # Fallback till A4-ish
                
            calculated_dpi = round(424.264 * ((501157 / area) ** 0.5))
            # Håll DPI inom rimliga gränser (minst 300, max 600)
            dpi = max(300, min(600, calculated_dpi))
            
            return width, height, dpi
    except Exception as e:
        print(f"⚠️ Kunde inte läsa PDF-info ({e}), använder standard A4-mått och 400 DPI.")
    
    return 595.0, 842.0, 424  # Standard fallback (A4)


def main() -> int:
    if len(sys.argv) < 2:
        print("Ange PDF-fil")
        return 1

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.is_file():
        print("Filen finns inte")
        return 1

    # Hämta dynamiska mått och DPI
    width, height, dpi = get_pdf_dimensions_and_dpi(input_path)
    print(f"📐 Detekterad storlek: {width}x{height} pt | 🧠 Smart upplösning: {dpi} DPI")

    base_name = input_path.stem
    ramdisk = Path("/dev/shm")

    if ramdisk.is_dir():
        workdir = Path(
            tempfile.mkdtemp(prefix=f"{base_name}_WORK_", dir=str(ramdisk))
        )
        print(f"⚡ Använder RAM-disk: {workdir}")
    else:
        workdir = Path(tempfile.mkdtemp(prefix=f"{base_name}_WORK_"))
        print("⚠️  RAM-disk saknas, använder disk")

    pages_dir = workdir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"1️⃣ Renderar till 1-bit PBM ({width}x{height} pt, {dpi} dpi)…")
        subprocess.run(
            [
                "gs",
                "-sDEVICE=pbmraw",
                f"-r{dpi}",
                "-dBATCH",
                "-dNOPAUSE",
                "-dFIXEDMEDIA",
                f"-dDEVICEWIDTHPOINTS={width}",
                f"-dDEVICEHEIGHTPOINTS={height}",
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

