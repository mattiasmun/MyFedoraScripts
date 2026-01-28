import cv2
import os
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

def deskew_image(gray_img):
    """Rätar upp bilden för bättre läsbarhet och OCR-resultat."""
    # Invertera för att hitta textstrukturer (Otsu's binarisering hjälper detekteringen)
    thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Hitta koordinater för alla text-pixlar
    coords = np.column_stack(np.where(thresh > 0))
    
    # Beräkna vinkeln på den minsta omslutande rektangeln
    angle = cv2.minAreaRect(coords)[-1]
    
    # Justera vinkeln så den blir korrekt för rotation
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    if abs(angle) < 0.1: # Ingen märkbar lutning
        return gray_img

    # Rotera bilden med högkvalitativ interpolation
    (h, w) = gray_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def process_single_image(args):
    """Huvudfunktion för bearbetning av en enskild sida."""
    input_path, target_dpi = args
    try:
        # 1. Detektera ursprungs-DPI
        with Image.open(input_path) as temp_img:
            orig_dpi = temp_img.info.get('dpi', (200, 200))[0]
        
        # 2. Läs in gråskala
        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None
        
        # 3. Uppskalning (enligt din logik för att bevara detaljer vid bitonal konvertering)
        scale = target_dpi / orig_dpi
        img_resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        
        # 4. Deskew (görs i gråskala för att minimera pixel-aliasing)
        img_deskewed = deskew_image(img_resized)
        
        # 5. Adaptiv Thresholding (hanterar skuggor och ojämnt papper)
        bitonal_cv = cv2.adaptiveThreshold(
            img_deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 6. Konvertera till 1-bit format för PDF
        return Image.fromarray(bitonal_cv).convert('1')
    except Exception as e:
        print(f"\nFel vid bearbetning av {input_path}: {e}")
        return None

def main(input_folder, output_filename, target_dpi=600):
    valid_ext = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
    files = sorted([os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(valid_ext)])
    
    if not files:
        print("Inga bilder hittades.")
        return

    print(f"Startar arkiv-optimering ({len(files)} sidor) → {target_dpi} DPI")
    
    tasks = [(f, target_dpi) for f in files]
    processed_images = []

    # Kör parallellt på alla CPU-kärnor
    print(f"Startar optimering till {target_dpi} DPI…")
    with ProcessPoolExecutor() as executor:
        processed_images = list(tqdm(executor.map(process_single_image, tasks),
                                     total=len(tasks),
                                     desc="Bearbetar",
                                     unit="sid"))

    # Städa bort eventuella None-värden
    processed_images = [img for img in processed_images if img is not None]

    if processed_images:
        print("Kompilerar PDF med CCITT G4-komprimering…")
        processed_images[0].save(
            output_filename,
            save_all=True,
            append_images=processed_images[1:],
            resolution=target_dpi,
            compression="group4"
        )
        print(f"Klart! Resultat sparat i: {output_filename}")

if __name__ == '__main__':
    # JUSTERA DESSA TVÅ RADER:
    IN_MAP = "$HOME/Bilder"
    UT_FIL = IN_MAP + "optimerat_arkiv.pdf"
    
    main(IN_MAP, UT_FIL)
