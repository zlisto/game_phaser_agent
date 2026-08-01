"""HTML pose → screenshot → critic → spritesheet pipeline.

Consistency rule: lock one base HTML per character, then pose by editing that HTML
(same approach as rabbit_idle.html → rabbit_left/right/…).
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

from .agents import (
    critique_sprite,
    generate_base_html_sprite,
    pose_html_from_locked_base,
    revise_html_sprite,
)
from .models import ArtBundle, ConceptDoc, CriticFeedback, SpriteSpec
from .render_art import render_world_art

CELL = 256
GAME_CELL = 64


def _wrap_stage(inner_svg_or_body: str, title: str) -> str:
    """Ensure HTML has a fixed transparent #stage for screenshots."""
    html = inner_svg_or_body.strip()
    lower = html.lower()

    if "<html" in lower:
        if 'id="stage"' not in lower and "id='stage'" not in lower:
            m = re.search(r"<body[^>]*>(.*)</body>", html, flags=re.I | re.S)
            if m:
                inner = m.group(1).strip()
                html = re.sub(
                    r"<body[^>]*>.*</body>",
                    f'<body>\n<div class="stage" id="stage">\n{inner}\n</div>\n</body>',
                    html,
                    count=1,
                    flags=re.I | re.S,
                )
        if ".stage" not in html:
            html = html.replace(
                "</head>",
                f"""<style>
html,body{{margin:0;width:100%;height:100%;background:transparent!important;overflow:hidden}}
.stage{{width:{CELL}px;height:{CELL}px;position:relative;margin:0 auto;background:transparent}}
.stage svg{{width:100%;height:100%;display:block;overflow:visible}}
</style>
</head>""",
                1,
            )
        return html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>{title}</title>
<style>
  html,body{{margin:0;width:100%;height:100%;background:transparent;overflow:hidden}}
  .stage{{width:{CELL}px;height:{CELL}px;position:relative;margin:0 auto;background:transparent}}
  .stage svg{{width:100%;height:100%;display:block;overflow:visible}}
