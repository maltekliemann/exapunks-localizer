"""Download the open-licensed (SIL OFL) fonts used to redraw WorkHouse textures and create the
static instances Pillow needs. Fonts go to workspace/fonts/workhouse/ (not committed)."""
import urllib.request

import common

# pinned google/fonts commit, so upstream renames can't break downloads
GOOGLE_FONTS_COMMIT = "9710da1eacb3be272583c3224dcb70f9da6eadbb"
BASE = f"https://raw.githubusercontent.com/google/fonts/{GOOGLE_FONTS_COMMIT}/ofl/"
SOURCES = {
    "Roboto.ttf": "roboto/Roboto%5Bwdth,wght%5D.ttf",
    "Roboto-Italic.ttf": "roboto/Roboto-Italic%5Bwdth,wght%5D.ttf",
    "RobotoCondensed.ttf": "robotocondensed/RobotoCondensed%5Bwght%5D.ttf",
    "BigShouldersDisplay.ttf": "bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf",
    "Kalam-Bold.ttf": "kalam/Kalam-Bold.ttf",
}
# instance name -> (variable source, axes). R = Roboto, RC = Roboto Condensed, RI = Roboto Italic,
# RCI = Roboto Italic at width 75 (condensed italic), BSD = Big Shoulders Display (engraved buttons)
INSTANCES = {
    "R-400": ("Roboto.ttf", {"wght": 400, "wdth": 100}), "R-700": ("Roboto.ttf", {"wght": 700, "wdth": 100}),
    "RC-400": ("RobotoCondensed.ttf", {"wght": 400}), "RC-700": ("RobotoCondensed.ttf", {"wght": 700}),
    "RI-400": ("Roboto-Italic.ttf", {"wght": 400, "wdth": 100}),
    "RCI-400": ("Roboto-Italic.ttf", {"wght": 400, "wdth": 75}),
    "RCI-700": ("Roboto-Italic.ttf", {"wght": 700, "wdth": 75}),
    "BSD-300": ("BigShouldersDisplay.ttf", {"wght": 300}),
}


def font_dir():
    d = common.WS / "fonts/workhouse"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure():
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    d = font_dir()
    for name, url in SOURCES.items():
        if not (d / name).exists():
            print("downloading", name)
            urllib.request.urlretrieve(BASE + url, d / name)
    for name, (src, axes) in INSTANCES.items():
        out = d / f"{name}.ttf"
        if not out.exists():
            f = TTFont(d / src)
            instantiateVariableFont(f, axes, inplace=True)
            f.save(out)
    return d


if __name__ == "__main__":
    print("fonts in", ensure())
