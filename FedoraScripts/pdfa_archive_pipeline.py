#!/usr/bin/env python3
"""
PDF/A Archive Pipeline
Version: 1.4-stable

Funktioner:
- PDF/A-2B som standard
- PDF/A-3B vid XML-bilagor
- ISO 19005-2 / ISO 19005-3 kompatibel
- ICC-verifiering (sRGB IEC61966-2.1)
- Ghostscript-konvertering
- veraPDF-validering
- SHA-256 fixitet
- Manifest (JSON) + CSV-rapport
- Batch-hantering
- Timeout-skydd
- Säker temporärfilshantering

Arkivmässigt avsedd för kommunal e-arkivleverans.
"""

import json
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

PIPELINE_VERSION = "1.4-stable"
GHOSTSCRIPT_TIMEOUT = 300
VERAPDF_TIMEOUT = 180

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
# STREAM-SÖK (överlappssäker)
# ============================================================

def file_contains(path: Path, needle: bytes, chunk_size: int = 65536) -> bool:
    overlap = len(needle) - 1
    previous = b""

    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            data = previous + chunk
            if needle in data:
                return True

            previous = data[-overlap:] if overlap > 0 else b""

    return False

# ============================================================
# ICC – ENDAST LOKAL PROFIL (reproducerbar arkivmodell)
# ============================================================

PROJECT_ROOT = Path(__file__).parent
LOCAL_ICC = PROJECT_ROOT / "icc" / "sRGB.icc"

if not LOCAL_ICC.exists():
    logging.error("Lokal ICC-profil saknas: icc/sRGB.icc")
    sys.exit(1)

def verify_icc_profile(path: Path):
    """
    Verifierar att ICC-profilen är en giltig RGB-profil
    lämplig för PDF/A (t.ex. sRGB IEC61966-2.1).
    """

    with open(path, "rb") as f:
        header = f.read(128)

        if len(header) < 128:
            raise ValueError("ICC-fil för kort")

        if header[36:40] != b'acsp':
            raise ValueError("ICC saknar giltig 'acsp'-signatur")

        device_class = header[12:16]
        color_space = header[16:20]
        pcs = header[20:24]

        if color_space != b"RGB ":
            raise ValueError("ICC är inte RGB")

        if pcs != b"XYZ ":
            raise ValueError("ICC PCS är inte XYZ")

        if device_class not in [b"mntr", b"prtr", b"scnr"]:
            raise ValueError("ICC har oväntad device class")

    logging.info("ICC verifierad: giltig lokal RGB-profil för PDF/A")

verify_icc_profile(LOCAL_ICC)

ICC_SHA256 = sha256_file(LOCAL_ICC)

# ============================================================
# DYNAMISK PDFA_def GENERERING (deterministisk)
# ============================================================

