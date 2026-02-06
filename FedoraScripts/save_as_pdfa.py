#!/usr/bin/python
import subprocess
import sys

def convert_to_pdfa(input_file, output_file):
    # Kommando för att tvinga konvertering till PDF/A-2b
    gs_command = [
        "gswin64c", "-dPDFA", "-dBATCH", "-dNOPAUSE",
        "-sColorConversionStrategy=UseDeviceIndependentColor",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1",
        f"-sOutputFile={output_file}",
        input_file
    ]

    try:
        subprocess.run(gs_command, check=True)
        print(f"Konvertering klar: {output_file}")
    except Exception as e:
        print(f"Fel vid konvertering: {e}")

# Användning
if __name__ == "__main__":
    if len(sys.argv) > 2:
        convert_to_pdfa(sys.argv[1], sys.argv[2])
    else:
        print("Användning: python skript.py indata_fil utdata_fil")

