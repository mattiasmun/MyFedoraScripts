import os
import pandas as pd
from openpyxl.styles import Font
from datetime import datetime
import re

# Funktion för att läsa in förkortningar från en textfil
def las_in_forkortningar(filnamn):
    forkortningar = {}
    with open(filnamn, 'r', encoding='utf-8') as fil:
        for rad in fil:
            kort, lang = rad.strip().split(',')
            forkortningar[kort] = lang
    return forkortningar

# Funktion för att byta ut förkortningar i filnamn
def byt_ut_forkortningar(filnamn, forkortningar):
    for kort, lang in forkortningar.items():
        # Använd reguljära uttryck för att matcha hela ord
        filnamn = re.sub(r'\b' + re.escape(kort) + r'\b', lang, filnamn)
    return filnamn

# Använd den aktuella arbetsmappen
huvud_mapp = os.getcwd()

# Räknare för antalet skapade Excel-filer och mappar
antal_excel_filer = 0
antal_mappar = 0
antal_filer = 0
mappar_med_excel_filer = []

# Tidsstämpel för start
start_tid = datetime.now()

# Läs in förkortningar från textfil
#forkortningar = las_in_forkortningar('foerkortningar.txt')

# Gå igenom alla mappar i huvudmappen
for rot, mappar, filer in os.walk(huvud_mapp):
    antal_mappar += 1  # Öka mappräknaren
    # Skapa en lista med filnamn
    filnamn = [f for f in filer if os.path.isfile(os.path.join(rot, f))]
    antal_filer += len(filnamn)  # Räkna antalet filer

    # Om det finns filer i mappen, skapa en Excel-fil
    if filnamn:
        # Hämta mappnamnet
        mappnamn = os.path.basename(rot)

        # Skapa en DataFrame med två kolumner
        df = pd.DataFrame({
            'Gammalt namn': filnamn,
            'Nytt namn': filnamn
            #'Nytt namn': [byt_ut_forkortningar(f, forkortningar) for f in filnamn]  # Byt ut förkortningar i filnamn
        })

        # Skapa Excel-filnamn med mappnamnet som prefix
        excel_fil = os.path.join(rot, f'{mappnamn}_filnamn.xlsx')  # Namnet på Excel-filen

        # Spara DataFrame till Excel
        df.to_excel(excel_fil, index=False)

        # Öppna Excel-filen för att ställa in fet stil och justera kolumnbredd
        with pd.ExcelWriter(excel_fil, engine='openpyxl', mode='a') as writer:
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            # Ställ in rubrikerna som fetstil
            for cell in worksheet["A1:B1"][0]:  # Första raden
                cell.font = Font(bold=True)

            # Justera kolumnbredd
            worksheet.column_dimensions['A'].width = 30  # Justera bredd för kolumn A
            worksheet.column_dimensions['B'].width = 30  # Justera bredd för kolumn B

        print(f'Excel-dokumentet "{excel_fil}" har skapats med filnamnen.')
        
        # Öka räknaren och spara mappens namn
        antal_excel_filer += 1
        mappar_med_excel_filer.append(rot)

# Tidsstämpel för slut
slut_tid = datetime.now()

# Skriv ut sammanställning av resultat
print("\nSammanställning av resultat:\n" + "-"*40)
print(f'Totalt antal skapade Excel-filer: {antal_excel_filer}')
print(f'Totalt antal mappar genomsökta: {antal_mappar}')
print(f'Totalt antal filer hittades: {antal_filer}')

if mappar_med_excel_filer:
    print(f'Mappar där Excel-filer skapades:\n' + '\n'.join(mappar_med_excel_filer))
else:
    print('Inga mappar hade några Excel-filer skapade.')

print(f'\nProcessen startade: {start_tid.strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Processen avslutades: {slut_tid.strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Tid för processen: {slut_tid - start_tid} (ungefär {round((slut_tid - start_tid).total_seconds(), 2)} sekunder)')
