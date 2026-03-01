#!/usr/bin/env python3
"""
scale_and_crop_pdf_parallel.py

Extremt snabb PDF-beskärning med multiprocessing.
Automatisk DPI + aggressiv NumPy-analys.

Kräver: pikepdf, pdf2image, numpy, Pillow
"""

import io
import argparse
import numpy as np
import pikepdf
from pikepdf import Array, Stream
from pdf2image import convert_from_bytes
from multiprocessing import Pool, cpu_count
from pathlib import Path

DEFAULT_MARGIN_MM = 15
DPI = 200

# ------------------------------------------------------------

def analyze_page(args):
    """
    Körs parallellt.
    Returnerar (page_index, bbox)
    """
    page_index, input_path, mode, value = args

    with pikepdf.Pdf.open(input_path) as pdf:
        page = pdf.pages[page_index]

        # skapa minimal pdf med bara denna sida
        temp_pdf = pikepdf.Pdf.new()
        temp_pdf.pages.append(page)

        buf = io.BytesIO()
        temp_pdf.save(buf)
        pdf_bytes = buf.getvalue()

    images = convert_from_bytes(pdf_bytes, dpi=DPI)
    im = images[0].convert("L")
    arr = np.array(im)

    mask = arr < 250

    pdf_width_pt = float(page.MediaBox[2])
    pdf_height_pt = float(page.MediaBox[3])

    if not mask.any():
        return page_index, (0, 0, pdf_width_pt, pdf_height_pt)

    if mode == "exact":
        ys, xs = np.where(mask)
        top, bottom = ys.min(), ys.max()
        left, right = xs.min(), xs.max()

    else:
        row_counts = np.sum(mask, axis=1)
        col_counts = np.sum(mask, axis=0)

        if mode == "pixels":
            threshold = int(value)
            valid_rows = np.where(row_counts > threshold)[0]
            valid_cols = np.where(col_counts > threshold)[0]

        elif mode == "ratio":
            threshold = float(value)
            row_ratio = row_counts / mask.shape[1]
            col_ratio = col_counts / mask.shape[0]
            valid_rows = np.where(row_ratio > threshold)[0]
            valid_cols = np.where(col_ratio > threshold)[0]

        else:
            raise ValueError("Unknown mode")

        if len(valid_rows) == 0 or len(valid_cols) == 0:
            return page_index, (0, 0, pdf_width_pt, pdf_height_pt)

        top, bottom = valid_rows[0], valid_rows[-1]
        left, right = valid_cols[0], valid_cols[-1]

    scale_x = pdf_width_pt / im.width
    scale_y = pdf_height_pt / im.height

    llx = left * scale_x
    lly = (im.height - bottom - 1) * scale_y
    urx = (right + 1) * scale_x
    ury = (im.height - top) * scale_y

    return page_index, (llx, lly, urx, ury)

# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("margin", nargs="?", default=DEFAULT_MARGIN_MM, type=float)
    parser.add_argument("--mode", choices=["exact", "pixels", "ratio"], default="exact")
    parser.add_argument("--value")

    args = parser.parse_args()

    margin_pt = args.margin / 0.3528
    input_path = args.input

    with pikepdf.Pdf.open(input_path) as pdf:
        num_pages = len(pdf.pages)

    print(f"Analyserar {num_pages} sidor med {cpu_count()} kärnor...")

    tasks = [
        (i, input_path, args.mode, args.value)
        for i in range(num_pages)
    ]

    with Pool(cpu_count()) as pool:
        results = pool.map(analyze_page, tasks)

    results.sort()  # sortera tillbaka i sidordning

    with pikepdf.Pdf.open(input_path) as pdf:

        for page_index, bbox in results:
            page = pdf.pages[page_index]

            llx, lly, urx, ury = [float(v) for v in page.MediaBox]
            width = urx - llx
            height = ury - lly

            content_llx, content_lly, content_urx, content_ury = bbox
            content_width = content_urx - content_llx
            content_height = content_ury - content_lly

            # Tillgängligt utrymme
            available_width = width - 2 * margin_pt
            available_height = height - 2 * margin_pt

            scale = min(
                1.0,
                available_width / content_width,
                available_height / content_height
            )

            if scale < 1.0:

                contents_obj = page.get("/Contents")
                content_bytes = b""

                if contents_obj is None:
                    continue

                elif isinstance(contents_obj, Array):
                    for obj in contents_obj:
                        if isinstance(obj, Stream):
                            content_bytes += obj.read_bytes()

                elif isinstance(contents_obj, Stream):
                    content_bytes = contents_obj.read_bytes()

                scaled_width = content_width * scale
                scaled_height = content_height * scale

                # Horisontell centrering
                x_offset = (width - scaled_width) / 2

                # Exakt 15 mm toppmarginal
                y_offset = height - margin_pt - scaled_height

                # 🔥 Kompensera för ursprunglig position
                tx = x_offset - content_llx * scale
                ty = y_offset - content_lly * scale

                wrapped = f"""
q
{scale} 0 0 {scale} {tx} {ty} cm
""".encode() + content_bytes + b"\nQ\n"

                page.Contents = pdf.make_stream(wrapped)

        pdf.save(args.output)

    print("Klar.")

# ------------------------------------------------------------

if __name__ == "__main__":
    main()
