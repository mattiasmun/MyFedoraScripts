#!/usr/bin/python
import os
import logging
import argparse
from datetime import datetime
from tqdm import tqdm

# ⎯⎯ IMPORT LIBRARIES ⎯⎯
try:
    from docx2pdf import convert
    from pikepdf import Pdf, PdfError, ObjectStreamMode
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install docx2pdf pikepdf tqdm'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Configuration ⎯⎯
SOURCE_DIR = '.'
DESTINATION_DIR = '.'
LOG_FILE = ''

# ⎯⎯ Status Constants ⎯⎯
CONVERSION_FAIL = 0
CONVERSION_SUCCESS = 1
CONVERSION_SKIPPED = 2

# ⎯⎯ Helper Functions ⎯⎯

def format_size(bytes_size):
    """Konverterar bytes till MB för rapporten."""
    return bytes_size / (1024 * 1024)

def setup_directories(dest_dir: str):
    os.makedirs(dest_dir, exist_ok=True)

def setup_logging(dest_dir: str) -> str:
    global LOG_FILE
    LOG_FILE = os.path.join(dest_dir, 'conversion_log.log')
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("⎯⎯ Program Start ⎯⎯")
    return LOG_FILE

# ⎯⎯ Core Processing Functions ⎯⎯

def convert_docx_to_pdf(source_path: str, dest_path: str, skip_existing: bool) -> int:
    if skip_existing and os.path.exists(dest_path):
        logging.warning(f"SKIPPED: PDF already exists at '{dest_path}'.")
        return CONVERSION_SKIPPED
    try:
        convert(source_path, dest_path)
        logging.info(f"SUCCESS: Converted '{source_path}' to '{dest_path}'")
        return CONVERSION_SUCCESS
    except Exception as e:
        msg = f"CONVERSION_FAIL: Failed to convert '{source_path}'. Error: {e}"
        logging.error(msg)
        tqdm.write(msg)
        return CONVERSION_FAIL

def validate_and_compress_pdf(pdf_path: str) -> tuple[bool, bool, int]:
    """Returnerar (is_valid, is_compressed, bytes_saved)"""
    try:
        size_before = os.path.getsize(pdf_path)

        # Logik för linjärisering (Endast om filen är 8 MB eller mindre)
        should_linearize = size_before <= (8 * 1024 * 1024)

        with Pdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            pdf.remove_unreferenced_resources()
            pdf.save(
                pdf_path,
                fix_metadata_version=True,
                # Inaktiverat för PDF 1.4-kompatibilitet
                object_stream_mode=ObjectStreamMode.disable,
                compress_streams=True,
                recompress_flate=True,
                linearize=should_linearize,
                qdf=False
            )

        size_after = os.path.getsize(pdf_path)
        bytes_saved = size_before - size_after

        # Om bytes_saved är positivt har vi sparat plats
        is_compressed = bytes_saved > 0

        if is_compressed:
            logging.info(f"OPTIMIZATION: '{pdf_path}' reduced by {bytes_saved} bytes.")
        elif bytes_saved < 0:
            logging.info(f"OPTIMIZATION: '{pdf_path}' increased by {abs(bytes_saved)} bytes.")

        return True, is_compressed, bytes_saved

    except Exception as e:
        logging.error(f"VALIDATION_ERROR: {e}")
        return False, False, 0

def process_directory_recursively(args: argparse.Namespace) -> dict:
    results = {
        'files_found': 0, 'conversion_success': 0, 'conversion_fail': 0,
        'validation_success': 0, 'validation_fail': 0, 'optimization_success': 0,
        'files_removed': 0, 'files_skipped': 0, 'total_bytes_saved': 0
    }

    all_files = []
    for root, _, files in os.walk(args.source_dir):
        for filename in files:
            if filename.lower().endswith('.docx'):
                all_files.append((root, filename))

    results['files_found'] = len(all_files)
    if not all_files:
        tqdm.write("Inga .docx-filer hittades.")
        return results

    for root, filename in tqdm(all_files, desc="Bearbetar filer", unit="fil"):
        rel_path = os.path.relpath(root, args.source_dir)
        dest_dir = os.path.join(args.destination_dir, rel_path)
        os.makedirs(dest_dir, exist_ok=True)

        src_path = os.path.join(root, filename)
        dest_path = os.path.join(dest_dir, filename[:-5] + '.pdf')

        conv_status = convert_docx_to_pdf(src_path, dest_path, args.skip_existing)

        if conv_status == CONVERSION_SKIPPED:
            results['files_skipped'] += 1
            conv_status = CONVERSION_SUCCESS

        if conv_status == CONVERSION_SUCCESS:
            results['conversion_success'] += 1
            is_valid, is_compressed, saved = validate_and_compress_pdf(dest_path)

            if is_valid:
                results['validation_success'] += 1
                # Lägger till resultatet (kan vara negativt om filen växte)
                results['total_bytes_saved'] += saved
                if is_compressed:
                    results['optimization_success'] += 1
                if args.remove_original:
                    os.remove(src_path)
                    results['files_removed'] += 1
            else:
                results['validation_fail'] += 1
        else:
            results['conversion_fail'] += 1

    return results

def main():
    parser = argparse.ArgumentParser(description="DOCX till PDF med PDF 1.4-optimering.")
    parser.add_argument('-r', '--remove-original', action='store_true', help="Ta bort originalfil om PDF är giltig.")
    parser.add_argument('-s', '--skip-existing', action='store_true', help="Hoppa över om PDF redan finns.")
    parser.add_argument('-i', '--source-dir', type=str, default=SOURCE_DIR, help="Ingångsmapp.")
    parser.add_argument('-o', '--destination-dir', type=str, default=DESTINATION_DIR, help="Utgångsmapp.")
    args = parser.parse_args()

    start_time = datetime.now()
    setup_directories(args.destination_dir)
    setup_logging(args.destination_dir)

    tqdm.write(f"Startar process… Loggar till: {LOG_FILE}\n")
    results = process_directory_recursively(args)

    execution_time = datetime.now() - start_time
    saved_mb = format_size(results['total_bytes_saved'])

    summary = f"""
⎯⎯ BEARBETNINGSRAPPORT ⎯⎯
Total körtid: {execution_time}
Total utrymme sparat: {saved_mb:.2f} MB

Filer:
  - Hittade DOCX: {results['files_found']}
  - Hoppade över: {results['files_skipped']}
  - Konverterade: {results['conversion_success']}
  - Lyckade optimeringar (minskad storlek): {results['optimization_success']}
  - Borttagna original: {results['files_removed']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    logging.info(summary)
    print(summary)

if __name__ == "__main__":
    main()