def generate_pdfa_def(icc_path: Path, level: int) -> Path:
    """
    Genererar deterministisk PDFA_def med korrekt GTS_PDFA-nivå.
    """

    icc_abs = icc_path.resolve().as_posix()
    gts = "GTS_PDFA3" if level == 3 else "GTS_PDFA2"

    content = f"""%!
% Auto-generated PDF/A prefix (deterministisk)

[ /Title (PDF/A Document)
  /DOCINFO pdfmark

/ICCProfile ({icc_abs}) def

[/_objdef {{icc_PDFA}} /type /stream /OBJ pdfmark
[{{icc_PDFA}} <<
  /N 3
>> /PUT pdfmark

[
{{icc_PDFA}}
{{ICCProfile (r) file}} stopped
{{
  (\\nFailed to open ICC profile.\\n) print
  cleartomark
}}
{{
  /PUT pdfmark

  [/_objdef {{OutputIntent_PDFA}} /type /dict /OBJ pdfmark
  [{{OutputIntent_PDFA}} <<
    /Type /OutputIntent
    /S /{gts}
    /DestOutputProfile {{icc_PDFA}}
    /OutputConditionIdentifier (sRGB IEC61966-2.1)
    /Info (sRGB IEC61966-2.1)
  >> /PUT pdfmark

  [{{Catalog}} <</OutputIntents [ {{OutputIntent_PDFA}} ]>> /PUT pdfmark
}} ifelse
"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ps")
    tmp.write(content.encode("utf-8"))
    tmp.close()

    return Path(tmp.name)

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
# PDFMARK
# ============================================================

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
    /Desc (XML metadata)
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
# KONVERTERING – STABIL 1.5
# ============================================================

def convert_to_pdfa(input_pdf: Path,
                    output_pdf: Path,
                    xml_attachment: Path = None) -> tuple[bool, int, str]:

    level = 3 if xml_attachment else 2
    pdfa_def_path = generate_pdfa_def(LOCAL_ICC, level)
    pdfa_def_sha256 = sha256_file(pdfa_def_path)
    attachment_def = None

    if xml_attachment and xml_attachment.exists():
        attachment_def = create_attachment_pdfmark(xml_attachment)

    cmd = [
        GS_EXEC,
        f"-dPDFA={level}",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        "-dUseCIEColor",
        "-sColorConversionStrategy=RGB",
        "-sProcessColorModel=DeviceRGB",
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dAutoRotatePages=/None",
        "-dCompatibilityLevel=1.7",
        f"--permit-file-read={LOCAL_ICC.resolve()}",
        f"-sOutputFile={output_pdf}",
        "-f", str(pdfa_def_path),
    ]

    if attachment_def:
        cmd += ["-f", attachment_def]

    cmd += ["-f", str(input_pdf)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=GHOSTSCRIPT_TIMEOUT
        )

        if result.returncode != 0:
            logging.error(f"Ghostscript-fel:\n{result.stderr}")
            return False, level, pdfa_def_sha256

        return True, level, pdfa_def_sha256

    except subprocess.TimeoutExpired:
        logging.error(f"Ghostscript timeout efter {GHOSTSCRIPT_TIMEOUT} sekunder.")
        return False, level, pdfa_def_sha256

    finally:
        if attachment_def and os.path.exists(attachment_def):
            os.remove(attachment_def)

        if pdfa_def_path.exists():
            pdfa_def_path.unlink(missing_ok=True)

# ============================================================
# RASTER FALLBACK – STABIL 1.5
# ============================================================

def convert_to_pdfa_raster(input_pdf: Path,
                           output_pdf: Path,
                           level: int) -> tuple[bool, str]:

    pdfa_def_path = generate_pdfa_def(LOCAL_ICC, level)
    pdfa_def_sha256 = sha256_file(pdfa_def_path)

    cmd = [
        GS_EXEC,
        f"-dPDFA={level}",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        "-dUseCIEColor",
        "-sColorConversionStrategy=RGB",
        "-sProcessColorModel=DeviceRGB",
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dAutoRotatePages=/None",
        "-r300",
        f"--permit-file-read={LOCAL_ICC.resolve()}",
        f"-sOutputFile={output_pdf}",
        "-f", str(pdfa_def_path),
        "-f", str(input_pdf)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=GHOSTSCRIPT_TIMEOUT
        )

        if result.returncode != 0:
            logging.error(f"Raster-Ghostscript-fel:\n{result.stderr}")
            return False, pdfa_def_sha256

        return True, pdfa_def_sha256

    except subprocess.TimeoutExpired:
        logging.error("Raster-konvertering timeout.")
        return False, pdfa_def_sha256

    finally:
        if pdfa_def_path.exists():
            pdfa_def_path.unlink(missing_ok=True)

# ============================================================
# VERIFIERING
# ============================================================

def verify_output_intent(pdf_path: Path) -> bool:
    if not file_contains(pdf_path, b"/OutputIntents"):
        return False
    if not file_contains(pdf_path, b"/ICCProfile"):
        return False
    if not any(file_contains(pdf_path, tag)
               for tag in [b"/GTS_PDFA2", b"/GTS_PDFA3"]):
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
    return all(file_contains(pdf_path, c) for c in checks)

def validate_pdfa(file_path: Path, level: int) -> bool:
    flavour = "3b" if level == 3 else "2b"

    cmd = VERAPDF_CMD + [
        "--format", "xml",
        "--flavour", flavour,
        str(file_path)
    ]

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=VERAPDF_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        logging.error(f"veraPDF timeout efter {VERAPDF_TIMEOUT} sekunder.")
        return False

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
# PROCESS
# ============================================================

def process_file_with_level(input_pdf: Path,
                            pdfa_dir: Path,
                            xml_attachment: Path = None) -> tuple[bool, int, str, str]:

    output_pdf = pdfa_dir / input_pdf.name
    level = 3 if xml_attachment else 2

    # 1️⃣ Direktförsök
    ok, _, pdfa_def_hash = convert_to_pdfa(
        input_pdf, output_pdf, xml_attachment
    )

    if ok:
        if validate_pdfa(output_pdf, level):
            logging.info(f"GODKÄND PDF/A-{level}B (direkt): {input_pdf.name}")
            return True, level, "direct", pdfa_def_hash

    # 2️⃣ Raster fallback (endast om direkt misslyckades tekniskt)
    if not ok:
        logging.warning(f"Fallback rasterisering: {input_pdf.name}")

        raster_ok, pdfa_def_hash = convert_to_pdfa_raster(
            input_pdf, output_pdf, level
        )

        if raster_ok:
            if validate_pdfa(output_pdf, level):
                logging.info(f"GODKÄND PDF/A-{level}B (raster): {input_pdf.name}")
                return True, level, "rasterized", pdfa_def_hash
            else:
                logging.warning(f"veraPDF underkände (raster): {input_pdf.name}")

    # 3️⃣ Misslyckande – MEN SPARA FILEN
    logging.error(f"UNDERKÄND men sparad: {input_pdf.name}")
    return False, level, "failed", pdfa_def_hash

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
    manifest_file = output_root / "manifest.json"
    manifest_entries = []

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
        if xml_candidate.exists() and xml_candidate.stat().st_size > 0:
            xml_attachment = xml_candidate
        else:
            xml_attachment = None

        original_hash = sha256_file(pdf)
        xml_hash = sha256_file(xml_attachment) if xml_attachment else ""

        ok, level, method, pdfa_def_hash = process_file_with_level(pdf, pdfa_dir, xml_attachment)
        pdfa_level_str = f"{level}B"

        if ok:
            success += 1
            status = "PASS"
            pdfa_hash = sha256_file(pdfa_dir / pdf.name)
        else:
            fail += 1
            status = "FAIL"

        generated_pdf = pdfa_dir / pdf.name
        if generated_pdf.exists():
            shutil.move(
                generated_pdf,
                rejected_dir / pdf.name
            )
            pdfa_hash = sha256_file(rejected_dir / pdf.name)
        else:
            pdfa_hash = ""

        report_rows.append([
            pdf.name,
            status,
            original_hash,
            pdfa_hash,
            xml_hash,
            datetime.now().isoformat(),
            PIPELINE_VERSION
        ])

        manifest_entries.append({
            "filename": pdf.name,
            "status": status,
            "pdfa_level": pdfa_level_str,
            "conversion_method": method,
            "sha256_original": original_hash,
            "sha256_pdfa": pdfa_hash,
            "sha256_xml": xml_hash,
            "icc_profile": "sRGB IEC61966-2.1",
            "icc_sha256": ICC_SHA256,
            "pdfa_def_sha256": pdfa_def_hash,
            "timestamp": datetime.now().isoformat()
        })

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

    manifest_data = {
        "package": {
            "created": datetime.now().isoformat(),
            "pipeline_version": PIPELINE_VERSION,
            "total_files": len(pdf_files),
            "approved": success,
            "rejected": fail
        },
        "files": manifest_entries
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    logging.info(f"Manifest skapad: {manifest_file}")

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

    sys.exit(process_directory(input_dir, output_root))

if __name__ == "__main__":
    main()
