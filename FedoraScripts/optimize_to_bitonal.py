#!/bin/python
import cv2
import os
import numpy as np
from PIL import Image
import io
import img2pdf
import pikepdf
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from datetime import datetime

def deskew_image(gray_img):
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
    input_path, doc_target_dpi = args
    photo_target_dpi = 200
    TARGET_WIDTH_MM = 200
    TARGET_WIDTH_INCHES = TARGET_WIDTH_MM / 25.4
    filename_lower = os.path.basename(input_path).lower()

    try:
        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None

        # 1. Bestäm läge (Override via filnamn eller automatik)
        if "foto" in filename_lower:
            is_photo = True
        elif "doc" in filename_lower:
            is_photo = False
        else:
            # Automatisk detektering om inget nyckelord finns
            std_dev = np.std(img)
            is_photo = std_dev < 45

        # 2. Skalning och upprättning
        actual_target_dpi = photo_target_dpi if is_photo else doc_target_dpi
        required_pixels_width = int(TARGET_WIDTH_INCHES * actual_target_dpi)
        scale_factor = required_pixels_width / img.shape[1]

        img_resized = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)
        img_processed = deskew_image(img_resized)

        img_io = io.BytesIO()

        if is_photo:
            # JPEG2000 för foton (Bevarar gråskala snyggt)
            Image.fromarray(img_processed).convert('L').save(img_io, format='JPEG2000', quality_layers=[20])
        else:
            # Adaptiv tröskel för dokument (Ger ren 1-bit för CCITT)
            # block_size=11 och C=2 är bra standardvärden för text
            bitonal = cv2.adaptiveThreshold(
                img_processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            Image.fromarray(bitonal).convert('1').save(img_io, format='TIFF', compression='group4')

        return img_io.getvalue(), actual_target_dpi

    except Exception as e:
        print(f"\nFel vid bearbetning av {input_path}: {e}")
        return None

def main(input_folder, output_filename, target_dpi=600):
    valid_ext = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
    files = sorted([os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(valid_ext)])

    if not files:
        print("Inga filer hittades.")
        return

    # ⎯⎯ STARTA TIDTAGNING ⎯⎯
    start_time = datetime.now()
    print(f"Startar hybrid-PDF skapande: {start_time.strftime('%H:%M:%S')}")
    print(f"Bearbetar {len(files)} bilder...")

    print(f"Skapar hybrid-PDF (CCITT G4 + JPEG2000).")
    tasks = [(f, target_dpi) for f in files]

    with ProcessPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_single_image, tasks), total=len(tasks), desc="Bildbehandling"))

    # Använd img2pdf för att skapa individuella PDF-sidor
    pdf_pages = []
    for img_data, dpi in [r for r in results if r is not None]:
        layout = img2pdf.get_layout_fun(pagesize=(img2pdf.mm_to_pt(200), None))
        pdf_pages.append(img2pdf.convert(img_data, layout_fun=layout))

    # Slå ihop sidorna med pikepdf
    final_pdf = pikepdf.Pdf.new()
    for page_data in pdf_pages:
        with pikepdf.open(io.BytesIO(page_data)) as src:
            final_pdf.pages.extend(src.pages)

    final_pdf.save(output_filename)

    # ⎯⎯ AVSLUTA OCH BERÄKNA TIDSSKILLNAD ⎯⎯
    end_time = datetime.now()
    duration = end_time - start_time  # Detta skapar ett timedelta-objekt

    print("\n" + "⎯" * 30)
    print(f"Klar! Hybrid-PDF sparad som {output_filename}")
    print(f"Sluttid: {end_time.strftime('%H:%M:%S')}")
    print(f"Total tid: {duration}")
    print("⎯" * 30)

if __name__ == '__main__':
    home = os.path.expanduser("~")
    IN_MAP = os.path.join(home, "Bilder")
    UT_FIL = os.path.join(IN_MAP, "optimerat_hybrid_arkiv.pdf")
    main(IN_MAP, UT_FIL)
