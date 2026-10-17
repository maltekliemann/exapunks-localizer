"""Shared paths and settings. Everything user-specific lives in the git-ignored workspace/.

workspace/
  config.json      written by tools/setup.py: game dir, language, config.cfg path
  backup/          untouched copies: Content/, PackedContent/, EXAPUNKS.exe, config.cfg
  source/          extracted English material for translators (never commit, never share)
  <lang>/          your translations + glossary + notes (e.g. workspace/de/)
  build/           generated game files
  bin/             compiled helpers (Patch.exe, Mono.Cecil.dll, …)
"""
import json
import os
import sys
from pathlib import Path

# Tool output contains non-ASCII (‗, umlauts…); Windows pipes default to a legacy code page.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Every tool imports this module first: answer -h/--help with the tool's docstring before it
# reads the workspace, downloads anything or touches files.
if any(a in ("-h", "--help") for a in sys.argv[1:]):
    _doc = getattr(sys.modules.get("__main__"), "__doc__", None)
    print((_doc or "No help available.").strip())
    raise SystemExit(0)

REPO = Path(__file__).resolve().parents[1]
WS = Path(os.environ.get("EXALOC_WORKSPACE") or REPO / "workspace").expanduser().resolve()

# Language enum in the game: Pseudo=0, English=1, German=2, French=3, Russian=4, Chinese=5, Japanese=6.
# strings.csv columns: 0 English key, 1 context, 2 German, 3 French, 4 Russian, 5 Chinese, 6 Japanese.
LANGS = {"de": ("German", 2), "fr": ("French", 3), "ru": ("Russian", 4), "zh": ("Chinese", 5), "ja": ("Japanese", 6)}


def config():
    p = WS / "config.json"
    if not p.exists():
        raise SystemExit("No workspace/config.json. Run: .venv/bin/python tools/setup.py --game <path> --lang <code>")
    return json.loads(p.read_text(encoding="utf-8"))


def game():
    """Directory that contains EXAPUNKS.exe, Content/ and PackedContent/."""
    return Path(config()["game"])


def lang():
    return config()["lang"]


def lang_name():
    return LANGS[lang()][0]


def lang_column():
    return LANGS[lang()][1]


def backup():
    return WS / "backup"


def source():
    return WS / "source"


def tr():
    """Translation directory for the configured language, e.g. workspace/de/."""
    return WS / lang()


def build():
    return WS / "build"


def bin_dir():
    return WS / "bin"
