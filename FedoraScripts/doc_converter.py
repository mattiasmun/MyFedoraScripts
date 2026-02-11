#!/usr/bin/env python3
import os
import shutil
import logging
import argparse
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from tqdm import tqdm

# ⎯⎯ IMPORT LIBRARIES ⎯⎯
try:
    from docx2pdf import convert
    import pymupdf  # Kraftfull motor för PDF-hantering
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install docx2pdf pymupdf'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Status Constants ⎯⎯
CONVERSION_FAIL = 0
CONVERSION_SUCCESS = 1
CONVERSION_SKIPPED = 2

# ⎯⎯ Helper Functions ⎯⎯

def format_size(bytes_size):
    return bytes_size / (1024 * 1024)

def setup_logging(dest_dir: str):
    log_path = os.path.join(dest_dir, 'conversion_log.log')
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return log_path

# ⎯⎯ Core Processing Functions ⎯⎯

def convert_docx_to_pdf(source_path: str, dest_path: str, skip_existing: bool) -> int:
    if skip_existing and os.path.exists(dest_path):
        return CONVERSION_SKIPPED
    try:
        convert(source_path, dest_path)
        logging.info(f"SUCCESS: Converted '{source_path}'")
        return CONVERSION_SUCCESS
    except Exception as e:
        logging.error(f"CONVERSION_FAIL: '{source_path}'. Error: {e}")
        return CONVERSION_FAIL

def optimize_pdf_with_images(pdf_path: str) -> tuple[bool, int]:
    """
    Optimerar PDF med JPEG, Bicubic subsampling och avancerad ström-kompression.
    """
    temp_optimized = f"temp_opt_{os.getpid()}_{os.path.basename(pdf_path)}"

    try:
        size_before = os.path.getsize(pdf_path)

        doc = pymupdf.open(pdf_path)

        # ⎯⎯ PYMUPDF OPTIMERING ⎯⎯
        # Konfigurera omskrivning av bilder (JPEG + Bicubic + 200 DPI)
        opts = pymupdf.mupdf.PdfImageRewriterOptions()

        # JPEG Metod (3) och Bicubic Subsampling (1)
        for opt_set in ['color_lossy', 'gray_lossy', 'color_lossless', 'gray_lossless']:
            setattr(opts, f"{opt_set}_image_recompress_method", 3)
            setattr(opts, f"{opt_set}_image_recompress_quality", "75")
            setattr(opts, f"{opt_set}_image_subsample_method", 1)
            setattr(opts, f"{opt_set}_image_subsample_threshold", 210)
            setattr(opts, f"{opt_set}_image_subsample_to", 200)

        opts.bitonal_image_recompress_method = 5
        opts.bitonal_image_subsample_method = 1
        opts.bitonal_image_subsample_threshold = 630
        opts.bitonal_image_subsample_to = 600

        # 1. Optimera bilderna i minnet
        doc.rewrite_images(options=opts)

        # 2. Spara direkt till den temporära filen på disk
        doc.save(
            temp_optimized,
            garbage=4,           # Maximal rensning av dubletter
            deflate=True,        # Komprimera alla strömmar
            use_objstms=1,       # Packa PDF-objekt för mindre storlek (viktigt för PDF 1.5+)
            clean=True,          # Sanera innehållsströmmar
            linear=False,        # Prioritera minsta storlek framför webb-streaming
            no_new_id=False      # Skapar/uppdaterar fil-ID (viktigt för PDF/A)
        )
        doc.close()

        shutil.move(temp_optimized, pdf_path)
        size_after = os.path.getsize(pdf_path)
        return True, (size_before - size_after)
    except Exception as e:
        logging.error(f"OPTIMIZATION_ERROR på {pdf_path}: {e}")
        return False, 0
    finally:
        # Sista städning av temp-filen om den finns kvar
        if os.path.exists(temp_optimized):
            os.remove(temp_optimized)

