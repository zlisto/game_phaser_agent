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


class MechanicsDoc(BaseModel):
    game_type: GameType
    controls: KeyMap
    player: PlayerStats
    enemies: list[EnemyStats]
    items: list[ItemEffect]
    win_condition: str
    lose_condition: str
    juice_notes: list[str] = Field(default_factory=list)
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


class StudioReport(BaseModel):
    output_dir: str
    files_created: list[str]
    how_to_run: str
    summary: str
