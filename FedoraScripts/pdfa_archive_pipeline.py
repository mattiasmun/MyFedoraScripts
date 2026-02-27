#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import logging
import xml.etree.ElementTree as ET
import tempfile
import hashlib
import csv

from pathlib import Path
from datetime import datetime

# ============================================================
# VERSION
# ============================================================

PIPELINE_VERSION = "1.2-production"

# ============================================================
# LOGGNING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ============================================================
# HASH
# ============================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# ============================================================
# STREAM-SÖK
# ============================================================

def file_contains(path: Path, needle: bytes) -> bool:
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            if needle in chunk:
                return True
    return False

# ============================================================
# ICC
# ============================================================

def get_icc_path():
    local_icc = Path(__file__).parent / "sRGB.icc"
    if local_icc.exists():
        logging.info("Använder lokal sRGB.icc")
        return str(local_icc)

    system_icc = Path("/usr/share/ghostscript/iccprofiles/srgb.icc")
    if system_icc.exists():
        logging.info("Använder systemets Ghostscript sRGB.icc")
        return str(system_icc)

    logging.error("Ingen sRGB.icc hittades.")
    sys.exit(1)

def verify_icc_profile(path: str):
    with open(path, "rb") as f:
        data = f.read()

    if data[36:40] != b'acsp':
        raise ValueError("ICC saknar acsp-signatur")
    if data[16:20] != b'RGB ':
        raise ValueError("ICC är inte RGB")
    if b"sRGB IEC61966-2.1" not in data:
        raise ValueError("ICC är inte sRGB IEC61966-2.1")

    logging.info("ICC verifierad.")

ICC_RGB = get_icc_path()
verify_icc_profile(ICC_RGB)

# ============================================================
# EXTERNAL TOOLS
# ============================================================

def find_ghostscript():
    for candidate in ["gs", "gswin64c", "gswin32c"]:
        if shutil.which(candidate):
            return candidate
    logging.error("Ghostscript hittades inte.")
    sys.exit(1)

def find_verapdf():
    if shutil.which("verapdf"):
        return ["verapdf"]
    if shutil.which("flatpak"):
        return ["flatpak", "run", "--command=verapdf", "org.verapdf.veraPDF"]
    logging.error("veraPDF hittades inte.")
    sys.exit(1)

GS_EXEC = find_ghostscript()
VERAPDF_CMD = find_verapdf()

# ============================================================
# PDFMARK GENERERING
# ============================================================

def create_pdfa_def() -> str:
    icc_abs = os.path.abspath(ICC_RGB).replace("\\", "/")

    ps = f"""%!
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
    tmp.write(ps.encode("utf-8"))
    tmp.close()
    return tmp.name

def create_attachment_pdfmark(xml_path: Path) -> str:
    xml_abs = os.path.abspath(xml_path).replace("\\", "/")
    filename = xml_path.name

    ps = f"""%!
