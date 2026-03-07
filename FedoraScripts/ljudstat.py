#!/usr/bin/env python3
import os
import sys
from mutagen import File
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

STODDA = (".mp3", ".m4a", ".flac", ".ogg")

def format_tid(sek):
    h = int(sek // 3600)
    m = int((sek % 3600) // 60)
    s = int(sek % 60)
    return f"{h}h {m}m {s}s"

def scan_fil(path):
    try:
        audio = File(path)
        if audio is None or not hasattr(audio.info, "length"):
            return None

        length = audio.info.length
        bitrate = getattr(audio.info, "bitrate", 0)
        size = os.path.getsize(path)

        return (path, length, bitrate, size)

    except Exception:
        return None


if len(sys.argv) < 2:
    print("Användning: python ljudstat_fast_progress.py <mapp>")
    sys.exit(1)

mapp = sys.argv[1]

alla_filer = []

for root, dirs, files in os.walk(mapp):
    for f in files:
        if f.lower().endswith(STODDA):
            alla_filer.append(os.path.join(root, f))

resultat = []

with ThreadPoolExecutor() as pool:
    for r in tqdm(
        pool.map(scan_fil, alla_filer),
        total=len(alla_filer),
        desc="Skannar ljudfiler",
        unit="fil",
        dynamic_ncols=True
    ):
        if r:
            resultat.append(r)

if not resultat:
    print("Inga ljudfiler hittades.")
    sys.exit()

total_tid = sum(r[1] for r in resultat)
total_size = sum(r[3] for r in resultat)

bitrates = [r[2] for r in resultat if r[2] > 0]

antal = len(resultat)

gen_tid = total_tid / antal
gen_bitrate = sum(bitrates) / len(bitrates) if bitrates else 0

resultat.sort(key=lambda x: x[1], reverse=True)

print("\nResultat")
print("--------")
print("Antal filer:", antal)
print("Total speltid:", format_tid(total_tid))
print("Genomsnittlig längd:", format_tid(gen_tid))
print("Total storlek:", round(total_size / (1024**3), 2), "GB")
print("Genomsnittlig bitrate:", int(gen_bitrate / 1000), "kb/s")

print("\nLängsta filer:")
for path, length, _, _ in resultat[:10]:
    print(format_tid(length), "-", os.path.basename(path))
