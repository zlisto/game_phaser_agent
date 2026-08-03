"""Orchestrator — runs specialist agents in lecture order."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from .agents import (
    run_art,
    run_assembler_plan,
    run_concept,
    run_levels,
    run_mechanics,
    run_sound,
)
from .blips import render_sound_bundle
from .html_sprites import run_character_art_pipeline
from .models import (
    ArtBundle,
    ConceptDoc,
    LevelsDoc,
    MechanicsDoc,
    StudioBrief,
    StudioReport,
)
from .phaser_builder import build_phaser_project
from .render_art import write_layout_preview


def format_elapsed(seconds: float) -> str:
    """Wall-clock duration as e.g. '4m 32s' or '48s'."""
    total = max(0, int(round(seconds)))
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


async def run_studio(brief: StudioBrief, root: Path | None = None) -> StudioReport:
    root = root or Path.cwd()
    from .agents import MODEL as ACTIVE_MODEL

    t0 = time.perf_counter()
    print(f"[1/7] Concept Agent... ({ACTIVE_MODEL})")
    concept = await run_concept(brief)
    print(f"      -> {concept.title}")

    print("[2/7] Mechanics Agent (poses + HUD + SFX cues)...")
    mechanics = await run_mechanics(concept, brief)
    print(
        f"      -> hp={mechanics.player.max_hp}, "
        f"enemies={len(mechanics.enemies)}, poses={len(mechanics.sprite_poses)}, "
        f"sfx={len(mechanics.sfx)}"
    )

    print("[3/7] Levels Agent (maps + BGM briefs)...")
    levels = await run_levels(concept, mechanics, brief)
    print(
        f"      -> {len(levels.levels)} level(s), "
        f"bgm tracks={len(levels.background_music)}"
    )

    print("[4/7] Art Agent (names + detailed descriptions)...")
    art = await run_art(concept, mechanics, levels, brief)
    print(f"      -> {len(art.sprites)} sprite briefs")

    print("[5/7] HTML sprites + screenshots + critic...")
    out_dir = (root / brief.output_folder).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(exist_ok=True)
    (out_dir / "data" / "concept.json").write_text(
        concept.model_dump_json(indent=2), encoding="utf-8"
    )
    (out_dir / "data" / "mechanics.json").write_text(
        mechanics.model_dump_json(indent=2), encoding="utf-8"
    )
    (out_dir / "data" / "levels.json").write_text(
        levels.model_dump_json(indent=2), encoding="utf-8"
    )

    art_result = await run_character_art_pipeline(
        out_dir, concept, art, critic_rounds=brief.critic_rounds
    )

    print("[6/7] Sound Agent (blip recipes -> WAV)...")
    sound = await run_sound(concept, mechanics, levels)
    (out_dir / "data" / "sound.json").write_text(
        sound.model_dump_json(indent=2), encoding="utf-8"
    )
    audio_files = render_sound_bundle(sound, out_dir / "assets")
    print(f"      -> {len(sound.sfx)} sfx, {len(sound.music)} music loops")

    print("[7/7] Assembler Agent (+ Phaser wire-up, HUD, audio)...")
    plan = await run_assembler_plan(concept, mechanics, levels, brief)
    preview = write_layout_preview(out_dir, levels)
    files = build_phaser_project(out_dir, concept, mechanics, levels, plan)
    files.extend(f"assets/{n}" for n in art_result["sheets"])
    files.extend(f"assets/{n}" for n in art_result["world_files"])
    files.extend(audio_files)
    files.append(preview)
    files.append("data/art.json")
    files.append("data/frame_map.json")
    files.append("data/art_critiques.json")
    files.append("data/sound.json")

    from .agents import MODEL

    elapsed = time.perf_counter() - t0
    elapsed_human = format_elapsed(elapsed)

    (out_dir / "data" / "run_meta.json").write_text(
        json.dumps(
            {
                "model": MODEL,
                "critic_rounds": brief.critic_rounds,
                "mode": "full",
                "elapsed_seconds": round(elapsed, 2),
                "elapsed_human": elapsed_human,
                "sfx_count": len(sound.sfx),
                "music_count": len(sound.music),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    files.append("data/run_meta.json")

    report = StudioReport(
        output_dir=str(out_dir),
        files_created=sorted(set(files)),
        how_to_run=f'cd "{out_dir}" && npx --yes serve .',
        summary=(
            f"Built '{concept.title}' ({concept.game_type}) with "
            f"{len(levels.levels)} levels, {len(art.sprites)} HTML sprites, "
            f"{len(sound.sfx)} sfx, {len(sound.music)} bgm into {out_dir} "
            f"(model={MODEL}, took {elapsed_human})"
        ),
        elapsed_seconds=round(elapsed, 2),
        elapsed_human=elapsed_human,
    )
    (out_dir / "STUDIO_REPORT.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(report.summary)
    print(f"Took: {elapsed_human} ({elapsed:.1f}s)")
    print("How to run:", report.how_to_run)
    return report


async def rerun_art_only(
    game_dir: Path,
    critic_rounds: int = 1,
    model: str | None = None,
) -> StudioReport:
    """Rebuild character sprites from existing concept/mechanics/levels."""
    from .agents import MODEL, configure_model

    t0 = time.perf_counter()
    if model:
        configure_model(model)

    concept = ConceptDoc.model_validate_json((game_dir / "data" / "concept.json").read_text(encoding="utf-8"))
    mechanics = MechanicsDoc.model_validate_json((game_dir / "data" / "mechanics.json").read_text(encoding="utf-8"))
    levels = LevelsDoc.model_validate_json((game_dir / "data" / "levels.json").read_text(encoding="utf-8"))

    # Ensure poses exist on older mechanics.json
    if not mechanics.sprite_poses:
        from .agents import default_sprite_poses

        eids = [e.id for e in mechanics.enemies] or ["snake"]
        mechanics.sprite_poses = default_sprite_poses(concept.game_type, eids)
        (game_dir / "data" / "mechanics.json").write_text(
            mechanics.model_dump_json(indent=2), encoding="utf-8"
        )

    brief = StudioBrief(
        concept_sentence=concept.pitch,
        game_type=concept.game_type,
        output_folder=str(game_dir),
        critic_rounds=critic_rounds,
    )
    print("[art] Art Agent (descriptions)...")
    art = await run_art(concept, mechanics, levels, brief)
    print(f"      -> {len(art.sprites)} sprite briefs")
    print("[art] HTML + screenshot + critic + sheets...")
    art_result = await run_character_art_pipeline(
        game_dir, concept, art, critic_rounds=critic_rounds
    )

    print("[art] Rewiring Phaser project...")
    from .models import AssemblerPlan
    from .phaser_builder import build_phaser_project

    plan = AssemblerPlan(
        game_folder_name=game_dir.name,
        html_title=concept.title,
        subtitle=concept.pitch[:160],
        win_text="Harvest saved — feast time!",
        lose_text="Bun needs another try...",
        notes_for_player=[
            "Punch or stomp snakes — walking into them is death",
            "Wall-jump off platform sides",
            "Carrots heal · eggs power punch",
        ],
    )
    phaser_files = build_phaser_project(game_dir, concept, mechanics, levels, plan)
    write_layout_preview(game_dir, levels)

    elapsed = time.perf_counter() - t0
    elapsed_human = format_elapsed(elapsed)

    meta = {
        "model": MODEL,
        "critic_rounds": critic_rounds,
        "mode": "art-from",
        "elapsed_seconds": round(elapsed, 2),
        "elapsed_human": elapsed_human,
    }
    (game_dir / "data" / "run_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    report = StudioReport(
        output_dir=str(game_dir),
        files_created=sorted(
            set(
                [f"assets/{n}" for n in art_result["sheets"]]
                + [f"assets/{n}" for n in art_result["world_files"]]
                + phaser_files
                + [
                    "data/art.json",
                    "data/frame_map.json",
                    "data/art_critiques.json",
                    "data/run_meta.json",
                ]
            )
        ),
        how_to_run=f'cd "{game_dir}" && npx --yes serve .',
        summary=(
            f"Rebuilt HTML sprite sheets + Phaser for {game_dir} "
            f"({len(art.sprites)} poses, model={MODEL}, took {elapsed_human})"
        ),
        elapsed_seconds=round(elapsed, 2),
        elapsed_human=elapsed_human,
    )
    print(report.summary)
    print(f"Took: {elapsed_human} ({elapsed:.1f}s)")
    return report


def run_studio_sync(brief: StudioBrief, root: Path | None = None) -> StudioReport:
    return asyncio.run(run_studio(brief, root=root))


def rerun_art_only_sync(
    game_dir: Path,
    critic_rounds: int = 1,
    model: str | None = None,
) -> StudioReport:
    return asyncio.run(rerun_art_only(game_dir, critic_rounds=critic_rounds, model=model))


def load_brief(path: Path) -> StudioBrief:
    data = json.loads(path.read_text(encoding="utf-8"))
    return StudioBrief.model_validate(data)
