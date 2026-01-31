#!/bin/python
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image

def log_message(message, log_file):
    """Skriver ett meddelande till både terminalen och loggfilen."""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def convert_to_webp(target_dir):
    # Setup för tider och loggfil
    start_time = datetime.now()
    log_file = target_dir / "conversion_log.txt"

    # Initiera loggfilen
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\nREKURSIV KÖRNING: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n")

    log_message(f"Målmapp: {target_dir.absolute()}", log_file)
    log_message(f"Starttid: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", log_file)
    log_message("⎯" * 60, log_file)

    count = 0
    total_saved_bytes = 0

    # rglob hittar alla matchande filer i alla undermappar
    extensions = ('*.jpg', '*.jpeg', '*.JPG', '*.JPEG')
    files = []
    for ext in extensions:
        files.extend(list(target_dir.rglob(ext)))

    if not files:
        log_message("Inga JPG/JPEG-filer hittades i målmappen eller dess undermappar.", log_file)
        return

    for file_path in files:
        # Undvik att processa filer som redan har en motsvarande .webp (valfritt)
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

            # 3. Kopiera metadata med ExifTool
            # I webp-convert.py, ersätt subprocess-anropet med detta:
            quality_str = f"Original JPEG Quality: {quality}"
            subprocess.run(
                [
                    "exiftool",
                    "-overwrite_original",
                    "-TagsFromFile", str(file_path),
                    f"-ImageDescription={quality_str}", # Här sparar vi värdet
                    str(output_path)
                ],
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

            # Visa relativ sökväg i loggen för bättre överblick vid rekursion
            relative_path = file_path.relative_to(target_dir)
            log_message(f"Bearbetat: {relative_path} | Kvalitet: {quality} | Sparat: {saved / (1024*1024):.2f} MB", log_file)
            count += 1

        except Exception as e:
            log_message(f"FEL vid bearbetning av {file_path}: {str(e)}", log_file)

    # Slutlig rapport
    end_time = datetime.now()
    duration = end_time - start_time
    total_saved_mb = total_saved_bytes / (1024 * 1024)

    log_message("⎯" * 60, log_file)
    log_message("RESULTAT (REKURSIVT):", log_file)
    log_message(f"Antal filer bearbetade: {count}", log_file)
    log_message(f"Total plats sparad:     {total_saved_mb:.2f} MB", log_file)
    log_message(f"Total tid (timedelta):  {duration}", log_file)
    log_message("⎯" * 60, log_file)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path(".")

    if target.is_dir():
        convert_to_webp(target)
    else:
        print(f"Fel: '{target}' är inte en giltig mapp.")
