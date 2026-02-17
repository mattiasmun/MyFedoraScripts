#!/usr/bin/env python3
import subprocess
import os
import shutil
import sys
import platform

def get_icc_path():
    """Returnerar rätt sökvägar till ICC-profiler baserat på operativsystem."""
    if platform.system() == "Windows":
        home = os.path.expanduser("~")
        # För MSYS2 UCRT64 på Windows.
        # Vi försöker hitta msys64-roten dynamiskt eller antar standard C:/msys64
        backup_msys_root = os.path.join(home, "msys64", "ucrt64")
        msys_root = os.environ.get("MSYSTEM_PREFIX", backup_msys_root)
        # Om vi kör inifrån MSYS2-shell (bash) fungerar /ucrt64/… direkt,
        # men för nativ Python är det säkrast med fullständiga Windows-sökvägar.
        base_path = os.path.join(msys_root, "share", "texmf-dist", "tex", "generic", "colorprofiles")

        # Om miljövariabeln inte pekar rätt, kan vi hårdkoda din önskade sträng:
        #base_path = "C:/Users/ai21558/msys64/ucrt64/share/texmf-dist/tex/generic/colorprofiles"

        return os.path.join(base_path, "sRGB.icc")
    else:
        # Standard Linux-sökvägar
        return "/usr/share/ghostscript/iccprofiles/srgb.icc"

# Initiera sökvägarna
ICC_RGB = get_icc_path()

def check_icc_exists():
    """Validerar att profilerna finns på disk."""
    missing = []
    if not os.path.exists(ICC_RGB): missing.append(ICC_RGB)

    if missing:
        print("\n--- FEL: ICC-PROFILER SAKNAS ---")
        for p in missing:
            print(f"Hittade inte: {p}")
        print("\nKontrollera att Ghostscript är installerat i MSYS2 (pacman -S mingw-w64-ucrt-x86_64-ghostscript)")
        print(f"Sökväg som letades efter: {os.path.dirname(ICC_RGB)}")
        return False
    return True

def create_pdfa_def(attachment_paths=None, part=3, conformance="B"):
    """
    Skapar PDFA_def.ps med stöd för PDF/A-3 genom att inkludera /AF (Associated Files)
    och korrekt namnträd för bilagor.
    """
    icc_rgb_abs = os.path.abspath(ICC_RGB).replace("\\", "/")

    ps_content = f"""%!
% 1. Metadata och PDF/A-standard
[ /Part {part} /Conformance ({conformance}) /DOCINFO pdfmark

% 2. Definiera ICC-profil objekt
[/_objdef {{icc_obj}} /type /stream /OBJ pdfmark
[{{icc_obj}} ({icc_rgb_abs}) (r) file /PUT pdfmark
[{{icc_obj}} << /N 3 /Alternate /DeviceRGB >> /PUT pdfmark

% 3. OutputIntent (Krävs för RGB-validering)
[ /ICCProfile {{icc_obj}}
  /Subtype /GTS_PDFA1
  /OutputConditionIdentifier (sRGB)
  /RegistryName (http://www.color.org)
  /Info (sRGB IEC61966-2.1)
  /DESTINATION pdfmark

% 4. Tvinga färgrum
/CurrentStd {{{{ /DefaultRGB /ICCBased {{icc_obj}} /SETPS pdfmark }}}} def
CurrentStd
"""
    if attachment_paths:
        ps_content += "\n% --- Avancerad PDF/A-3 Inbäddning ---\n"
        file_spec_objs = []

        for i, path in enumerate(attachment_paths):
            file_name = os.path.basename(path)
            abs_path = os.path.abspath(path).replace("\\", "/")
            stream_obj = f"EmbedStream{i}"
            spec_obj = f"FileSpec{i}"
            file_spec_objs.append(spec_obj)

            ps_content += f"""
% Skapa filströmmen
[/_objdef {{{stream_obj}}} /type /stream /OBJ pdfmark
[{{{stream_obj}}} << /Type /EmbeddedFile /Subtype (application/octet-stream) >> /PUT pdfmark
[{{{stream_obj}}} ({abs_path}) (r) file /PUT pdfmark

% Skapa FileSpec-objektet (Kopplar strömmen till ett filnamn och PDF/A-relation)
[/_objdef {{{spec_obj}}} /type /dict /OBJ pdfmark
[{{{spec_obj}}} <<
  /Type /F
  /F ({file_name})
  /UF ({file_name})
  /EF << /F {{{stream_obj}}} >>
  /AFRelationship /Unspecified
>> /PUT pdfmark
"""

        # Koppla alla FileSpecs till dokumentets /AF-array (Associated Files)
        af_array = " ".join([f"{{{obj}}}" for obj in file_spec_objs])
        ps_content += f"\n[ {{Catalog}} << /AF [{af_array}] >> /PUT pdfmark\n"

        # Skapa namnträdet så att bilagorna syns i PDF-läsare
        names_list = ""
        for i, path in enumerate(attachment_paths):
            file_name = os.path.basename(path)
            names_list += f"({file_name}) {{FileSpec{i}}} "

        ps_content += f"""
[ /_objdef {{names_dict}} /type /dict /OBJ pdfmark
[{{names_dict}} << /Names [{names_list}] >> /PUT pdfmark
[ {{Catalog}} << /Names << /EmbeddedFiles {{names_dict}} >> >> /PUT pdfmark
"""

    with open("temp_pdfa_def.ps", "w", encoding="utf-8") as f:
        f.write(ps_content)

