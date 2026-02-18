#!/usr/bin/env python3
import os
import shutil
import logging
import argparse
import re
import subprocess
import socket
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from tqdm import tqdm

# ⎯⎯ IMPORT LIBRARIES ⎯⎯
try:
    import pymupdf
    try:
        from docx2pdf import convert as docx2pdf_convert
    except ImportError:
        docx2pdf_convert = None
except ImportError as e:
    print("Error: Required library not found. Please run 'pip install pymupdf'")
    print(f"Details: {e}")
    exit(1)

# ⎯⎯ Status Constants ⎯⎯
CONVERSION_FAIL = 0
CONVERSION_SUCCESS = 1
CONVERSION_SKIPPED = 2

# ⎯⎯ Helper Functions ⎯⎯

def is_unoserver_running(host='127.0.0.1', port=2003):
    """Kollar om unoserver lyssnar på standardporten."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def format_size(bytes_size):
    return bytes_size / (1024 * 1024)

def setup_logging(dest_dir: str):
    log_path = os.path.join(dest_dir, 'conversion_log.log')
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return log_path

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

# ⎯⎯ Conversion Engine Logic ⎯⎯

def convert_docx_to_pdf(source_path: str, dest_path: str, skip_existing: bool, use_unoserver: bool) -> int:
    if skip_existing and os.path.exists(dest_path):
        return CONVERSION_SKIPPED

    abs_source = os.path.abspath(source_path)
    abs_dest = os.path.abspath(dest_path)
    success = False

    # 1. Försök med unoserver + PDF/A-flagga (för att klara valideringen)
    if use_unoserver and shutil.which('unoconvert'):
        try:
            # Vi tvingar fram PDF/A-1 genom LibreOffice-filter
            subprocess.run([
                'unoconvert',
                '--convert-to', 'pdf',
                '--filter-option', 'SelectPdfVersion=3',
                abs_source, abs_dest
            ], check=True, capture_output=True)
            logging.info(f"SUCCESS (unoserver PDF/A): '{source_path}'")
            success = True
        except Exception as e:
            logging.error(f"unoserver failed: {e}")

    # 2. Fallback: LibreOffice Headless
    if not success and shutil.which('libreoffice'):
        try:
            dest_dir = os.path.dirname(dest_path)
            subprocess.run([
                'libreoffice', '--headless', '--convert-to', 'pdf:writer_pdf_Export',
                '--outdir', dest_dir, source_path
            ], check=True, capture_output=True)
            logging.info(f"SUCCESS (LibreOffice Headless): '{source_path}'")
            success = True
        except Exception: pass

    # 3. Försök med docx2pdf (Windows/macow med MS Word)
    if not success and docx2pdf_convert:
        try:
            docx2pdf_convert(source_path, dest_path)
            logging.info(f"SUCCESS (docx2pdf): '{source_path}'")
            success = True
        except Exception as e:
            logging.error(f"docx2pdf failed: {e}")

    if success:
        return CONVERSION_SUCCESS
    else:
        logging.error(f"ALL ENGINES FAILED for: '{source_path}'")
        return CONVERSION_FAIL

# ⎯⎯ PDF Optimization ⎯⎯

def optimize_pdf_with_images(pdf_path: str) -> int:
    temp_optimized = f"temp_opt_{os.getpid()}_{os.path.basename(pdf_path)}"
    try:
        size_before = os.path.getsize(pdf_path)
        doc = pymupdf.open(pdf_path)
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

        # 6. Kontrollera storlek innan överskrivning
        size_after = os.path.getsize(temp_optimized)
        shutil.move(temp_optimized, pdf_path)
        #if size_before > size_after:
        #    return size_before - size_after
        return size_before - size_after
    except Exception as e:
        logging.error(f"OPTIMIZATION_ERROR på {pdf_path}: {e}")
        return 0
    finally:
        if os.path.exists(temp_optimized): os.remove(temp_optimized)

# ⎯⎯ VeraPDF Logic (Optimized for your Terminal Output) ⎯⎯

def run_verapdf_batch(directory: str) -> dict:
    """Kör veraPDF CLI via Flatpak med absoluta sökvägar."""
    results = {}
    # Vi gör mappsökvägen absolut för att Flatpak ska hitta den
    abs_dir = os.path.abspath(directory)
    if os.name == 'nt':
        home = os.path.expanduser("~")
        cmd_base = [os.path.join(home, "Program", "verapdf", "verapdf.bat")]
        shell_mode = True
    else:
        cmd_base = ["flatpak", "run", "--command=verapdf", "org.verapdf.veraPDF"]
        shell_mode = False

    try:
        # Vi använder -r för rekursiv sökning i mappen och --format xml för att kunna parsa svaret
        cmd = cmd_base + ["--format", "xml", "-r", abs_dir]

        # Kör kommandot och fånga resultatet
        process = subprocess.run(cmd, capture_output=True, text=True, shell=shell_mode)
        if process.returncode not in [0, 1]:
            logging.error(f"veraPDF kraschade med kod {process.returncode}")
            # Logga stderr men ignorera Java-meddelanden om tmpdir
            clean_stderr = "\n".join([line for line in process.stderr.split('\n') if "JAVA_TOOL_OPTIONS" not in line])
            if clean_stderr: logging.error(f"VeraPDF Error: {clean_stderr}")
            return results

        if not process.stdout.strip():
            logging.warning("veraPDF returnerade ingen data.")
            return results

        # Parsa XML-resultatet
        root = ET.fromstring(process.stdout)
        for item in root.findall('.//{*}job'):
            name_node = item.find('.//{*}name')
            compliant_node = item.find('.//{*}validationReport')
            if name_node is not None and compliant_node is not None:
                # Vi använder basename för att matcha filnamnet oavsett hur sökvägen ser ut i XML:en
                full_path = name_node.text.strip()
                is_compliant = compliant_node.get('isCompliant', 'false').lower() == 'true'
                results[full_path] = is_compliant
    except Exception as e:
        logging.error(f"Kritiskt fel i valideringssteget: {e}")
    return results

def main():
    parser = argparse.ArgumentParser(description="Multi-engine DOCX/ODT till PDF konverterare.")
    parser.add_argument('-i', '--source-dir', type=str, default='.', help="Ingångsmapp.")
    parser.add_argument('-o', '--destination-dir', type=str, default='.', help="Utgångsmapp.")
    parser.add_argument('-s', '--skip-existing', action='store_true', help="Hoppa över befintliga PDF:er.")
    args = parser.parse_args()

    start_time = datetime.now()
    # Kontrollera unoserver innan start
    unoserver_active = is_unoserver_running()
    if not unoserver_active:
        print("💡 Tips: Starta 'unoserver' i en annan terminal för snabbare konvertering.")
    else:
        print("🚀 unoserver hittades och kommer att användas.")

    os.makedirs(args.destination_dir, exist_ok=True)
    log_file = setup_logging(args.destination_dir)

    all_files = []
    for root, _, files in os.walk(args.source_dir):
        for f in files:
            if f.lower().endswith(('.docx', '.odt')):
                all_files.append((root, f))

    if not all_files:
        print("Inga dokument hittades.")
        return

    stats = {
        'found': len(all_files), 'conv_ok': 0, 'conv_fail': 0,
        'skipped': 0, 'saved_bytes': 0, 'pdfa_ok': 0, 'pdfa_fail': 0
    }

    print(f"Bearbetar {len(all_files)} filer… (Logg: {log_file})")

    # Steg 1: Konvertera och Optimera
    for root, filename in tqdm(all_files, desc="Bearbetar", unit="fil"):
        rel_path = os.path.relpath(root, args.source_dir)
        dest_dir = os.path.normpath(os.path.join(args.destination_dir, rel_path))
        os.makedirs(dest_dir, exist_ok=True)

        src_path = os.path.join(root, filename)
        dest_path = os.path.join(dest_dir, os.path.splitext(filename)[0] + '.pdf')

        status = convert_docx_to_pdf(src_path, dest_path, args.skip_existing, unoserver_active)

        if status == CONVERSION_SKIPPED:
            stats['skipped'] += 1
        elif status == CONVERSION_SUCCESS:
            stats['conv_ok'] += 1
            saved = optimize_pdf_with_images(dest_path)
            stats['saved_bytes'] += saved
        else:
            stats['conv_fail'] += 1

    # Steg 2: Batch-validering med veraPDF
    print("Startar PDF/A-validering (Batch)…")
    compliance_report = run_verapdf_batch(args.destination_dir)

    # Vi mappar om för att kontrollera mot de absoluta sökvägarna
    for root, filename in all_files:
        rel_path = os.path.relpath(root, args.source_dir)
        dest_path = os.path.join(args.destination_dir, rel_path, os.path.splitext(filename)[0] + '.pdf')
        abs_pdf_path = os.path.abspath(dest_path)

        if abs_pdf_path in compliance_report:
            if compliance_report[abs_pdf_path]: 
                stats['pdfa_ok'] += 1
            else:
                stats['pdfa_fail'] += 1
                logging.warning(f"COMPLIANCE FAIL: {abs_pdf_path}")

    # Rapport
    duration = datetime.now() - start_time
    summary = f"""
⎯⎯ BEARBETNINGSRAPPORT ⎯⎯
Tid: {duration}
Sparat utrymme: {format_size(stats['saved_bytes']):.2f} MB

Filer:
  - Hittade: {stats['found']}
  - Konverterade: {stats['conv_ok']}
  - Hoppade över: {stats['skipped']}
  - PDF/A Godkända: {stats['pdfa_ok']}
  - PDF/A Underkända: {stats['pdfa_fail']}
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
"""
    print(summary)
    logging.info(summary)

if __name__ == "__main__":
    main()
