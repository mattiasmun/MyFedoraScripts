#!/usr/bin/env python3
import ocrmypdf
import os
import glob
import argparse
import re
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from ocrmypdf.api import configure_logging, Verbosity
from tqdm import tqdm

# ⎯⎯ IMPORT PYMUPDF ⎯⎯
try:
    import pymupdf  # Kraftfull motor för PDF-hantering
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pymupdf'")
    print(f"Details: {e}")
    exit(1)

def get_pdfa_info_pymupdf(doc):
    xml_metadata = doc.get_xml_metadata()

    # Vi använder regex för att hitta värdena i XML-strängen
    part_match = re.search(r'<pdfaid:part>(\d+)</pdfaid:part>', xml_metadata)
    conf_match = re.search(r'<pdfaid:conformance>(\w+)</pdfaid:conformance>', xml_metadata)

    # Standardvärden om de inte hittas (t.ex. om filen inte är PDF/A från början)
    pdfa_part = part_match.group(1) if part_match else "3"
    pdfa_conf = conf_match.group(1) if conf_match else "B"

    return pdfa_part, pdfa_conf

def generate_pdfa_xmp(keywords, pdf_date, creator, producer, pdfa_part, pdfa_conf, title="null", subject="null"):
    # Rensa datum
    clean_date = pdf_date.replace("D:", "").replace("'", "")

    # ISO-format: YYYY-MM-DDTHH:MM:SS+01:00
    iso_date = (f"{clean_date[0:4]}-{clean_date[4:6]}-{clean_date[6:8]}T"
                f"{clean_date[8:10]}:{clean_date[10:12]}:{clean_date[12:14]}+01:00")

    doc_id = f"uuid:{uuid.uuid4()}"

    # Om title eller subject saknas, sätt till "null" sträng för att matcha din mall
    display_title = title if title else "null"
    display_subject = subject if subject else "null"

    # Skapa själva XMP-innehållet
    xmp_content = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.1.0-jc003">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"
        xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/"
        xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"
        xmlns:dc="http://purl.org/dc/elements/1.1/">
      <pdfaid:part>{pdfa_part}</pdfaid:part>
      <pdfaid:conformance>{pdfa_conf}</pdfaid:conformance>
      <pdf:Producer>{producer}</pdf:Producer>
      <pdf:Keywords>{keywords}</pdf:Keywords>
      <xmp:ModifyDate>{iso_date}</xmp:ModifyDate>
      <xmp:CreateDate>{iso_date}</xmp:CreateDate>
      <xmp:MetadataDate>{iso_date}</xmp:MetadataDate>
      <xmp:CreatorTool>{creator}</xmp:CreatorTool>
      <xmpMM:DocumentID>{doc_id}</xmpMM:DocumentID>
      <xmpMM:InstanceID>{doc_id}</xmpMM:InstanceID>
      <xmpMM:RenditionClass>default</xmpMM:RenditionClass>
      <xmpMM:VersionID>1</xmpMM:VersionID>
      <dc:format>application/pdf</dc:format>
      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">{display_title}</rdf:li>
        </rdf:Alt>
      </dc:title>
      <dc:description>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">{display_subject}</rdf:li>
        </rdf:Alt>
      </dc:description>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>"""

    # Lägg till padding (ca 2048 tecken) för snabbare filredigering
    padding = " " * 2048
    return f"{xmp_content}\n{padding}\n<?xpacket end=\"w\"?>"

def process_file(pdf_path, output_path):
    """
    1. Optimerar bilder till 200 DPI via PyMuPDF (JPEG + Bicubic).
    2. Kör OCRmyPDF för textigenkänning och PDF/A-3 arkivering.
    """
    temp_optimized = f"temp_opt_{os.getpid()}_{os.path.basename(pdf_path)}"

    try:
        doc = pymupdf.open(pdf_path)

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
        curr_title = doc.metadata.get("title", "null")
        curr_subject = doc.metadata.get("subject", "null")

        # 3. Uppdatera Info-Dictionary
        doc.set_metadata({
            "creationDate": pdf_date_str,
            "modDate": pdf_date_str,
            "keywords": keywords,
            "creator": creator,
            "producer": producer,
            "title": curr_title,
            "subject": curr_subject
        })

        # 4. Uppdatera XMP (Den nya PDF/A-standarden)
        # Vi skickar med pdf_date_str. Vår funktion rensar "D:" automatiskt nu.
        pdfa_part, pdfa_conf = get_pdfa_info_pymupdf(doc)
        new_xmp = generate_pdfa_xmp(
            keywords,
            pdf_date_str,
            creator,
            producer,
            pdfa_part,
            pdfa_conf,
            title=curr_title,
            subject=curr_subject
        )
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

        # ⎯⎯ STEG 2: OCRMYPDF (OCR & ARKIVERING) ⎯⎯
        # Eftersom vi redan har optimerat bilderna kan vi sänka kraven i ocrmypdf
        ocrmypdf.ocr(
            temp_optimized,
            output_path,
            optimize=1,            # Låg nivå eftersom vi redan optimerat med PyMuPDF
            clean=False,
            output_type='pdfa-3',
            skip_text=True,
            language=['swe', 'eng'],
            progress_bar=False
        )

        return True
    except Exception as e:
        tqdm.write(f"!!! Ett fel uppstod vid bearbetning av {os.path.basename(input_path)}: {e}")
        return False
    finally:
        # Sista städning av temp-filen om den finns kvar
        if os.path.exists(temp_optimized):
            os.remove(temp_optimized)

def main():
    parser = argparse.ArgumentParser(
        description="Batch-optimerar PDF: PyMuPDF (200 DPI J2K) + OCRmyPDF (PDF/A-3)."
    )
    parser.add_argument('input_dir', type=str, help="Indatamapp")
    parser.add_argument('-o', '--output_dir', type=str, default=None, help="Utdatamapp")
    parser.add_argument('-r', '--recursive', action='store_true', help="Sök rekursivt")

    args = parser.parse_args()

    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir if args.output_dir else INPUT_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Hitta alla PDF-filer
    search_path = os.path.join(INPUT_DIR, '**', '*.pdf') if args.recursive else os.path.join(INPUT_DIR, '*.pdf')
    pdf_files = glob.glob(search_path, recursive=args.recursive)

    try:
        configure_logging(verbosity=Verbosity.default, progress_bar_friendly=True, manage_root_logger=False)
    except:
        pass

    if not pdf_files:
        print(f"\nInga PDF-filer hittades i: {INPUT_DIR}")
        return

    # ⎯⎯ STARTA LOGGNING OCH TID ⎯⎯
    start_time_raw = time.time()
    start_dt = datetime.fromtimestamp(start_time_raw)

    total_size_before = 0
    total_size_after = 0
    success_count = 0

    print(f"\nSTARTAR BATCH-PROCESS (Motor: PyMuPDF + OCRmyPDF)")
    print(f"Inställning: J2K @ 200 DPI -> PDF/A-3")
    print(f"Starttid: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hittade {len(pdf_files)} filer…")
    print("⎯" * 25)

    pbar = tqdm(pdf_files, desc="Bearbetar", unit=" fil")

    for input_path in pbar:
        # Undvik att processa temp-filer om de råkar ligga i samma mapp
        if os.path.basename(input_path).startswith("temp_opt_"):
            continue

        pbar.set_postfix_str(os.path.basename(input_path))
        size_before = os.path.getsize(input_path)
        total_size_before += size_before

        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        if process_file(input_path, output_path):
            if os.path.exists(output_path):
                total_size_after += os.path.getsize(output_path)
                success_count += 1
        else:
            total_size_after += size_before

    # ⎯⎯ AVSLUTA OCH BERÄKNA ⎯⎯
    end_time_raw = time.time()
    diff = datetime.fromtimestamp(end_time_raw) - start_dt

    saved_mb = (total_size_before - total_size_after) / (1024 * 1024)
    reduction = ((total_size_before - total_size_after) / total_size_before * 100) if total_size_before > 0 else 0

    print("⎯" * 25)
    print(f"KLAR. Total tid: {str(diff).split('.')[0]}")
    print(f"Status: {success_count}/{len(pdf_files)} lyckade")
    print(f"Sparat: {saved_mb:.2f} MB ({reduction:.1f}%)")
    print("⎯" * 25)

if __name__ == "__main__":
    main()
