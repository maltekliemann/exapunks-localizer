#!/usr/bin/env python3
"""Download the open-licence fonts the manual renderer uses and make static instances.

MuPDF (the PDF typesetter used by render.py) cannot use variable fonts, so every weight/style a
spec may ask for is instantiated into its own static .ttf in workspace/fonts/manual/static/.
Sources: the google/fonts repository (OFL / Apache 2.0). Nothing is committed to this repo.

Usage: python tools/manual/fonts.py            (skips files that already exist)
"""
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

# pinned google/fonts commit, so upstream renames can't break downloads
GOOGLE_FONTS_COMMIT = "9710da1eacb3be272583c3224dcb70f9da6eadbb"
BASE = f"https://raw.githubusercontent.com/google/fonts/{GOOGLE_FONTS_COMMIT}/"
DL = common.WS / "fonts/manual"
STATIC = DL / "static"

# source key -> path in google/fonts
SOURCES = {
    "Anton": "ofl/anton/Anton-Regular.ttf",
    "Archivo": "ofl/archivo/Archivo[wdth,wght].ttf",
    "ArchivoBlack": "ofl/archivoblack/ArchivoBlack-Regular.ttf",
    "Audiowide": "ofl/audiowide/Audiowide-Regular.ttf",
    "BebasNeue": "ofl/bebasneue/BebasNeue-Regular.ttf",
    "Caveat": "ofl/caveat/Caveat[wght].ttf",
    "Cinzel": "ofl/cinzel/Cinzel[wght].ttf",
    "CourierPrime-Regular": "ofl/courierprime/CourierPrime-Regular.ttf",
    "CourierPrime-Bold": "ofl/courierprime/CourierPrime-Bold.ttf",
    "CrimsonPro": "ofl/crimsonpro/CrimsonPro[wght].ttf",
    "CrimsonPro-Italic": "ofl/crimsonpro/CrimsonPro-Italic[wght].ttf",
    "Dosis": "ofl/dosis/Dosis[wght].ttf",
    "Doto": "ofl/doto/Doto[ROND,wght].ttf",
    "EBGaramond": "ofl/ebgaramond/EBGaramond[wght].ttf",
    "EBGaramond-Italic": "ofl/ebgaramond/EBGaramond-Italic[wght].ttf",
    "LibreBaskerville": "ofl/librebaskerville/LibreBaskerville[wght].ttf",
    "LibreBaskerville-Italic": "ofl/librebaskerville/LibreBaskerville-Italic[wght].ttf",
    "Michroma": "ofl/michroma/Michroma-Regular.ttf",
    "Montserrat": "ofl/montserrat/Montserrat[wght].ttf",
    "NotoSansMono": "ofl/notosansmono/NotoSansMono[wdth,wght].ttf",
    "Orbitron": "ofl/orbitron/Orbitron[wght].ttf",
    "Oswald": "ofl/oswald/Oswald[wght].ttf",
    "PermanentMarker": "apache/permanentmarker/PermanentMarker-Regular.ttf",
    "PixelifySans": "ofl/pixelifysans/PixelifySans[wght].ttf",
    "Roboto": "ofl/roboto/Roboto[wdth,wght].ttf",
    "Roboto-Italic": "ofl/roboto/Roboto-Italic[wdth,wght].ttf",
    "RobotoCondensed": "ofl/robotocondensed/RobotoCondensed[wght].ttf",
    "RubikMonoOne": "ofl/rubikmonoone/RubikMonoOne-Regular.ttf",
    "ShareTechMono": "ofl/sharetechmono/ShareTechMono-Regular.ttf",
    "Silkscreen": "ofl/silkscreen/Silkscreen-Regular.ttf",
    "SpecialElite": "apache/specialelite/SpecialElite-Regular.ttf",
    "VT323": "ofl/vt323/VT323-Regular.ttf",
}

# static file name -> (source key, axis values or None for a plain copy)
STATICS = {
    "Anton-Regular.ttf": ("Anton", None),
    "ArchivoBlack-Regular.ttf": ("ArchivoBlack", None),
    "Audiowide-Regular.ttf": ("Audiowide", None),
    "BebasNeue-Regular.ttf": ("BebasNeue", None),
    "CourierPrime-Regular.ttf": ("CourierPrime-Regular", None),
    "CourierPrime-Bold.ttf": ("CourierPrime-Bold", None),
    "Michroma-Regular.ttf": ("Michroma", None),
    "PermanentMarker-Regular.ttf": ("PermanentMarker", None),
    "RubikMonoOne-Regular.ttf": ("RubikMonoOne", None),
    "ShareTechMono-Regular.ttf": ("ShareTechMono", None),
    "Silkscreen-Regular.ttf": ("Silkscreen", None),
    "SpecialElite-Regular.ttf": ("SpecialElite", None),
    "VT323-Regular.ttf": ("VT323", None),
    "DotoRound-900.ttf": ("Doto", {"ROND": 100, "wght": 900}),
}


def _add(prefix, src, weights, italic_src=None, extra=None):
    for w in weights:
        STATICS[f"{prefix}-{w}.ttf"] = (src, {"wght": w, **(extra or {})})
        if italic_src:
            STATICS[f"{prefix}-{w}i.ttf"] = (italic_src, {"wght": w, **(extra or {})})


_add("Archivo", "Archivo", [300, 400, 700, 900], extra={"wdth": 100})
_add("Caveat", "Caveat", [400, 700])
_add("Cinzel", "Cinzel", [400, 700, 900])
_add("CrimsonPro", "CrimsonPro", [300, 400, 700, 900], "CrimsonPro-Italic")
_add("Dosis", "Dosis", [300, 400, 700])
_add("EBGaramond", "EBGaramond", [400, 700], "EBGaramond-Italic")
_add("LibreBaskerville", "LibreBaskerville", [400, 700], "LibreBaskerville-Italic")
_add("Montserrat", "Montserrat", [300, 400, 700, 900])
_add("NotoSansMono", "NotoSansMono", [300, 400, 700, 900], extra={"wdth": 100})
_add("Orbitron", "Orbitron", [400, 700, 900])
_add("Oswald", "Oswald", [300, 400, 700])
_add("PixelifySans", "PixelifySans", [400, 700])
_add("Roboto", "Roboto", [300, 400, 700, 900], "Roboto-Italic", extra={"wdth": 100})
_add("RobotoCondensed", "RobotoCondensed", [300, 400, 700, 900])


def download(key):
    path = SOURCES[key]
    dst = DL / Path(path).name
    if not dst.exists():
        url = BASE + urllib.parse.quote(path)
        print("download", path)
        with urllib.request.urlopen(url) as r:
            dst.write_bytes(r.read())
    return dst


def main():
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    STATIC.mkdir(parents=True, exist_ok=True)
    made = 0
    for name, (key, axes) in STATICS.items():
        out = STATIC / name
        if out.exists():
            continue
        src = download(key)
        f = TTFont(src)
        if axes:
            have = {a.axisTag for a in f["fvar"].axes}
            instantiateVariableFont(f, {k: v for k, v in axes.items() if k in have}, inplace=True)
        f.save(out)
        made += 1
    print(f"fonts ready in {STATIC} ({len(STATICS)} files, {made} new)")


if __name__ == "__main__":
    main()
