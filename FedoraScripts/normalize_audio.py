#!/usr/bin/env python3

import subprocess
from pathlib import Path
import multiprocessing
from tqdm import tqdm

INPUT_EXT = ".m4a"

FILTER = (
    "highpass=f=70,"
    "lowpass=f=14000,"
    "dynaudnorm"
)

def get_audio_info(file):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    lines = result.stdout.strip().split("\n")

    try:
        codec = lines[0]
        sample_rate = int(lines[1])
        channels = int(lines[2])
        return codec, sample_rate, channels
    except:
        return None

def get_duration(file):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return float(result.stdout.strip())
    except:
        return 0.0

def process_file(file):
    if file.stem.endswith("_normalized"):
        return file

    info = get_audio_info(file)

    if info:
        codec, sr, ch = info

        if codec == "aac" and sr == 32000 and ch == 1:
            return file

    output = file.with_name(file.stem + "_normalized.m4a")
    temp = output.with_suffix(".tmp.m4a")

    cmd = [
        "ffmpeg",
        "-threads", "1",
        "-nostats",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-analyzeduration", "0",
        "-probesize", "32k",
        "-i", str(file),
        "-map_metadata", "0",
        "-vn",
        "-sn",
        "-dn",
        "-ac", "1",
        "-ar", "32000",
        "-af", FILTER,
        "-c:a", "aac",
        "-q:a", "1.2",
        "-movflags", "+faststart",
        str(temp)
    ]

    try:
        subprocess.run(cmd, check=True)
        temp.replace(output)
    except subprocess.CalledProcessError:
        if temp.exists():
            temp.unlink()
        print(f"FFmpeg failed: {file}")
    return file

def main():

    files = sorted(Path(".").glob(f"*{INPUT_EXT}"))

    if not files:
        print("No input files found.")
        return

    print("Scanning durations…")

    durations = {f: get_duration(f) for f in files}
    total_duration = sum(durations.values()) + 0.001

    workers = max(1, multiprocessing.cpu_count() // 2)

    print(f"Files: {len(files)}")
    print(f"Workers: {workers}\n")

    with multiprocessing.Pool(workers) as pool:

        results = pool.imap_unordered(process_file, files)

        with tqdm(
            total=total_duration,
            desc="Processing audio",
            unit="s",
            unit_scale=True,
            dynamic_ncols=True
        ) as pbar:

            for f in results:
                pbar.update(durations[f])

    print("\nAll done.")

if __name__ == "__main__":
    main()
