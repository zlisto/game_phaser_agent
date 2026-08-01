"""PIL helpers for tiles / items / backgrounds (characters use HTML→PNG pipeline)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .models import ArtBundle, ConceptDoc


def _hex(color: str) -> tuple[int, int, int, int]:
    c = color.lstrip("#")
    if len(c) == 6:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return (r, g, b, 255)
    return (255, 255, 255, 255)


def _blank(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _draw_item(draw: ImageDraw.ImageDraw, item_id: str, pal: ArtBundle) -> None:
    dark = _hex(pal.palette.dark)
    key = item_id.lower()
    if "carrot" in key:
        draw.polygon([(32, 12), (22, 48), (42, 48)], fill=_hex(pal.palette.accent), outline=dark)
        draw.ellipse([26, 6, 38, 18], fill=_hex(pal.palette.secondary), outline=dark)
    elif "egg" in key:
        draw.ellipse([18, 14, 46, 52], fill=_hex(pal.palette.light), outline=dark)
        draw.rectangle([18, 28, 46, 34], fill=_hex(pal.palette.secondary))
        draw.ellipse([26, 20, 34, 28], fill=_hex(pal.palette.accent))
    else:
        draw.ellipse([14, 18, 34, 38], fill=_hex(pal.palette.hazard))
        draw.ellipse([30, 18, 50, 38], fill=_hex(pal.palette.hazard))
        draw.polygon([(16, 30), (32, 52), (48, 30)], fill=_hex(pal.palette.hazard))


def _draw_tile(draw: ImageDraw.ImageDraw, tile_id: str, pal: ArtBundle, size: int = 32) -> None:
    dark = _hex(pal.palette.dark)
    key = tile_id.lower()
    if "grass" in key or "ground" in key:
        draw.rectangle([0, 10, size, size], fill=_hex("#8d6e63"), outline=dark)
        draw.rectangle([0, 0, size, 14], fill=_hex(pal.palette.secondary), outline=dark)
    elif "platform" in key or "ledge" in key or "wood" in key:
        draw.rectangle([0, 8, size, 24], fill=_hex("#a1887f"), outline=dark)
        draw.rectangle([0, 8, size, 14], fill=_hex(pal.palette.secondary))
    else:
        draw.rectangle([0, 0, size, size], fill=_hex("#8d6e63"), outline=dark)


def render_world_art(out_assets: Path, art: ArtBundle, concept: ConceptDoc) -> list[str]:
    """Write item/tile/bg sheets. Returns filenames."""
    out_assets.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    cell = 64

    items = art.item_ids[:6] or ["carrot", "easter_egg", "heart"]
    img = _blank(cell * len(items), cell)
    for i, item_id in enumerate(items):
        cell_img = _blank(cell, cell)
        d = ImageDraw.Draw(cell_img)
        _draw_item(d, item_id, art)
        img.paste(cell_img, (i * cell, 0), cell_img)
    img.save(out_assets / "items_sheet.png")
    written.append("items_sheet.png")

    tiles = art.tile_ids[:4] or ["grass", "dirt", "platform"]
    tsize = 32
    img = _blank(tsize * len(tiles), tsize)
    for i, tid in enumerate(tiles):
        cell_img = _blank(tsize, tsize)
        d = ImageDraw.Draw(cell_img)
        _draw_tile(d, tid, art, tsize)
        img.paste(cell_img, (i * tsize, 0), cell_img)
    img.save(out_assets / "tileset_sheet.png")
    written.append("tileset_sheet.png")

    bg = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    top = _hex(art.palette.light)
    bot = _hex(art.palette.secondary)
    for y in range(180):
        t = y / 179
        col = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)) + (255,)
        bd.line([(0, y), (319, y)], fill=col)
    bd.ellipse([-40, 110, 160, 220], fill=_hex(art.palette.secondary))
    bd.ellipse([120, 120, 360, 230], fill=_hex(art.palette.primary))
    bg.save(out_assets / "bg_sheet.png")
    written.append("bg_sheet.png")

    (out_assets / "ART_NOTES.txt").write_text(
        f"Style: {art.style_notes}\nConcept style: {concept.style}\n"
        f"Characters use HTML→screenshot pipeline in art_work/\n",
        encoding="utf-8",
    )
    written.append("ART_NOTES.txt")
    return written


def write_layout_preview(out_dir: Path, levels_doc) -> str:
    blocks = []
    color = {
        "#": "#6d4c41",
        "=": "#a1887f",
        ".": "#e8f5e9",
        "S": "#42a5f5",
        "X": "#ab47bc",
        "C": "#ff7043",
        "G": "#fff59d",
        "N": "#66bb6a",
    }
    for level in levels_doc.levels:
        rows_html = []
        for row in level.rows:
            cells = "".join(
                f'<span style="background:{color.get(ch, "#ccc")}">{ch}</span>' for ch in row
            )
            rows_html.append(f'<div class="row">{cells}</div>')
        blocks.append(
            f"<section><h2>{level.name} ({level.id})</h2>"
            f'<div class="map">{" ".join(rows_html)}</div>'
            f"<p>{level.notes}</p></section>"
        )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Layout preview</title>
<style>
body {{ font-family: ui-monospace, Consolas, monospace; background:#1e1e2e; color:#eee; padding:1rem; }}
.map .row {{ line-height: 1; letter-spacing: 0; }}
.map span {{ display:inline-block; width:14px; height:14px; font-size:10px; text-align:center; color:#111; }}
section {{ margin-bottom: 2rem; }}
</style></head><body>
<h1>Level layout preview</h1>
<p>Blueprint only — not final art. # wall · = platform · S spawn · X exit · C carrot · G egg · N snake</p>
{"".join(blocks)}
</body></html>
"""
    path = out_dir / "layout_preview.html"
    path.write_text(html, encoding="utf-8")
    return "layout_preview.html"
