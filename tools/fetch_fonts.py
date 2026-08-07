"""Download the web fonts, subset them, and emit a self-hosted stylesheet.

Self-hosting keeps the page free of third-party requests, and subsetting to the
characters the site actually uses cuts the payload by roughly 90%. Re-run this
only when the font selection changes.

Usage: python3 tools/fetch_fonts.py
"""

import io
import re
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
CSS_OUT = FONT_DIR / "fonts.css"

# A browser UA is required or the API returns legacy truetype instead of woff2.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

SOURCE = (
    "https://fonts.googleapis.com/css2"
    "?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400"
    "&family=Inter:wght@400..600"
    "&family=IBM+Plex+Mono:wght@500"
    "&display=swap"
)

# Only the base Latin subset; the site has no text needing the extended ranges.
LATIN = "U+0000-00FF"

# Printable ASCII plus the non-ASCII characters the page relies on: umlauts and
# accents in author names, the superscript two in VILA², arrows, and dashes.
CHARSET = "".join(chr(code) for code in range(0x20, 0x7F)) + "äöüåéèêáíóúñçø²·–—’‘“”↗×°"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request) as response:
        return response.read()


def pin_axes(font, keep_weight):
    """Drop every variation axis except weight.

    These are variable fonts whose optical-size axis carries a large share of
    the file. The site uses one optical size, so pinning it is free visually.
    """
    if "fvar" not in font:
        return font
    pins = {
        axis.axisTag: axis.defaultValue
        for axis in font["fvar"].axes
        if not (axis.axisTag == "wght" and keep_weight)
    }
    if not pins:
        return font
    return instancer.instantiateVariableFont(font, pins, updateFontNames=False)


def subset_font(raw, keep_weight=True):
    """Cut the font down to CHARSET and flatten unused variation axes.

    Subsetting has to run before instancing; the reverse order trips over
    glyph variations that instancing leaves behind.
    """
    font = TTFont(io.BytesIO(raw))
    subsetter = subset.Subsetter(
        options=subset.Options(
            layout_features=["kern", "liga", "calt"],
            drop_tables=["DSIG"],
            notdef_outline=True,
            recalc_bounds=True,
        )
    )
    subsetter.populate(text=CHARSET)
    subsetter.subset(font)
    font = pin_axes(font, keep_weight)
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer)
    return buffer.getvalue()


def main():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    css = fetch(SOURCE).decode()

    blocks = re.findall(r"@font-face\s*\{[^}]*\}", css)
    rules, seen, total = [], {}, 0

    for block in blocks:
        if LATIN not in block:
            continue
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        style = re.search(r"font-style:\s*([^;]+);", block).group(1).strip()
        weight = re.search(r"font-weight:\s*([^;]+);", block).group(1).strip()

        if url not in seen:
            name = f"{family}-{style}".lower().replace(" ", "-") + ".woff2"
            raw = fetch(url)
            trimmed = subset_font(raw, keep_weight=style == "normal")
            (FONT_DIR / name).write_bytes(trimmed)
            seen[url] = name
            total += len(trimmed)
            print(
                f"{name:<28} {len(raw) / 1024:>6,.0f} KB -> {len(trimmed) / 1024:>5,.0f} KB"
            )

        rules.append(
            "@font-face {\n"
            f"  font-family: '{family}';\n"
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            f"  src: url('{seen[url]}') format('woff2');\n"
            "}"
        )

    CSS_OUT.write_text("\n".join(rules) + "\n")
    print(f"\n{len(rules)} @font-face rules, {total / 1024:.0f} KB of woff2")


if __name__ == "__main__":
    main()
