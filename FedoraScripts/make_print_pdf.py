#!/usr/bin/env python3
"""Create an ultra-fast print-ready PDF from an input PDF."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Ange PDF-fil")
        return 1

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.is_file():
        print("Filen finns inte")
        return 1

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
        print("1️⃣ Renderar till 1-bit PBM (A5 fixed mediabox, 400 dpi)…")
        subprocess.run(
            [
                "gs",
                "-sDEVICE=pbmraw",
                "-r400",
                "-dBATCH",
                "-dNOPAUSE",
                "-dFIXEDMEDIA",
                "-dDEVICEWIDTHPOINTS=420",
                "-dDEVICEHEIGHTPOINTS=595",
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
            ],
            check=True,
        )

        print(f"🏁 KLAR: {output_pdf.name}")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

