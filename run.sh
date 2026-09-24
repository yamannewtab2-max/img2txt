#!/usr/bin/env bash
# Drop images/PDFs/zips into ~/repos/img2txt/in and run:  bash ~/repos/img2txt/run.sh
set -e
cd "$(dirname "$0")"
IN="${1:-in}"
OUT="${2:-ocr-out}"
echo "OCR: $IN -> $OUT (lang ara+eng, preprocessing on)"
python3 ocr.py "$IN" --out "$OUT" --pre
echo
echo "per-file text: $OUT/*.txt"
echo "one big file : $OUT/combined.txt"
echo "summary      : $OUT/report.txt"