def convert_to_pdfa3(input_pdf, output_pdf, attachments=None):
    global gs_exec
    if not os.path.exists(input_pdf) or not os.path.exists(ICC_RGB):
        print(f"FEL: Indatafilen '{input_pdf}' saknas.")
        return

    if not check_icc_exists():
        return

    if attachments:
        missing_files = [f for f in attachments if not os.path.exists(f)]
        if missing_files:
            print(f"FEL: Följande bilagor saknas: {', '.join(missing_files)}")
            return

    # Skapa definitionsfilen
    create_pdfa_def(attachments)

    # Ghostscript-kommando optimerat för PDF/A-3b validering
    gs_command = [
        gs_exec,
        "-dPDFSETTINGS=/ebook",
        "-dPDFA=3",
        "-dCompressMode=2",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sCompression=zip",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        "-dAutoRotatePages=/PageByPage",
        "-dConvertCMYKImagesToRGB=true",
        "-dColorImageDownsampleThreshold=1.1",
        "-dColorImageDownsampleType=/Bicubic",
        "-dColorImageResolution=200",
        "-sColorConversionStrategy=RGB",
        "-dCompatibilityLevel=1.7",
        "-dGrayImageDownsampleThreshold=1.1",
        "-dGrayImageResolution=200",
        "-dMonoImageDownsampleThreshold=1.1",
        "-dMonoImageResolution=600",
        "-dParseMetadata=true",
        "-dProcessColorModel=/DeviceRGB",
        "-dOverrideICC=true",
        "-dRenderIntent=1",             # Relative Colorimetric (viktigt för PDF/A)
        "-dEmbedAllFonts=true",         # Tvingar in Nimbus/Helvetica
        "-dSubsetFonts=true",           # Minskar filstorlek men behåller inbäddning
        f"-sOutputFile={output_pdf}",
        "-f", "temp_pdfa_def.ps",
        "-f", input_pdf
    ]

    try:
        print(f"Konverterar '{input_pdf}'…")
        result = subprocess.run(gs_command, capture_output=True, text=True)

        if result.stdout:
            print("--- Ghostscript Logg ---")
            print(result.stdout)

        if result.stderr:
            print("--- Ghostscript Debug/Fel ---")
            print(result.stderr)

        if result.returncode == 0:
            print(f"Klart! '{output_pdf}' har skapats.")
            if attachments:
                print(f"Bäddade in {len(attachments)} bilagor.")
        else:
            print("Ett fel uppstod vid konverteringen.")

    except Exception as e:
        print(f"Ett oväntat fel uppstod: {e}")
    finally:
        if os.path.exists("temp_pdfa_def.ps"):
            os.remove("temp_pdfa_def.ps")

def check_dependencies():
    """Kontrollerar om Ghostscript är installerat och tillgängligt."""
    global gs_exec
    gs_exec = "gs"
    if platform.system() == "Windows":
        # På Windows kan exe-filen ibland heta gswin64c eller gswin32c 
        # beroende på installation, men i MSYS2 är det oftast bara 'gs'
        if not shutil.which(gs_exec):
            gs_exec = "gswin64c"
    
    path = shutil.which(gs_exec)
    if not path:
        print("\n--- FEL: GHOSTSCRIPT SAKNAS ---")
        print("Kunde inte hitta 'gs' i systemets PATH.")
        if platform.system() == "Windows":
            print("Installera via MSYS2: pacman -S mingw-w64-ucrt-x86_64-ghostscript")
        else:
            print("Installera via din pakethanterare (t.ex. sudo apt install ghostscript)")
        return None
    return gs_exec

def main():
    # 1. Kontrollera om Ghostscript finns
    gs_cmd = check_dependencies()
    if not gs_cmd:
        sys.exit(1)

    # 2. Kontrollera argument
    if len(sys.argv) >= 3:
        input_f = sys.argv[1]
        output_f = sys.argv[2]
        attach_f = sys.argv[3:] if len(sys.argv) > 3 else None
        convert_to_pdfa3(input_f, output_f, attach_f)
    else:
        print("\nAnvändning: python save_as_pdfa.py <indata.pdf> <utdata.pdf> [bilaga1 bilaga2 …]")

if __name__ == "__main__":
    main()
