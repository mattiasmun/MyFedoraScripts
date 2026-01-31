#!/bin/python
import os
import glob
import subprocess
from datetime import datetime
from pathlib import Path
from PIL import Image

def log_message(message, log_file):
    """Skriver ett meddelande till både terminalen och loggfilen."""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def convert_to_webp():
    # Setup för tider och loggfil
    start_time = datetime.now()
    log_file = "conversion_log.txt"

    # Initiera loggfilen med en rubrik
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\nNY KÖRNING: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n")

    log_message(f"Starttid: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", log_file)
    log_message("⎯" * 50, log_file)

    count = 0
    total_saved_bytes = 0

    # Hitta JPG-filer
    extensions = ('*.jpg', '*.jpeg', '*.JPG', '*.JPEG')
    files = []
    for ext in extensions:
        files.extend(glob.glob(ext))

    for f in files:
        file_path = Path(f)
        output_path = file_path.with_suffix(".webp")

        try:
            # 1. Öppna bilden och hämta originalkvalitet
            with Image.open(file_path) as img:
                old_size = file_path.stat().st_size

                # Pillow kan ofta läsa JPG-kvalitet från info-dicten
                # Om den inte hittas, faller vi tillbaka på 75
                quality = img.info.get("quality", 75)

                # 2. Spara som WebP via Pillow
                img.save(output_path, "WEBP", quality=quality)

            # 3. Kopiera metadata med ExifTool (eftersom Pillow kan tappa viss metadata)
            subprocess.run(
                ["exiftool", "-overwrite_original", "-TagsFromFile", str(file_path), str(output_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

            # Beräkna besparing
            new_size = output_path.stat().st_size
            saved = old_size - new_size
            total_saved_bytes += saved

            # 4. Radera originalet
            file_path.unlink()

            log_message(f"Bearbetat: {f} | Kvalitet: {quality} | Sparat: {saved / (1024*1024):.2f} MB", log_file)
            count += 1

        except Exception as e:
            log_message(f"FEL vid bearbetning av {f}: {str(e)}", log_file)

    # Slutlig rapport
    end_time = datetime.now()
    duration = end_time - start_time
    total_saved_mb = total_saved_bytes / (1024 * 1024)

    log_message("⎯" * 50, log_file)
    log_message("RESULTAT:", log_file)
    log_message(f"Antal filer bearbetade: {count}", log_file)
    log_message(f"Total plats sparad:     {total_saved_mb:.2f} MB", log_file)
    log_message(f"Total tid (timedelta):  {duration}", log_file)
    log_message("⎯" * 50, log_file)

if __name__ == "__main__":
    convert_to_webp()