</style>
</head>
<body>
<div class="stage" id="stage">
{html}
</div>
</body>
</html>
"""


async def screenshot_html(html_path: Path, png_path: Path, size: int = CELL) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    url = html_path.resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": size, "height": size},
            device_scale_factor=1,
        )
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(150)
        stage = page.locator("#stage")
        if await stage.count() == 0:
            await page.screenshot(path=str(png_path), omit_background=True)
        else:
            await stage.screenshot(path=str(png_path), omit_background=True)
        await browser.close()


def combine_character_sheet(
    frame_paths: list[Path],
    out_path: Path,
    cell: int = GAME_CELL,
) -> None:
    if not frame_paths:
        return
    sheet = Image.new("RGBA", (cell * len(frame_paths), cell), (0, 0, 0, 0))
    for i, fp in enumerate(frame_paths):
        im = Image.open(fp).convert("RGBA")
        im = im.resize((cell, cell), Image.Resampling.LANCZOS)
        sheet.paste(im, (i * cell, 0), im)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _pick_base_spec(specs: list[SpriteSpec]) -> SpriteSpec:
    """Prefer idle facing right/front as the locked master."""
    for prefer in (
        lambda s: s.action == "idle" and s.facing == "right",
        lambda s: s.action == "idle" and s.facing == "front",
        lambda s: s.action == "idle" and s.facing == "down",
        lambda s: s.action == "idle",
    ):
        for s in specs:
            if prefer(s):
                return s
    return specs[0]


async def _critic_loop(
    spec: SpriteSpec,
    html: str,
    html_path: Path,
    png_path: Path,
    concept: ConceptDoc,
    art: ArtBundle,
    work_dir: Path,
    critic_rounds: int,
    locked_base_html: str | None = None,
) -> tuple[str, list[dict]]:
    critiques: list[dict] = []
    for round_i in range(max(0, critic_rounds)):
        feedback: CriticFeedback = await critique_sprite(spec, png_path)
        critiques.append({"round": round_i + 1, **feedback.model_dump()})
        (work_dir / "critiques" / f"{spec.id}_r{round_i + 1}.json").write_text(
            feedback.model_dump_json(indent=2), encoding="utf-8"
        )
        if feedback.ok:
            break
        revised = await revise_html_sprite(
            spec,
            html,
            feedback,
            concept,
            art,
            locked_base_html=locked_base_html,
        )
        html = _wrap_stage(revised.html, spec.id)
        html_path.write_text(html, encoding="utf-8")
        await screenshot_html(html_path, png_path)
    return html, critiques


async def build_base_character(
    spec: SpriteSpec,
    concept: ConceptDoc,
    art: ArtBundle,
    work_dir: Path,
    critic_rounds: int = 1,
) -> tuple[str, Path, list[dict]]:
    """Lock master HTML for one character_id."""
    html_dir = work_dir / "html"
    png_dir = work_dir / "png"
    html_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "critiques").mkdir(parents=True, exist_ok=True)

    base_path = html_dir / f"{spec.character_id}_base.html"
    html_path = html_dir / f"{spec.id}.html"
    png_path = png_dir / f"{spec.id}.png"

    print(f"      BASE lock {spec.character_id} via {spec.id}...")
    html_out = await generate_base_html_sprite(spec, concept, art)
    html = _wrap_stage(html_out.html, spec.id)
    html_path.write_text(html, encoding="utf-8")
    await screenshot_html(html_path, png_path)

    html, critiques = await _critic_loop(
        spec, html, html_path, png_path, concept, art, work_dir, critic_rounds
    )
    base_path.write_text(html, encoding="utf-8")
    print(f"      BASE locked -> {base_path.name}")
    return html, png_path, critiques


async def build_pose_from_base(
    spec: SpriteSpec,
    locked_base_html: str,
    concept: ConceptDoc,
    art: ArtBundle,
    work_dir: Path,
    critic_rounds: int = 1,
) -> tuple[Path, list[dict]]:
    """Pose by editing locked base HTML (not redrawing)."""
    html_dir = work_dir / "html"
    png_dir = work_dir / "png"
    html_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "critiques").mkdir(parents=True, exist_ok=True)

    html_path = html_dir / f"{spec.id}.html"
    png_path = png_dir / f"{spec.id}.png"

    print(f"      pose from base {spec.id} ({spec.action}, {spec.facing})...")
    html_out = await pose_html_from_locked_base(spec, locked_base_html, concept, art)
    html = _wrap_stage(html_out.html, spec.id)
    html_path.write_text(html, encoding="utf-8")
    await screenshot_html(html_path, png_path)

    html, critiques = await _critic_loop(
        spec,
        html,
        html_path,
        png_path,
        concept,
        art,
        work_dir,
        critic_rounds,
        locked_base_html=locked_base_html,
    )
    return png_path, critiques


def _alias_phaser_sheets(assets: Path, frame_map: dict, sheets_written: list[str]) -> None:
    ids = list(frame_map.keys())
    player_id = "player" if "player" in frame_map else (ids[0] if ids else None)
    if player_id:
        src = assets / f"{player_id}_sheet.png"
        dst = assets / "player_sheet.png"
        if src.exists() and player_id != "player":
            Image.open(src).save(dst)
            if "player_sheet.png" not in sheets_written:
                sheets_written.append("player_sheet.png")
        elif player_id == "player" and src.exists() and "player_sheet.png" not in sheets_written:
            sheets_written.append("player_sheet.png")

    enemy_ids = [cid for cid in ids if cid != player_id]
    if enemy_ids:
        src = assets / f"{enemy_ids[0]}_sheet.png"
        if src.exists():
            Image.open(src).save(assets / "snake_sheet.png")
            if "snake_sheet.png" not in sheets_written:
                sheets_written.append("snake_sheet.png")


async def run_character_art_pipeline(
    out_dir: Path,
    concept: ConceptDoc,
    art: ArtBundle,
    critic_rounds: int = 1,
) -> dict:
    """
    Per character_id:
      1) Lock base HTML (critic loop)
      2) Pose all other frames FROM that locked HTML (parallel)
      3) Combine screenshots into a sheet
    """
    work = out_dir / "art_work"
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    sprites = art.sprites[:16]
    if len(art.sprites) > 16:
        print(f"      note: capping sprites {len(art.sprites)} -> 16")

    # Preserve brief order, group by character
    by_character: dict[str, list[SpriteSpec]] = {}
    character_order: list[str] = []
    for s in sprites:
        if s.character_id not in by_character:
            character_order.append(s.character_id)
            by_character[s.character_id] = []
        by_character[s.character_id].append(s)

    frame_map: dict[str, dict] = {}
    all_critiques: dict[str, list] = {}
    sheet_pairs: dict[str, list[tuple[SpriteSpec, Path]]] = {}
    sheets_written: list[str] = []

    for character_id in character_order:
        specs = by_character[character_id]
        base_spec = _pick_base_spec(specs)

        locked_html, base_png, base_critiques = await build_base_character(
            base_spec, concept, art, work, critic_rounds=critic_rounds
        )
        all_critiques[base_spec.id] = base_critiques
        (work / "html" / f"{character_id}_base.html").write_text(locked_html, encoding="utf-8")

        other = [s for s in specs if s.id != base_spec.id]

        async def _one(spec: SpriteSpec) -> tuple[SpriteSpec, Path, list[dict]]:
            png, critiques = await build_pose_from_base(
                spec, locked_html, concept, art, work, critic_rounds=critic_rounds
            )
            return spec, png, critiques

        # Pose fan-out in parallel (like the lecture slide)
        results = await asyncio.gather(*[_one(s) for s in other]) if other else []

        # Keep original brief order for sheet cells
        path_by_id = {base_spec.id: base_png}
        for spec, png, critiques in results:
            path_by_id[spec.id] = png
            all_critiques[spec.id] = critiques

        ordered_pairs: list[tuple[SpriteSpec, Path]] = []
        for s in specs:
            if s.id in path_by_id:
                ordered_pairs.append((s, path_by_id[s.id]))
        sheet_pairs[character_id] = ordered_pairs

        paths = [p for _, p in ordered_pairs]
        ids = [s.id for s, _ in ordered_pairs]
        sheet_name = f"{character_id}_sheet.png"
        combine_character_sheet(paths, assets / sheet_name, cell=GAME_CELL)
        frame_map[character_id] = {
            "sheet": f"assets/{sheet_name}",
            "frame_width": GAME_CELL,
            "frame_height": GAME_CELL,
            "base_html": f"art_work/html/{character_id}_base.html",
            "frames": [
                {
                    "index": i,
                    "id": sid,
                    "action": ordered_pairs[i][0].action,
                    "facing": ordered_pairs[i][0].facing,
                }
                for i, sid in enumerate(ids)
            ],
        }
        sheets_written.append(sheet_name)
        print(f"      sheet -> assets/{sheet_name} ({len(ids)} frames, base-locked)")

    _alias_phaser_sheets(assets, frame_map, sheets_written)
    if "player" not in frame_map and frame_map:
        first = next(iter(frame_map))
        frame_map["player"] = frame_map[first]

    world_files = render_world_art(assets, art, concept)

    (out_dir / "data").mkdir(exist_ok=True)
    (out_dir / "data" / "art.json").write_text(art.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "data" / "frame_map.json").write_text(
        json.dumps(frame_map, indent=2), encoding="utf-8"
    )
    (out_dir / "data" / "art_critiques.json").write_text(
        json.dumps(all_critiques, indent=2), encoding="utf-8"
    )

    return {
        "sheets": sheets_written,
        "world_files": world_files,
        "frame_map": frame_map,
        "work_dir": str(work),
    }
