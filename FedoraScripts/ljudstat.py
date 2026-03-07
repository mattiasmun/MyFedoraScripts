#!/usr/bin/env python3
import os
import sys
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from mutagen import File
from tqdm import tqdm

STODDA = (".mp3", ".m4a", ".flac", ".ogg")


def scan_fil(path):
    try:
        audio = File(path)

        if not audio or not hasattr(audio.info, "length"):
            return None

        return (
            path,
            audio.info.length,
            getattr(audio.info, "bitrate", 0),
            os.path.getsize(path)
        )

    except Exception:
        return None


def iter_ljudfiler(root):
    stack = [root]

    while stack:
        path = stack.pop()

        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)

                    elif entry.name.lower().endswith(STODDA):
                        yield entry.path
        except PermissionError:
            pass


if len(sys.argv) < 2:
    print("Användning: python ljudstat_ultra.py <mapp>")
    sys.exit(1)

mapp = sys.argv[1]

workers = min(32, os.cpu_count() * 4)

resultat = []
bitrates = []
total_size = 0
total_seconds = 0
antal = 0

with ThreadPoolExecutor(workers) as pool:

    filer = list(iter_ljudfiler(mapp))

    for r in tqdm(
        pool.map(scan_fil, filer, chunksize=64),
        total=len(filer),
        desc="Skannar ljudfiler",
        unit="fil",
        dynamic_ncols=True
    ):
        if not r:
            continue

        path, length, bitrate, size = r

        resultat.append(r)
        total_seconds += length
        total_size += size
        antal += 1

        if bitrate:
            bitrates.append(bitrate)


if antal == 0:
    print("Inga ljudfiler hittades.")
    sys.exit()

total_tid = timedelta(seconds=total_seconds)
gen_tid = timedelta(seconds=total_seconds / antal)
gen_bitrate = sum(bitrates) / len(bitrates) if bitrates else 0


print("\nResultat")
print("--------")
print("Antal filer:", antal)
print("Total speltid:", total_tid)
print("Genomsnittlig längd:", gen_tid)
print("Total storlek:", round(total_size / (1024**3), 2), "GB")
print("Genomsnittlig bitrate:", int(gen_bitrate / 1000), "kb/s")


print("\nLängsta filer:")

for path, length, _, _ in sorted(resultat, key=lambda x: x[1], reverse=True)[:10]:
    print(timedelta(seconds=int(length)), "-", os.path.basename(path))
