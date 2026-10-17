#!/usr/bin/env python3
"""Rasterise the original manual PDFs at 300 dpi and OCR every page half.

Needs poppler (pdftoppm) and tesseract with English data on PATH.
  workspace/source/manual/pages/z{1,2}s-NN.png      zine spreads (3500 x 2750 px)
  workspace/source/manual/pages/z{1,2}s-NN_{0,1}.png  left / right page half
  workspace/source/manual/pages/epi-N.png           epilogue pages
  workspace/source/manual/ocr/<page>.txt / .tsv     Tesseract text + word boxes (for blocks.py)

Usage: python tools/manual/ocr.py
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main():
    P.PAGES.mkdir(parents=True, exist_ok=True)
    P.OCR.mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        subprocess.run(["pdftoppm", "-r", str(P.DPI), "-png", str(P.ORIG / f"digital_en_{i}.pdf"),
                        str(P.PAGES / f"z{i}s")], check=True)
    subprocess.run(["pdftoppm", "-r", str(P.DPI), "-png", str(P.ORIG / "epilogue_en.pdf"),
                    str(P.PAGES / "epi")], check=True)
    todo = []
    for f in sorted(P.PAGES.glob("z?s-*.png")):
        if "_" in f.stem:
            continue
        im = Image.open(f)
        w, h = im.size
        for k, box in enumerate([(0, 0, w // 2, h), (w // 2, 0, w, h)]):
            half = P.PAGES / f"{f.stem}_{k}.png"
            im.crop(box).save(half)
            todo.append(half)
    todo += sorted(P.PAGES.glob("epi-*.png"))
    for f in todo:
        subprocess.run(["tesseract", str(f), str(P.OCR / f.stem), "-l", "eng", "--psm", "3", "txt", "tsv"],
                       check=True, capture_output=True)
        print("ocr", f.name)
    print(f"done: {len(todo)} pages -> {P.OCR}")


if __name__ == "__main__":
    main()
