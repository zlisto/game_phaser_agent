"""PydanticAI specialist agents for the 2D game studio."""

from __future__ import annotations

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModelSettings

from .env_loader import load_studio_env

load_studio_env()

from .models import (
    ArtBundle,
    AssemblerPlan,
    ConceptDoc,
    CriticFeedback,
    HtmlSpriteOut,
    LevelsDoc,
    MechanicsDoc,
    PoseNeed,
    SoundBundle,
    SpriteSpec,
    StudioBrief,
)

DEFAULT_MODEL = "gpt-5.6-luna"
MODEL_SETTINGS = OpenAIChatModelSettings(openai_reasoning_effort="none")

# Active model string for pydantic-ai (openai:…)
MODEL = f"openai:{DEFAULT_MODEL}"

concept_agent: Agent
mechanics_agent: Agent
levels_agent: Agent
art_agent: Agent
html_sprite_agent: Agent
html_pose_agent: Agent
critic_agent: Agent
sound_agent: Agent
assembler_agent: Agent


def normalize_model_id(model: str) -> str:
    """Accept 'gpt-5.6-sol' or 'openai:gpt-5.6-sol' → openai provider string."""
    m = model.strip()
    if ":" not in m:
        m = f"openai:{m}"
    return m


def configure_model(model: str | None = None, *, quiet: bool = False) -> str:
    """Rebuild all specialist agents for the given model. Returns the model id used."""
    global MODEL
    global concept_agent, mechanics_agent, levels_agent, art_agent
    global html_sprite_agent, html_pose_agent, critic_agent, sound_agent, assembler_agent

    MODEL = normalize_model_id(model or DEFAULT_MODEL)
    if not quiet:
        print(f"[model] {MODEL}")

    def _agent(output_type, instructions: str) -> Agent:
        return Agent(
            MODEL,
            output_type=output_type,
            instructions=instructions,
            model_settings=MODEL_SETTINGS,
        )

    concept_agent = _agent(
        ConceptDoc,
        "You are the Concept Agent for a tiny student 2D game. "
        "Output a crisp concept: pitch, characters, style, win/lose, story beats, level beats. "
        "Honor the requested game_type (side_scroller or top_down). "
        "Keep scope tiny and finishable. Prefer re-skinning Zelda-like or Mario-like structures.",
    )
    mechanics_agent = _agent(
        MechanicsDoc,
        "You are the Mechanics Agent. Turn the concept into concrete verbs, stats, damage, items, "
        "controls, HUD, SFX cues, and a complete sprite_poses list for every character animation. "
        "ALWAYS fill hud: show_hp=true, show_score=true (unless story forbids), show_punch when attacks upgrade, "
        "labels for hp/score/punch/level, and score_per_enemy / score_per_item. "
        "If brief wants carrot icons for HP / compact image HUD, set labels.hp to Carrots and juice_notes accordingly. "
        "If brief: walk-into-enemy kills instantly — write lose_condition that way (stomp or punch only kill snakes). "
        "If brief includes wall-jump, note it in juice_notes. "
        "ALWAYS fill sfx[] — sound effect shopping list for the Sound Agent. Each SfxCue needs: "
        "id, trigger (when it plays), mood (short design note), category. "
        "Required ids (use these exact ids): jump, punch, hurt, stomp, pickup_heal, pickup_power, win, lose. "
        "Add extra ids only if the game clearly needs them. "
        "sprite_poses MUST include clear facing and actions idle/run/jump/punch/hurt as relevant. "
        "For the hero include at least: idle_right, idle_left, run_right, punch_right, punch_left, hurt_right, jump_right. "
        "For each enemy include idle + move + hurt, with left and right facings where relevant. "
        "Keep numbers small and playable.",
    )
    levels_agent = _agent(
        LevelsDoc,
        "You are the Levels Agent. Build tiny ASCII tile maps in levels[].rows. "
        "Every row in a level MUST be the same length = width. height = number of rows. "
        "Legend: # solid, = platform, . empty, S player_spawn (exactly one), X exit (exactly one), "
        "C carrot, G easter_egg, N snake. "
        "Side scroller: width 30-50, height 12-16, ground along the bottom, a few platforms. "
        "CRITICAL physics: respect max_jump_tiles from the prompt — never place a platform more than "
        "that many tiles ABOVE the nearest lower floor/platform. Stair-step climbs (1–2 tiles up). "
        "No floating islands the player cannot reach with a single jump. "
        "Top down: 3-5 room-like chambers with # walls, corridors, 10-16 tiles wide. "
        "Exactly the requested number of levels if specified, else 2. "
        "Also fill art_shopping_list (include HUD icons: heart/hp, coin/score if needed) and short layout_notes. "
        "ALWAYS fill background_music[] — one MusicTrack per level: id, level_id (match levels[].id), "
        "mood (how the BGM should feel), tempo_bpm, loop=true. Also set levels[].music_id to that track id. "
        "Teach → twist → payoff across the level.",
    )
    art_agent = _agent(
        ArtBundle,
        "You are the Art Agent cataloguer. Given concept + mechanics.sprite_poses, produce art.json: "
        "style_notes, palette, and sprites[] — one SpriteSpec per pose. "
        "Each sprite MUST have a DETAILED description the HTML artist can draw from: species, outfit, "
        "colors, face expression, limb positions, which way the character faces, what the action looks like "
        "(e.g. right arm extended with red boxing glove for punch_right; flinch and closed eyes for hurt). "
        "Demand a detailed character (eyes with highlights, ears, clothing/gloves, readable silhouette) — "
        "not a stick figure. "
        "Do not invent poses missing from mechanics; cover every sprite_poses entry. "
        "Also list item_ids and tile_ids for world art.",
    )
    html_sprite_agent = _agent(
        HtmlSpriteOut,
        "You are the HTML/SVG Sprite Artist. Output one standalone HTML document "
        "for a SINGLE character on a transparent 256x256 stage (#stage). "
        "Use detailed layered SVG with named groups (ear-left, head, body, arm-left, glove-left, …), "
        "gradients, outlines, eyes with highlights. "
        "Character must look hand-crafted and cute/readable — not abstract blobs. "
        "No background fill on the stage. No external images.",
    )
    html_pose_agent = _agent(
        HtmlSpriteOut,
        "You are the HTML/SVG Pose Editor. You receive LOCKED base character HTML. "
        "Your job is to produce a NEW pose by editing THAT same SVG — keep the same colors, "
        "gradients, proportions, face, outfit, and part IDs. "
        "Only nudge transforms / limb positions / facing for the requested action. "
        "Do NOT redraw a different character. Do NOT invent a new style. "
        "Return full HTML with #stage. Transparent background.",
    )
    critic_agent = _agent(
        CriticFeedback,
        "You are the Sprite Critic. You inspect a screenshot of one HTML sprite pose. "
        "Check: (1) detailed enough (face, limbs, outfit — not a blob), "
        "(2) facing matches the required facing, "
        "(3) action is readable (punching arm extended, hurt flinch, run stride, etc.), "
        "(4) transparent/no ugly full-frame background rectangle, "
        "(5) silhouette clear at game size. "
        "If anything fails, ok=false and give concrete revision_instructions for the SVG/HTML. "
        "If it passes, ok=true with empty issues.",
    )
    sound_agent = _agent(
        SoundBundle,
        "You are the Sound Agent for a tiny Phaser 3 student game. "
        "You do NOT output audio files — you output synthesis recipes (jsfxr-style params) "
        "that a procedural blip library will turn into WAV files. "
        "Given mechanics.sfx cues and levels.background_music tracks, produce: "
        "style_notes (one line), sfx[] BlipRecipe for every cue id, music[] MusicRecipe for every track. "
        "Keep SFX short (80–350ms). Prefer square/saw/sine/noise for cartoon readability. "
        "Match mood text (soft hop vs thwack vs sad flop). "
        "Music: short looping chiptune (major/minor/pentatonic, 4 bars, tempo from the track). "
        "Ids MUST match the inputs exactly.",
    )
    assembler_agent = _agent(
        AssemblerPlan,
        "You are the Assembler Agent planner for a Phaser 3 CDN game. "
        "Produce the playable project's title, subtitle, HUD labels (match mechanics.hud), win/lose text, "
        "folder name (kebab-case), and short player tips. "
        "Assume always-visible HUD for HP/score and audio (SFX + looping BGM) — do not omit them. "
        "Do not invent new mechanics — reflect the concept/mechanics provided.",
    )
    return MODEL


