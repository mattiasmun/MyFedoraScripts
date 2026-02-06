#!/usr/bin/python
import subprocess
import sys

def convert_to_pdfa3(input_file, output_file):
    # Kommando för att tvinga konvertering till PDF/A-3b
    gs_command = [
        "gswin64c", "-dPDFA=3", "-dBATCH", "-dNOPAUSE",
        "-sColorConversionStrategy=UseDeviceIndependentColor",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        f"-sOutputFile={output_file}",
        "PDFA_def.ps",
        input_file
    ]

    try:
        subprocess.run(gs_command, check=True)
        print(f"Konvertering till PDF/A-3b klar: {output_file}")
    except Exception as e:
        print(f"Fel vid konvertering: {e}")

# Användning
if __name__ == "__main__":
    if len(sys.argv) > 2:
        convert_to_pdfa3(sys.argv[1], sys.argv[2])
    else:
        print("Användning: python save_as_pdfa.py indata.pdf utdata.pdf")
