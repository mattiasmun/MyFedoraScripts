#!/usr/bin/env python3
"""
scale_and_crop_pdf_numpy_auto_dpi.py

Beskär och skalar PDF-sidor med korrekt marginal, oavsett DPI eller blandade bildformat.
NumPy används för snabb bounding box-beräkning.
Automatisk DPI per sida.

Kräver: pikepdf, pdf2image, numpy, Pillow

Usage:
    python3 scale_and_crop_pdf_numpy_auto_dpi.py input.pdf output.pdf [margin_mm]
"""

import sys
from pathlib import Path
import io
import numpy as np
import pikepdf
from pdf2image import convert_from_bytes
from pikepdf import Array, Stream

DEFAULT_MARGIN_MM = 15  # standard 15 mm

def get_content_bbox(page, pdf):
    """
    Returnerar bounding box i PDF-punkter (llx, lly, urx, ury) för innehållet.
    Renderar sidan via pdf2image till gråskala, använder NumPy för snabb analys.
    DPI beräknas per sida automatiskt.
    """
    pdf_bytes = io.BytesIO()
    pdf.save(pdf_bytes)

    # Rendera först med låg dpi för storlek (t.ex. 72) för att få pixelmått
    temp_images = convert_from_bytes(
        pdf_bytes.getvalue(),
        first_page=page.index+1,
        last_page=page.index+1,
        dpi=72
    )
    temp_image = temp_images[0].convert("L")
    img_width, img_height = temp_image.size

    # MediaBox i pt
    pdf_width_pt = float(page.MediaBox[2])
    pdf_height_pt = float(page.MediaBox[3])

    # Beräkna dpi som behövs för 1 px ≈ 1 pt
    dpi_x = img_width / (pdf_width_pt / 72.0) * 72
    dpi_y = img_height / (pdf_height_pt / 72.0) * 72
    dpi = int(max(dpi_x, dpi_y))

    # Rendera sidan på rätt dpi
    images = convert_from_bytes(
        pdf_bytes.getvalue(),
        first_page=page.index+1,
        last_page=page.index+1,
        dpi=dpi
    )
    im = images[0].convert("L")
    arr = np.array(im)
    mask = arr < 255

    if not mask.any():
        return (0, 0, pdf_width_pt, pdf_height_pt)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    top, bottom = np.where(rows)[0][[0, -1]]
    left, right = np.where(cols)[0][[0, -1]]

    scale_x = pdf_width_pt / im.width
    scale_y = pdf_height_pt / im.height

    llx = left * scale_x
    lly = (im.height - bottom - 1) * scale_y
    urx = (right + 1) * scale_x
    ury = (im.height - top) * scale_y

    return (llx, lly, urx, ury)

def read_content_bytes(page):
    contents_obj = page.get("/Contents")
    content_bytes = b""
    if contents_obj is None:
        return b""
    elif isinstance(contents_obj, Array):
        for item in contents_obj:
            if isinstance(item, Stream):
                content_bytes += item.read_bytes()
            else:
                content_bytes += Stream(item).read_bytes()
    else:
        if isinstance(contents_obj, Stream):
            content_bytes = contents_obj.read_bytes()
        else:
            content_bytes = Stream(contents_obj).read_bytes()
    return content_bytes

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_pdf = Path(sys.argv[1])
    output_pdf = Path(sys.argv[2])
    margin_mm = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_MARGIN_MM
    margin_pt = margin_mm / 0.3528  # mm → pt

    if not input_pdf.exists():
        print(f"❌ Input PDF finns inte: {input_pdf}")
        sys.exit(1)

    with pikepdf.Pdf.open(str(input_pdf)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            llx, lly, urx, ury = [float(v) for v in page.MediaBox]
            width = urx - llx
            height = ury - lly

            content_llx, content_lly, content_urx, content_ury = get_content_bbox(page, pdf)
            content_width = content_urx - content_llx
            content_height = content_ury - content_lly

            available_width = width - 2 * margin_pt
            available_height = height - 2 * margin_pt
            scale_x = available_width / content_width
            scale_y = available_height / content_height
            scale = min(1.0, scale_x, scale_y)

            if scale < 1.0:
                content_bytes = read_content_bytes(page)
                if content_bytes:
                    wrapped = f"""
q
{scale} 0 0 {scale} {margin_pt} {margin_pt} cm
""".encode() + content_bytes + b"\nQ\n"

                    page.Contents = pdf.make_stream(wrapped)
                print(f"✅ Sida {page_num} skalad med faktor {scale:.3f}")
            else:
                print(f"ℹ Sida {page_num} behöver ingen skalning")

        pdf.save(str(output_pdf))
        print(f"✅ PDF sparad: {output_pdf}")

if __name__ == "__main__":
    main()