[/_objdef {{xml_file}} /type /stream /OBJ pdfmark
[{{xml_file}} ({xml_abs}) (r) file /PUT pdfmark
[{{xml_file}} <<
    /Type /EmbeddedFile
    /Subtype /application#2Fxml
>> /PUT pdfmark

[/_objdef {{xml_filespec}} /type /dict /OBJ pdfmark
[{{xml_filespec}} <<
    /Type /Filespec
    /F ({filename})
    /UF ({filename})
    /EF << /F {{xml_file}} >>
    /AFRelationship /Data
>> /PUT pdfmark

[{{Catalog}} << /AF [ {{xml_filespec}} ] >> /PUT pdfmark
[{{Catalog}} << /Names << /EmbeddedFiles << /Names
  [ ({filename}) {{xml_filespec}} ]
>> >> >> /PUT pdfmark
"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ps")
    tmp.write(ps.encode("utf-8"))
    tmp.close()
    return tmp.name

# ============================================================
# KONVERTERING
# ============================================================

def convert_to_pdfa3b(input_pdf: Path, output_pdf: Path, xml_attachment: Path = None) -> bool:

    pdfa_def = create_pdfa_def()
    attachment_def = None

    if xml_attachment and xml_attachment.exists():
        attachment_def = create_attachment_pdfmark(xml_attachment)

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
        "-f", pdfa_def,
    ]

    if attachment_def:
        cmd += ["-f", attachment_def]

    cmd += ["-f", str(input_pdf)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(result.stderr)
            return False
        return True
    finally:
        if os.path.exists(pdfa_def):
            os.remove(pdfa_def)
        if attachment_def and os.path.exists(attachment_def):
            os.remove(attachment_def)

# ============================================================
# VERIFIERING
# ============================================================

def verify_embedded_icc(pdf_path: Path) -> bool:
    checks = [b"/OutputIntents", b"/GTS_PDFA3", b"/ICCProfile"]
    for c in checks:
        if not file_contains(pdf_path, c):
            logging.error(f"Saknar {c}")
            return False
    return True

def verify_embedded_xml(pdf_path: Path, xml_filename: str) -> bool:
    checks = [
        b"/AF",
        b"/AFRelationship",
        b"/EmbeddedFile",
        b"/application#2Fxml",
        xml_filename.encode("utf-8")
    ]
    for c in checks:
        if not file_contains(pdf_path, c):
            logging.error(f"Saknar {c}")
            return False
    return True

def validate_pdfa3b(file_path: Path) -> bool:

    cmd = VERAPDF_CMD + [
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
# PROCESS FIL
# ============================================================

def process_file(input_pdf: Path, pdfa_dir: Path, xml_attachment: Path = None) -> bool:

    output_pdf = pdfa_dir / input_pdf.name

    if not convert_to_pdfa3b(input_pdf, output_pdf, xml_attachment):
        return False

    if not verify_embedded_icc(output_pdf):
        output_pdf.unlink(missing_ok=True)
        return False

    if xml_attachment:
        if not verify_embedded_xml(output_pdf, xml_attachment.name):
            output_pdf.unlink(missing_ok=True)
            return False

    if not validate_pdfa3b(output_pdf):
        output_pdf.unlink(missing_ok=True)
        return False

    logging.info(f"GODKÄND: {input_pdf.name}")
    return True

# ============================================================
# BATCH
# ============================================================

def process_directory(input_dir: Path, output_root: Path) -> int:

    if not input_dir.exists():
        logging.error("Indatakatalog saknas.")
        return 1

    if input_dir.resolve() == output_root.resolve():
        logging.error("Indata och utdata får inte vara samma.")
        return 1

    pdfa_dir = output_root / "pdfa"
    rejected_dir = output_root / "rejected"
    report_file = output_root / "report.csv"

    pdfa_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.rglob("*.pdf"))
    if not pdf_files:
        logging.warning("Inga PDF-filer hittades.")
        return 0

    report_rows = []
    success = 0
    fail = 0

    for pdf in pdf_files:

        xml_candidate = pdf.with_suffix(".xml")
        xml_attachment = xml_candidate if xml_candidate.exists() else None

        original_hash = sha256_file(pdf)
        xml_hash = sha256_file(xml_attachment) if xml_attachment else ""

        ok = process_file(pdf, pdfa_dir, xml_attachment)

        if ok:
            success += 1
            status = "PASS"
            pdfa_hash = sha256_file(pdfa_dir / pdf.name)
        else:
            fail += 1
            status = "FAIL"
            pdfa_hash = ""
            (rejected_dir / pdf.name).write_bytes(pdf.read_bytes())

        report_rows.append([
            pdf.name,
            status,
            original_hash,
            pdfa_hash,
            xml_hash,
            datetime.now().isoformat(),
            PIPELINE_VERSION
        ])

    with open(report_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "filename",
            "status",
            "sha256_original_pdf",
            "sha256_pdfa",
            "sha256_xml",
            "timestamp",
            "pipeline_version"
        ])
        writer.writerows(report_rows)

    logging.info(f"GODKÄNDA: {success}")
    logging.info(f"UNDERKÄNDA: {fail}")
    logging.info(f"Rapport: {report_file}")

    return 0 if fail == 0 else 1

# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) != 3:
        print("Användning:")
        print("python pdfa_archive_pipeline.py <indata_mapp> <leverans_mapp>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_root = Path(sys.argv[2])

    exit_code = process_directory(input_dir, output_root)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
