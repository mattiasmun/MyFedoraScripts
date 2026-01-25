#!/usr/bin/python
import os
import shutil
import logging
import argparse
from datetime import datetime
from tqdm import tqdm

# ⎯⎯ IMPORT LIBRARIES ⎯⎯
try:
    import pymupdf  # Kraftfull motor för PDF-hantering
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pymupdf tqdm'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Configuration ⎯⎯
SOURCE_DIR = '.'
LOG_FILE = ''

# ⎯⎯ Status Constants for Processing ⎯⎯
PDF_SUCCESS = 1
PDF_FAIL = 0
PDF_SKIPPED = 2
PDF_ALREADY_OPTIMIZED = 3

# ⎯⎯ Helper Functions ⎯⎯

def format_size(bytes_size):
    return bytes_size / (1024 * 1024)

def setup_logging(source_dir: str) -> str:
    global LOG_FILE
    LOG_FILE = os.path.join(source_dir, 'pdf_optimization_log.log')
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("⎯⎯ PDF Advanced Optimizer Start (Smart Check + J2K + PDF 1.7) ⎯⎯")
    return LOG_FILE

def is_already_optimized(doc) -> bool:
    """
    Kollar om filen redan är optimerad genom att kontrollera version
    och om bilderna använder JPXDecode (JPEG 2000).
    """
    # Kolla version (måste vara 1.7 eller högre)
    v_str = doc.pdf_get_metadata().get("format", "1.0")
    try:
        version = float(v_str.replace("PDF ", "").replace("PDF-", ""))
    except ValueError:
        version = 1.0

    # Stickprov på de första bilderna för att se om de använder J2K (JPXDecode)
    img_list = doc.get_page_images(0)
    if not img_list:
        return True # Inga bilder att optimera, räknas som klar

    for img in img_list[:3]: # Kolla max 3 bilder för snabbhet
        xref = img[0]
        if "JPXDecode" in doc.xref_object(xref):
            return True

    return False

# ⎯⎯ Core Processing Function ⎯⎯

def validate_and_compress_pdf(pdf_path: str, skip_existing: bool, corrupt_dir: str, force: bool) -> tuple[int, bool, int]:
    try:
        file_size_before = os.path.getsize(pdf_path)
        doc = pymupdf.open(pdf_path)

        # Smart Check: Hoppa över om den redan är optimerad (om inte --force används)
        if not force and is_already_optimized(doc):
            doc.close()
            return PDF_ALREADY_OPTIMIZED, False, 0

        # --- PYMUPDF OPTIMERING ---
        # Konfigurera omskrivning av bilder (J2K + Bicubic + 200 DPI)
        opts = pymupdf.mupdf.PdfImageRewriterOptions()

        # Metod 4 = J2K, Metod 1 = Bicubic
        opts.color_lossy_image_recompress_method = 4
        opts.color_lossy_image_recompress_quality = "85"
        opts.color_lossy_image_subsample_method = 1
        opts.color_lossy_image_subsample_threshold = 210
        opts.color_lossy_image_subsample_to = 200

        opts.gray_lossy_image_recompress_method = 4
        opts.gray_lossy_image_recompress_quality = "85"
        opts.gray_lossy_image_subsample_method = 1
        opts.gray_lossy_image_subsample_threshold = 210
        opts.gray_lossy_image_subsample_to = 200

        # Inkludera även förlustfria format
        opts.color_lossless_image_recompress_method = 4
        opts.gray_lossless_image_recompress_method = 4

        # Utför bild-omskrivningen
        doc.rewrite_images(options=opts)

        # Spara och uppgradera till PDF 1.7 struktur
        doc.save(
            pdf_path,
            incremental=False,
            garbage=4,          # Tar bort dubbletter och oanvända objekt
            deflate=True,        # Komprimerar strömmar
            use_objstms=1,       # Packar PDF-objekt i strömmar (PDF 1.5+)
            clean=True,          # Sanerar innehåll
            no_new_id=False      # Skapar/uppdaterar fil-ID (viktigt för PDF/A)
        )

        # Uppgradera versionsnumret i trailern till 1.7
        doc.init_xref()
        doc.close()

        file_size_after = os.path.getsize(pdf_path)
        bytes_saved = file_size_before - file_size_after

        return PDF_SUCCESS, bytes_saved > 0, bytes_saved

    except Exception as e:
        filename = os.path.basename(pdf_path)
        dest_path = os.path.join(corrupt_dir, filename)

        # Hantera filnamnskonflikter i corrupt-mappen
        if os.path.exists(dest_path):
            dest_path = os.path.join(corrupt_dir, f"{datetime.now().strftime('%H%M%S')}_{filename}")

        try:
            shutil.move(pdf_path, dest_path)
            logging.error(f"ERROR: '{pdf_path}' flyttad. Fel: {e}")
        except: pass
        return PDF_FAIL, False, 0

def process_directory_recursively(args: argparse.Namespace) -> dict:
    results = {
        'found': 0, 'success': 0, 'fail': 0, 'skipped': 0, 'already_opt': 0, 'saved': 0
    }

    corrupt_dir = os.path.join(args.source_dir, 'corrupt_pdfs')
    os.makedirs(corrupt_dir, exist_ok=True)

    all_files = []
    for root, dirs, files in os.walk(args.source_dir):
        if 'corrupt_pdfs' in dirs: dirs.remove('corrupt_pdfs')
        for f in files:
            if f.lower().endswith('.pdf') and f != 'pdf_optimization_log.log':
                all_files.append(os.path.join(root, f))

    results['found'] = len(all_files)

    for pdf_path in tqdm(all_files, desc="Bearbetar", unit="fil"):
        status, reduced, saved = validate_and_compress_pdf(pdf_path, args.skip_existing, corrupt_dir, args.force)

        if status == PDF_SUCCESS:
            results['success'] += 1
            results['saved'] += saved
        elif status == PDF_ALREADY_OPTIMIZED:
            results['already_opt'] += 1
        elif status == PDF_SKIPPED:
            results['skipped'] += 1
        else:
            results['fail'] += 1

    # Ta bort corrupt-mappen om den förblev tom
    if os.path.exists(corrupt_dir) and not os.listdir(corrupt_dir):
        os.rmdir(corrupt_dir)

    return results

def main():
    parser = argparse.ArgumentParser(description="Smart PDF-optimering med J2K och PDF 1.7.")
    parser.add_argument('-s', '--skip-existing', action='store_true', help="Hoppa över baserat på loggens tidsstämpel.")
    parser.add_argument('-f', '--force', action='store_true', help="Tvinga optimering även om filen ser klar ut.")
    parser.add_argument('-i', '--source-dir', type=str, default=SOURCE_DIR, help="Mapp att bearbeta.")
    args = parser.parse_args()

    start_time = datetime.now()
    setup_logging(args.source_dir)

    print(f"Startar smart optimering i: {args.source_dir}\n")
    res = process_directory_recursively(args)

    summary = f"""
⎯⎯ SLUTRAPPORT ⎯⎯
Tid: {datetime.now() - start_time}
Sparat: {format_size(res['saved']):.2f} MB

Filer:
  - Hittade: {res['found']}
  - Optimerade nu: {res['success']}
  - Redan optimerade: {res['already_opt']}
  - Fel/Flyttade: {res['fail']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    print(summary)
    logging.info(summary)

if __name__ == "__main__":
    main()
