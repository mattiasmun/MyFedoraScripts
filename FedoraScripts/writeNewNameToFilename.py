#!/usr/bin/env python3
import os
import pandas as pd
import logging
import argparse
import sys
from datetime import datetime

def konfigurera_loggning(loggfil):
    """Ställer in loggning med ett rent tidsformat."""
    logging.basicConfig(
        filename=loggfil,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def doep_om_filer_i_mapp(rot, excel_fil, logg_namn):
    """Hanterar omdöpningslogiken för en enskild mapp baserat på dess Excel-fil."""
    try:
        df = pd.read_excel(excel_fil)
    except Exception as e:
        msg = f"Kunde inte läsa Excel-filen {excel_fil}: {e}"
        print(msg)
        logging.error(msg)
        return

    # Validera kolumner
    if 'Gammalt namn' not in df.columns or 'Nytt namn' not in df.columns:
        msg = f"Fel: Obligatoriska kolumner saknas i {excel_fil}"
        print(msg)
        logging.error(msg)
        return

    # Kontrollera tomma värden
    if df['Gammalt namn'].isnull().any() or df['Nytt namn'].isnull().any():
        msg = f"Varning: Tomma celler hittades i {excel_fil}. Hoppar över rader."
        print(msg)
        logging.warning(msg)
        df = df.dropna(subset=['Gammalt namn', 'Nytt namn'])

    print(f"\n--- Bearbetar mapp: {os.path.basename(rot)} ---")

    for _, row in df.iterrows():
        gammalt_namn = str(row['Gammalt namn']).strip()
        nytt_namn = str(row['Nytt namn']).strip()

        gammal_fil = os.path.join(rot, gammalt_namn)
        ny_fil = os.path.join(rot, nytt_namn)

        # Skydda systemfiler och själva verktyget
        if gammalt_namn.endswith('_filnamn.xlsx') or gammalt_namn == logg_namn:
            continue

        if os.path.isfile(gammal_fil):
            if gammalt_namn == nytt_namn:
                logging.info(f"Ingen ändring krävs: {gammalt_namn}")
                continue

            try:
                # Hantera om målfilen redan existerar
                if os.path.exists(ny_fil):
                    base, ext = os.path.splitext(nytt_namn)
                    count = 1
                    while os.path.exists(ny_fil):
                        ny_fil = os.path.join(rot, f"{base} ({count}){ext}")
                        count += 1
                    slutgiltigt_namn = os.path.basename(ny_fil)
                    msg = f"KOLLISION: '{gammalt_namn}' -> '{slutgiltigt_namn}' (Mål fanns redan)"
                    logging.warning(msg)
                else:
                    slutgiltigt_namn = nytt_namn

                os.rename(gammal_fil, ny_fil)
                print(f"OK: {gammalt_namn} -> {slutgiltigt_namn}")
                logging.info(f"Omdöpt: {gammalt_namn} -> {slutgiltigt_namn}")

            except Exception as e:
                msg = f"FEL vid omdöpning av {gammalt_namn}: {e}"
                print(msg)
                logging.error(msg)
        else:
            msg = f"Hittades ej: {gammalt_namn} (i {rot})"
            # print(msg) # Avkommentera om du vill se saknade filer i terminalen
            logging.warning(msg)

def processa_alla_mappar(start_mapp, logg_namn):
    """Vandrar genom filträdet och letar efter Excel-instruktioner."""
    for rot, mappar, filer in os.walk(start_mapp):
        mappnamn = os.path.basename(rot)
        # Om vi är i en rot-mapp (basename är tomt), använd namnet på startmappen istället
        if not mappnamn:
            mappnamn = os.path.basename(start_mapp.rstrip(os.sep))

        # Om det fortfarande är tomt (t.ex. om start_mapp var '/'), kör på "root"
        if not mappnamn:
            mappnamn = "root"

        excel_fil = os.path.join(rot, f'{mappnamn}_filnamn.xlsx')

        if os.path.isfile(excel_fil):
            doep_om_filer_i_mapp(rot, excel_fil, logg_namn)
        else:
            logging.debug(f"Ingen Excel-fil i {rot}, hoppar över.")

def main():
    logg_namn = 'filhantering.log'
    konfigurera_loggning(logg_namn)

    parser = argparse.ArgumentParser(description="Döper om filer baserat på Excel-listor rekursivt.")
    parser.add_argument("mapp", nargs="?", default=os.getcwd(),
                        help="Sökvägen till mappen som ska bearbetas (default: nuvarande)")

    args = parser.parse_args()
    target_dir = os.path.abspath(args.mapp)

    if not os.path.isdir(target_dir):
        print(f"Fel: '{target_dir}' är inte en giltig mapp.")
        sys.exit(1)

    print(f"Startar omdöpning i: {target_dir}")
    print(f"Loggar händelser till: {logg_namn}")

    start_tid = datetime.now()

    processa_alla_mappar(target_dir, logg_namn)

    slut_tid = datetime.now()
    print(f"\nKlar! Tid: {round((slut_tid - start_tid).total_seconds(), 2)} sekunder.")
    print("Se filhantering.log för detaljer.")

if __name__ == "__main__":
    main()
