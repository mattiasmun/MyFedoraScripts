#!/usr/bin/env python3
import os
import shutil
import logging
import argparse
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from tqdm import tqdm

# ⎯⎯ IMPORT PYMUPDF ⎯⎯
try:
    import pymupdf  # Kraftfull motor för PDF-hantering
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pymupdf'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Configuration ⎯⎯
SOURCE_DIR = '.'
LOG_FILE = ''

# ⎯⎯ Status Constants for Processing ⎯⎯
PDF_SUCCESS = 1
PDF_FAIL = 0
PDF_SKIPPED = 2
PDF_ALREADY_OPTIMIZED = 3

# ⎯⎯ Helper Functions ⎯⎯

def format_size(bytes_size):
    return bytes_size / (1024 * 1024)

def setup_logging(source_dir: str) -> str:
    global LOG_FILE
    LOG_FILE = os.path.join(source_dir, 'pdf_optimization_log.log')
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("⎯⎯ PDF Advanced Optimizer Start (Smart Check + JPEG + PDF 1.5) ⎯⎯")
    return LOG_FILE

def generate_pdfa_xmp(keywords, pdf_date, creator, producer):
    # Om datumet kommer in som "D:2023…", ta bort "D:"
    clean_date = pdf_date.replace("D:", "").replace("'", "")

    # ISO-format: YYYY-MM-DDTHH:MM:SS+01:00
    iso_date = (f"{clean_date[0:4]}-{clean_date[4:6]}-{clean_date[6:8]}T"
                f"{clean_date[8:10]}:{clean_date[10:12]}:{clean_date[12:14]}+01:00")

    doc_id = f"uuid:{uuid.uuid4()}"

    # Skapa själva XMP-innehållet
    xmp_content = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
   <pdfaid:part>3</pdfaid:part>
   <pdfaid:conformance>B</pdfaid:conformance>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:pdf="http://ns.adobe.com/pdf/1.3/">
   <pdf:Keywords>{keywords}</pdf:Keywords>
   <pdf:Producer>{producer}</pdf:Producer>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/">
   <xmp:CreatorTool>{creator}</xmp:CreatorTool>
   <xmp:CreateDate>{iso_date}</xmp:CreateDate>
   <xmp:ModifyDate>{iso_date}</xmp:ModifyDate>
   <xmp:MetadataDate>{iso_date}</xmp:MetadataDate>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/">
   <xmpMM:DocumentID>{doc_id}</xmpMM:DocumentID>
   <xmpMM:InstanceID>{doc_id}</xmpMM:InstanceID>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>"""

    # Lägg till padding (ca 2048 mellanslag)
    # Detta gör att filen kan redigeras snabbare av t.ex. Adobe Acrobat
    padding = " " * 2048
    return f"{xmp_content}\n{padding}\n<?xpacket end=\"w\"?>"

def is_already_optimized(doc) -> bool:
    """
    Kollar om filen redan är optimerad genom att kontrollera metadata
    och bildernas egenskaper via PyMuPDF:s inbyggda metoder.
    """
    # 1. Kolla efter vårt eget "fingeravtryck" i metadata
    # (Vi lägger till detta i doc.save i validate_and_compress_pdf)
    if doc.metadata.get("keywords") and "OptimizedByPythonScript" in doc.metadata["keywords"]:
        return True

    # 2. Kontrollera PDF-version (PDF 1.5+ krävs för objektströmmar/optimal komprimering)
    v_str = doc.metadata.get("format", "1.0")
    try:
        version = float(v_str.replace("PDF ", "").replace("PDF-", ""))
        if version < 1.5:
            return False
    except:
        pass

    # 3. Analysera bildfilter via objekt-inställningar istället för rå strängmatchning
    try:
        found_image = False
        for page_index in range(min(doc.page_count, 3)): # Kolla de första 3 sidorna
            img_list = doc.get_page_images(page_index)
            for img in img_list:
                found_image = True
                xref = img[0]

                # Hämta bildens egenskaper som en dictionary
                # 'colorspace' 1 = Grayscale, 3 = RGB
                # Vi kollar om filtret är ['DCTDecode'] (vilket är JPEG)
                img_info = doc.extract_image(xref)
                if img_info and img_info.get("extension") == "jpeg":
                    # Om bilden redan är JPEG och har rätt upplösning (valfritt att kolla)
                    return True
                break

        if not found_image:
            return True # Inga bilder att optimera
    except Exception as e:
        logging.error(f"Kunde inte analysera bildegenskaper: {e}")
        return False

    return False

# ⎯⎯ Core Processing Function ⎯⎯

def validate_and_compress_pdf(pdf_path: str, skip_existing: bool, corrupt_dir: str, force: bool) -> tuple[int, bool, int]:
    # Skapa ett unikt namn för den temporära filen baserat på process-ID
    temp_optimized = f"temp_opt_{os.getpid()}_{os.path.basename(pdf_path)}"

    try:
        size_before = os.path.getsize(pdf_path)
        doc = pymupdf.open(pdf_path)

        # Smart Check: Hoppa över om den redan är optimerad
        if not force and is_already_optimized(doc):
            doc.close()
            return PDF_ALREADY_OPTIMIZED, False, 0

        # ⎯⎯ PYMUPDF OPTIMERING ⎯⎯
        # Konfigurera omskrivning av bilder (JPEG + Bicubic + 200 DPI)
        opts = pymupdf.mupdf.PdfImageRewriterOptions()

        # JPEG Metod (3) och Bicubic Subsampling (1)
        for opt_set in ['color_lossy', 'gray_lossy', 'color_lossless', 'gray_lossless']:
            setattr(opts, f"{opt_set}_image_recompress_method", 3)
            setattr(opts, f"{opt_set}_image_recompress_quality", "75")
            setattr(opts, f"{opt_set}_image_subsample_method", 1)
            setattr(opts, f"{opt_set}_image_subsample_threshold", 210)
            setattr(opts, f"{opt_set}_image_subsample_to", 200)

        opts.bitonal_image_recompress_method = 5
        opts.bitonal_image_subsample_method = 1
        opts.bitonal_image_subsample_threshold = 630
        opts.bitonal_image_subsample_to = 600

        # 1. Optimera bilderna i minnet
        doc.rewrite_images(options=opts)

        # 2. Definiera värden
        # Vi skapar en ren tidsstämpel först för att lättare formatera den åt båda håll
        raw_now = datetime.now()
        pdf_date_str = raw_now.strftime("D:%Y%m%d%H%M%S+01'00'") # Format för Info-Dict
        keywords = "OptimizedByPythonScript"
        creator = "Python Script"
        producer = "PyMuPDF"

        # 3. Uppdatera Info-Dictionary
        doc.set_metadata({
            "creationDate": pdf_date_str,
            "modDate": pdf_date_str,
            "keywords": keywords,
            "creator": creator,
            "producer": producer,
            "title": doc.metadata.get("title", ""),
            "subject": doc.metadata.get("subject", "")
        })

        # 4. Uppdatera XMP (Den nya PDF/A-standarden)
        # Vi skickar med pdf_date_str. Vår funktion rensar "D:" automatiskt nu.
        new_xmp = generate_pdfa_xmp(keywords, pdf_date_str, creator, producer)
        doc.set_xml_metadata(new_xmp)

        # 5. Spara direkt till den temporära filen på disk
        doc.save(
            temp_optimized,
            garbage=4,           # Maximal rensning av dubletter
            deflate=True,        # Komprimera alla strömmar
            deflate_images=True, # Komprimera alla bildströmmar
            deflate_fonts=True,  # Komprimera alla typsnittsfilströmmar
            use_objstms=1,       # Tillåtet i PDF/A-3
            clean=True,          # Sanera innehållsströmmar
            linear=False,        # Prioritera minsta storlek framför webb-streaming
            no_new_id=False,     # Skapar/uppdaterar fil-ID (viktigt för PDF/A)
            incremental=False,
            ascii=False,
            expand=0
        )
        doc.close()

        # 6. Kontrollera storlek innan överskrivning
        size_after = os.path.getsize(temp_optimized)
        bytes_saved = size_before - size_after

        if bytes_saved > 0:
            # Filen blev mindre - ersätt originalet
            shutil.move(temp_optimized, pdf_path)
            return PDF_SUCCESS, True, bytes_saved
        else:
            # Ingen vinst - behåll originalet och ta bort temp-filen
            if os.path.exists(temp_optimized):
                os.remove(temp_optimized)
            return PDF_SKIPPED, False, 0

    except Exception as e:
        # Vid fel: Flytta originalet till corrupt-mappen
        if 'doc' in locals():
            doc.close()

        filename = os.path.basename(pdf_path)
        dest_path = os.path.join(corrupt_dir, filename)

        # Hantera filnamnskonflikter i corrupt-mappen
        if os.path.exists(dest_path):
            dest_path = os.path.join(corrupt_dir, f"{datetime.now().strftime('%H%M%S')}_{filename}")

        try:
            shutil.move(pdf_path, dest_path)
            logging.error(f"ERROR: '{pdf_path}' flyttad. Fel: {e}")
        except: pass
        return PDF_FAIL, False, 0
    finally:
        # Sista städning av temp-filen om den finns kvar
        if os.path.exists(temp_optimized): os.remove(temp_optimized)

def process_directory_recursively(args: argparse.Namespace) -> dict:
    results = {
        'found': 0, 'success': 0, 'fail': 0, 'skipped': 0, 'already_opt': 0, 'saved': 0
    }

    corrupt_dir = os.path.join(args.source_dir, 'corrupt_pdfs')
    os.makedirs(corrupt_dir, exist_ok=True)

    all_files = []
    for root, dirs, files in os.walk(args.source_dir):
        if 'corrupt_pdfs' in dirs: dirs.remove('corrupt_pdfs')
        for f in files:
            if f.lower().endswith('.pdf') and f != 'pdf_optimization_log.log':
                all_files.append(os.path.join(root, f))

    results['found'] = len(all_files)

    for pdf_path in tqdm(all_files, desc="Bearbetar", unit="fil"):
        status, reduced, saved = validate_and_compress_pdf(pdf_path, args.skip_existing, corrupt_dir, args.force)

        if status == PDF_SUCCESS:
            results['success'] += 1
            results['saved'] += saved
        elif status == PDF_ALREADY_OPTIMIZED:
            results['already_opt'] += 1
        elif status == PDF_SKIPPED:
            results['skipped'] += 1
        else:
            results['fail'] += 1

    # Ta bort corrupt-mappen om den förblev tom
    if os.path.exists(corrupt_dir) and not os.listdir(corrupt_dir):
        os.rmdir(corrupt_dir)

    return results

def main():
    parser = argparse.ArgumentParser(description="Smart PDF-optimering med JPEG och PDF 1.5.")
    parser.add_argument('-s', '--skip-existing', action='store_true', help="Hoppa över baserat på loggens tidsstämpel.")
    parser.add_argument('-f', '--force', action='store_true', help="Tvinga optimering även om filen ser klar ut.")
    parser.add_argument('-i', '--source-dir', type=str, default=SOURCE_DIR, help="Mapp att bearbeta.")
    args = parser.parse_args()

    start_time = datetime.now()
    setup_logging(args.source_dir)

    print(f"Startar smart optimering i: {args.source_dir}\n")
    res = process_directory_recursively(args)

    summary = f"""
⎯⎯ SLUTRAPPORT ⎯⎯
Tid: {datetime.now() - start_time}
Sparat: {format_size(res['saved']):.2f} MB

Filer:
  - Hittade: {res['found']}
  - Optimerade nu: {res['success']}
  - Redan optimerade: {res['already_opt']}
  - Fel/Flyttade: {res['fail']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    print(summary)
    logging.info(summary)

if __name__ == "__main__":
    main()
