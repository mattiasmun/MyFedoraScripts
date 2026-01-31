import os
import glob
import subprocess
from datetime import datetime
from pathlib import Path
from PIL import Image

def convert_to_webp():
    # Starta tidtagning
    start_time = datetime.now()
    print(f"Starttid: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("⎯" * 50)

    count = 0
    total_saved_bytes = 0

    # Hitta JPG-filer (hanterar .jpg, .JPG, .jpeg, .JPEG)
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

                print(f"Bearbetar: {f} (Kvalitet: {quality})... ", end="", flush=True)

                # 2. Spara som WebP via Pillow
                img.save(output_path, "WEBP", quality=quality)

            # 3. Kopiera metadata med ExifTool (eftersom Pillow kan tappa viss metadata)
            subprocess.run(
                ["exiftool", "-overwrite_original", "-TagsFromFile", str(file_path), str(output_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

            # Statistik
            new_size = output_path.stat().st_size
            saved = old_size - new_size
            total_saved_bytes += saved

            # 4. Radera originalet
            file_path.unlink()

            print(f"KLART ({saved / (1024*1024):.2f} MB sparade)")
            count += 1

        except Exception as e:
            print(f"\nFEL vid bearbetning av {f}: {e}")

    # Slutlig rapport
    end_time = datetime.now()
    duration = end_time - start_time
    total_saved_mb = total_saved_bytes / (1024 * 1024)

    print("⎯" * 50)
    print("RESULTAT:")
    print(f"Antal filer bearbetade: {count}")
    print(f"Total plats sparad:     {total_saved_mb:.2f} MB")
    print(f"Total tid (timedelta):  {duration}")
    print("⎯" * 50)

if __name__ == "__main__":
    convert_to_webp()
