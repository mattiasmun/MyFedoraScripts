#!/usr/bin/python
import ocrmypdf

ocrmypdf.ocr(
    'input.pdf',
    'output_max_optimized.pdf',
    
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
    
    # --- OCR-Kontroll (Den nya kompromissen) ---
    
    # 9. KÖR OCR ENDAST om inget sökbart textlager finns.
    #    Detta är snabbare än force_ocr.
    redo_ocr=True,
    
    # 10. Ställer in standard metadata för dokumentet
    title='Mitt Optimerade Dokument',
    author='OCR-Process',
    
    # 11. Ställer in önskat språk för OCR (justera vid behov)
    language=['swe', 'eng']
)
