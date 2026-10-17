#!/usr/bin/env python3
"""Print the translated text of a spread spec (region by region, tags stripped), for review.
Usage: python tools/manual/dumptext.py z1-06 [z1-07 ...]
English source text: workspace/source/manual/ocr/<page>_0.txt / _1.txt (OCR, has errors; the scan
is authoritative).
"""
import html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

for sid in sys.argv[1:]:
    spec = json.loads(P.spec_path(sid).read_text(encoding="utf-8"))
    print(f"##### {sid}  (source {spec['source']})")
    for r in spec["regions"]:
        t = r.get("html") or ""
        t = re.sub(r"<br\s*/?>|</p>", "\n", t)
        t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("­", "")
        if t.strip():
            print(f"[{r.get('id')}] {t.strip()}")
