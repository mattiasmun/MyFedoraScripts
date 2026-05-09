import os
import pandas as pd
import logging
from datetime import datetime

# Ställ in loggning utan millisekunder i tidsstämpeln
logging.basicConfig(filename='filhantering.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Anpassa loggformatet för att ta bort millisekunder
logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Justera tidsformatet (utan millisekunder)
def remove_ms(record, fmt):
    """
    Tar bort millisekunder från tidsstämpeln.
    """
    record.asctime = record.asctime.split(',')[0]  # Ta bort millisekunder
    return fmt(record)

# Använd den aktuella arbetsmappen
huvud_mapp = os.getcwd()

# Gå igenom alla mappar i huvudmappen
for rot, mappar, filer in os.walk(huvud_mapp):
    # Hämta mappnamnet för att skapa filnamnet
    mappnamn = os.path.basename(rot)

    # Kolla om filnamnet ska vara "_filnamn.xlsx" i root-katalogen
    #if rot == huvud_mapp:
   #     excel_fil = os.path.join(rot, '_filnamn.xlsx')
   # else:
    excel_fil = os.path.join(rot, f'{mappnamn}_filnamn.xlsx')

    if os.path.isfile(excel_fil):
        # Läs in den existerande Excel-filen
        df = pd.read_excel(excel_fil)

        # Kontrollera att kolumn B heter "Nytt namn"
        if 'Nytt namn' not in df.columns or df.columns[1] != 'Nytt namn':
            msg = f'Fel: Kolumnen "Nytt namn" saknas eller har fel namn i "{excel_fil}".'
            print(msg)
            logging.error(msg)
            continue

        # Kontrollera att det finns värden i både kolumn A och B
        if df['Gammalt namn'].isnull().any() or df['Nytt namn'].isnull().any():
            msg = f'Fel: Det finns tomma värden i antingen "Gammalt namn" eller "Nytt namn" i "{excel_fil}".'
            print(msg)
            logging.error(msg)
            continue

        # Döp om filer
        gamla_filer = df['Gammalt namn'].tolist()
        nya_filer = df['Nytt namn'].tolist()

        print(f"\n=== Sammanfattning av filhantering i \"{rot}\" ===")
        print("Ändrade filer:")

        for index, row in df.iterrows():
            gammalt_namn = row['Gammalt namn']
            nytt_namn = row['Nytt namn']

            # Bygg sökvägar för gammalt och nytt filnamn
            gammal_fil = os.path.join(rot, gammalt_namn)
            ny_fil = os.path.join(rot, nytt_namn)

            # Kontrollera om den gamla filen finns och döp om den
            if os.path.isfile(gammal_fil):
                if gammalt_namn == nytt_namn:
                    msg = f'- Ingen ändring: "{gammalt_namn}".'
                    print(msg)
                    logging.info(msg)
                else:
                    try:
                        os.rename(gammal_fil, ny_fil)
                        msg = f'- Ändrade: "{gammalt_namn}" → "{nytt_namn}".'
                        print(msg)
                        logging.info(msg)
                    except FileExistsError:
                        # Generera nytt namn
                        base, ext = os.path.splitext(nytt_namn)
                        count = 1
                        while os.path.isfile(ny_fil):
                            ny_fil = os.path.join(rot, f"{base} ({count}){ext}")
                            count += 1
                        msg = f'- VARNING!!! NYTT NAMN TILLDELADES: "{gammalt_namn}" → "{os.path.basename(ny_fil)}".'
                        os.rename(gammal_fil, ny_fil)
                        print(msg)
                        logging.warning(msg)
                    except PermissionError as e:
                        msg = f'Fel vid döpning av "{gammalt_namn}": {e}'
                        print(msg)
                        logging.error(msg)
            else:
                msg = f'Fil "{gammalt_namn}" hittades inte i mappen "{rot}".'
                print(msg)
                logging.warning(msg)

        # Kontrollera om det finns nya filer som inte är med i Excel-filen
        nya_filer_i_mappen = [f for f in filer if f not in gamla_filer and f != (f'{mappnamn}_filnamn.xlsx' if rot != huvud_mapp else '_filnamn.xlsx')]

        if nya_filer_i_mappen:
            print("\nNya filer som inte finns med i Excel-filen:")
            print(f'- {", ".join(nya_filer_i_mappen)}.')
    else:
        msg = f'Excel-filen "{excel_fil}" hittades inte i mappen "{rot}".'
        print(msg)
        logging.warning(msg)
