#!/usr/bin/env python3
"""A `design/icons/anthropicons.json` előállítása: a Claude app ikonkészlete (Anthropicons)
SVG-útként, a lap 16-os rácsán.

Kézzel futtatandó, ha a készletet frissíteni kell. A forrás a Claude app saját fájljai: az
ikonfont (`anthropicons-variable.woff2`) és a CDS-bundle (`vendor-ant-cds-*.js` vagy
`shared-frame-*.js`) névtáblája (`{icons:{Activity:57344,…}}`). Mindkettő a claude.ai
oldalról jön, az app a gyorsítótárában tartja; a kibontott fájlok útját kell megadni:

    uv run --no-project --with fonttools==4.60.1 --with brotli==1.1.0 \\
        python scripts/anthropicons.py <font.woff2> <bundle.js>

Két méret: `icons` az app 16 px-es ikonja (`sm`: `opsz` 16, `wght` 533,3), `icons_xs` a 12 px-es
(`xs`: `opsz` 12, `wght` 577,8) — az Icon komponens a méret vonalvastagságából ennyit számol. Mindkét
készlet a 16-os rácson (az em-doboz 16 egység); a 12 px-es a lapon 12 px-esre rajzolandó. Az út
kitöltött kontúr, nem vonal: a lapon `stroke="none"`-nal kell rajzolni.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUT = Path(__file__).resolve().parent.parent / "design" / "icons" / "anthropicons.json"
SIZES = {"icons": (533.3, 16), "icons_xs": (577.8, 12)}   # (wght, opsz): az Icon `sm` és `xs` mérete


def names(bundle: str) -> dict[str, int]:
    """A legbővebb ikonnév-tábla a bundle-ből."""
    tables = [dict(re.findall(r"(\w+):(\d+)", m.group(1)))
              for m in re.finditer(r"\{icons:\{([^}]*)\}", Path(bundle).read_text(errors="replace"))]
    best = max(tables, key=len)
    return {k: int(v) for k, v in best.items()}


def num(v: float) -> str:
    """Két tizedes, felesleges nullák nélkül; a `-0` is `0`."""
    return f"{v:.2f}".rstrip("0").rstrip(".") if round(v, 2) else "0"


def main() -> None:
    font_path, bundle = sys.argv[1], sys.argv[2]
    table = names(bundle)
    sets = {}
    for key, (wght, opsz) in SIZES.items():
        font = TTFont(font_path)
        axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
        font = instantiateVariableFont(font, {**axes, "wght": wght, "opsz": opsz})
        glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
        upm = font["head"].unitsPerEm
        icons = {}
        for name, cp in sorted(table.items()):
            if cp not in cmap:
                continue
            pen = SVGPathPen(glyphs, ntos=num)
            # font-egység → 16-os rács, az y tengely lefelé (az em-doboz teteje a 0)
            glyphs[cmap[cp]].draw(TransformPen(pen, (16 / upm, 0, 0, -16 / upm, 0, 16 * font["hhea"].ascent / upm)))
            icons[name] = pen.getCommands()
        sets[key] = icons
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": "Claude app, Anthropicons (anthropicons-variable.woff2)",
                               "sizes": {k: {"wght": w, "opsz": o, "px": o} for k, (w, o) in SIZES.items()},
                               "viewBox": "0 0 16 16", **sets}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(sets['icons'])} ikon, két méretben → {OUT}")


if __name__ == "__main__":
    main()
