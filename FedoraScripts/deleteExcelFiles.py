#!/usr/bin/env python3
import os
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

def ta_bort_excel_i_mapp(start_mapp, rot, logg_namn):
    """Identifierar och raderar den specifika Excel-filen i en mapp."""
    mappnamn = os.path.basename(rot)
    # Om vi är i en rot-mapp (basename är tomt), använd namnet på startmappen istället
    if not mappnamn:
        mappnamn = os.path.basename(start_mapp.rstrip(os.sep))

    # Om det fortfarande är tomt (t.ex. om start_mapp var '/'), kör på "root"
    if not mappnamn:
        mappnamn = "root"

    # Skapa namnet på filen vi letar efter
    excel_fil = os.path.join(rot, f'{mappnamn}_filnamn.xlsx')

    if os.path.isfile(excel_fil):
        try:
            os.remove(excel_fil)
            msg = f"Raderat: {os.path.relpath(excel_fil, os.getcwd())}"
            print(msg)
            logging.info(msg)
            return True
        except Exception as e:
            msg = f"FEL vid borttagning av {excel_fil}: {e}"
            print(msg)
            logging.error(msg)
    return False

def stada_mappar(start_mapp, logg_namn):
    """Går igenom filträdet och raderar Excel-filer."""
    antal_raderade = 0

    for rot, mappar, filer in os.walk(start_mapp):
        # Vi raderar bara om det faktiskt finns filer i mappen (eller om vi vill städa oavsett)
        if ta_bort_excel_i_mapp(start_mapp, rot, logg_namn):
            antal_raderade += 1

    return antal_raderade

def main():
    logg_namn = 'filhantering_radera.log'
    konfigurera_loggning(logg_namn)

    parser = argparse.ArgumentParser(description="Raderar skapade Excel-listor rekursivt.")
    parser.add_argument("mapp", nargs="?", default=os.getcwd(),
                        help="Sökvägen till mappen som ska städas (default: nuvarande)")

    args = parser.parse_args()
    target_dir = os.path.abspath(args.mapp)

    if not os.path.isdir(target_dir):
        print(f"Fel: '{target_dir}' är inte en giltig mapp.")
        sys.exit(1)

    print(f"Startar städning i: {target_dir}")
    start_tid = datetime.now()

    antal = stada_mappar(target_dir, logg_namn)

    slut_tid = datetime.now()
    tids_delta = slut_tid - start_tid

    print("\n" + "="*40)
    print(f"STÄDNING KLAR!")
    print(f"Antal raderade Excel-filer: {antal}")
    print(f"Tid:                        {round(tids_delta.total_seconds(), 2)} sekunder")
    print("="*40)

if __name__ == "__main__":
    main()
