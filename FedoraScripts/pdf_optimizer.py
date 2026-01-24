#!/usr/bin/python
import os
import shutil
import logging
import argparse
import subprocess
from datetime import datetime
from tqdm import tqdm

# ⎯⎯ IMPORT LIBRARIES ⎯⎯
try:
    from pikepdf import Pdf, PdfError, ObjectStreamMode
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pikepdf tqdm'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Configuration ⎯⎯
SOURCE_DIR = '.'
LOG_FILE = ''

# ⎯⎯ Status Constants for Processing ⎯⎯
PDF_SUCCESS = 1
PDF_FAIL = 0
PDF_SKIPPED = 2

# ⎯⎯ Helper Functions ⎯⎯

def format_size(bytes_size):
    return bytes_size / (1024 * 1024)

def setup_directories(source_dir: str):
    os.makedirs(source_dir, exist_ok=True)

def setup_logging(source_dir: str) -> str:
    global LOG_FILE
    LOG_FILE = os.path.join(source_dir, 'pdf_optimization_log.log')
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("⎯⎯ PDF Advanced Optimizer Start (GS + pikepdf) ⎯⎯")
    return LOG_FILE

# ⎯⎯ Core Processing Function ⎯⎯

def validate_and_compress_pdf(pdf_path: str, skip_existing: bool, corrupt_dir: str) -> tuple[int, bool, int]:
    temp_downsampled = f"temp_{os.getpid()}_{os.path.basename(pdf_path)}"

    try:
        file_size_before = os.path.getsize(pdf_path)

        # 1. Skip Check
        if skip_existing and os.path.exists(LOG_FILE):
            if os.path.getmtime(pdf_path) < os.path.getmtime(LOG_FILE):
                return PDF_SKIPPED, False, 0

        # --- STEG 1: GHOSTSCRIPT (DPI-REDUKTION TILL 200 DPI) ---
        gs_command = [
            "gs",
            "-o", temp_downsampled,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/printer",
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageDownsampleType=/Bicubic",
            "-dColorImageResolution=200",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dGrayImageResolution=200",
            "-dMonoImageDownsampleType=/Bicubic",
            "-dMonoImageResolution=200",
            "-dColorImageDownsampleThreshold=1.0",
            "-dGrayImageDownsampleThreshold=1.0",
            "-dMonoImageDownsampleThreshold=1.0",
            "-dNOPAUSE", "-dBATCH", "-dQUIET",
            pdf_path
        ]

        subprocess.run(gs_command, check=True)

        # --- STEG 2: PIKEPDF (STRUKTURELL OPTIMERING) ---
        # Vi läser in temp-filen från GS och skriver tillbaka till originalet
        should_linearize = file_size_before <= (8 * 1024 * 1024)

        with Pdf.open(temp_downsampled, allow_overwriting_input=True) as pdf:
            pdf.remove_unreferenced_resources()
            pdf.save(
                pdf_path,
                fix_metadata_version=True,
                object_stream_mode=ObjectStreamMode.disable,
                compress_streams=True,
                recompress_flate=True,
                linearize=should_linearize,
                qdf=False
            )

        # Städa upp temp-filen
        if os.path.exists(temp_downsampled):
            os.remove(temp_downsampled)

        file_size_after = os.path.getsize(pdf_path)
        bytes_saved = file_size_before - file_size_after

        return PDF_SUCCESS, bytes_saved > 0, bytes_saved

    except (PdfError, subprocess.CalledProcessError, Exception) as e:
        # Städa upp temp-fil om den finns kvar vid fel
        if os.path.exists(temp_downsampled):
            os.remove(temp_downsampled)

        filename = os.path.basename(pdf_path)
        dest_path = os.path.join(corrupt_dir, filename)
        if os.path.exists(dest_path):
            dest_path = os.path.join(corrupt_dir, f"{datetime.now().strftime('%H%M%S')}_{filename}")

        try:
            shutil.move(pdf_path, dest_path)
            logging.error(f"CORRUPT/ERROR: '{pdf_path}' flyttad. Fel: {e}")
        except:
            pass

        return PDF_FAIL, False, 0

def process_directory_recursively(args: argparse.Namespace) -> dict:
    results = {
        'files_found': 0, 'optimization_success': 0, 'optimization_fail': 0,
        'files_skipped': 0, 'size_reduction_count': 0, 'total_bytes_saved': 0
    }

    corrupt_dir = os.path.join(args.source_dir, 'corrupt_pdfs')
    os.makedirs(corrupt_dir, exist_ok=True)

    all_files = []
    for root, dirs, files in os.walk(args.source_dir):
        if 'corrupt_pdfs' in dirs:
            dirs.remove('corrupt_pdfs')
        for filename in files:
            if filename.lower().endswith('.pdf') and filename != 'pdf_optimization_log.log':
                all_files.append(os.path.join(root, filename))

    results['files_found'] = len(all_files)

    for pdf_path in tqdm(all_files, desc="Bearbetar (GS + pikepdf)", unit="fil"):
        status, size_was_reduced, saved = validate_and_compress_pdf(pdf_path, args.skip_existing, corrupt_dir)

        if status == PDF_SUCCESS:
            results['optimization_success'] += 1
            results['total_bytes_saved'] += saved
            if size_was_reduced:
                results['size_reduction_count'] += 1
        elif status == PDF_SKIPPED:
            results['files_skipped'] += 1
        else:
            results['optimization_fail'] += 1

    if os.path.exists(corrupt_dir) and not os.listdir(corrupt_dir):
        os.rmdir(corrupt_dir)

    return results

def main():
    parser = argparse.ArgumentParser(description="PDF-optimering med Ghostscript DPI-downsampling och pikepdf.")
    parser.add_argument('-s', '--skip-existing', action='store_true', help="Hoppa över bearbetade filer.")
    parser.add_argument('-i', '--source-dir', type=str, default=SOURCE_DIR, help="Mapp att bearbeta.")
    args = parser.parse_args()

    start_time = datetime.now()
    setup_directories(args.source_dir)
    setup_logging(args.source_dir)

    tqdm.write(f"Startar avancerad optimering i: {args.source_dir}\n")
    results = process_directory_recursively(args)

    execution_time = datetime.now() - start_time
    saved_mb = format_size(results['total_bytes_saved'])

    summary = f"""
⎯⎯ BEARBETNINGSRAPPORT (AVANCERAD) ⎯⎯
Total körtid: {execution_time}
Total utrymme sparat: {saved_mb:.2f} MB

Filer:
  - PDF-filer hittade: {results['files_found']}
  - Hoppade över: {results['files_skipped']}
  - Lyckade (DPI + Struktur): {results['optimization_success']}
  - Korrupta/Fel (flyttade): {results['optimization_fail']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    logging.info(summary)
    print(summary)

if __name__ == "__main__":
    main()
