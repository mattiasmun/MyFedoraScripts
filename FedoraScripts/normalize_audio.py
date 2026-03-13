#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path
import multiprocessing
from tqdm import tqdm

INPUT_EXT = ".m4a"

def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def get_audio_metadata(file):

    cmd = [
        "ffprobe",
        "-v", "error",
        "-analyzeduration", "0",
        "-probesize", "32k",
        "-select_streams", "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels:format=duration",
        "-print_format", "json",
        str(file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)

        streams = data.get("streams", [])

        if not streams:
            raise ValueError("No audio stream")

        stream = streams[0]
        duration = float(data.get("format", {}).get("duration", 0.0))

        return {
            "codec": stream.get("codec_name"),
            "sample_rate": to_int(stream.get("sample_rate")),
            "channels": to_int(stream.get("channels")),
            "duration": duration
        }

    except Exception:

        return {
            "codec": None,
            "sample_rate": 0,
            "channels": 0,
            "duration": 0.0
        }

def process_file(file_meta):

    file, meta = file_meta

    if (
        meta["codec"] == "aac"
        and meta["sample_rate"] == 32000
        and meta["channels"] == 1
    ):
        return file

    output = file.parent / f"{file.stem}_normalized.m4a"

    # safety check (normally filtered earlier)
    if output.exists():
        return file

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
        "-af", "highpass=f=70,lowpass=f=14000,dynaudnorm",
        "-c:a", "aac",
        "-q:a", "1.2",
        "-movflags", "+faststart",
        str(temp)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        temp.replace(output)
        return file

    except subprocess.CalledProcessError:

        if temp.exists():
            temp.unlink()

        print(f"FFmpeg failed: {file}")
        return file

def find_files():
    files = sorted(Path(".").glob(f"*{INPUT_EXT}"))
    filtered_files = []

    for f in files:

        if f.stem.endswith("_normalized"):
            continue

        output = f.parent / f"{f.stem}_normalized.m4a"

        if output.exists():
            continue

        filtered_files.append(f)

    return filtered_files

def main():

    files = find_files()

    if not files:
        print("No input files found.")
        return

    workers = max(1, multiprocessing.cpu_count() - 1)

    print(f"Files: {len(files)}")
    print(f"Workers: {workers}\n")
    print("Scanning metadata…")

    chunksize = max(1, len(files) // (workers * 4))

    with multiprocessing.Pool(workers) as pool:
        metadata = {
            f: m for f, m in zip(
                files,
                pool.map(get_audio_metadata, files, chunksize=chunksize)
            )
        }

        durations = {f: max(m["duration"], 1.0) for f, m in metadata.items()}
        total_duration = sum(durations.values())

        results = pool.imap_unordered(
            process_file,
            zip(files, metadata.values()),
            chunksize=chunksize
        )

        with tqdm(
            total=total_duration,
            desc="Processing audio",
            unit="s",
            unit_scale=True,
            dynamic_ncols=True
        ) as pbar:

            for f in results:
                pbar.update(durations.get(f, 0.0))

    print("\nAll done.")

if __name__ == "__main__":
    main()
