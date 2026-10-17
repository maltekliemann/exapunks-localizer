#!/usr/bin/env python3
"""List OCR paragraphs of a zine spread with bounding boxes in spread coordinates.

Usage: python tools/manual/blocks.py z1s-05 [--lines]   (spread)   or   epi-2   (single page)
       --lines lists individual text lines (useful for precise erase boxes around ragged text)
Output per paragraph: [x, y, w, h]  ~xheight/size estimate  text
Boxes come from Tesseract and are a starting point only: verify against the image.
"""
import csv, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402


def paras(tsv, dx, lines=False):
    groups = defaultdict(list)
    with open(tsv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if row["level"] != "5" or not row["text"].strip() or float(row["conf"]) < 0:
                continue
            key = (row["block_num"], row["par_num"]) + ((row["line_num"],) if lines else ())
            groups[key].append(row)
    out = []
    for key, ws in groups.items():
        xs = [int(w["left"]) for w in ws]
        ys = [int(w["top"]) for w in ws]
        x1 = [int(w["left"]) + int(w["width"]) for w in ws]
        y1 = [int(w["top"]) + int(w["height"]) for w in ws]
        hs = sorted(int(w["height"]) for w in ws)
        text = " ".join(w["text"] for w in ws)
        out.append((min(ys), min(xs) + dx, max(x1) - min(xs), max(y1) - min(ys), hs[len(hs) // 2], text))
    return out


def main(sid, lines=False):
    if sid.startswith("epi"):
        parts = [(P.OCR / f"{sid}.tsv", 0)]
    else:
        parts = [(P.OCR / f"{sid}_0.tsv", 0), (P.OCR / f"{sid}_1.tsv", P.HALF)]
    for tsv, dx in parts:
        if not tsv.exists():
            continue
        print(f"--- {tsv.name} (x offset {dx})")
        for y, x, w, h, wh, text in sorted(paras(tsv, dx, lines), key=lambda p: (p[1] >= P.HALF, p[0], p[1])):
            print(f"[{x}, {y}, {w}, {h}]  word-h~{wh}px (font-size ≈{round(wh * 1.25)}px)  {text[:160]}")


if __name__ == "__main__":
    main(sys.argv[1], "--lines" in sys.argv)
