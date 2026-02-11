#!/usr/bin/env python3
import subprocess
import os
import sys

# Sökvägar till ICC-profiler
ICC_RGB = "/usr/share/ghostscript/iccprofiles/srgb.icc"
ICC_GRAY = "/usr/share/ghostscript/iccprofiles/sgray.icc"

def create_pdfa_def(attachment_paths=None, part=3, conformance="B"):
    """Skapar PDFA_def.ps med extra tydlig metadata för att tillfredsställa VeraPDF."""
    icc_rgb_abs = os.path.abspath(ICC_RGB).replace("\\", "/")
    icc_gray_abs = os.path.abspath(ICC_GRAY).replace("\\", "/")

    ps_content = f"""%!
% 1. Metadata
[ /Part {part} /Conformance ({conformance}) /DOCINFO pdfmark

% 2. Define ICC Profile Object
[/_objdef {{icc_obj}} /type /stream /OBJ pdfmark
[{{icc_obj}} ({icc_rgb_abs}) (r) file /PUT pdfmark
[{{icc_obj}} << /N 3 /Alternate /DeviceRGB >> /PUT pdfmark

% 3. Set OutputIntent (Crucial for RGB Validation)
[ /ICCProfile {{icc_obj}}
  /Subtype /GTS_PDFA1
  /OutputConditionIdentifier (sRGB)
  /RegistryName (http://www.color.org)
  /Info (sRGB IEC61966-2.1)
  /DESTINATION pdfmark

% 4. Force Default Color Spaces to use the ICC profiles
/CurrentStd {{{{ /DefaultRGB /ICCBased {{icc_obj}} /SETPS pdfmark }}}} def
CurrentStd
"""
    if attachment_paths:
        ps_content += "\n% --- Inbäddning av bilagor ---\n"
        for i, path in enumerate(attachment_paths):
            file_name = os.path.basename(path)
            abs_path = os.path.abspath(path).replace("\\", "/")
            obj_name = f"EmbedObj{i}"
            ps_content += f"""
[/_objdef {{{obj_name}}} /type /stream /OBJ pdfmark
[{{{obj_name}}} << /Type /EmbeddedFile /Subtype (application/octet-stream) >> /PUT pdfmark
[{{{obj_name}}} ({abs_path}) (r) file /PUT pdfmark
[{{{obj_name}}} /CLOSE pdfmark
[/Name ({file_name}) /FS << /Type /F /F ({file_name}) /EF << /F {{{obj_name}}} >> >> /EMBED pdfmark
"""

    with open("temp_pdfa_def.ps", "w", encoding="utf-8") as f:
        f.write(ps_content)

def convert_to_pdfa3(input_pdf, output_pdf, attachments=None):
    if not os.path.exists(input_pdf) or not os.path.exists(ICC_RGB):
        print("FEL: Indata eller ICC-profil saknas.")
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
        "gs",
        "-dPDFA=3",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        "-sColorConversionStrategy=UseDeviceIndependentColor",
        "-dProcessColorModel=/DeviceRGB",
        "-dOverrideICC=true",
        "-dRenderIntent=1",             # Relative Colorimetric (viktigt för PDF/A)
        "-dEmbedAllFonts=true",         # Tvingar in Nimbus/Helvetica
        "-dSubsetFonts=true",           # Minskar filstorlek men behåller inbäddning
        "-dPDFSETTINGS=/prepress",      # Högsta kvalitet, tvingar inbäddning
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

def main():
    if len(sys.argv) >= 3:
        input_f = sys.argv[1]
        output_f = sys.argv[2]
        attach_f = sys.argv[3:] if len(sys.argv) > 3 else None
        convert_to_pdfa3(input_f, output_f, attach_f)
    else:
        print("\nAnvändning: python save_as_pdfa.py <indata.pdf> <utdata.pdf> [bilaga1 bilaga2 …]")

if __name__ == "__main__":
    main()
