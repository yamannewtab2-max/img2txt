# Image → Text (OCR)

Turn images and scans into text. Two ways, both unlimited and free.

## 1. Web app (no install)

Single-file, runs fully in the browser (WASM Tesseract) — **your files are never uploaded to a server**.
Open `index.html`, choose images, pick a language, hit Start. Copy text per page or download everything as one `.txt`.

- Multi-file / drag & drop, progress bar, word count + confidence per page.
- Languages: Arabic+English, Arabic, English/Indonesian.
- Engine + language data are fetched once from a CDN (~10–30 MB for Arabic), then cached.

## 2. CLI (batch, offline)

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng imagemagick poppler-utils
python3 ocr.py INPUT... --out out --pre          # files, folders, globs, .pdf, .zip
bash run.sh                                      # shorthand: OCR everything in ./in
```

Output: `out/<name>.txt` per input, `out/combined.txt` (page-separated), `out/report.txt` (word counts + empty-page flags).

| Use | Best choice |
| --- | --- |
| 250 images, offline, zero cost | CLI (`--pre` for phone photos) |
| Phone / share a link | Web app |
| Handwritten pages | Neither — use a vision model (Gemini free tier) |

Tesseract is strong on **printed** text (Arabic + English verified) and cannot read handwriting.

## Notes

- `--pre` adds grayscale + normalize + sharpen + white border — needed for real scans, skip for screenshots.
- Empty output page = rotated or blank scan: `convert page.png -rotate 180 out.png` and re-run that file.
- PDFs are rasterised at 300 dpi before OCR (`--dpi` to change).
