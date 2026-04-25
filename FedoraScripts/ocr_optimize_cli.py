#!/usr/bin/env python3
import argparse
import os
import pymupdf
import re
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from tqdm import tqdm


# ⎯⎯ OCR ⎯⎯
def run_ocr(input_path, output_path, retries=2):
    command = [
        "ocrmypdf",
        "--optimize", "2",
        "--jbig2-threshold", "0.85",
        "--clean",
        "--deskew",
        "--output-type", "pdfa-3",
        "--skip-text",
        "-l", "swe+eng",
        str(input_path),
        str(output_path)
    ]

    for i in range(retries + 1):
        try:
            subprocess.run(command, check=True, timeout=600, capture_output=True, text=True)
            return
        except subprocess.CalledProcessError as e:
            if i == retries:
                raise
            time.sleep(2 * (i + 1))


# ⎯⎯ PDF/A info ⎯⎯
def get_pdfa_info(doc):
    xml = doc.get_xml_metadata() or ""
    part = re.search(r"<pdfaid:part>(\d+)</pdfaid:part>", xml)
    conf = re.search(r"<pdfaid:conformance>(\w+)</pdfaid:conformance>", xml)
    return (part.group(1) if part else "3", conf.group(1) if conf else "B")


# ⎯⎯ XMP ⎯⎯
def generate_xmp(keywords, pdf_date, creator, producer, part, conf, title, subject):
    clean = pdf_date.replace("D:", "").replace("'", "")
    iso = f"{clean[0:4]}-{clean[4:6]}-{clean[6:8]}T{clean[8:10]}:{clean[10:12]}:{clean[12:14]}+01:00"

    xmp = f"""<?xpacket begin="﻿"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"
      xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
      xmlns:xmp="http://ns.adobe.com/xap/1.0/"
      xmlns:dc="http://purl.org/dc/elements/1.1/">
      <pdfaid:part>{part}</pdfaid:part>
      <pdfaid:conformance>{conf}</pdfaid:conformance>
      <pdf:Producer>{producer}</pdf:Producer>
      <pdf:Keywords>{keywords}</pdf:Keywords>
      <xmp:ModifyDate>{iso}</xmp:ModifyDate>
      <xmp:CreateDate>{iso}</xmp:CreateDate>
      <xmp:MetadataDate>{iso}</xmp:MetadataDate>
      <xmp:CreatorTool>{creator}</xmp:CreatorTool>
      <dc:format>application/pdf</dc:format>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>"""
    return xmp + "\n" + (" " * 2048) + "\n<?xpacket end=\"w\"?>"


# ⎯⎯ Worker ⎯⎯
def process_file(args):
    pdf_path, output_path = args

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_path = Path(tmp.name)

    tmp.close()

    try:
        with pymupdf.open(pdf_path) as doc:
            opts = pymupdf.mupdf.PdfImageRewriterOptions()

            for opt in ["color_lossy", "gray_lossy", "color_lossless", "gray_lossless"]:
                setattr(opts, f"{opt}_image_recompress_method", 3)
                setattr(opts, f"{opt}_image_recompress_quality", "75")
                setattr(opts, f"{opt}_image_subsample_method", 1)
                setattr(opts, f"{opt}_image_subsample_threshold", 330)
                setattr(opts, f"{opt}_image_subsample_to", 300)

            doc.rewrite_images(options=opts)

            now = datetime.now()
            pdf_date = now.strftime("D:%Y%m%d%H%M%S+01'00'")
            meta = doc.metadata or {}

            title = meta.get("title") or "null"
            subject = meta.get("subject") or "null"

            doc.set_metadata({
                "creationDate": pdf_date,
                "modDate": pdf_date,
                "keywords": "OptimizedByPython",
                "creator": "Python",
                "producer": "PyMuPDF",
                "title": title,
                "subject": subject,
            })

            part, conf = get_pdfa_info(doc)
            xmp = generate_xmp("OptimizedByPython", pdf_date, "Python", "PyMuPDF",
                               part, conf, title, subject)
            doc.set_xml_metadata(xmp)

            doc.save(temp_path, garbage=4, deflate=True, deflate_images=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        run_ocr(temp_path, output_path)
        return (True, None)

    except subprocess.CalledProcessError as e:
        return (False, f"{pdf_path.name}: {e.stderr or str(e)}")

    except Exception as e:
        return (False, f"{pdf_path.name}: {str(e)}")

    finally:
        if temp_path.exists():
            temp_path.unlink()


# ⎯⎯ MAIN ⎯⎯
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("-o", "--output_dir")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-j", "--jobs", type=int, default=max(1, os.cpu_count() // 2))

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(exist_ok=True)

    files = list(input_dir.rglob("*.pdf") if args.recursive else input_dir.glob("*.pdf"))
    files = [f for f in files if not f.name.startswith("temp_")]

    if not files:
        print("Inga PDF-filer hittades")
        return

    print(f"Hittade {len(files)} filer")

    start = time.time()

    total_before = sum(f.stat().st_size for f in files)

    tasks = [(f, output_dir / f.name) for f in files]

    success = 0
    fail = 0
    failed_files = []

    with ProcessPoolExecutor(max_workers=args.jobs) as exe:
        for ok, err in tqdm(
            exe.map(process_file, tasks),
            total=len(tasks),
            desc="Bearbetar",
            unit=" fil"
        ):
            if ok:
                success += 1
            else:
                fail += 1
                failed_files.append(err)

    total_after = sum(
        p.stat().st_size
        for p in map(lambda f: output_dir / f.name, files)
        if p.exists()
    )

    elapsed = time.time() - start

    print("\n⎯" * 25)
    print(f"KLAR på {int(elapsed)}s")
    print(f"Status: {success}/{len(files)} lyckade")
    print(f"Misslyckade: {fail}")

    if failed_files:
        error_log = output_dir / "failed_files.txt"
        with open(error_log, "w", encoding="utf-8") as f:
            f.write("\n".join(failed_files))

        print(f"\nFel loggade i: {error_log}")

    print(f"Sparat: {(total_before - total_after)/1024/1024:.2f} MB")
    print("⎯" * 25)


if __name__ == "__main__":
    main()