# Default agents at import (luna) — quiet so CLI --model is the only printed line
configure_model(DEFAULT_MODEL, quiet=True)


def default_sprite_poses(game_type: str, enemy_ids: list[str] | None = None) -> list[PoseNeed]:
    enemy_ids = enemy_ids or ["snake"]
    poses: list[PoseNeed] = [
        PoseNeed(id="player_idle_right", character_id="player", action="idle", facing="right", purpose="standing facing right"),
        PoseNeed(id="player_idle_left", character_id="player", action="idle", facing="left", purpose="standing facing left"),
        PoseNeed(id="player_run_right", character_id="player", action="run", facing="right", purpose="running right"),
        PoseNeed(id="player_run_left", character_id="player", action="run", facing="left", purpose="running left"),
        PoseNeed(id="player_punch_right", character_id="player", action="punch", facing="right", purpose="attack facing right"),
        PoseNeed(id="player_punch_left", character_id="player", action="punch", facing="left", purpose="attack facing left"),
        PoseNeed(id="player_hurt_right", character_id="player", action="hurt", facing="right", purpose="took damage"),
    ]
    if game_type == "side_scroller":
        poses.append(
            PoseNeed(id="player_jump_right", character_id="player", action="jump", facing="right", purpose="in air")
        )
    else:
        poses.extend(
            [
                PoseNeed(id="player_idle_up", character_id="player", action="idle", facing="up", purpose="facing up"),
                PoseNeed(id="player_idle_down", character_id="player", action="idle", facing="down", purpose="facing down"),
            ]
        )
    for eid in enemy_ids[:2]:
        poses.extend(
            [
                PoseNeed(id=f"{eid}_idle_right", character_id=eid, action="idle", facing="right", purpose="enemy idle"),
                PoseNeed(id=f"{eid}_move_right", character_id=eid, action="move", facing="right", purpose="enemy move"),
                PoseNeed(id=f"{eid}_idle_left", character_id=eid, action="idle", facing="left", purpose="enemy idle left"),
                PoseNeed(id=f"{eid}_hurt", character_id=eid, action="hurt", facing="right", purpose="enemy hit"),
            ]
        )
    return poses


