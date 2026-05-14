#!/usr/bin/env python3
import os
import pandas as pd
from openpyxl.styles import Font
from datetime import datetime
import re
import argparse
import sys

def las_in_forkortningar(filnamn):
    """Läser in förkortningar från en textfil (format: kort,lang)."""
    forkortningar = {}
    if not filnamn or not os.path.exists(filnamn):
        if filnamn:
            print(f"Varning: Förkortningsfilen '{filnamn}' hittades inte. Hoppar över.")
        return forkortningar

    try:
        with open(filnamn, 'r', encoding='utf-8') as fil:
            for rad in fil:
                if ',' in rad:
                    # Hanterar rader med flera kommatecken genom att bara splitta vid första
                    kort, lang = rad.strip().split(',', 1)
                    forkortningar[kort.strip()] = lang.strip()
    except Exception as e:
        print(f"Fel vid inläsning av förkortningar: {e}")

    return forkortningar

def byt_ut_forkortningar(filnamn, forkortningar):
    """Byter ut förkortningar i filnamn (hanterar understreck, punkter etc)."""
    if not forkortningar:
        return filnamn

    # Sortera förkortningar efter längd (längst först) för att undvika
    # att korta förkortningar förstör längre (t.ex. 'dok' vs 'dokum')
    sorterade_kort = sorted(forkortningar.keys(), key=len, reverse=True)

    for kort in sorterade_kort:
        lang = forkortningar[kort]
        # Matchar 'kort' om det inte är omgivet av bokstäver eller siffror
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(kort) + r'(?![a-zA-Z0-9])'
        filnamn = re.sub(pattern, lang, filnamn)
    return filnamn

def skapa_excel_for_mapp(start_mapp, rot, filer, forkortningar):
    """Skapar en Excel-fil för en specifik mapp med gamla och nya namn."""
    mappnamn = os.path.basename(rot)
    # Om vi är i en rot-mapp (basename är tomt), använd namnet på startmappen istället
    if not mappnamn:
        mappnamn = os.path.basename(start_mapp.rstrip(os.sep))

    # Om det fortfarande är tomt (t.ex. om start_mapp var '/'), kör på "root"
    if not mappnamn:
        mappnamn = "root"

    excel_filpath = os.path.join(rot, f'{mappnamn}_filnamn.xlsx')

    nya_namn = [byt_ut_forkortningar(f, forkortningar) for f in filer]

    df = pd.DataFrame({
        'Gammalt namn': filer,
        'Nytt namn': nya_namn
    })

    df.to_excel(excel_filpath, index=False)

    # Definiera typsnitt här (t.ex. Calibri, Arial, Liberation Sans)
    VALT_TYPSNITT = "Liberation Sans"

    rubrik_font = Font(name=VALT_TYPSNITT, size=11, bold=True)
    data_font = Font(name=VALT_TYPSNITT, size=11, bold=False)

    # Formatering av rubriker, data och kolumner
    with pd.ExcelWriter(excel_filpath, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # 1. Sätt Liberation Sans som standardtypsnitt för ALLA celler (inklusive tomma)
        worksheet.views.sheetView[0].showGridLines = True  # Valfritt: Säkerställ att stödlinjer syns

        # Ändra den inbyggda "Normal"-stilen i openpyxl för detta blad
        workbook.styles.fonts[0] = Font(name=VALT_TYPSNITT, size=11)

        # 2. Formatera rubrikraden (Rad 1) till fetstil
        for cell in worksheet[1]:
            cell.font = rubrik_font

        # 3. Formatera datan explicit (för säkerhets skull så att pandas-exporten matchar)
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=1, max_col=2):
            for cell in row:
                cell.font = data_font

        # Sätt kolumnbredd
        worksheet.column_dimensions['A'].width = 35
        worksheet.column_dimensions['B'].width = 35

    return excel_filpath

def processa_mappar(start_mapp, forkortningar):
    """Går igenom mappar rekursivt och genererar Excel-filer."""
    stats = {
        'antal_excel_filer': 0,
        'antal_mappar': 0,
        'antal_filer': 0,
        'mappar_med_excel_filer': []
    }

    for rot, mappar, filer in os.walk(start_mapp):
        # Ignorera redan existerande Excel-listor för att undvika dubbelarbete
        rena_filer = [f for f in filer if not f.endswith('_filnamn.xlsx')]

        stats['antal_mappar'] += 1
        stats['antal_filer'] += len(rena_filer)

        if rena_filer:
            excel_fil = skapa_excel_for_mapp(start_mapp, rot, rena_filer, forkortningar)
            print(f'Skapat: "{os.path.relpath(excel_fil, start_mapp)}"')

            stats['antal_excel_filer'] += 1
            stats['mappar_med_excel_filer'].append(rot)

    return stats

def main():
    parser = argparse.ArgumentParser(description="Skapa Excel-listor över filer rekursivt.")

    # Positionellt argument: Mappen som ska skannas
    parser.add_argument("mapp", nargs="?", default=os.getcwd(),
                        help="Sökvägen till mappen (default: nuvarande)")

    # Valfritt argument: Fil med förkortningar
    parser.add_argument("-f", "--foerkortningar", type=str,
                        help="Sökväg till textfil med förkortningar (format: kort,lang)")

    args = parser.parse_args()
    target_dir = os.path.abspath(args.mapp)

    if not os.path.isdir(target_dir):
        print(f"Fel: '{target_dir}' är inte en giltig mapp.")
        sys.exit(1)

    # Läs in förkortningar om flaggan används
    forkortningar = {}
    if args.foerkortningar:
        forkortningar = las_in_forkortningar(args.foerkortningar)
        if forkortningar:
            print(f"Laddat {len(forkortningar)} förkortningar.")

    print(f"Skannar: {target_dir}\n")
    start_tid = datetime.now()

    resultat = processa_mappar(target_dir, forkortningar)

    slut_tid = datetime.now()
    tids_delta = slut_tid - start_tid

    print("\n" + "="*40)
    print("KLART!")
    print(f"Excel-filer skapade: {resultat['antal_excel_filer']}")
    print(f"Filer indexerade:     {resultat['antal_filer']}")
    print(f"Tid:                  {round(tids_delta.total_seconds(), 2)} sekunder")
    print("="*40)

if __name__ == "__main__":
    main()
