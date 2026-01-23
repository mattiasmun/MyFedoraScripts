#!/usr/bin/python
import ocrmypdf
import os
import glob
import argparse
import time
from datetime import datetime
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
        help="Valfri sökväg till mappen där de optimerade filerna ska sparas."
    )

    # Valfritt argument: Rekursiv bearbetning av mappar
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help="Sök efter PDF-filer i undermappar också."
    )

    args = parser.parse_args()

    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir if args.output_dir else INPUT_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Hitta alla PDF-filer
    search_path = os.path.join(INPUT_DIR, '**', '*.pdf') if args.recursive else os.path.join(INPUT_DIR, '*.pdf')
    pdf_files = glob.glob(search_path, recursive=args.recursive)

    try:
        configure_logging(verbosity=Verbosity.default, progress_bar_friendly=True, manage_root_logger=False)
    except Exception:
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

    print(f"\nSTARTAR BATCH-PROCESS")
    print(f"Starttid: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hittade {len(pdf_files)} filer…")
    print("⎯" * 25)

    pbar = tqdm(pdf_files, desc="Optimerar", unit=" fil")

    for input_path in pbar:
        pbar.set_postfix_str(os.path.basename(input_path))

        size_before = os.path.getsize(input_path)
        total_size_before += size_before

        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        if process_file(input_path, output_path):
            if os.path.exists(output_path):
                size_after = os.path.getsize(output_path)
                total_size_after += size_after
                success_count += 1
        else:
            total_size_after += size_before

    # ⎯⎯ AVSLUTA OCH BERÄKNA SKILLNAD ⎯⎯
    end_time_raw = time.time()
    end_dt = datetime.fromtimestamp(end_time_raw)

    # Beräkna exakt tidsskillnad
    diff = end_dt - start_dt
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Storleksberäkning
    saved_bytes = total_size_before - total_size_after
    saved_mb = saved_bytes / (1024 * 1024)
    reduction_percent = (saved_bytes / total_size_before * 100) if total_size_before > 0 else 0

    print("⎯" * 25)
    print("BATCH-PROCESS SLUTFÖRD.")
    print(f"Startade: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Slutade:   {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # Visa dagar endast om det faktiskt tagit mer än ett dygn
    if days > 0:
        print(f"Total körtid: {days}d {hours}h {minutes}m {seconds}s")
    else:
        print(f"Total körtid: {hours}h {minutes}m {seconds}s")

    print(f"Status: {success_count}/{len(pdf_files)} filer optimerade")

    if success_count > 0:
        print(f"Storlek före: {total_size_before / (1024*1024):.2f} MB")
        print(f"Storlek efter: {total_size_after / (1024*1024):.2f} MB")
        print(f"Sparat utrymme: {saved_mb:.2f} MB ({reduction_percent:.1f}% mindre)")

    if len(pdf_files) > 0:
        avg_time = (end_time_raw - start_time_raw) / len(pdf_files)
        print(f"Genomsnittstid per fil: {avg_time:.1f} sekunder")
    print("⎯" * 25)

if __name__ == "__main__":
    main()
