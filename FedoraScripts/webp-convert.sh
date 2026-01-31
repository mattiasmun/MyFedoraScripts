#!/bin/bash

# Hantera stora/små bokstäver i filändelser
shopt -s nocaseglob

# Registrera starttid
start_time_raw=$(date +%Y-%m-%d\ %H:%M:%S)
echo "Starttid: $start_time_raw"
echo "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"

count=0
total_saved_bytes=0

for f in *.jpg *.jpeg; do
    [ -e "$f" ] || continue

    # Spara ursprunglig filstorlek för statistik
    old_size=$(stat -c%s "$f")

    # 1. Detektera originalkvalitet (fallback till 75)
    orig_quality=$(magick identify -format "%Q" "$f" 2>/dev/null)
    if [ -z "$orig_quality" ] || [ "$orig_quality" -eq 0 ]; then
        orig_quality=75
    fi

    output="${f%.*}.webp"
    echo -n "Bearbetar: $f (Kvalitet: $orig_quality)... "

    # 2. Konvertera med ImageMagick
    if magick "$f" -quality "$orig_quality" "$output"; then

        # 3. Kopiera metadata med ExifTool
        exiftool -overwrite_original -TagsFromFile "$f" "$output" > /dev/null

        # Beräkna besparing för denna fil
        new_size=$(stat -c%s "$output")
        saved=$((old_size - new_size))
        total_saved_bytes=$((total_saved_bytes + saved))

        # 4. Radera originalet
        rm "$f"

        echo "KLART (Sparade $(bc <<< "scale=2; $saved / 1024 / 1024") MB)"
        ((count++))
    else
        echo "FEL: Kunde inte konvertera $f"
    fi
done

# Registrera sluttid
end_time_raw=$(date +%Y-%m-%d\ %H:%M:%S)

# Beräkna timedelta via Python
duration=$(python3 -c "from datetime import datetime; print(datetime.strptime('$end_time_raw', '%Y-%m-%d %H:%M:%S') - datetime.strptime('$start_time_raw', '%Y-%m-%d %H:%M:%S'))")

# Omvandla total besparing till MB
total_saved_mb=$(bc <<< "scale=2; $total_saved_bytes / 1024 / 1024")

echo "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
echo "RESULTAT:"
echo "Antal filer bearbetade: $count"
echo "Total plats sparad:     $total_saved_mb MB"
echo "Sluttid:                $end_time_raw"
echo "Total tid (timedelta):  $duration"
echo "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