async def run_concept(brief: StudioBrief) -> ConceptDoc:
    prompt = (
        f"Concept sentence: {brief.concept_sentence}\n"
        f"Game type: {brief.game_type}\n"
        f"Title hint: {brief.title_hint or '(none)'}\n"
        f"Constraints:\n- " + "\n- ".join(brief.constraints or ["Keep it tiny"])
    )
    result = await concept_agent.run(prompt)
    doc = result.output
    doc.game_type = brief.game_type
    return doc


async def run_mechanics(concept: ConceptDoc, brief: StudioBrief) -> MechanicsDoc:
    prompt = (
        f"Concept JSON:\n{concept.model_dump_json(indent=2)}\n\n"
        f"Extra constraints:\n- " + "\n- ".join(brief.constraints or []) + "\n"
        "Fill sprite_poses thoroughly for the hero and each enemy.\n"
        "Fill sfx[] with jump, punch, hurt, stomp, pickup_heal, pickup_power, win, lose "
        "(ids exact) plus mood notes matching the game's tone."
    )
    result = await mechanics_agent.run(prompt)
    doc = result.output
    doc.game_type = concept.game_type
    if len(doc.sprite_poses) < 6:
        eids = [e.id for e in doc.enemies] or ["snake"]
        doc.sprite_poses = default_sprite_poses(concept.game_type, eids)
    # Guarantee a playable HUD even if the model dims the fields
    doc.hud.show_hp = True
    doc.hud.show_score = True
    # Guarantee core SFX shopping list
    from .blips import default_sfx_cues

    have = {c.id for c in doc.sfx}
    for cue in default_sfx_cues(concept.game_type):
        if cue.id not in have:
            doc.sfx.append(cue)
    return doc


# Must match Phaser arcade gravity in phaser_builder.py
ARCADE_GRAVITY_Y = 1000.0


