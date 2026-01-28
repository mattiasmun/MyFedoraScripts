#!/bin/python
import cv2
import os
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

def deskew_image(gray_img):
    # Rätar upp bilden baserat på textens lutning.
    thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0: return gray_img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45: angle = -(90 + angle)
    else: angle = -angle
    if abs(angle) < 0.1: return gray_img
    (h, w) = gray_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def process_single_image(args):
    # Bearbetar en enskild bild med hybrid-logik.
    input_path, doc_target_dpi = args
    photo_target_dpi = 200
    # Vi siktar på att bilden ska vara ca 200mm bred (nästan en full A4)
    TARGET_WIDTH_MM = 200
    TARGET_WIDTH_INCHES = TARGET_WIDTH_MM / 25.4

    try:
        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None

        # 1. Foto-detektering (Tröskel 45)
        std_dev = np.std(img)
        is_photo = std_dev < 45

        # 2. Skalningslogik
        actual_target_dpi = photo_target_dpi if is_photo else doc_target_dpi
        required_pixels_width = int(TARGET_WIDTH_INCHES * actual_target_dpi)
        scale_factor = required_pixels_width / img.shape[1]

        # 3. Utför skalning och upprätning
        img_resized = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)
        img_processed = deskew_image(img_resized)

        if is_photo:
            # Spara som Gråskala 8-bit
            return (Image.fromarray(img_processed).convert('L'), actual_target_dpi)
        else:
            # Spara som Bitonal 1-bit
            bitonal_cv = cv2.adaptiveThreshold(
                img_processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            return (Image.fromarray(bitonal_cv).convert('1'), actual_target_dpi)

    except Exception as e:
        print(f"\nFel vid bearbetning av {input_path}: {e}")
        return None

def main(input_folder, output_filename, target_dpi=600):
    valid_ext = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
    files = sorted([os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(valid_ext)])

    if not files: return

    print(f"Skapar PDF. Mål: Dokument {target_dpi} DPI, Foto 200 DPI.")
    tasks = [(f, target_dpi) for f in files]

    with ProcessPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_single_image, tasks),
                                     total=len(tasks),
                                     desc="Bearbetar",
                                     unit="sid"))

    # Filtrera bort fel och separera bild från DPI
    valid_results = [r for r in results if r is not None]
    images = [r[0] for r in valid_results]
    res_list = [r[1] for r in valid_results]

    # Spara PDF med den första sidans upplösning som referens
    images[0].save(
        output_filename,
        save_all=True,
        append_images=images[1:],
        resolution=res_list[0]
    )
    print(f"Klar! Fil sparad som {output_filename}")

if __name__ == '__main__':
    home = os.path.expanduser("~")
    IN_MAP = os.path.join(home, "Bilder")
    UT_FIL = os.path.join(IN_MAP, "optimerat_arkiv.pdf")

    main(IN_MAP, UT_FIL)
