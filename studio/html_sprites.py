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


# Phaser BootScene always loads assets/snake_sheet.png — never skip enemy art entirely.
_SPRITE_CAP = 16
_ACTION_PRIORITY = {
    "idle": 0,
    "run": 1,
    "move": 1,
    "slither": 1,
    "jump": 2,
    "punch": 3,
    "hurt": 4,
    "wall_jump": 5,
    "wall_slide": 6,
    "stomp": 7,
    "strike": 8,
    "defeated": 9,
    "stomp_bounce": 10,
    "lose": 11,
    "win": 12,
}


def _sprite_action_rank(spec: SpriteSpec) -> tuple:
    act = (spec.action or "").lower()
    pri = _ACTION_PRIORITY.get(act, 50)
    face = 0 if (spec.facing or "").lower() == "right" else 1
    return (pri, face, spec.id)


def _cap_sprites_fairly(sprites: list[SpriteSpec], max_total: int = _SPRITE_CAP) -> list[SpriteSpec]:
    """Cap pose count while ensuring every character gets frames (not just the first N).

    Naive ``sprites[:16]`` drops all enemy poses when the player list is long, which
    leaves games without snake_sheet.png and Phaser fails to boot.
    """
    if len(sprites) <= max_total:
        return list(sprites)

    by_character: dict[str, list[SpriteSpec]] = {}
    character_order: list[str] = []
    for s in sprites:
        if s.character_id not in by_character:
            character_order.append(s.character_id)
            by_character[s.character_id] = []
        by_character[s.character_id].append(s)

    n_chars = len(character_order)
    # Give every character a share; prefer even counts for L/R pairs.
    base_each = max(2, max_total // max(n_chars, 1))
    if base_each % 2:
        base_each = max(2, base_each - 1)

    per_char: dict[str, int] = {}
    remaining = max_total
    for cid in character_order:
        take = min(base_each, remaining, len(by_character[cid]))
        if take > 1 and take % 2:
            take -= 1
        per_char[cid] = take
        remaining -= take

    # Distribute leftovers to earlier characters (player first).
    while remaining > 0:
        progressed = False
        for cid in character_order:
            if remaining <= 0:
                break
            if per_char[cid] < len(by_character[cid]):
                per_char[cid] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            break

    selected: list[SpriteSpec] = []
    for cid in character_order:
        ranked = sorted(by_character[cid], key=_sprite_action_rank)
        selected.extend(ranked[: per_char[cid]])
    return selected


def _write_placeholder_snake_sheet(path: Path, cells: int = 6) -> None:
    """Simple solid green snake frames so Phaser can always load the enemy sheet."""
    cell = GAME_CELL
    sheet = Image.new("RGBA", (cell * cells, cell), (0, 0, 0, 0))
    for i in range(cells):
        frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        # Body wave offset per frame
        ox = 4 + (i % 2) * 2
        for y in range(28, 48):
            for x in range(12 + ox, 50 + ox):
                if 0 <= x < cell and 0 <= y < cell:
                    frame.putpixel((x, y), (46, 140, 70, 255))
        # Head (left or right)
        face_right = i % 2 == 0
        hx = 46 if face_right else 10
        for y in range(22, 40):
            for x in range(hx, hx + 12):
                if 0 <= x < cell:
                    frame.putpixel((x, y), (56, 170, 80, 255))
        # Eye
        eye_x = hx + (8 if face_right else 2)
        for y in range(26, 30):
            for x in range(eye_x, eye_x + 3):
                if 0 <= x < cell:
                    frame.putpixel((x, y), (20, 20, 20, 255))
        sheet.paste(frame, (i * cell, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def _ensure_snake_sheet(
    assets: Path, frame_map: dict, sheets_written: list[str]
) -> None:
    """Guarantee assets/snake_sheet.png + a non-player frame_map entry exist."""
    snake_path = assets / "snake_sheet.png"
    enemy_keys = [k for k in frame_map if k != "player"]

    if not snake_path.exists():
        aliased = False
        for eid in enemy_keys:
            src = assets / f"{eid}_sheet.png"
            if src.exists():
                Image.open(src).save(snake_path)
                aliased = True
                break
        if not aliased:
            print("      warn: no enemy sheet — writing placeholder snake_sheet.png")
            _write_placeholder_snake_sheet(snake_path)

    if "snake_sheet.png" not in sheets_written:
        sheets_written.append("snake_sheet.png")

    if not enemy_keys:
        # BootScene looks up any non-player key; insert a minimal entry.
        frame_map["sneaky_snake"] = {
            "sheet": "assets/snake_sheet.png",
            "frame_width": GAME_CELL,
            "frame_height": GAME_CELL,
            "frames": [
                {"index": 0, "id": "sneaky_snake_move_right", "action": "move", "facing": "right"},
                {"index": 1, "id": "sneaky_snake_move_left", "action": "move", "facing": "left"},
                {"index": 2, "id": "sneaky_snake_idle_right", "action": "idle", "facing": "right"},
                {"index": 3, "id": "sneaky_snake_idle_left", "action": "idle", "facing": "left"},
                {"index": 4, "id": "sneaky_snake_hurt_right", "action": "hurt", "facing": "right"},
                {"index": 5, "id": "sneaky_snake_hurt_left", "action": "hurt", "facing": "left"},
            ],
        }


async def run_character_art_pipeline(
    out_dir: Path,
    concept: ConceptDoc,
    art: ArtBundle,
    critic_rounds: int = 1,
) -> dict:
    """
    Parallel art:
      Level A — all characters in parallel
      Level B — within each character: lock base, then all poses in parallel
      Level C — world tiles / items / BG (threaded parallel draws)
    """
    work = out_dir / "art_work"
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    sprites = _cap_sprites_fairly(art.sprites, _SPRITE_CAP)
    if len(art.sprites) > len(sprites):
        n_chars = len({s.character_id for s in art.sprites})
        print(
            f"      note: capping sprites {len(art.sprites)} -> {len(sprites)} "
            f"(fair share across {n_chars} characters)"
        )

    # Preserve brief order, group by character
    by_character: dict[str, list[SpriteSpec]] = {}
    character_order: list[str] = []
    for s in sprites:
        if s.character_id not in by_character:
            character_order.append(s.character_id)
            by_character[s.character_id] = []
        by_character[s.character_id].append(s)

    async def _build_char(character_id: str) -> dict:
        specs = by_character[character_id]
        base_spec = _pick_base_spec(specs)

        locked_html, base_png, base_critiques = await build_base_character(
            base_spec, concept, art, work, critic_rounds=critic_rounds
        )
        (work / "html" / f"{character_id}_base.html").write_text(locked_html, encoding="utf-8")

        other = [s for s in specs if s.id != base_spec.id]

        async def _one_pose(spec: SpriteSpec, base_html: str = locked_html):
            png, pose_critiques = await build_pose_from_base(
                spec, base_html, concept, art, work, critic_rounds=critic_rounds
            )
            return spec, png, pose_critiques

        pose_results = (
            await asyncio.gather(*[_one_pose(s) for s in other]) if other else []
        )

        path_by_id = {base_spec.id: base_png}
        char_critiques: dict[str, list] = {base_spec.id: base_critiques}
        for spec, png, pose_critiques in pose_results:
            path_by_id[spec.id] = png
            char_critiques[spec.id] = pose_critiques

        ordered_pairs: list[tuple[SpriteSpec, Path]] = []
        for s in specs:
            if s.id in path_by_id:
                ordered_pairs.append((s, path_by_id[s.id]))

        paths = [p for _, p in ordered_pairs]
        ids = [s.id for s, _ in ordered_pairs]
        sheet_name = f"{character_id}_sheet.png"
        await asyncio.to_thread(
            combine_character_sheet, paths, assets / sheet_name, GAME_CELL
        )
        fmap = {
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
        print(
            f"      sheet -> assets/{sheet_name} ({len(ids)} frames, parallel chars+poses)"
        )
        return {
            "character_id": character_id,
            "sheet_name": sheet_name,
            "frame_map": fmap,
            "critiques": char_critiques,
        }

    print(f"      parallel characters: {character_order}")
    char_results = await asyncio.gather(*[_build_char(cid) for cid in character_order])

    frame_map: dict[str, dict] = {}
    all_critiques: dict[str, list] = {}
    sheets_written: list[str] = []
    for res in char_results:
        cid = res["character_id"]
        frame_map[cid] = res["frame_map"]
        all_critiques.update(res["critiques"])
        sheets_written.append(res["sheet_name"])

    _alias_phaser_sheets(assets, frame_map, sheets_written)
    if "player" not in frame_map and frame_map:
        first = next(iter(frame_map))
        frame_map["player"] = frame_map[first]
    _ensure_snake_sheet(assets, frame_map, sheets_written)

    from .render_art import render_world_art_parallel

    world_files = await render_world_art_parallel(assets, art, concept)

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
