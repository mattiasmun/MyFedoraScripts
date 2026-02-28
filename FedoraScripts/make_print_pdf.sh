#!/bin/bash

# Kontrollera att input finns
if [ -z "$1" ]; then
  echo "Användning: $0 input.pdf"
  exit 1
fi

INPUT="$1"
BASENAME=$(basename "$INPUT" .pdf)
ICC="/usr/share/ghostscript/iccprofiles/default_cmyk.icc"
WORKDIR="gs_work_$$"

mkdir "$WORKDIR"

# Hämta antal sidor
PAGES=$(gs -q -dNODISPLAY -c "($INPUT) (r) file runpdfbegin pdfpagecount = quit")
LAST=$PAGES
MIDLAST=$((LAST-1))

echo "Antal sidor: $PAGES"

############################################
# Inställningar
############################################

A5W=419    # A5 width in points
A5H=595    # A5 height in points
SCALE=0.797   # ≈ 15 mm marginal

############################################
# 1. Första sidan – CMYK
############################################

gs -dBATCH -dNOPAUSE -dSAFER \
   -sDEVICE=pdfwrite \
   -dFirstPage=1 -dLastPage=1 \
   -sProcessColorModel=DeviceCMYK \
   -sColorConversionStrategy=CMYK \
   -dBlackText -dBlackVector \
   -dFIXEDMEDIA \
   -dDEVICEWIDTHPOINTS=$A5W \
   -dDEVICEHEIGHTPOINTS=$A5H \
   -c "<</BeginPage {$SCALE $SCALE scale}>> setpagedevice" \
   -o "$WORKDIR/p1.pdf" \
   "$INPUT"

############################################
# 2. Sista sidan – CMYK
############################################

gs -dBATCH -dNOPAUSE -dSAFER \
   -sDEVICE=pdfwrite \
   -dFirstPage=$LAST -dLastPage=$LAST \
   -sProcessColorModel=DeviceCMYK \
   -sColorConversionStrategy=CMYK \
   -dBlackText -dBlackVector \
   -dFIXEDMEDIA \
   -dDEVICEWIDTHPOINTS=$A5W \
   -dDEVICEHEIGHTPOINTS=$A5H \
   -c "<</BeginPage {$SCALE $SCALE scale}>> setpagedevice" \
   -o "$WORKDIR/last.pdf" \
   "$INPUT"

############################################
# 3. Mitten – JBIG2 1-bit
############################################

if [ "$PAGES" -gt 2 ]; then
gs -dBATCH -dNOPAUSE -dSAFER \
   -sDEVICE=pdfwrite \
   -dFirstPage=2 -dLastPage=$MIDLAST \
   -sProcessColorModel=DeviceGray \
   -sColorConversionStrategy=Gray \
   -dMonoImageResolution=300 \
   -dEncodeMonoImages=true \
   -dMonoImageFilter=/JBIG2Encode \
   -dBlackText -dBlackVector \
   -dFIXEDMEDIA \
   -dDEVICEWIDTHPOINTS=$A5W \
   -dDEVICEHEIGHTPOINTS=$A5H \
   -c "<</BeginPage {$SCALE $SCALE scale}>> setpagedevice" \
   -o "$WORKDIR/middle.pdf" \
   "$INPUT"
fi

############################################
# 4. Slå ihop + PDF/A-2B + ICC
############################################

if [ "$PAGES" -gt 2 ]; then
INPUTS="$WORKDIR/p1.pdf $WORKDIR/middle.pdf $WORKDIR/last.pdf"
else
INPUTS="$WORKDIR/p1.pdf $WORKDIR/last.pdf"
fi

gs -dBATCH -dNOPAUSE -dSAFER \
   --permit-file-read="$ICC" \
   -sDEVICE=pdfwrite \
   -dPDFA=2 \
   -dPDFACompatibilityPolicy=1 \
   -dOverrideICC \
   -sOutputICCProfile="$ICC" \
   -sProcessColorModel=DeviceCMYK \
   -sColorConversionStrategy=CMYK \
   -dBlackText -dBlackVector \
   -o "${BASENAME}_A5_PRINT.pdf" \
   $INPUTS

echo "Klar: ${BASENAME}_A5_PRINT.pdf"

rm -rf "$WORKDIR"
