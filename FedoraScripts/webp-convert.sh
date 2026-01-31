#!/bin/bash

# Gå igenom alla jpg, jpeg (oavsett stora/små bokstäver)
shopt -s nocaseglob

# Registrera starttid
start_time=$(date +%Y-%m-%d\ %H:%M:%S)
echo "Starttid: $start_time"
echo "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"

count=0

for f in *.jpg *.jpeg; do
    [ -e "$f" ] || continue

    output="${f%.*}.webp"
    echo "Bearbetar: $f"

    # 1. Konvertera
    if magick "$f" -quality 75 "$output"; then
        
        # 2. Kopiera metadata
        exiftool -overwrite_original -TagsFromFile "$f" "$output" > /dev/null
        
        # 3. Radera originalet (Valfritt: ta bort nästa rad om du vill behålla JPG)
        rm "$f"
        
        ((count++))
    else
        echo "FEL: Kunde inte konvertera $f"
    fi
done

# Registrera sluttid
end_time=$(date +%Y-%m-%d\ %H:%M:%S)

# Använd Python för att räkna ut timedelta (snyggt format)
duration=$(python3 -c "from datetime import datetime; print(datetime.strptime('$end_time', '%Y-%m-%d %H:%M:%S') - datetime.strptime('$start_time', '%Y-%m-%d %H:%M:%S'))")

echo "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
echo "KLART! Bearbetade $count filer."
echo "Sluttid: $end_time"
echo "Total tid (timedelta): $duration"
