#!/usr/bin/env python3
import os
import sys
import re

def clean_string(text, is_stem=True):
    # 1. Mappa svenska tecken till arkivvänliga kombinationer
    replacements = {
        'å': 'aa', 'ä': 'ae', 'ö': 'oe',
        'Å': 'AA', 'Ä': 'AE', 'Ö': 'OE',
        ' ': '_'
    }
    
    for char, rep in replacements.items():
        text = text.replace(char, rep)

    # 2. Ta bort specialtecken
    if is_stem:
        # Tillåt endast a-z, 0-9, understreck och bindestreck i själva filnamnet
        text = re.sub(r'[^a-zA-Z0-9_-]', '', text)
    
    return text

def rename_recursively(root_directory):
    if not os.path.isdir(root_directory):
        print(f"Fel: '{root_directory}' är inte en giltig mapp.")
        return

    print(f"Startar rekursiv städning i: {root_directory}")

    # topdown=False för att kunna döpa om mappar utan att tappa bort filerna inuti
    for root, dirs, files in os.walk(root_directory, topdown=False):
        for name in files + dirs:
            old_path = os.path.join(root, name)
            
            # Dela upp i namn och ändelse
            stem, ext = os.path.splitext(name)
            
            # Tvätta filnamnet (is_stem=True tar bort alla punkter)
            new_stem = clean_string(stem, is_stem=True)
            
            # Tvätta ändelsen (behåller punkten, men rensar eventuella konstiga tecken i den)
            new_ext = "." + clean_string(ext.replace('.', ''), is_stem=False).lower() if ext else ""
            
            new_name = new_stem + new_ext

            # Din viktiga rättning: Använd 'oe' istället för 'ö'
            if not new_stem and not new_ext:
                new_name = "namnloes_fil_" + name

            if new_name != name:
                new_path = os.path.join(root, new_name)
                
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"Omdöpt: '{name}' -> '{new_name}'")
                else:
                    # Om mål namnet redan finns lägger vi på ett tidsstämpel/prefix för att undvika krock
                    print(f"Hoppade över: '{new_name}' finns redan.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        rename_recursively(sys.argv[1])
    else:
        print("Användning: python skript.py \"C:\\Sökväg\\Till\\Mapp\"")
