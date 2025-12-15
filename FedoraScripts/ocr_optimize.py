#!/usr/bin/python
import ocrmypdf
import os
import glob # För att hitta filer som matchar ett mönster

# --- INSTÄLLNINGAR ---

# 1. Ange mapparna:
INPUT_DIR = 'input_pdfs'    # Mappen där dina ooptimerade PDF-filer ligger
OUTPUT_DIR = 'output_optimized_pdfs' # Mappen där de färdiga filerna ska sparas

# 2. Skapa utdatamappen om den inte finns
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- FUNKTION FÖR ENKEL FIL ---

def process_file(input_path, output_path):
    """
    Kör ocrmypdf med dina specificerade optimeringsparametrar.
    """
    print(f"-> Bearbetar: {os.path.basename(input_path)}")
    
    try:
        ocrmypdf.ocr(
            input_path,
            output_path,
            
            # --- Optimering och Komprimering ---
            optimize=2,
            optimize_resolution=200, 
            jpg_quality=85,
            jbig2_lossy=True,
            
            # --- Ytterligare Optimering och Rengöring ---
            clean=True, 
            remove_vectors=True, 
            fast_web_view=True,
            output_type='pdfa-3u',
            
            # --- OCR-Kontroll ---
            redo_ocr=True,
            
            # --- Metadata och Språk ---
            title='Optimerad för Arkiv/Webb',
            author='Batch OCR Script',
            language=['swe', 'eng'],
            
            # Lägg till loggning/utskrift
            progress_bar=False,
            log_level='WARNING'
        )
        print(f"<- Klar: Sparad i {os.path.basename(output_path)}")
        
    except ocrmypdf.exceptions.EncryptedPdfError:
        print(f"!!! Fel: Filen {os.path.basename(input_path)} är lösenordsskyddad och kunde inte bearbetas.")
    except Exception as e:
        print(f"!!! Ett oväntat fel uppstod vid bearbetning av {os.path.basename(input_path)}: {e}")


# --- HUVUDPROGRAM ---

def main():
    # Använder glob för att hitta alla filer som slutar på .pdf (case-insensitive)
    search_path = os.path.join(INPUT_DIR, '*.pdf')
    pdf_files = glob.glob(search_path, recursive=False)
    
    if not pdf_files:
        print(f"\nInga PDF-filer hittades i mappen: {INPUT_DIR}")
        print("Kontrollera att mappen finns och innehåller filer.")
        return

    print(f"\nSTARTAR BATCH-PROCESS (Hittade {len(pdf_files)} filer)...")
    print("-" * 40)
    
    for input_path in pdf_files:
        # Skapa sökvägen till utdatafilen
        filename = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        # Anropa funktionen för varje fil
        process_file(input_path, output_path)

    print("-" * 40)
    print("BATCH-PROCESS SLUTFÖRD.")

if __name__ == "__main__":
    main()
