#!/usr/bin/python
import ocrmypdf
import os
import glob
import argparse
from ocrmypdf.api import configure_logging, Verbosity
from tqdm import tqdm

# --------------------------------------------------------------------------
# LÖSNING FÖR JBIG2 Snapd-problem:
# Använd den exakta sökvägen hittad via 'which jbig2enc'
JBIG2_PATH = '/var/lib/snapd/snap/bin/jbig2enc'
# Kontrollera om JBIG2-binären finns innan du använder den
if not os.path.exists(JBIG2_PATH):
    # Du kan lägga till en automatisk sökning här eller bara en varning
    tqdm.write(f"VARNING: JBIG2-programmet hittades INTE på den angivna sökvägen: {JBIG2_PATH}")
    # Ändra JBIG2_PATH till None eller standardvärde om det inte hittas
    # Detta kräver en lite mer avancerad hantering inuti process_file
# --------------------------------------------------------------------------

def process_file(input_path, output_path):
    """
    Kör ocrmypdf med de specificerade optimeringsparametrarna.
    """
    # Vi skriver inte ut "-> Bearbetar" här, det sköter progressbaren

    try:
        # ocrmypdf har en egen progressbar. Vi stänger av den här
        # för att undvika konflikter med tqdm's progressbar.
        ocrmypdf.ocr(
            input_path,
            output_path,

            # --- Optimering och Komprimering ---
            optimize=2,
            jpg_quality=85,
            jbig2_lossy=True,

            # --- Ytterligare Optimering och Rengöring ---
            clean=True,
            remove_vectors=True,
            fast_web_view=0.03,
            output_type='pdfa-3',

            # --- OCR-Kontroll ---
            redo_ocr=True,

            # --- Metadata och Språk ---
            title='Optimerad för Arkiv/Webb',
            author='Batch OCR Script',
            language=['swe', 'eng'],

            progress_bar=False
        )
        # print(f"<- Klar: Sparad i {os.path.basename(output_path)}") # Vi använder loggning istället

    except ocrmypdf.exceptions.EncryptedPdfError:
        # Använd tqdm.write för att skriva ut meddelanden utan att störa baren
        tqdm.write(f"!!! Fel: Filen {os.path.basename(input_path)} är lösenordsskyddad.")
    except Exception as e:
        tqdm.write(f"!!! Ett oväntat fel uppstod vid bearbetning av {os.path.basename(input_path)}: {e}")


# --- HUVUDPROGRAM ---

def main():
    parser = argparse.ArgumentParser(
        description="Batch-optimerar PDF-filer för maximal komprimering och PDF/A-kompatibilitet."
    )

    # Obligatoriskt argument: Indatamapp
    parser.add_argument(
        'input_dir',
        type=str,
        help="Sökvägen till mappen som innehåller de PDF-filer som ska optimeras."
    )

    # Valfritt argument: Utdatamapp
    parser.add_argument(
        '-o', '--output_dir',
        type=str,
        default=None,
        help="Valfri sökväg till mappen där de optimerade filerna ska sparas. Om den inte anges skapas 'output_optimized' inuti indatamappen."
    )

    # Valfritt argument: Rekursiv bearbetning av mappar
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help="Sök efter PDF-filer i undermappar också."
    )

    args = parser.parse_args()

    # Bestämmer utdatamappen
    INPUT_DIR = args.input_dir
    if args.output_dir:
        OUTPUT_DIR = args.output_dir
    else:
        # Skapar en standardmapp i indatamappen om output_dir inte angivs
        OUTPUT_DIR = os.path.join(INPUT_DIR, 'output_optimized')

    # Skapa utdatamappen om den inte finns
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Hitta alla PDF-filer
    search_path = os.path.join(INPUT_DIR, '**', '*.pdf') if args.recursive else os.path.join(INPUT_DIR, '*.pdf')
    pdf_files = glob.glob(search_path, recursive=args.recursive)

    # ------------------------------------------------------------------
    # NYTT STEG: Konfigurera loggningen för Progressbar-kompatibilitet
    # Verbosity.default motsvarar standardnivån utan extra -v
    try:
        configure_logging(
            verbosity=Verbosity.default,
            progress_bar_friendly=True, # Mycket viktigt för tqdm-kompatibilitet
            manage_root_logger=False    # Låt skriptet hantera sin egen logik
        )
    except Exception as e:
        # Detta kan vara nödvändigt om du kör i en miljö där loggningsstrukturen redan är låst
        print(f"Varning: Kunde inte konfigurera ocrmypdf-loggning: {e}")
    # ------------------------------------------------------------------

    if not pdf_files:
        print(f"\nInga PDF-filer hittades i mappen: {INPUT_DIR}")
        print("Kontrollera sökvägen och att mappen innehåller filer.")
        return

    print(f"\nSTARTAR BATCH-PROCESS (Källmapp: {INPUT_DIR}, Målmapp: {OUTPUT_DIR})")
    print(f"Hittade {len(pdf_files)} filer…")
    print("-" * 50)

    # --- IMPLEMENTERING AV PROGRESSBAR ---
    # Spara progressbar-instansen i variabeln 'pbar'
    pbar = tqdm(pdf_files, desc="Optimerar PDF-filer", unit=" fil")

    for input_path in pbar:

        # ANVÄND NU 'pbar' (instansen) istället för 'tqdm' (klassen/modulen)
        pbar.set_postfix_str(os.path.basename(input_path))

        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        process_file(input_path, output_path)

    print("-" * 50)
    print("BATCH-PROCESS SLUTFÖRD.")

if __name__ == "__main__":
    main()
