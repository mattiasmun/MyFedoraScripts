import os
import logging

# Ställ in loggning
logging.basicConfig(filename='filhantering_radera.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Använd den aktuella arbetsmappen
huvud_mapp = os.getcwd()

# Gå igenom alla mappar i huvudmappen
for rot, mappar, filer in os.walk(huvud_mapp):
    # Hämta mappnamnet
    mappnamn = os.path.basename(rot)
    
    # Skapa filnamnet för att radera
    if rot == huvud_mapp:
        excel_fil = os.path.join(rot, '_filnamn.xlsx')  # För root-katalogen
    else:
        excel_fil = os.path.join(rot, f'{mappnamn}_filnamn.xlsx')  # För undermappar

    # Kontrollera om mappen är tom
    if not any(filer):
        continue  # Om mappen är tom, hoppa till nästa mapp

    # Kontrollera om Excel-filen finns och ta bort den
    if os.path.isfile(excel_fil):
        try:
            os.remove(excel_fil)
            msg = f'Excel-filen "{excel_fil}" har tagits bort.'
            print(msg)
            logging.info(msg)
        except Exception as e:
            msg = f'Fel vid borttagning av "{excel_fil}": {e}'
            print(msg)
            logging.error(msg)
    else:
        # Logga om filen inte hittades, men endast om mappen inte är tom
        msg = f'Excel-filen "{excel_fil}" hittades inte i mappen "{rot}".'
        print(msg)
        logging.warning(msg)
