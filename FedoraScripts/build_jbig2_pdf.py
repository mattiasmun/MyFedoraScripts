#!/usr/bin/env encoding=utf-8
#!/usr/bin/env python3

import sys
import shutil
import subprocess
import re
from pathlib import Path
import pikepdf

if len(sys.argv) != 4:
    print("Usage: build_jbig2_pdf.py <pages_dir> <output_pdf> <dpi>")
    sys.exit(1)

PAGES_DIR = Path(sys.argv[1])
OUTPUT_PDF = sys.argv[2]
DPI = float(sys.argv[3])

pbms = sorted(PAGES_DIR.glob("*.pbm"))
if not pbms:
    print("❌ Inga PBM-filer hittades")
    sys.exit(1)

def get_pbm_dimensions(pbm_path: Path) -> tuple[float, float]:
    """Läser PBM-headern på ett robust sätt oavsett radbrytningar och kommentarer."""
    with open(pbm_path, "rb") as f:
        # Läs de första 200 bytesen (mer än väl för att täcka headern)
        chunk = f.read(200)

        # Ta bort eventuella kommentarer som börjar med # och sträcker sig till radslut
        chunk_clean = re.sub(b"#.*?\n", b"\n", chunk)

        # Dela upp headern i tokens baserat på whitespace
        tokens = chunk_clean.split()

        if not tokens or tokens[0] != b"P4":
            raise ValueError(f"Inte en giltig P4 PBM-fil: {pbm_path.name}")

        if len(tokens) < 3:
            raise ValueError(f"Kunde inte hitta dimensioner i headern för {pbm_path.name}")

        pixels_w = int(tokens[1])
        pixels_h = int(tokens[2])

        # Konvertera pixlar till PostScript points (1 tum = 72 points)
        pt_w = (pixels_w / DPI) * 72.0
        pt_h = (pixels_h / DPI) * 72.0
        return pt_w, pt_h

# ==========================================================
# 1️⃣ Kör jbig2
# ==========================================================
tmp_base = PAGES_DIR / "output"

cmd = [
    "jbig2",
    "-s", "-a", "-p",
    "-t", "0.80",
    "-b", str(tmp_base)
] + [str(p) for p in pbms]

print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)

sym_file = Path(str(tmp_base) + ".sym")
page_files = [Path(str(tmp_base) + f".{i:04d}") for i in range(len(pbms))]

if not sym_file.exists() or not all(p.exists() for p in page_files):
    print("❌ jbig2 skapade inte förväntade filer")
    sys.exit(1)

# ==========================================================
# 2️⃣ Bygg PDF via jbig2topdf.py
# ==========================================================
raw_pdf_path = PAGES_DIR / "jbig2_raw.pdf"
jbig2topdf_path = shutil.which("jbig2topdf.py") or "/usr/local/bin/jbig2topdf.py"

cmd = [jbig2topdf_path, str(tmp_base)]
print("Running:", " ".join(cmd))

with open(raw_pdf_path, "wb") as f:
    process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)
    _, stderr = process.communicate()

if process.returncode != 0:
    print("❌ jbig2topdf misslyckades:", stderr.decode())
    sys.exit(1)

# ==========================================================
# 3️⃣ Skala korrekt till individuella sidmått
# ==========================================================
src_pdf = pikepdf.Pdf.open(raw_pdf_path)
out_pdf = pikepdf.Pdf.new()

for idx, page in enumerate(src_pdf.pages):
    mediabox = page["/MediaBox"]
    src_w = float(mediabox[2]) - float(mediabox[0])
    src_h = float(mediabox[3]) - float(mediabox[1])

    # Hämta de exakta målen för just denna sida baserat på PBM-filen
    target_w, target_h = get_pbm_dimensions(pbms[idx])

    scale_x = target_w / src_w
    scale_y = target_h / src_h

    new_page = out_pdf.add_blank_page(page_size=(target_w, target_h))
    new_page["/Resources"] = out_pdf.copy_foreign(page["/Resources"])

    original_content = page.Contents.read_bytes()
    wrapped = f"\nq\n{scale_x} 0 0 {scale_y} 0 0 cm\n".encode() + original_content + b"\nQ\n"
    new_page.Contents = out_pdf.make_stream(wrapped)

out_pdf.save(OUTPUT_PDF)
