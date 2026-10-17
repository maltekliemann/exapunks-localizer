"""Paths for the manual pipeline (all inside the git-ignored workspace, see tools/common.py).

  original PDFs   workspace/backup/Content/manual/*.pdf
  page images     workspace/source/manual/pages/   (300 dpi; zine spreads z1s-NN.png, epilogue epi-N.png)
  OCR             workspace/source/manual/ocr/     (Tesseract .txt + .tsv per page half)
  specs           workspace/<lang>/manual/spec/<id>.json   (your translation: one per spread)
  render output   workspace/build/manual/work/<id>.pdf|.png|-compare.png|-zoom.png
  final PDFs      workspace/build/manual/*.pdf     (same file names as the game's Content/manual/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ORIG = common.backup() / "Content/manual"
SRC = common.source() / "manual"
PAGES = SRC / "pages"
OCR = SRC / "ocr"
SPEC = common.tr() / "manual/spec"
OUT = common.build() / "manual"
WORK = OUT / "work"
FONTS = common.WS / "fonts/manual/static"
DPI = 300
HALF = 1750  # x offset of the right page half in a 300 dpi zine spread (spread width 3500 px)


def spec_path(sid):
    return SPEC / f"{sid}.json"


def source_image(spec):
    """Spec "source" is relative to the source/manual dir, e.g. "pages/z1s-05.png"."""
    return SRC / spec["source"]
