#!/usr/bin/env python3
import ocrmypdf
import os
import glob
import argparse
import time
from datetime import datetime
from ocrmypdf.api import configure_logging, Verbosity
from tqdm import tqdm

# ⎯⎯ IMPORT PYMUPDF ⎯⎯
try:
    import pymupdf  # Kraftfull motor för PDF-hantering
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pymupdf'")
    print(f"Details: {e}")
    exit(1)

def process_file(pdf_path, output_path):
    """
    1. Optimerar bilder till 200 DPI via PyMuPDF (J2K + Bicubic).
    2. Kör OCRmyPDF för textigenkänning och PDF/A-3 arkivering.
    """
    temp_optimized = f"temp_opt_{os.getpid()}_{os.path.basename(pdf_path)}"

    try:
        doc = pymupdf.open(pdf_path)

        # ⎯⎯ PYMUPDF OPTIMERING ⎯⎯
        # Konfigurera omskrivning av bilder (J2K + Bicubic + 200 DPI)
        opts = pymupdf.mupdf.PdfImageRewriterOptions()

        # J2K Metod (4) och Bicubic Subsampling (1)
        for opt_set in ['color_lossy', 'gray_lossy', 'color_lossless', 'gray_lossless']:
            setattr(opts, f"{opt_set}_image_recompress_method", 4)
            setattr(opts, f"{opt_set}_image_recompress_quality", "[20]")
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

        # ⎯⎯ STEG 2: OCRMYPDF (OCR & ARKIVERING) ⎯⎯
        # Eftersom vi redan har optimerat bilderna kan vi sänka kraven i ocrmypdf
        ocrmypdf.ocr(
            temp_optimized,
            output_path,
            optimize=1,            # Låg nivå eftersom vi redan optimerat med PyMuPDF
            clean=False,
            output_type='pdfa-3',
            skip_text=True,
            language=['swe', 'eng'],
            progress_bar=False
        )

        return True
    except Exception as e:
        tqdm.write(f"!!! Ett fel uppstod vid bearbetning av {os.path.basename(input_path)}: {e}")
        return False
    finally:
        # Sista städning av temp-filen om den finns kvar
        if os.path.exists(temp_optimized):
            os.remove(temp_optimized)

def main():
    parser = argparse.ArgumentParser(
        description="Batch-optimerar PDF: PyMuPDF (200 DPI J2K) + OCRmyPDF (PDF/A-3)."
    )
    parser.add_argument('input_dir', type=str, help="Indatamapp")
    parser.add_argument('-o', '--output_dir', type=str, default=None, help="Utdatamapp")
    parser.add_argument('-r', '--recursive', action='store_true', help="Sök rekursivt")

    args = parser.parse_args()

    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir if args.output_dir else INPUT_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Hitta alla PDF-filer
    search_path = os.path.join(INPUT_DIR, '**', '*.pdf') if args.recursive else os.path.join(INPUT_DIR, '*.pdf')
    pdf_files = glob.glob(search_path, recursive=args.recursive)

    try:
        configure_logging(verbosity=Verbosity.default, progress_bar_friendly=True, manage_root_logger=False)
    except:
        pass

    if not pdf_files:
        print(f"\nInga PDF-filer hittades i: {INPUT_DIR}")
        return

    # ⎯⎯ STARTA LOGGNING OCH TID ⎯⎯
    start_time_raw = time.time()
    start_dt = datetime.fromtimestamp(start_time_raw)

    total_size_before = 0
    total_size_after = 0
    success_count = 0

    print(f"\nSTARTAR BATCH-PROCESS (Motor: PyMuPDF + OCRmyPDF)")
    print(f"Inställning: J2K @ 200 DPI -> PDF/A-3")
    print(f"Starttid: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hittade {len(pdf_files)} filer…")
    print("⎯" * 25)

    pbar = tqdm(pdf_files, desc="Bearbetar", unit=" fil")

    for input_path in pbar:
        # Undvik att processa temp-filer om de råkar ligga i samma mapp
        if os.path.basename(input_path).startswith("temp_opt_"):
            continue

        pbar.set_postfix_str(os.path.basename(input_path))
        size_before = os.path.getsize(input_path)
        total_size_before += size_before

        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        if process_file(input_path, output_path):
            if os.path.exists(output_path):
                total_size_after += os.path.getsize(output_path)
                success_count += 1
        else:
            total_size_after += size_before

    # ⎯⎯ AVSLUTA OCH BERÄKNA ⎯⎯
    end_time_raw = time.time()
    diff = datetime.fromtimestamp(end_time_raw) - start_dt

    saved_mb = (total_size_before - total_size_after) / (1024 * 1024)
    reduction = ((total_size_before - total_size_after) / total_size_before * 100) if total_size_before > 0 else 0

    print("⎯" * 25)
    print(f"KLAR. Total tid: {str(diff).split('.')[0]}")
    print(f"Status: {success_count}/{len(pdf_files)} lyckade")
    print(f"Sparat: {saved_mb:.2f} MB ({reduction:.1f}%)")
    print("⎯" * 25)

if __name__ == "__main__":
    main()
