#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image

def check_dependencies():
    """Kontrollerar att nödvändiga externa program är installerade."""
    dependencies = ["magick", "exiftool"]
    missing = [dep for dep in dependencies if shutil.which(dep) is None]

    if missing:
        print(f"FEL: Följande program saknas: {', '.join(missing)}")
        print("Installera dem med: sudo dnf install ImageMagick perl-Image-ExifTool")
        sys.exit(1)

def log_message(message, log_file):
    """Skriver ett meddelande till både terminalen och loggfilen."""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def get_jpeg_quality(file_path, pillow_img):
    """Försöker hämta JPEG-kvalitet via Pillow eller ImageMagick."""
    # 1. Försök med Pillow
    quality = pillow_img.info.get("quality")
    if quality is not None:
        return quality

    # 2. Fallback: ImageMagick identify
    try:
        result = subprocess.run(
            ["magick", "identify", "-format", "%Q", str(file_path)],
            capture_output=True,
            text=True,
            check=True
        )
        q_val = int(result.stdout.strip())
        if 1 <= q_val <= 100:
            return q_val
    except Exception:
        pass

    return 75

def convert_to_webp(target_dir):
    check_dependencies() # Kontrollera magick och exiftool

    start_time = datetime.now()
    log_file = target_dir / "conversion_log.txt"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\nREKURSIV KÖRNING: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n")

    log_message(f"Målmapp: {target_dir.absolute()}", log_file)
    log_message(f"Starttid: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", log_file)
    log_message("⎯" * 60, log_file)

    count = 0
    skipped = 0
    total_saved_bytes = 0

    extensions = ('*.jpg', '*.jpeg', '*.JPG', '*.JPEG')
    files = []
    for ext in extensions:
        files.extend(list(target_dir.rglob(ext)))

    if not files:
        log_message("Inga JPG/JPEG-filer hittades.", log_file)
        return

    for file_path in files:
        output_path = file_path.with_suffix(".webp")

        # NYTT: Hoppa över om WebP redan finns
        if output_path.exists():
            # Vi raderar originalet även här om du vill att scriptet ska städa upp
            # men i detta läge loggar vi bara att den hoppas över för säkerhets skull.
            skipped += 1
            continue

        try:
            # Spara originalets tidsstämplar
            stat = file_path.stat()
            original_times = (stat.st_atime, stat.st_mtime)

            with Image.open(file_path) as img:
                old_size = stat.st_size
                quality = get_jpeg_quality(file_path, img) # Smart kvalitetskontroll
                img.save(output_path, "WEBP", quality=quality)

            # Kopiera metadata och spara kvalitet i beskrivningen
            quality_str = f"Original JPEG Quality: {quality}"
            subprocess.run(
                [
                    "exiftool",
                    "-overwrite_original",
                    "-TagsFromFile", str(file_path),
                    f"-ImageDescription={quality_str}",
                    str(output_path)
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

            # Återställ tidsstämplar på den nya WebP-filen
            os.utime(output_path, original_times)

            new_size = output_path.stat().st_size
            saved = old_size - new_size
            total_saved_bytes += saved
            file_path.unlink() # Radera originalet

            relative_path = file_path.relative_to(target_dir)
            log_message(f"Bearbetat: {relative_path} | Kvalitet: {quality} | Sparat: {saved / (1024*1024):.2f} MB", log_file)
            count += 1

        except Exception as e:
            log_message(f"FEL vid bearbetning av {file_path}: {str(e)}", log_file)

    end_time = datetime.now()
    duration = end_time - start_time
    log_message("⎯" * 60, log_file)
    log_message(f"Filer konverterade:   {count}", log_file)
    log_message(f"Filer hoppades över: {skipped}", log_file)
    log_message(f"Total plats sparad:  {total_saved_bytes / (1024 * 1024):.2f} MB", log_file)
    log_message(f"Total tid:           {duration}", log_file)

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if target.is_dir():
        convert_to_webp(target)
    else:
        print(f"Fel: '{target}' är inte en giltig mapp.")
