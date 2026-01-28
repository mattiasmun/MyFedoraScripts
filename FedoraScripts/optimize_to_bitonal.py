import cv2
import os
from PIL import Image
import numpy as np

def process_to_single_pdf(input_folder, output_filename, target_dpi=600):
    valid_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
    processed_images = []
    
    # Hämta och sortera filerna (viktigt för sidordning)
    files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(valid_extensions)])
    
    for filename in files:
        input_path = os.path.join(input_folder, filename)
        
        # 1. Hitta ursprungs-DPI med Pillow
        with Image.open(input_path) as temp_img:
            # info.get('dpi') returnerar ofta en tuple (x, y)
            orig_dpi_tuple = temp_img.info.get('dpi')
            if orig_dpi_tuple:
                orig_dpi = orig_dpi_tuple[0]
            else:
                orig_dpi = 200  # Fallback om info saknas
                print(f"Varning: Ingen DPI funnen i {filename}, antar 200.")
        
        # 2. Läs in med OpenCV för bildbehandling
        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is None: continue

        # 3. Beräkna dynamisk skalningsfaktor
        # Här använder vi din logik: (Mål-DPI / Ursprungs-DPI)
        scale = target_dpi / orig_dpi
        print(f"Bearbetar {filename}: Ursprungs-DPI={orig_dpi}, Skalar med faktor {scale:.2f}")

        # 4. Skala upp
        img_resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

        # 5. Adaptiv Thresholding (Gaussian)
        bitonal_cv = cv2.adaptiveThreshold(
            img_resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        # 6. Konvertera till 1-bit (PIL)
        pil_img = Image.fromarray(bitonal_cv).convert('1')
        processed_images.append(pil_img)

    # 7. Spara allt till EN flersidig PDF
    if processed_images:
        # Första bilden sparas, resten läggs till som "append_images"
        processed_images[0].save(
            output_filename, 
            save_all=True, 
            append_images=processed_images[1:], 
            resolution=target_dpi, 
            compression="group4"
        )
        print(f"\nKlart! Skapade '{output_filename}' med {len(processed_images)} sidor.")
    else:
        print("Inga bilder hittades.")

# Kör scriptet
process_to_single_pdf("mina_skanningar", "sammanställt_dokument.pdf")
