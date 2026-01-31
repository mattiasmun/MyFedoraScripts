#!/bin/python
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
        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None

        # Bestäm orientering för skalning
        h_orig, w_orig = img.shape[:2]
        is_landscape = w_orig > h_orig

        # Sätt måtten enligt önskemål
        if is_landscape:
            target_w_mm, target_h_mm = 271.6, 182.3
        else:
            target_w_mm, target_h_mm = 182.3, 271.6

        # Bestäm läge (Foto vs Dokument)
        if "foto" in filename_lower:
            is_photo = True
        elif "doc" in filename_lower:
            is_photo = False
        else:
            # Automatisk detektering om inget nyckelord finns
            std_dev = np.std(img)
            is_photo = std_dev < 45

        # Skalning baserat på mål-bredd (mm till inches för DPI-beräkning)
        actual_target_dpi = photo_target_dpi if is_photo else doc_target_dpi
        target_w_inches = target_w_mm / 25.4
        required_pixels_width = int(target_w_inches * actual_target_dpi)
        scale_factor = required_pixels_width / w_orig

        img_resized = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)
        img_processed = deskew_image(img_resized)

        if is_photo:
            final_img = Image.fromarray(img_processed).convert('L')
        else:
            # Adaptiv tröskel för dokument (Ger ren 1-bit för CCITT)
            # block_size=11 och C=2 är bra standardvärden för text
            bitonal = cv2.adaptiveThreshold(
                img_processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            final_img = Image.fromarray(bitonal).convert('1')

        return final_img, actual_target_dpi

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
        processed_images = list(tqdm(executor.map(process_single_image, tasks), total=len(tasks), desc="Bildbehandling"))

    # 2. Skapa PDF med ReportLab
    c = canvas.Canvas(output_filename)
    total_pages = len([r for r in processed_images if r is not None])

    for i, result in enumerate(processed_images):
        if result is None: continue
        img_obj, dpi = result
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

        # Bildens storlek i mm (omvandlat till punkter för ReportLab)
        draw_w = img_w_px * (72 / dpi)
        draw_h = img_h_px * (72 / dpi)

        # Säkerställ att bilden inte överskrider ritytan (vid avrundningsfel)
        if draw_w > available_w or draw_h > available_h:
            ratio = min(available_w / draw_w, available_h / draw_h)
            draw_w *= ratio
            draw_h *= ratio

        # Centrera position
        x_pos = m_west + (available_w - draw_w) / 2
        y_pos = m_south + (available_h - draw_h) / 2

        # Grå ram
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(0.2)
        c.rect(x_pos, y_pos, draw_w, draw_h, stroke=1, fill=0)

        # Rita bild
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(img_obj)
        c.drawImage(img_reader, x_pos, y_pos, width=draw_w, height=draw_h)

        # 3. Lägg till sidnumrering (nere till höger)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
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
    home = os.path.expanduser("~")
    IN_MAP = os.path.join(home, "Bilder")
    UT_FIL = os.path.join(IN_MAP, "arkiv_slutversion.pdf")
    main(IN_MAP, UT_FIL)
