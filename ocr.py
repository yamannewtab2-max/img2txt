#!/usr/bin/env python3
"""Batch OCR: images (and PDFs) -> text. Unlimited, offline, Tesseract.

Usage:
  ocr.py INPUT... [--out DIR] [--lang ara+eng] [--pre] [--psm N] [--pdf]

INPUT: files, folders (non-recursive unless --recursive), globs, or a .zip
       (zip is unpacked to a temp dir first).
Output: DIR/<name>.txt  per input, DIR/combined.txt with page separators,
        DIR/report.txt  word-count/confidence summary.
"""
import argparse, glob, os, re, shutil, subprocess, sys, tempfile, zipfile

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".pnm", ".gif"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def expand(inputs, recursive):
    files = []
    for item in inputs:
        if os.path.isdir(item):
            walk = os.walk(item) if recursive else [(item, [], os.listdir(item))]
            for root, _dirs, names in walk:
                for n in sorted(names):
                    p = os.path.join(root, n)
                    if os.path.splitext(n)[1].lower() in IMG_EXT or n.lower().endswith(".pdf"):
                        files.append(p)
        elif item.lower().endswith(".zip"):
            tmp = tempfile.mkdtemp(prefix="ocr_zip_")
            with zipfile.ZipFile(item) as z:
                z.extractall(tmp)
            files += expand([tmp], True)
        elif os.path.isfile(item):
            files.append(item)
        else:
            files += sorted(glob.glob(item, recursive=recursive))
    # de-dup, keep order
    seen, out = set(), []
    for f in files:
        r = os.path.realpath(f)
        if r not in seen:
            seen.add(r)
            out.append(f)
    return out


def to_images(path, workdir, dpi):
    """Return list of image paths. PDFs are rendered page by page."""
    if path.lower().endswith(".pdf"):
        base = os.path.join(workdir, os.path.splitext(os.path.basename(path))[0])
        run(["pdftoppm", "-r", str(dpi), "-png", path, base])
        return sorted(glob.glob(base + "*.png"))
    return [path]


def preprocess(src, dst):
    """Grayscale, deskew-ish normalize, upscale small scans. Falls back to copy."""
    r = run(["convert", src, "-density", "300", "-colorspace", "Gray",
             "-normalize", "-sharpen", "0x1", "-bordercolor", "white",
             "-border", "10", dst])
    if r.returncode != 0 or not os.path.exists(dst):
        shutil.copy(src, dst)


def ocr_one(img, lang, psm, pre):
    if pre:
        fixed = img + ".pre.png"
        preprocess(img, fixed)
        target = fixed
    else:
        target = img
    r = run(["tesseract", target, "stdout", "-l", lang, "--psm", str(psm),
             "-c", "preserve_interword_spaces=1"])
    if os.path.exists(img + ".pre.png"):
        os.remove(img + ".pre.png")
    return r.stdout if r.returncode == 0 else ""


def clean(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", default="ocr-out")
    ap.add_argument("--lang", default="ara+eng")
    ap.add_argument("--psm", type=int, default=3)
    ap.add_argument("--pre", action="store_true", help="preprocess with ImageMagick")
    ap.add_argument("--dpi", type=int, default=300, help="PDF render dpi")
    ap.add_argument("--recursive", action="store_true")
    a = ap.parse_args()

    for tool in ("tesseract", "convert"):
        if not shutil.which(tool):
            sys.exit(f"missing: {tool}")

    files = expand(a.inputs, a.recursive)
    if not files:
        sys.exit("no input files found")

    os.makedirs(a.out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="ocr_work_")
    combined, report, total_words, failed = [], [], 0, []

    for i, path in enumerate(files, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        chunks = []
        for img in to_images(path, work, a.dpi):
            txt = clean(ocr_one(img, a.lang, a.psm, a.pre))
            if txt:
                chunks.append(txt)
        page = clean("\n\n".join(chunks))
        flag = ""
        if not page:
            failed.append(path)
            flag = "  <-- EMPTY (check image/rotation)"
        words = len(page.split())
        total_words += words
        report.append(f"{words:>7}  {os.path.basename(path)}{flag}")
        # avoid collisions when names repeat across folders
        dest = os.path.join(a.out, name + ".txt")
        n = 2
        while os.path.exists(dest):
            dest = os.path.join(a.out, f"{name}_{n}.txt")
            n += 1
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(page + "\n")
        combined.append(f"===== {i}/{len(files)}  {os.path.basename(path)} =====\n{page}\n")

        print(f"[{i}/{len(files)}] {os.path.basename(path)} -> {words} words", flush=True)

    with open(os.path.join(a.out, "combined.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(combined))
    with open(os.path.join(a.out, "report.txt"), "w", encoding="utf-8") as fh:
        fh.write("words  file\n" + "\n".join(report) +
                 f"\n\nfiles: {len(files)}  words: {total_words}  empty: {len(failed)}\n")
        if failed:
            fh.write("empty files:\n" + "\n".join(failed) + "\n")

    print(f"\ndone: {len(files)} files, {total_words} words -> {a.out}/  "
          f"(combined.txt, report.txt)" + (f", {len(failed)} empty" if failed else ""))


if __name__ == "__main__":
    main()
