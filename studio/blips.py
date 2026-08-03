"""Procedural blip / chiptune synth (jsfxr-style) — pure Python, no deps."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

from .models import BlipRecipe, MusicRecipe, MusicTrack, SfxCue, SoundBundle

SAMPLE_RATE = 22050


def write_wav(path: Path, samples: list[float], sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s))
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(frames)


def _envelope(i: int, n: int, attack: int, decay: int) -> float:
    if n <= 0:
        return 0.0
    if attack > 0 and i < attack:
        return i / attack
    # linear decay toward end
    remain = n - i
    if decay > 0 and remain < decay:
        return max(0.0, remain / decay)
    return 1.0


def synth_blip(recipe: BlipRecipe, sample_rate: int = SAMPLE_RATE) -> list[float]:
    n = max(1, int(sample_rate * recipe.duration_ms / 1000.0))
    attack = int(sample_rate * recipe.attack_ms / 1000.0)
    decay = int(sample_rate * recipe.decay_ms / 1000.0)
    phase = 0.0
    out: list[float] = []
    rng = random.Random(hash(recipe.id) & 0xFFFFFFFF)

    for i in range(n):
        t = i / max(1, n - 1)
        freq = recipe.start_freq_hz + (recipe.end_freq_hz - recipe.start_freq_hz) * t
        if recipe.vibrato_hz > 0 and recipe.vibrato_depth > 0:
            freq *= 1.0 + recipe.vibrato_depth * math.sin(
                2 * math.pi * recipe.vibrato_hz * (i / sample_rate)
            )
        phase += 2 * math.pi * max(20.0, freq) / sample_rate
        wave_name = recipe.wave
        if wave_name == "square":
            sig = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave_name == "saw":
            sig = 2.0 * ((phase / (2 * math.pi)) % 1.0) - 1.0
        elif wave_name == "noise":
            sig = rng.uniform(-1.0, 1.0)
        else:  # sine
            sig = math.sin(phase)
        if recipe.noise_amount > 0 and wave_name != "noise":
            sig = sig * (1.0 - recipe.noise_amount) + rng.uniform(-1, 1) * recipe.noise_amount
        env = _envelope(i, n, attack, decay)
        out.append(sig * recipe.volume * env)
    return out


# C major-ish intervals from root
_SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
}


def _midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def synth_music(recipe: MusicRecipe, sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Short looping 8-bit-ish arpeggio / melody for level BGM."""
    scale = _SCALES.get(recipe.scale, _SCALES["major"])
    # 4 beats/bar, 2 notes per beat arpeggio feel
    notes_per_bar = 8
    total_notes = recipe.bars * notes_per_bar
    beat_sec = 60.0 / max(60, recipe.tempo_bpm)
    note_sec = beat_sec / 2.0
    note_samples = max(1, int(sample_rate * note_sec))

    # simple walk up/down the scale with a few octave hops
    pattern = []
    for i in range(total_notes):
        deg = scale[i % len(scale)]
        octave = 12 if (i // len(scale)) % 2 else 0
        if i % 7 == 3:
            midi = recipe.root_midi - 12 + scale[0]  # drone bass blip
        else:
            midi = recipe.root_midi + deg + octave
        pattern.append(midi)

    out: list[float] = []
    for midi in pattern:
        n = note_samples
        attack = max(1, int(0.02 * sample_rate))
        decay = max(1, int(0.5 * n))
        phase = 0.0
        freq = _midi_to_hz(midi)
        for i in range(n):
            phase += 2 * math.pi * freq / sample_rate
            if recipe.wave == "triangle":
                # triangle from phase
                u = (phase / (2 * math.pi)) % 1.0
                sig = 4 * abs(u - 0.5) - 1.0
            elif recipe.wave == "sine":
                sig = math.sin(phase)
            else:
                sig = 1.0 if math.sin(phase) >= 0 else -1.0
            env = _envelope(i, n, attack, decay) * 0.85
            # soft fade last notes of loop for cleaner restart
            out.append(sig * recipe.volume * env)
    return out


# --- defaults when the LLM underspecifies ---

_DEFAULT_SFX: dict[str, BlipRecipe] = {
    "jump": BlipRecipe(
        id="jump", wave="square", start_freq_hz=320, end_freq_hz=620,
        duration_ms=110, attack_ms=5, decay_ms=90, volume=0.4,
    ),
    "punch": BlipRecipe(
        id="punch", wave="noise", start_freq_hz=180, end_freq_hz=90,
        duration_ms=90, attack_ms=2, decay_ms=80, volume=0.5, noise_amount=1.0,
    ),
    "hurt": BlipRecipe(
        id="hurt", wave="saw", start_freq_hz=260, end_freq_hz=90,
        duration_ms=180, attack_ms=5, decay_ms=150, volume=0.4,
    ),
    "stomp": BlipRecipe(
        id="stomp", wave="square", start_freq_hz=200, end_freq_hz=80,
        duration_ms=100, attack_ms=3, decay_ms=90, volume=0.45, noise_amount=0.3,
    ),
    "pickup_heal": BlipRecipe(
        id="pickup_heal", wave="sine", start_freq_hz=520, end_freq_hz=780,
        duration_ms=140, attack_ms=8, decay_ms=100, volume=0.4,
    ),
    "pickup_power": BlipRecipe(
        id="pickup_power", wave="square", start_freq_hz=400, end_freq_hz=900,
        duration_ms=160, attack_ms=8, decay_ms=120, volume=0.4, vibrato_hz=12, vibrato_depth=0.05,
    ),
    "win": BlipRecipe(
        id="win", wave="square", start_freq_hz=440, end_freq_hz=880,
        duration_ms=320, attack_ms=10, decay_ms=200, volume=0.4,
    ),
    "lose": BlipRecipe(
        id="lose", wave="saw", start_freq_hz=300, end_freq_hz=80,
        duration_ms=400, attack_ms=15, decay_ms=300, volume=0.4,
    ),
}


def default_sfx_cues(game_type: str = "side_scroller") -> list[SfxCue]:
    cues = [
        SfxCue(id="jump", trigger="player jumps", mood="soft bouncy cotton hop", category="player"),
        SfxCue(id="punch", trigger="player attacks", mood="glove thwack", category="combat"),
        SfxCue(id="hurt", trigger="player takes damage", mood="soft flinch oof", category="player"),
        SfxCue(id="stomp", trigger="enemy defeated by stomp or punch", mood="tiny pop defeat", category="combat"),
        SfxCue(id="pickup_heal", trigger="collect carrot / heal item", mood="bright healthy chime", category="pickup"),
        SfxCue(id="pickup_power", trigger="collect power-up egg", mood="sparkly power-up arpeggio", category="pickup"),
        SfxCue(id="win", trigger="all levels cleared", mood="happy farmyard fanfare blip", category="ui"),
        SfxCue(id="lose", trigger="player dies or falls", mood="sad descending flop", category="ui"),
    ]
    if game_type == "top_down":
        cues[0] = SfxCue(id="jump", trigger="unused in top-down (kept for schema)", mood="quiet click", category="ui")
    return cues


def default_music_tracks(level_ids: list[str]) -> list[MusicTrack]:
    moods = [
        ("sunny meadow stroll", 118),
        ("braver chase, slightly darker", 132),
        ("victory harvest festival", 124),
    ]
    tracks: list[MusicTrack] = []
    for i, lid in enumerate(level_ids):
        mood, bpm = moods[i % len(moods)]
        tid = lid if lid else f"level_{i + 1}"
        tracks.append(
            MusicTrack(
                id=tid,
                level_id=lid,
                mood=mood,
                tempo_bpm=bpm,
                loop=True,
                notes="chiptune loop for level",
            )
        )
    return tracks


def recipe_from_cue(cue: SfxCue) -> BlipRecipe:
    base = _DEFAULT_SFX.get(cue.id)
    if base:
        r = base.model_copy()
        r.notes = cue.mood
        # nudge frequency slightly from mood text
        nudge = (sum(ord(c) for c in cue.mood) % 40) - 20
        r.start_freq_hz = max(80.0, r.start_freq_hz + nudge)
        r.end_freq_hz = max(60.0, r.end_freq_hz + nudge * 0.5)
        return r
    # generic soft blip
    return BlipRecipe(
        id=cue.id,
        wave="square",
        start_freq_hz=360,
        end_freq_hz=240,
        duration_ms=120,
        notes=cue.mood,
    )


def recipe_from_track(track: MusicTrack) -> MusicRecipe:
    mood_l = track.mood.lower()
    if any(w in mood_l for w in ("dark", "danger", "chase", "cave", "night")):
        scale, root = "minor", 55
        wave: str = "square"
    elif any(w in mood_l for w in ("festival", "win", "bright", "spark")):
        scale, root = "pentatonic", 64
        wave = "triangle"
    else:
        scale, root = "major", 60
        wave = "square"
    return MusicRecipe(
        id=track.id,
        level_id=track.level_id,
        root_midi=root,
        scale=scale,  # type: ignore[arg-type]
        tempo_bpm=track.tempo_bpm or 120,
        bars=4,
        wave=wave,  # type: ignore[arg-type]
        volume=0.16,
        mood_note=track.mood,
    )


def fill_sound_bundle(
    sfx_cues: list[SfxCue],
    music_tracks: list[MusicTrack],
    agent_bundle: SoundBundle | None = None,
) -> SoundBundle:
    """Merge agent recipes with defaults so every cue/track has a recipe."""
    agent = agent_bundle or SoundBundle()
    by_sfx = {r.id: r for r in agent.sfx}
    by_bgm = {r.id: r for r in agent.music}

    sfx_out: list[BlipRecipe] = []
    for cue in sfx_cues:
        sfx_out.append(by_sfx.get(cue.id) or recipe_from_cue(cue))

    # ensure core ids always present
    have = {r.id for r in sfx_out}
    for cid, default in _DEFAULT_SFX.items():
        if cid not in have:
            sfx_out.append(default)

    music_out: list[MusicRecipe] = []
    for track in music_tracks:
        music_out.append(by_bgm.get(track.id) or recipe_from_track(track))

    return SoundBundle(
        style_notes=agent.style_notes or "cute 8-bit blips and short chiptune loops",
        sfx=sfx_out,
        music=music_out,
    )


def render_sound_bundle(bundle: SoundBundle, assets_dir: Path) -> list[str]:
    """Write assets/sfx_*.wav and assets/bgm_*.wav. Returns relative paths from game root."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for r in bundle.sfx:
        write_wav(assets_dir / f"sfx_{r.id}.wav", synth_blip(r))
        files.append(f"assets/sfx_{r.id}.wav")
    for m in bundle.music:
        write_wav(assets_dir / f"bgm_{m.id}.wav", synth_music(m))
        files.append(f"assets/bgm_{m.id}.wav")
    return files
