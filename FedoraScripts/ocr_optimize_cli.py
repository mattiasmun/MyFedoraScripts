#!/usr/bin/env python3
import argparse
import os
import pymupdf
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

# ——— Nyckelord ———
def update_keywords(doc, *new_tags):
    meta = doc.metadata or {}
    tags = [
        t.strip()
        for t in re.split(r"[;,]", meta.get("keywords", ""))
        if t.strip()
    ]
    for tag in new_tags:
        if tag and tag not in tags:
            tags.append(tag)
    return ", ".join(tags)


# ——— OCR ———
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
        except subprocess.CalledProcessError:
            if i == retries:
                raise
            time.sleep(2 * (i + 1))


# ——— PDF/A info ———
def get_pdfa_info(doc):
    xml = doc.get_xml_metadata() or ""
    part = re.search(r"<pdfaid:part>(\d+)</pdfaid:part>", xml)
    conf = re.search(r"<pdfaid:conformance>(\w+)</pdfaid:conformance>", xml)
    return (part.group(1) if part else "3", conf.group(1) if conf else "B")


# ——— XMP Generering (Robust med datetime) ———
def generate_xmp_from_dt(keywords, dt, creator, producer, part, conf, title, subject):
    iso = dt.isoformat()
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
      <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>
      <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{subject}</rdf:li></rdf:Alt></dc:description>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>"""
    return xmp + "\n" + (" " * 2048) + "\n<?xpacket end=\"w\"?>"


# ——— Worker ———
def process_file(args):
    pdf_path, output_path = args
    temp_files = []

    try:
        # 1. Kontrollera om bearbetning behövs
        with pymupdf.open(pdf_path) as doc:
            meta = doc.metadata or {}
            the_keywords = meta.get("keywords", "")
            tags = {t.strip() for t in re.split(r"[;,]", the_keywords) if t.strip()}
            
            optimized = "OptimizedByPython" in tags
            ocr_done = "OCRByPython" in tags

            if optimized and ocr_done:
                if pdf_path != output_path:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(pdf_path, output_path)
                return (True, None)

        # Skapa en bas-tempfil för transformationerna
        current_input = pdf_path

        # 2. Bildoptimering (om det behövs)
        if not optimized:
            fd, tmp_opt = tempfile.mkstemp(suffix="_opt.pdf")
            os.close(fd)
            temp_files.append(Path(tmp_opt))

            with pymupdf.open(current_input) as doc:
                opts = pymupdf.mupdf.PdfImageRewriterOptions()
                for opt in ["color_lossy", "gray_lossy", "color_lossless", "gray_lossless"]:
                    setattr(opts, f"{opt}_image_recompress_method", 3)
                    setattr(opts, f"{opt}_image_recompress_quality", "75")
                    setattr(opts, f"{opt}_image_subsample_method", 1)
                    setattr(opts, f"{opt}_image_subsample_threshold", 330)
                    setattr(opts, f"{opt}_image_subsample_to", 300)

                doc.rewrite_images(options=opts)
                doc.save(tmp_opt, garbage=4, deflate=True, deflate_images=True)

            current_input = Path(tmp_opt)
            optimized = True

        # 3. OCR (om det behövs)
        if not ocr_done:
            fd, tmp_ocr = tempfile.mkstemp(suffix="_ocr.pdf")
            os.close(fd)
            temp_files.append(Path(tmp_ocr))

            run_ocr(current_input, tmp_ocr)
            current_input = Path(tmp_ocr)
            ocr_done = True

        # 4. Slutgiltig Metadata- och XMP-skrivning
        fd, tmp_final = tempfile.mkstemp(suffix="_final.pdf")
        os.close(fd)
        temp_files.append(Path(tmp_final))

        with pymupdf.open(current_input) as doc:
            the_keywords = update_keywords(
                doc,
                "OptimizedByPython" if optimized else None,
                "OCRByPython" if ocr_done else None,
            )

            now = datetime.now().astimezone()
            offset = now.strftime("%z")
            pdf_date = f"D:{now:%Y%m%d%H%M%S}{offset[:3]}'{offset[3:]}'"
            
            meta = doc.metadata or {}
            creation_date = meta.get("creationDate") or pdf_date
            creator = meta.get("creator") or "Python"
            producer = meta.get("producer") or "OCRmyPDF"
            title = meta.get("title") or ""
            subject = meta.get("subject") or ""

            meta.update({
                "creationDate": creation_date,
                "modDate": pdf_date,
                "keywords": the_keywords,
                "creator": creator,
                "producer": producer,
                "title": title,
                "subject": subject
            })
            doc.set_metadata(meta)

            part, conf = get_pdfa_info(doc)
            xmp = generate_xmp_from_dt(the_keywords, now, "Python", "PyMuPDF", part, conf, title, subject)
            doc.set_xml_metadata(xmp)

            doc.save(tmp_final, garbage=4, deflate=True, deflate_images=True)

        # Flytta färdig fil till destinationen
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_final, output_path)
        return (True, None)

    except subprocess.CalledProcessError as e:
        return (False, f"{pdf_path.name}: {e.stderr or str(e)}")
    except Exception as e:
        return (False, f"{pdf_path.name}: {str(e)}")
    finally:
        # Städa upp ALLA temporära filer som skapades under körningen
        for f in temp_files:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


# ——— MAIN ———
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

    tasks = [
        (f, output_dir / f.relative_to(input_dir))
        for f in files
    ]

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
        for p in (output_dir / f.relative_to(input_dir) for f in files)
        if p.exists()
    )

    elapsed = time.time() - start

    print("\n—" * 25)
    print(f"KLAR på {int(elapsed)}s")
    print(f"Status: {success}/{len(files)} lyckade")
    print(f"Misslyckade: {fail}")

    if failed_files:
        error_log = output_dir / "failed_files.txt"
        with open(error_log, "w", encoding="utf-8") as f:
            f.write("\n".join(failed_files))
        print(f"\nFel loggade i: {error_log}")

    print(f"Sparat: {(total_before - total_after)/1024/1024:.2f} MB")
    print("—" * 25)


if __name__ == "__main__":
    main()
