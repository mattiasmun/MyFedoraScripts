#!/bin/bash

# Gå igenom alla jpg, jpeg (både små och stora bokstäver)
shopt -s nocaseglob

echo "⎯⎯ Startar konvertering till WebP med metadata-bevaring ⎯⎯"
start_time=$(date +%s)
count=0

for f in *.jpg *.jpeg; do
    # Kontrollera om filen faktiskt finns (om inga matchningar hittas)
    [ -e "$f" ] || continue

    output="${f%.*}.webp"
    echo "Bearbetar: $f -> $output"

    # 1. Konvertera med ImageMagick (Kvalitet 75 är standard balans)
    magick "$f" -quality 75 "$output"

    # 2. Kopiera metadata från originalet och skriv över direkt (inga _original filer)
    exiftool -overwrite_original -TagsFromFile "$f" "$output" > /dev/null

    ((count++))
done

end_time=$(date +%s)
runtime=$((end_time-start_time))

echo "⎯" * 30
echo "KLART! Bearbetade $count filer på $runtime sekunder."
