# 2D Game Studio (PydanticAI → Phaser)

Agent pipeline from the Sasin *2D Games with AI Agents* lecture: concept → mechanics → levels → HTML sprites (with critic) → Phaser 3 CDN game.

## Layout

```
studio/                 # Python package (orchestrator + agents)
briefs/                 # Example game briefs (JSON)
games/                  # Generated playable games (gitignored)
requirements.txt
.env.example
```

## Setup

```bash
git clone <your-repo-url>
cd <repo>
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### API key

Put `OPENAI_API_KEY` in **either**:

- `.env` in the **repo root** (folder above `studio/`), or  
- `studio/.env`

(`.env` is gitignored. Copy from `.env.example`.)

```bash
cp .env.example .env
# edit .env and paste your key
```

## Run

From the **repo root**:

```bash
# Cheap draft (default model: gpt-5.6-luna)
python -m studio briefs/rabbit_side_scroller.json --name rabbit_punch_valley_luna

# Stronger model into its own folder
python -m studio briefs/rabbit_side_scroller.json --model gpt-5.6-terra --name rabbit_punch_valley_terra
python -m studio briefs/rabbit_side_scroller.json --model gpt-5.6-sol --name rabbit_punch_valley_sol
```

### Flags

| Flag | Meaning |
|------|---------|
| `--model` | OpenAI model id (`gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, or `openai:…`) |
| `--name` | Output folder under `games/` |
| `--art-from` | Rebuild art from an existing game’s `data/` |
| `--critic-rounds` | Critic revise loops (default `1`) |
| `--root` | Workspace root (default: cwd) |

### Play the game

```bash
cd games/rabbit_punch_valley_luna
npx --yes serve .
```

Open the printed `http://localhost:…` URL — do **not** use `file://`.

## Pipeline

1. **Concept Agent** → `data/concept.json`
2. **Mechanics Agent** → `data/mechanics.json` (includes `sprite_poses`)
3. **Levels Agent** → `data/levels.json` + `layout_preview.html`
4. **Art Agent** → pose names + detailed descriptions
5. **HTML + Critic** → lock `*_base.html` → pose from that HTML (parallel) → screenshots → sprite sheets
6. **Assembler** → Phaser 3 CDN project

Supports `side_scroller` and `top_down` via the brief’s `game_type`.

Model used is written to `data/run_meta.json`.

## Cost note (tiny rabbit demo)

Same brief (2 levels, one snake type), ballpark:

| Model | Cost | Time | Notes |
|-------|------|------|--------|
| luna | ~$0.15 | ~1–2 min | Cheapest; sprites often uglier |
| terra | ~$1.50 | ~1–2 min | Similar quality to sol on this demo |
| sol | ~$5.50 | ~5 min | Slow + spendy for similar look |

## License

Course / teaching material — add a license of your choice before publishing publicly.