def max_jump_tiles(mechanics: MechanicsDoc, tile_size: int = 32) -> int:
    """Approx max jump height in tiles from jump_velocity + gravity (side_scroller)."""
    if mechanics.game_type != "side_scroller":
        return 99
    v = abs(float(mechanics.player.jump_velocity))
    # v^2 / (2g) peak height in pixels
    peak_px = (v * v) / (2.0 * ARCADE_GRAVITY_Y)
    # Leave a little slack for jump timing / sprite size
    tiles = int(peak_px // max(1, tile_size))
    return max(1, min(tiles, 4))  # cap so agents don't invent mega-jumps


async def run_levels(
    concept: ConceptDoc, mechanics: MechanicsDoc, brief: StudioBrief
) -> LevelsDoc:
    jump_tiles = max_jump_tiles(mechanics)
    prompt = (
        f"Concept:\n{concept.model_dump_json(indent=2)}\n\n"
        f"Mechanics:\n{mechanics.model_dump_json(indent=2)}\n\n"
        f"PHYSICS (side_scroller): max_jump_tiles = {jump_tiles}. "
        f"Platforms (`=`) must be at most {jump_tiles} tiles above the nearest lower floor/#/=. "
        f"Stair-step upward climbs. Do not place unreachable floating platforms.\n\n"
        f"Constraints:\n- " + "\n- ".join(brief.constraints or []) + "\n"
        "Return playable ASCII maps with consistent row lengths.\n"
        "Also return background_music (one track per level) and set each level's music_id."
    )
    result = await levels_agent.run(prompt)
    doc = result.output
    doc.game_type = concept.game_type
    fixed = []
    for lv in doc.levels:
        if not lv.rows:
            continue
        width = max(len(r) for r in lv.rows)
        rows = [r.ljust(width, ".")[:width] for r in lv.rows]
        rows = [_strip_markers(r) for r in rows]
        rows = _ensure_ground(rows)
        if mechanics.game_type == "side_scroller":
            rows = _clamp_platforms_to_jump(rows, jump_tiles)
        rows = _place_on_walkable(rows, "S", near="start")
        rows = _place_on_walkable(rows, "X", near="end")
        lv.width = width
        lv.height = len(rows)
        lv.rows = rows
        fixed.append(lv)
    doc.levels = fixed

    # Guarantee background music briefs
    from .blips import default_music_tracks

    level_ids = [lv.id for lv in doc.levels]
    if not doc.background_music:
        doc.background_music = default_music_tracks(level_ids)
    else:
        have_lv = {t.level_id for t in doc.background_music}
        for lid in level_ids:
            if lid not in have_lv:
                doc.background_music.extend(default_music_tracks([lid]))
    # Link music_id on each level
    by_level = {t.level_id: t for t in doc.background_music}
    for lv in doc.levels:
        if not lv.music_id and lv.id in by_level:
            lv.music_id = by_level[lv.id].id
        elif not lv.music_id and doc.background_music:
            lv.music_id = doc.background_music[0].id
    return doc


def _strip_markers(row: str) -> str:
    return "".join("." if c in "SX" else c for c in row)


def _ensure_ground(rows: list[str]) -> list[str]:
    if not rows:
        return rows
    bottom = list(rows[-1])
    if bottom.count("#") < max(3, len(bottom) // 3):
        rows[-1] = "#" * len(bottom)
    return rows


def _is_solid(ch: str) -> bool:
    return ch in "#="


def _clamp_platforms_to_jump(rows: list[str], max_up: int) -> list[str]:
    """
    Lower or remove `=` platforms that sit more than max_up tiles above the
    nearest solid below (same column). Keeps jumps physically plausible.
    """
    if not rows or max_up < 1:
        return rows
    h = len(rows)
    w = len(rows[0])
    grid = [list(r) for r in rows]

    # Process from bottom to top so we settle platforms against already-fixed ones
    for y in range(h - 2, -1, -1):
        for x in range(w):
            if grid[y][x] != "=":
                continue
            # Find nearest solid below this platform tile
            below_y = None
            for yy in range(y + 1, h):
                if _is_solid(grid[yy][x]):
                    below_y = yy
                    break
            if below_y is None:
                # No support below — drop toward ground
                grid[y][x] = "."
                dest = max(1, h - 3)
                if not _is_solid(grid[dest][x]):
                    grid[dest][x] = "="
                continue
            # Stand on platform at y-1; stand on below solid at below_y-1
            # Vertical rise in tiles = (below_y - 1) - (y - 1) = below_y - y
            rise = below_y - y
            if rise <= max_up:
                continue
            # Move platform down so rise == max_up
            new_y = below_y - max_up
            if new_y <= 0 or new_y >= h - 1:
                grid[y][x] = "."
                continue
            if new_y != y:
                grid[y][x] = "."
                if grid[new_y][x] in ".C":
                    grid[new_y][x] = "="
                elif not _is_solid(grid[new_y][x]):
                    grid[new_y][x] = "="

    return ["".join(r) for r in grid]


def _walkable_cells(rows: list[str]) -> list[tuple[int, int]]:
    h = len(rows)
    w = len(rows[0])
    cells: list[tuple[int, int]] = []
    for y in range(h - 1):
        for x in range(w):
            here = rows[y][x]
            below = rows[y + 1][x]
            if here in ".CGN" and below in "#=":
                cells.append((x, y))
    return cells


def _place_on_walkable(rows: list[str], ch: str, near: str) -> list[str]:
    cells = _walkable_cells(rows)
    if not cells:
        y = max(0, len(rows) - 2)
        x = 2 if near == "start" else len(rows[0]) - 3
        chars = list(rows[y])
        chars[x] = ch
        rows[y] = "".join(chars)
        return rows
    cells = sorted(cells, key=lambda p: p[0], reverse=(near == "end"))
    x, y = cells[0]
    chars = list(rows[y])
    chars[x] = ch
    rows[y] = "".join(chars)
    return rows


async def run_art(
    concept: ConceptDoc,
    mechanics: MechanicsDoc,
    levels: LevelsDoc,
    brief: StudioBrief,
) -> ArtBundle:
    poses_json = [p.model_dump() for p in mechanics.sprite_poses]
    prompt = (
        f"Concept:\n{concept.model_dump_json(indent=2)}\n\n"
        f"Mechanics sprite_poses (MUST cover all):\n{poses_json}\n\n"
        f"Art shopping list:\n{levels.art_shopping_list.model_dump_json(indent=2)}\n\n"
        f"Style constraints:\n- " + "\n- ".join(brief.constraints or []) + "\n"
        "Write a rich description field for every sprite — this drives HTML generation."
    )
    result = await art_agent.run(prompt)
    art = result.output
    # Ensure every pose has a sprite entry
    have = {s.id for s in art.sprites}
    for pose in mechanics.sprite_poses:
        if pose.id not in have:
            art.sprites.append(
                SpriteSpec(
                    id=pose.id,
                    character_id=pose.character_id,
                    action=pose.action,
                    facing=pose.facing,
                    description=(
                        f"{concept.hero if pose.character_id == 'player' else pose.character_id}: "
                        f"{pose.action} facing {pose.facing}. {pose.purpose}. "
                        f"Style: {concept.style}. Detailed limbs, face, and silhouette."
                    ),
                )
            )
    return art


async def generate_base_html_sprite(
    spec: SpriteSpec, concept: ConceptDoc, art: ArtBundle
) -> HtmlSpriteOut:
    """Create the locked master character HTML (idle / canonical pose)."""
    prompt = (
        f"Create the LOCKED BASE character HTML (master identity for all later poses).\n"
        f"Game: {concept.title}\nStyle: {concept.style}\n"
        f"Global art notes: {art.style_notes}\n"
        f"Palette: {art.palette.model_dump()}\n\n"
        f"SPRITE ID: {spec.id}\n"
        f"character_id: {spec.character_id}\n"
        f"action: {spec.action}\n"
        f"facing: {spec.facing} (MUST be visually obvious)\n"
        f"DESCRIPTION:\n{spec.description}\n\n"
        "Use named SVG groups so poses can nudge limbs later. "
        "Return full HTML with <div id='stage' class='stage'>."
    )
    result = await html_sprite_agent.run(prompt)
    return result.output


async def pose_html_from_locked_base(
    spec: SpriteSpec,
    locked_base_html: str,
    concept: ConceptDoc,
    art: ArtBundle,
) -> HtmlSpriteOut:
    """Edit the locked base HTML into a new pose — same character DNA."""
    prompt = (
        f"Pose the LOCKED base character. Keep identity identical.\n"
        f"Game: {concept.title}\n"
        f"Target id={spec.id} action={spec.action} facing={spec.facing}\n"
        f"Pose description:\n{spec.description}\n\n"
        "RULES:\n"
        "- Start from the LOCKED BASE HTML below\n"
        "- Keep same colors, gradients, face, outfit, proportions, part structure\n"
        "- Only change transforms / limb placement / facing / action silhouette\n"
        "- Do not redraw a different character\n\n"
        f"LOCKED BASE HTML:\n{locked_base_html[:14000]}\n\n"
        "Return the full posed HTML with #stage."
    )
    result = await html_pose_agent.run(prompt)
    return result.output


async def critique_sprite(spec: SpriteSpec, png_path: Path) -> CriticFeedback:
    data = png_path.read_bytes()
    prompt = (
        f"Required sprite id={spec.id}, action={spec.action}, facing={spec.facing}.\n"
        f"Description that should be visible:\n{spec.description}\n\n"
        "Inspect the attached screenshot and critique it."
    )
    result = await critic_agent.run(
        [
            prompt,
            BinaryContent(data=data, media_type="image/png"),
        ]
    )
    return result.output


async def revise_html_sprite(
    spec: SpriteSpec,
    previous_html: str,
    feedback: CriticFeedback,
    concept: ConceptDoc,
    art: ArtBundle,
    *,
    locked_base_html: str | None = None,
) -> HtmlSpriteOut:
    base_note = ""
    if locked_base_html:
        base_note = (
            "Stay consistent with the LOCKED BASE character HTML "
            "(same colors/proportions/parts). Only fix pose issues.\n"
            f"LOCKED BASE (reference):\n{locked_base_html[:8000]}\n\n"
        )
    prompt = (
        f"Revise this HTML sprite.\n"
        f"id={spec.id} action={spec.action} facing={spec.facing}\n"
        f"Description: {spec.description}\n"
        f"Palette: {art.palette.model_dump()}\n"
        f"Critic issues: {feedback.issues}\n"
        f"Revision instructions: {feedback.revision_instructions}\n\n"
        f"{base_note}"
        f"PREVIOUS HTML:\n{previous_html[:12000]}\n\n"
        "Return improved full HTML. Keep transparent stage; fix facing/action/detail."
    )
    agent = html_pose_agent if locked_base_html else html_sprite_agent
    result = await agent.run(prompt)
    return result.output


async def run_sound(
    concept: ConceptDoc,
    mechanics: MechanicsDoc,
    levels: LevelsDoc,
) -> SoundBundle:
    """Sound Agent — emits synthesis recipes (SFX + BGM) from mechanics/levels briefs."""
    prompt = (
        f"Game: {concept.title}\nStyle mood: {concept.style}\nPitch: {concept.pitch}\n\n"
        f"SFX cues from Mechanics (must cover every id):\n"
        f"{[c.model_dump() for c in mechanics.sfx]}\n\n"
        f"Background music tracks from Levels:\n"
        f"{[t.model_dump() for t in levels.background_music]}\n\n"
        "Emit BlipRecipe for each SFX id and MusicRecipe for each BGM track. "
        "Keep it cute, readable, short. Match moods."
    )
    result = await sound_agent.run(prompt)
    from .blips import fill_sound_bundle

    return fill_sound_bundle(mechanics.sfx, levels.background_music, result.output)


async def run_assembler_plan(
    concept: ConceptDoc,
    mechanics: MechanicsDoc,
    levels: LevelsDoc,
    brief: StudioBrief,
) -> AssemblerPlan:
    prompt = (
        f"Output folder hint: {brief.output_folder}\n"
        f"Concept:\n{concept.model_dump_json(indent=2)}\n\n"
        f"Mechanics:\n{mechanics.model_dump_json(indent=2)}\n\n"
        f"Levels: {len(levels.levels)} maps — {[lv.id for lv in levels.levels]}"
    )
    result = await assembler_agent.run(prompt)
    plan = result.output
    if not plan.game_folder_name:
        plan.game_folder_name = brief.output_folder.rstrip("/").split("/")[-1]
    return plan
