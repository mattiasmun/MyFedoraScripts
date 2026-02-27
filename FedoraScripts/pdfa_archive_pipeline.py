#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import platform
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

# ============================================================
# KONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# ============================================================
# ICC-PROFIL
# ============================================================

def get_icc_path():
    if platform.system() == "Windows":
        return r"C:\msys64\ucrt64\share\texmf-dist\tex\generic\colorprofiles\sRGB.icc"
    else:
        return "/usr/share/ghostscript/iccprofiles/srgb.icc"

ICC_RGB = get_icc_path()

# ============================================================
# GHOSTSCRIPT
# ============================================================

def find_ghostscript():
    candidates = ["gs", "gswin64c", "gswin32c"]
    for c in candidates:
        if shutil.which(c):
            return c
    logging.error("Ghostscript hittades inte i PATH.")
    sys.exit(1)

GS_EXEC = find_ghostscript()

# ============================================================
# SKAPA PDF/A-DEFINITION (KORREKT FÖR PDF/A-3)
# ============================================================

def create_pdfa_def():
    icc_abs = os.path.abspath(ICC_RGB).replace("\\", "/")

    ps = f"""%!
% PDF/A-3B definition

[/_objdef {{icc_obj}} /type /stream /OBJ pdfmark
[{{icc_obj}} ({icc_abs}) (r) file /PUT pdfmark
[{{icc_obj}} << /N 3 >> /PUT pdfmark

[ /ICCProfile {{icc_obj}}
  /OutputConditionIdentifier (sRGB)
  /Info (sRGB IEC61966-2.1)
  /Subtype /GTS_PDFA3
  /Type /OutputIntent
  /S /GTS_PDFA3
  /DEST pdfmark

[{{Catalog}} << /OutputIntents [ {{icc_obj}} ] >> /PUT pdfmark
"""

    with open("pdfa_def.ps", "w", encoding="utf-8") as f:
        f.write(ps)

# ============================================================
# KONVERTERA EN FIL
# ============================================================

def convert_to_pdfa3b(input_pdf: Path, output_pdf: Path) -> bool:

    create_pdfa_def()

    cmd = [
        GS_EXEC,
        "-dPDFA=3",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        "-sColorConversionStrategy=RGB",
        "-sProcessColorModel=DeviceRGB",
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dAutoRotatePages=/None",
        "-dCompatibilityLevel=1.7",
        f"-sOutputFile={output_pdf}",
        "-f", "pdfa_def.ps",
        "-f", str(input_pdf)
    ]

    logging.info(f"Konverterar: {input_pdf.name}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logging.error(f"Ghostscript-fel för {input_pdf.name}")
        logging.error(result.stderr)
        return False

    return True

# ============================================================
# VALIDERING MED VERAPDF (PDF/A-3B STRICT)
# ============================================================

def validate_pdfa3b(file_path: Path) -> bool:

    cmd = [
        "flatpak",
        "run",
        "--command=verapdf",
        "org.verapdf.veraPDF",
        "--format", "xml",
        "--flavour", "3b",
        str(file_path)
    ]

    process = subprocess.run(cmd, capture_output=True, text=True)

    if process.returncode > 1:
        logging.error("veraPDF kraschade.")
        logging.error(process.stderr)
        return False

    if not process.stdout.strip():
        logging.error("veraPDF returnerade tom output.")
        return False

    root = ET.fromstring(process.stdout)
    job = root.find('.//{*}job')
    if job is None:
        return False

    report = job.find('{*}validationReport')
    if report is None:
        return False

    return report.attrib.get("isCompliant", "false").lower() == "true"

# ============================================================
# BEARBETA EN FIL
# ============================================================

def process_file(input_pdf: Path, output_dir: Path):

    output_pdf = output_dir / input_pdf.name

    if not convert_to_pdfa3b(input_pdf, output_pdf):
        return False

    if not validate_pdfa3b(output_pdf):
        logging.error(f"UNDERKÄND PDF/A-3B: {input_pdf.name}")
        output_pdf.unlink(missing_ok=True)
        return False

    logging.info(f"GODKÄND PDF/A-3B: {input_pdf.name}")
    return True

# ============================================================
# BATCH-HANTERING
# ============================================================

def process_directory(input_dir: Path, output_dir: Path):

    if not input_dir.exists():
        logging.error("Indatakatalog finns inte.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.rglob("*.pdf"))

    if not pdf_files:
        logging.warning("Inga PDF-filer hittades.")
        return

    logging.info(f"Hittade {len(pdf_files)} PDF-filer.")

    success = 0
    fail = 0

    for pdf in pdf_files:
        if process_file(pdf, output_dir):
            success += 1
        else:
            fail += 1

    logging.info("===================================")
    logging.info(f"GODKÄNDA: {success}")
    logging.info(f"UNDERKÄNDA: {fail}")
    logging.info("===================================")

# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) != 3:
        print("Användning:")
        print("  python pdfa_archive_pipeline.py <indata_mapp> <utdata_mapp>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    process_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()
