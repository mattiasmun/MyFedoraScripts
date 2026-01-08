#!/usr/bin/python
import ocrmypdf
import os
import glob
import argparse
import time
from ocrmypdf.api import configure_logging, Verbosity
from tqdm import tqdm

def process_file(input_path, output_path):
    """
    Kör ocrmypdf med de specificerade optimeringsparametrarna.
    """
    try:
        ocrmypdf.ocr(
            input_path,
            output_path,
            optimize=2,
            jpg_quality=85,
            jbig2_lossy=True,
            clean=True,
            remove_vectors=True,
            fast_web_view=0.03,
            output_type='pdfa-3',
            redo_ocr=True,
            title='Optimerad för Arkiv/Webb',
            author='Batch OCR Script',
            language=['swe', 'eng'],
            progress_bar=False
        )
        return True
    except Exception as e:
        tqdm.write(f"!!! Ett fel uppstod vid bearbetning av {os.path.basename(input_path)}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Batch-optimerar PDF-filer med tidtagning och storleksanalys."
    )

    # Obligatoriskt argument: Indatamapp
    parser.add_argument(
        'input_dir',
        type=str,
        help="Sökvägen till mappen som innehåller de PDF-filer som ska optimeras."
    )

    # Valfritt argument: Utdatamapp
    parser.add_argument(
        '-o', '--output_dir',
        type=str,
        default=None,
        help="Valfri sökväg till mappen där de optimerade filerna ska sparas. Om den inte anges skapas 'output_optimized' inuti indatamappen."
    )

    # Valfritt argument: Rekursiv bearbetning av mappar
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help="Sök efter PDF-filer i undermappar också."
    )

    args = parser.parse_args()

    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir if args.output_dir else os.path.join(INPUT_DIR, 'output_optimized')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Hitta alla PDF-filer
    search_path = os.path.join(INPUT_DIR, '**', '*.pdf') if args.recursive else os.path.join(INPUT_DIR, '*.pdf')
    pdf_files = glob.glob(search_path, recursive=args.recursive)

    # ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
    # Konfigurera loggningen för Progressbar-kompatibilitet
    # Verbosity.default motsvarar standardnivån utan extra -v
    try:
        configure_logging(
            verbosity=Verbosity.default,
            progress_bar_friendly=True, # Mycket viktigt för tqdm-kompatibilitet
            manage_root_logger=False    # Låt skriptet hantera sin egen logik
        )
    except Exception as e:
        # Detta kan vara nödvändigt om du kör i en miljö där loggningsstrukturen redan är låst
        print(f"Varning: Kunde inte konfigurera ocrmypdf-loggning: {e}")
    # ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

    if not pdf_files:
        print(f"\nInga PDF-filer hittades i mappen: {INPUT_DIR}")
        print("Kontrollera sökvägen och att mappen innehåller filer.")
        return

    print(f"\nSTARTAR BATCH-PROCESS (Källmapp: {INPUT_DIR}, Målmapp: {OUTPUT_DIR})")
    print(f"Hittade {len(pdf_files)} filer…")
    print("⎯" * 25)

    # Variabler för statistik
    start_time = time.time()
    total_size_before = 0
    total_size_after = 0
    success_count = 0

    pbar = tqdm(pdf_files, desc="Optimerar", unit=" fil")

    for input_path in pbar:
        pbar.set_postfix_str(os.path.basename(input_path))

        # Mät storlek före
        size_before = os.path.getsize(input_path)
        total_size_before += size_before

        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        if process_file(input_path, output_path):
            # Mät storlek efter (om filen skapades)
            if os.path.exists(output_path):
                size_after = os.path.getsize(output_path)
                total_size_after += size_after
                success_count += 1
        else:
            # Om det misslyckades, räkna med originalstorleken för att inte få missvisande statistik
            total_size_after += size_before

    # Beräkningar för slutskärmen
    end_time = time.time()
    duration = end_time - start_time
    saved_bytes = total_size_before - total_size_after
    saved_mb = saved_bytes / (1024 * 1024)

    # Förhindra division med noll om inga filer bearbetades
    reduction_percent = (saved_bytes / total_size_before * 100) if total_size_before > 0 else 0
    # Omvandla till minuter och sekunder för läsbarhet
    minutes = int(duration // 60)
    seconds = int(duration % 60)

    print("⎯" * 25)
    print("BATCH-PROCESS SLUTFÖRD.")
    print(f"Tid: {minutes}m {seconds}s ({success_count}/{len(pdf_files)} filer klara)")

    if success_count > 0:
        print(f"Storlek före: {total_size_before / (1024*1024):.2f} MB")
        print(f"Storlek efter: {total_size_after / (1024*1024):.2f} MB")
        print(f"Sparat utrymme: {saved_mb:.2f} MB ({reduction_percent:.1f}% mindre)")
    if len(pdf_files) > 0:
        avg_time = duration / len(pdf_files)
        print(f"Genomsnittstid per fil: {avg_time:.1f} sekunder")
    print("⎯" * 25)

if __name__ == "__main__":
    main()