def run_verapdf_batch(directory: str) -> dict:
    """Kör veraPDF via batch-fil på Windows med rekursiv sökning."""
    results = {}

    home = os.path.expanduser("~")
    verapdf_path = os.path.join(home, "Program", "verapdf-greenfield-1.28.1", "verapdf.bat")

    try:
        # 1. Vi lägger till -r för att söka i mappen
        # 2. Vi behåller --format xml för att kunna parsa resultatet
        cmd = [verapdf_path, "--format", "xml", "-r", directory]

        # shell=True behövs på Windows för .bat-filer
        process = subprocess.run(cmd, capture_output=True, text=True, shell=True)

        if process.returncode != 0:
            logging.error(f"veraPDF exekverades med felkod: {process.returncode}")
            # Skriv ut stderr för att underlätta felsökning om sökvägen är fel
            logging.error(f"Felmeddelande: {process.stderr}")
            return results

        if not process.stdout.strip():
            logging.warning("veraPDF returnerade ingen data.")
            return results

        root = ET.fromstring(process.stdout)

        # veraPDF:s XML-rapport (MRR) har ofta ett namespace.
        # Vi använder en sökning som ignorerar namespace för att vara robusta.
        for item in root.findall('.//{*}item'):
            name_node = item.find('{*}name')
            compliant_node = item.find('.//{*}compliant')

            if name_node is not None and compliant_node is not None:
                # Vi tar bara filnamnet för att matcha mot din stats-logik
                filename = os.path.basename(name_node.text)
                is_compliant = compliant_node.text.lower() == 'true'
                results[filename] = is_compliant
    except Exception as e:
        logging.error(f"BATCH_VALIDATION_FAILED: {e}")
    return results

def main():
    parser = argparse.ArgumentParser(description="DOCX till PDF med 200 DPI bildoptimering och PDF/A-validering.")
    parser.add_argument('-i', '--source-dir', type=str, default='.', help="Ingångsmapp.")
    parser.add_argument('-o', '--destination-dir', type=str, default='.', help="Utgångsmapp.")
    parser.add_argument('-s', '--skip-existing', action='store_true', help="Hoppa över befintliga PDF:er.")
    args = parser.parse_args()

    start_time = datetime.now()
    os.makedirs(args.destination_dir, exist_ok=True)
    log_file = setup_logging(args.destination_dir)

    # Hitta filer
    all_files = []
    for root, _, files in os.walk(args.source_dir):
        for f in files:
            if f.lower().endswith('.docx'):
                all_files.append((root, f))

    if not all_files:
        print("Inga .docx-filer hittades.")
        return

    stats = {
        'found': len(all_files), 'conv_ok': 0, 'conv_fail': 0,
        'skipped': 0, 'saved_bytes': 0, 'pdfa_ok': 0, 'pdfa_fail': 0
    }

    print(f"Bearbetar {len(all_files)} filer… (Logg: {log_file})")

    # Steg 1: Konvertera och Optimera
    for root, filename in tqdm(all_files, desc="Konverterar", unit="fil"):
        rel_path = os.path.relpath(root, args.source_dir)
        dest_dir = os.path.join(args.destination_dir, rel_path)
        os.makedirs(dest_dir, exist_ok=True)

        src_path = os.path.join(root, filename)
        dest_path = os.path.join(dest_dir, filename[:-5] + '.pdf')

        status = convert_docx_to_pdf(src_path, dest_path, args.skip_existing)

        if status == CONVERSION_SKIPPED:
            stats['skipped'] += 1
        elif status == CONVERSION_SUCCESS:
            stats['conv_ok'] += 1
            # Se till att namnet här matchar din def längre upp!
            _, saved = optimize_pdf_with_images(dest_path)
            stats['saved_bytes'] += saved
        else:
            stats['conv_fail'] += 1

    # Steg 2: Batch-validering med veraPDF
    print("Startar PDF/A-validering (Batch)…")
    compliance_report = run_verapdf_batch(args.destination_dir)

    # Matcha resultat
    for filename_pdf in [f[:-5]+'.pdf' for _, f in all_files]:
        if filename_pdf in compliance_report:
            if compliance_report[filename_pdf]:
                stats['pdfa_ok'] += 1
            else:
                stats['pdfa_fail'] += 1
                logging.warning(f"COMPLIANCE FAIL: {filename_pdf}")

    # Rapport
    duration = datetime.now() - start_time
    summary = f"""
⎯⎯ BEARBETNINGSRAPPORT ⎯⎯
Tid: {duration}
Sparat utrymme: {format_size(stats['saved_bytes']):.2f} MB

Filer:
  - Hittade: {stats['found']}
  - Konverterade: {stats['conv_ok']}
  - Hoppade över: {stats['skipped']}
  - PDF/A Godkända: {stats['pdfa_ok']}
  - PDF/A Underkända: {stats['pdfa_fail']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    print(summary)
    logging.info(summary)

if __name__ == "__main__":
    main()
