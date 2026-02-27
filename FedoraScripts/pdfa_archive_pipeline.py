#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import platform
import logging
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path

# ============================================================
# KONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# ============================================================
# ICC-HANTERING
# ============================================================

def get_icc_path():
    """
    Prioritet:
    1. Lokal sRGB.icc i samma mapp som scriptet
    2. Systemets Ghostscript-ICC (Linux)
    """

    local_icc = os.path.join(os.path.dirname(__file__), "sRGB.icc")
    if os.path.exists(local_icc):
        logging.info("Använder lokal sRGB.icc")
        return local_icc

    system_icc = "/usr/share/ghostscript/iccprofiles/srgb.icc"
    if os.path.exists(system_icc):
        logging.info("Använder systemets Ghostscript sRGB.icc")
        return system_icc

    logging.error("Ingen sRGB.icc hittades.")
    logging.error("Placera sRGB.icc i samma mapp som scriptet.")
    sys.exit(1)

def verify_icc_profile(path: str):
    """
    Verifierar att ICC är sRGB IEC61966-2.1
    """

    if not os.path.exists(path):
        logging.error(f"ICC-profil saknas: {path}")
        sys.exit(1)

    try:
        with open(path, "rb") as f:
            data = f.read()

        if data[36:40] != b'acsp':
            raise ValueError("ICC saknar 'acsp'-signatur")

        if data[16:20] != b'RGB ':
            raise ValueError("ICC är inte RGB")

        if b"sRGB IEC61966-2.1" not in data:
            raise ValueError("ICC är inte sRGB IEC61966-2.1")

        logging.info("ICC verifierad: sRGB IEC61966-2.1")

    except Exception as e:
        logging.error(f"Felaktig ICC-profil: {e}")
        sys.exit(1)

ICC_RGB = get_icc_path()
verify_icc_profile(ICC_RGB)

# ============================================================
# GHOSTSCRIPT
# ============================================================

def find_ghostscript():
    for candidate in ["gs", "gswin64c", "gswin32c"]:
        if shutil.which(candidate):
            return candidate
    logging.error("Ghostscript hittades inte i PATH.")
    sys.exit(1)

GS_EXEC = find_ghostscript()

# ============================================================
# SKAPA TEMPORÄR PDF/A-DEFINITION
# ============================================================

def create_pdfa_def() -> str:
    icc_abs = os.path.abspath(ICC_RGB).replace("\\", "/")

    ps_content = f"""%!
[/_objdef {{icc_obj}} /type /stream /OBJ pdfmark
[{{icc_obj}} ({icc_abs}) (r) file /PUT pdfmark
[{{icc_obj}} << /N 3 >> /PUT pdfmark

[ /ICCProfile {{icc_obj}}
  /OutputConditionIdentifier (sRGB)
  /Info (sRGB IEC61966-2.1)
  /Subtype /GTS_PDFA3
  /Type /OutputIntent
  /S /GTS_PDFA3
  /DESTINATION pdfmark

[{{Catalog}} << /OutputIntents [ {{icc_obj}} ] >> /PUT pdfmark
"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ps")
    tmp.write(ps_content.encode("utf-8"))
    tmp.close()

    return tmp.name

# ============================================================
# KONVERTERING
# ============================================================

def convert_to_pdfa3b(input_pdf: Path, output_pdf: Path) -> bool:

    pdfa_def_path = create_pdfa_def()

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
        "-f", pdfa_def_path,
        "-f", str(input_pdf)
    ]

    logging.info(f"Konverterar: {input_pdf.name}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    os.remove(pdfa_def_path)

    if result.returncode != 0:
        logging.error(f"Ghostscript-fel:\n{result.stderr}")
        return False

    return True

# ============================================================
# STRUKTURKONTROLL AV OUTPUTINTENT
# ============================================================

def verify_embedded_icc(pdf_path: Path) -> bool:
    try:
        with open(pdf_path, "rb") as f:
            data = f.read()

        if b"/OutputIntents" not in data:
            raise ValueError("Saknar /OutputIntents")

        if b"/GTS_PDFA3" not in data:
            raise ValueError("Saknar /GTS_PDFA3")

        if b"/ICCProfile" not in data:
            raise ValueError("Saknar /ICCProfile")

        logging.info("OutputIntent verifierad.")
        return True

    except Exception as e:
        logging.error(f"ICC-kontroll misslyckades: {e}")
        return False

# ============================================================
# VERAPDF (STRICT 3B)
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
        return False

    if not process.stdout.strip():
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
# BEARBETA FIL
# ============================================================

def process_file(input_pdf: Path, output_dir: Path) -> bool:

    output_pdf = output_dir / input_pdf.name

    if not convert_to_pdfa3b(input_pdf, output_pdf):
        return False

    if not verify_embedded_icc(output_pdf):
        output_pdf.unlink(missing_ok=True)
        return False

    if not validate_pdfa3b(output_pdf):
        logging.error(f"UNDERKÄND PDF/A-3B: {input_pdf.name}")
        output_pdf.unlink(missing_ok=True)
        return False

    logging.info(f"GODKÄND PDF/A-3B: {input_pdf.name}")
    return True

# ============================================================
# BATCH
# ============================================================

def process_directory(input_dir: Path, output_dir: Path) -> int:

    if not input_dir.exists():
        logging.error("Indatakatalog finns inte.")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.rglob("*.pdf"))
    if not pdf_files:
        logging.warning("Inga PDF-filer hittades.")
        return 0

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

    return 0 if fail == 0 else 1

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

    exit_code = process_directory(input_dir, output_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
