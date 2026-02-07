#!/usr/bin/env python3
import subprocess
import os
import sys

def create_pdfa_def(attachment_paths=None, part=3, conformance="B"):
    """Skapar en temporär PDFA_def.ps fil med stöd för flera bilagor."""
    ps_content = f"""%!
[/Value ({part}) /T (part) /DIR {{systemdict /pdfmark get}} cvx /DOCINFO pdfmark
[/Value ({conformance}) /T (conformance) /DIR {{systemdict /pdfmark get}} cvx /DOCINFO pdfmark
[/ICCProfile (srgb.icc) /DestOutputProfile {{systemdict /pdfmark get}} cvx /DESTINATION pdfmark
"""

    if attachment_paths:
        ps_content += "\n% --- Inbäddning av bilagor ---\n"
        for i, path in enumerate(attachment_paths):
            file_name = os.path.basename(path)
            # Vi använder absoluta sökvägar i PS-filen för att undvika problem
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
    # --- NYHET: Validering av filer innan körning ---
    if attachments:
        missing_files = [f for f in attachments if not os.path.exists(f)]
        if missing_files:
            print(f"FEL: Följande bilagor saknas: {', '.join(missing_files)}")
            return

    if not os.path.exists("srgb.icc"):
        print("VARNING: srgb.icc saknas i mappen. Validering kan misslyckas.")

    # 1. Skapa definitionsfilen
    create_pdfa_def(attachments)

    # 2. Ghostscript-kommando
    gs_command = [
        "gswin64c", "-dPDFA=3", "-dBATCH", "-dNOPAUSE",
        "-sColorConversionStrategy=UseDeviceIndependentColor",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        f"-sOutputFile={output_pdf}",
        "temp_pdfa_def.ps",
        input_pdf
    ]

    try:
        print("Konverterar…")
        subprocess.run(gs_command, check=True)
        status = f"med {len(attachments)} bilagor" if attachments else "utan bilagor"
        print(f"Klart! '{output_pdf}' är nu en PDF/A-3b {status}.")
    except Exception as e:
        print(f"Ett fel uppstod: {e}")
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
        print("\nAnvändning:")
        print("  python save_as_pdfa.py indata.pdf utdata.pdf [bilaga1 bilaga2 …]\n")

if __name__ == "__main__":
    main()
