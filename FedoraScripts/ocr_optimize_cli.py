#!/usr/bin/python
import ocrmypdf
import os
import glob
import argparse
import time
import subprocess
from datetime import datetime
from ocrmypdf.api import configure_logging, Verbosity
from tqdm import tqdm

def process_file(input_path, output_path):
    """
    1. Nedskalar bilden till 200 DPI via Ghostscript.
    2. Kör OCRmyPDF för textigenkänning och PDF/A-arkivering.
    """
    # Skapa ett unikt namn för temp-filen baserat på process-ID och filnamn
    temp_downsampled = f"temp_{os.getpid()}_{os.path.basename(input_path)}"

    try:
        # --- STEG 1: GHOSTSCRIPT (OPTIMERAD DPI-REDUKTION) ---
        gs_command = [
            "gs",
            "-o", temp_downsampled,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/printer",
            # Aktivera nerskalning explicit
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            # Metod och Upplösning
            "-dColorImageDownsampleType=/Bicubic",
            "-dColorImageResolution=200",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dGrayImageResolution=200",
            "-dMonoImageDownsampleType=/Bicubic",
            "-dMonoImageResolution=200",
            # Threshold=1.0 tvingar nerskalning av allt över 200 DPI
            "-dColorImageDownsampleThreshold=1.0",
            "-dGrayImageDownsampleThreshold=1.0",
            "-dMonoImageDownsampleThreshold=1.0",
            "-dNOPAUSE", "-dBATCH", "-dQUIET",
            input_path
        ]

        subprocess.run(gs_command, check=True)

        # --- STEG 2: OCRMYPDF (OCR & ARKIVERING) ---
        ocrmypdf.ocr(
            temp_downsampled,
            output_path,
            optimize=2,
            jpg_quality=85,
            jbig2_lossy=True,
            clean=True,
            remove_vectors=True,
            fast_web_view=8,
            output_type='pdfa-3',
            redo_ocr=True,
            language=['swe', 'eng'],
            progress_bar=False
        )

        return True
    except Exception as e:
        tqdm.write(f"!!! Ett fel uppstod vid bearbetning av {os.path.basename(input_path)}: {e}")
        return False
    finally:
        # Ta alltid bort temp-filen oavsett om det lyckades eller misslyckades
        if os.path.exists(temp_downsampled):
            os.remove(temp_downsampled)

def main():
    parser = argparse.ArgumentParser(
        description="Batch-optimerar PDF: Nedskalar till 200 DPI och kör OCR/PDF/A-3."
    )
    parser.add_argument('input_dir', type=str, help="Indatamapp")
    parser.add_argument('-o', '--output_dir', type=str, default=None, help="Utdatamapp")
    parser.add_argument('-r', '--recursive', action='store_true', help="Sök rekursivt")

    args = parser.parse_args()

    # Kontrollera beroenden innan start
    if not check_gs_version():
        return

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

    print(f"\nSTARTAR BATCH-PROCESS (Mål: 200 DPI + PDF/A-3)")
    print(f"Starttid: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hittade {len(pdf_files)} filer…")
    print("⎯" * 25)

    pbar = tqdm(pdf_files, desc="Bearbetar", unit=" fil")

    for input_path in pbar:
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

def check_gs_version():
    """Kontrollerar att Ghostscript är installerat och har en modern version för Lanczos."""
    try:
        result = subprocess.run(["gs", "--version"], capture_output=True, text=True, check=True)
        version_str = result.stdout.strip()
        # Hanterar versionsnummer som t.ex. "10.02.1" genom att ta de två första delarna
        parts = version_str.split('.')
        version_num = float(f"{parts[0]}.{parts[1]}")

        if version_num < 9.50:
            print(f"Varning: Din Ghostscript-version ({version_str}) är äldre än 9.50. Lanczos-resampling kan saknas eller fungera sämre.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        print("Fel: Ghostscript ('gs') hittades inte i systemets PATH. Installera Ghostscript för att fortsätta.")
        return False

if __name__ == "__main__":
    main()
