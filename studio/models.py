"""Shared schemas for the game-studio pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GameType = Literal["side_scroller", "top_down"]
Facing = Literal["left", "right", "front", "up", "down"]


class StudioBrief(BaseModel):
    """Human / CLI input that kicks off the orchestrator."""

    concept_sentence: str
    game_type: GameType
    title_hint: str | None = None
    constraints: list[str] = Field(default_factory=list)
    output_folder: str = "games/untitled"
    critic_rounds: int = 1


class ConceptDoc(BaseModel):
    title: str
    pitch: str
    game_type: GameType
    style: str
    hero: str
    enemies: list[str]
    goal: str
    fail_state: str
    story_beats: list[str]
    level_beats: list[str]
    reference_games: list[str] = Field(default_factory=list)


class KeyMap(BaseModel):
    left: str = "A / Left"
    right: str = "D / Right"
    up: str = "W / Up"
    down: str = "S / Down"
    jump: str = "Space / W"
    attack: str = "J / K"


class PlayerStats(BaseModel):
    max_hp: int = 5
    speed: float = 220
    jump_velocity: float = -420
    attack_damage: int = 1
    attack_cooldown_ms: int = 280
    invuln_ms: int = 900


class EnemyStats(BaseModel):
    id: str
    hp: int = 1
    damage: int = 1
    speed: float = 70
    stompable: bool = True
    notes: str = ""


class ItemEffect(BaseModel):
    id: str
    effect: str
    value: float = 1
    notes: str = ""


class PoseNeed(BaseModel):
    """Pose the game must animate — Mechanics Agent fills this."""

    id: str = Field(description="Unique pose id, e.g. player_punch_right")
    character_id: str = Field(description="player, or enemy id like sneaky_snake")
    action: str = Field(description="idle, run, jump, punch, hurt, slither, ...")
    facing: Facing
    purpose: str = Field(description="When this pose plays in gameplay")


class HudSpec(BaseModel):
    """What the Assembler must always show on screen (Mechanics decides)."""

    show_hp: bool = True
    show_score: bool = True
    show_punch: bool = True
    show_level: bool = True
    labels: dict[str, str] = Field(
        default_factory=lambda: {
            "hp": "HP",
            "score": "Score",
            "punch": "Punch",
            "level": "Level",
        }
    )
    score_per_enemy: int = 100
    score_per_item: int = 10


class SfxCue(BaseModel):
    """One sound effect the game must play — Mechanics lists; Sound Agent synthesizes."""

    id: str = Field(description="Stable id: jump, punch, hurt, stomp, pickup_heal, pickup_power, win, lose")
    trigger: str = Field(description="When it fires, e.g. player leaves ground, snake defeated")
    mood: str = Field(
        description="Short design note for Sound Agent, e.g. soft cotton thump, bright chime"
    )
    category: Literal["player", "combat", "pickup", "ui", "world"] = "player"


class MusicTrack(BaseModel):
    """Background music brief — Levels designs; Sound Agent synthesizes a loop."""

    id: str = Field(description="Stable id, e.g. meadow_day, cave_danger")
    level_id: str = Field(description="Which level map id this track is for")
    mood: str = Field(description="Musical mood / instrumentation note")
    tempo_bpm: int = Field(default=120, ge=60, le=200)
    loop: bool = True
    notes: str = ""


class MechanicsDoc(BaseModel):
    game_type: GameType
    controls: KeyMap
    player: PlayerStats
    enemies: list[EnemyStats]
    items: list[ItemEffect]
    win_condition: str
    lose_condition: str
    juice_notes: list[str] = Field(default_factory=list)
    hud: HudSpec = Field(
        default_factory=HudSpec,
        description="On-screen HUD the Assembler must wire up",
    )
    sfx: list[SfxCue] = Field(
        default_factory=list,
        description="SFX shopping list for the Sound Agent (event blips)",
    )
    sprite_poses: list[PoseNeed] = Field(
        default_factory=list,
        description="All character poses the Art Agent must draw",
    )


class LevelMap(BaseModel):
    id: str
    name: str
    width: int
    height: int
    rows: list[str]
    legend: dict[str, str] = Field(
        default_factory=lambda: {
            "#": "solid",
            ".": "empty",
            "S": "player_spawn",
            "X": "exit",
            "C": "carrot",
            "G": "easter_egg",
            "N": "snake",
            "=": "platform",
        }
    )
    notes: str = ""
    music_id: str = Field(
        default="",
        description="Id of background_music track for this level",
    )


class ArtShoppingList(BaseModel):
    characters: list[str]
    tiles: list[str]
    items: list[str]
    backgrounds: list[str]
    ui: list[str] = Field(default_factory=list)


class LevelsDoc(BaseModel):
    game_type: GameType
    tile_size: int = 32
    levels: list[LevelMap]
    art_shopping_list: ArtShoppingList
    layout_notes: list[str] = Field(default_factory=list)
    background_music: list[MusicTrack] = Field(
        default_factory=list,
        description="One mood track per level for the Sound Agent",
    )


class Palette(BaseModel):
    primary: str = "#f8bbd0"
    secondary: str = "#80cbc4"
    accent: str = "#ff7043"
    dark: str = "#37474f"
    light: str = "#fff8e1"
    enemy: str = "#66bb6a"
    hazard: str = "#ef5350"


class SpriteSpec(BaseModel):
    """One named sprite cell with a detailed brief for the HTML Art Agent."""

    id: str
    character_id: str
    action: str
    facing: Facing
    description: str = Field(
        description="Detailed visual brief: body, face, limbs, gloves, facing direction, action silhouette"
    )


class ArtBundle(BaseModel):
    style_notes: str
    palette: Palette
    sprites: list[SpriteSpec] = Field(
        description="Every character pose with a rich description for HTML/SVG art"
    )
    item_ids: list[str] = Field(default_factory=lambda: ["carrot", "easter_egg", "heart"])
    tile_ids: list[str] = Field(default_factory=lambda: ["grass", "dirt", "platform"])


class HtmlSpriteOut(BaseModel):
    html: str = Field(description="Full standalone HTML document with detailed SVG character")
    notes: str = ""


class CriticFeedback(BaseModel):
    ok: bool
    issues: list[str] = Field(default_factory=list)
    revision_instructions: str = Field(
        default="",
        description="Concrete HTML/SVG edits to fix the issues",
    )


class AssemblerPlan(BaseModel):
    game_folder_name: str
    html_title: str
    subtitle: str
    hud_labels: dict[str, str] = Field(
        default_factory=lambda: {"hp": "HP", "punch": "Punch", "level": "Level"}
    )
    win_text: str
    lose_text: str
    notes_for_player: list[str] = Field(default_factory=list)


class BlipRecipe(BaseModel):
    """jsfxr-style params the Sound Agent emits; blips.py turns them into WAV."""

    id: str
    wave: Literal["square", "saw", "sine", "noise"] = "square"
    start_freq_hz: float = 440.0
    end_freq_hz: float = 220.0
    duration_ms: int = Field(default=120, ge=30, le=2000)
    volume: float = Field(default=0.45, ge=0.05, le=1.0)
    attack_ms: int = Field(default=5, ge=0, le=200)
    decay_ms: int = Field(default=80, ge=10, le=1500)
    vibrato_hz: float = 0.0
    vibrato_depth: float = 0.0
    noise_amount: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str = ""


class MusicRecipe(BaseModel):
    """Simple chiptune loop params for background music."""

    id: str
    level_id: str
    root_midi: int = Field(default=60, ge=36, le=84)
    scale: Literal["major", "minor", "pentatonic"] = "major"
    tempo_bpm: int = Field(default=120, ge=60, le=200)
    bars: int = Field(default=4, ge=2, le=8)
    wave: Literal["square", "triangle", "sine"] = "square"
    volume: float = Field(default=0.18, ge=0.05, le=0.4)
    mood_note: str = ""


class SoundBundle(BaseModel):
    """Output of the Sound Agent — synthesis recipes, not final WAVs."""

    style_notes: str = ""
    sfx: list[BlipRecipe] = Field(default_factory=list)
    music: list[MusicRecipe] = Field(default_factory=list)


class StudioReport(BaseModel):
    output_dir: str
    files_created: list[str]
    how_to_run: str
    summary: str
    elapsed_seconds: float = 0.0
    elapsed_human: str = ""
