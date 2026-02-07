#!/usr/bin/env python3
import cv2
import os
import numpy as np
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from pathlib import Path
from PIL import Image
import io
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
    filename_lower = os.path.basename(input_path).lower()

    try:
        # Extrahera JPEG-kvalitet med Pillow innan OpenCV tar över
        with Image.open(input_path) as pilot_img:
            # 1. Kolla om det är en JPG med direkt info
            q_val = pilot_img.info.get("quality")

            # 2. Om det är en WebP, kolla ImageDescription i EXIF
            if q_val is None:
                exif_data = pilot_img.getexif()
                # 270 är tag-ID för ImageDescription
                q_val = exif_data.get(270, "Okänd")

            original_quality = q_val

        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None

        # ⎯⎯ DETEKTERING AV TOM SIDA ⎯⎯
        # Om standardavvikelsen är mycket låg (t.ex. under 8) är bilden troligen tom.
        if np.std(img) < 8:
            return "EMPTY"

        h_orig, w_orig = img.shape[:2]
        is_landscape = w_orig > h_orig

        # Sätt måtten enligt önskemål
        if is_landscape:
            target_w_mm = 271.6
        else:
            target_w_mm = 182.3

        # Bestäm läge (Foto vs Dokument)
        if "foto" in filename_lower:
            is_photo = True
        elif "doc" in filename_lower:
            is_photo = False
        else:
            is_photo = np.std(img) < 45

        # Skalning baserat på mål-bredd (mm till inches för DPI-beräkning)
        actual_target_dpi = photo_target_dpi if is_photo else doc_target_dpi
        target_w_inches = target_w_mm / 25.4
        required_pixels_width = int(target_w_inches * actual_target_dpi)
        scale_factor = required_pixels_width / w_orig

        # ⎯⎯ SMART SKALNINGSLOGIK ⎯⎯
        if is_photo:
            if scale_factor > 1.0: scale_factor = 1.0
            interp = cv2.INTER_AREA
        else:
            if scale_factor > 3.0: scale_factor = 3.0
            interp = cv2.INTER_LANCZOS4 if scale_factor > 1.0 else cv2.INTER_AREA

        img_resized = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=interp)
        img_processed = deskew_image(img_resized)

        if is_photo:
            final_img = Image.fromarray(img_processed).convert('L')
        else:
            # Tvätta bort brus innan bitonal konvertering
            img_blurred = cv2.medianBlur(img_processed, 3)
            # Adaptiv tröskel för dokument (Ger ren 1-bit för CCITT)
            # block_size=11 och C=2 är bra standardvärden för text
            bitonal = cv2.adaptiveThreshold(
                img_blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            final_img = Image.fromarray(bitonal).convert('1')

        # Returnera bild, DPI och den hittade originalkvaliteten
        return final_img, actual_target_dpi, original_quality

    except Exception as e:
        print(f"\nFel vid bearbetning av {input_path}: {e}")
        return None

def main(input_folder, output_filename, target_dpi=600):
    valid_ext = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp')
    files = sorted([os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(valid_ext)])

    if not files:
        print("Inga filer hittades.")
        return

    # ⎯⎯ STARTA TIDTAGNING ⎯⎯
    start_time = datetime.now()
    print(f"Starttid: {start_time.strftime('%H:%M:%S')}")
    print(f"Bearbetar {len(files)} bilder…")

    # 1. Processa bilderna parallellt
    tasks = [(f, target_dpi) for f in files]

    with ProcessPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_single_image, tasks), total=len(tasks), desc="Bildbehandling"))

    # Filtrera bort None och "EMPTY"
    valid_results = [r for r in results if r is not None and r != "EMPTY"]
    total_pages = len(valid_results)

    if total_pages == 0:
        print("Inga sidor kvar efter filtrering av tomma bilder.")
        return

    c = canvas.Canvas(output_filename)

    for i, result in enumerate(valid_results):
        img_obj, dpi, quality = result
        img_w_px, img_h_px = img_obj.size
        is_landscape = img_w_px > img_h_px
        page_num = i + 1

        # Marginaler för A4-papperet (Norr, Öst, Syd, Väst)
        if is_landscape:
            c.setPageSize(landscape(A4))
            p_width, p_height = landscape(A4)
            m_north, m_east, m_south, m_west = 15*mm, 12.7*mm, 12.7*mm, 12.7*mm
        else:
            c.setPageSize(A4)
            p_width, p_height = A4
            m_north, m_east, m_south, m_west = 12.7*mm, 12.7*mm, 12.7*mm, 15*mm

        # Beräkna rityta och anpassa bild
        available_w = p_width - m_west - m_east
        available_h = p_height - m_north - m_south

        # Beräkna bildens storlek i PDF-punkter (1/72 tum) baserat på vald DPI
        draw_w = img_w_px * (72 / dpi)
        draw_h = img_h_px * (72 / dpi)

        # Skala ner om bilden fysiskt inte får plats på papperet
        if draw_w > available_w or draw_h > available_h:
            ratio = min(available_w / draw_w, available_h / draw_h)
            draw_w *= ratio
            draw_h *= ratio

        # Position: Centrerad horisontellt, toppen av sidan vertikalt
        x_pos = (p_width - draw_w) / 2
        y_pos = p_height - m_north - draw_h

        # Grå ram
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(0.2)
        c.rect(x_pos, y_pos, draw_w, draw_h, stroke=1, fill=0)

        # Rita bild
        from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(img_obj), x_pos, y_pos, width=draw_w, height=draw_h)

        # Sidinfo
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)

        # Originalkvalitet till vänster
        c.drawString(m_west, m_south / 2, f"Originalkvalitet: {quality}")

        # Sidnummer till höger
        page_info = f"Sida {page_num} av {total_pages}"
        c.drawRightString(p_width - m_east, m_south / 2, page_info)

        c.showPage()

    c.save()

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "⎯" * 40)
    print(f"KLART! PDF sparad: {output_filename}")
    print(f"Sluttid: {end_time.strftime('%H:%M:%S')}")
    print(f"Total tid: {duration}")
    print("⎯" * 40)

if __name__ == '__main__':
    import sys

    # 1. Kontrollera att en mapp har skickats med som argument
    if len(sys.argv) < 2:
        print("Användning: python optimize_to_bitonal.py <mappsökväg>")
        sys.exit(1)

    # 2. Hämta och städa upp sökvägen
    input_path = os.path.abspath(sys.argv[1])

    # 3. Validera att det faktiskt är en mapp
    if not os.path.isdir(input_path):
        print(f"Fel: '{input_path}' är inte en giltig mapp.")
        sys.exit(1)

    # 4. Definiera utdatafilen i samma mapp
    output_pdf = os.path.join(input_path, "arkiv_slutversion.pdf")

    # 5. Kör huvudfunktionen
    main(input_path, output_pdf)
