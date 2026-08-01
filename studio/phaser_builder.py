"""Write a playable Phaser 3 CDN project from pipeline JSON."""

from __future__ import annotations

import json
from pathlib import Path

from .models import AssemblerPlan, ConceptDoc, LevelsDoc, MechanicsDoc


def build_phaser_project(
    out_dir: Path,
    concept: ConceptDoc,
    mechanics: MechanicsDoc,
    levels: LevelsDoc,
    plan: AssemblerPlan,
) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "js").mkdir(exist_ok=True)
    (out_dir / "data").mkdir(exist_ok=True)
    (out_dir / "assets").mkdir(exist_ok=True)

    files: list[str] = []

    def dump(rel: str, data) -> None:
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        files.append(rel)

    dump("data/concept.json", concept.model_dump())
    dump("data/mechanics.json", mechanics.model_dump())
    dump("data/levels.json", levels.model_dump())

    dump("index.html", _index_html(plan.html_title))
    dump("js/main.js", _main_js(plan, concept))
    dump("js/Player.js", _player_js(concept.game_type))
    dump("js/LevelScene.js", _level_scene_js(concept.game_type))
    dump("README.md", _readme(plan, concept))

    return files


def _index_html(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    html, body {{ margin: 0; height: 100%; background: #1a1b26; color: #eee;
      font-family: Georgia, "Times New Roman", serif; overflow: hidden; }}
    #game-parent {{ width: 100%; height: 100%; display: grid; place-items: center; }}
    canvas {{ image-rendering: pixelated; }}
  </style>
</head>
<body>
  <div id="game-parent"></div>
  <script src="https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.js"></script>
  <script src="js/Player.js"></script>
  <script src="js/LevelScene.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
"""


def _main_js(plan: AssemblerPlan, concept: ConceptDoc) -> str:
    # BootScene MUST be declared before config references it (class TDZ).
    return f"""/* global Phaser, LevelScene */
const GAME_META = {{
  title: {json.dumps(plan.html_title)},
  subtitle: {json.dumps(plan.subtitle)},
  gameType: {json.dumps(concept.game_type)},
  winText: {json.dumps(plan.win_text)},
  loseText: {json.dumps(plan.lose_text)},
  hud: {json.dumps(plan.hud_labels)},
  tips: {json.dumps(plan.notes_for_player)},
}};

class BootScene extends Phaser.Scene {{
  constructor() {{ super("boot"); }}
  preload() {{
    this.load.json("concept", "data/concept.json");
    this.load.json("mechanics", "data/mechanics.json");
    this.load.json("levels", "data/levels.json");
    this.load.json("frameMap", "data/frame_map.json");
    this.load.spritesheet("player", "assets/player_sheet.png", {{ frameWidth: 64, frameHeight: 64 }});
    this.load.spritesheet("snake", "assets/snake_sheet.png", {{ frameWidth: 64, frameHeight: 64 }});
    this.load.spritesheet("items", "assets/items_sheet.png", {{ frameWidth: 64, frameHeight: 64 }});
    this.load.spritesheet("tiles", "assets/tileset_sheet.png", {{ frameWidth: 32, frameHeight: 32 }});
    this.load.image("bg", "assets/bg_sheet.png");
  }}
  create() {{
    const fmap = this.cache.json.get("frameMap") || {{}};
    const mk = (key, texture, frame) => {{
      if (!this.anims.exists(key)) {{
        this.anims.create({{ key, frames: [{{ key: texture, frame }}], frameRate: 8 }});
      }}
    }};
    const playerFrames = (fmap.player && fmap.player.frames) || [];
    playerFrames.forEach((f) => {{
      mk(`player-${{f.action}}-${{f.facing}}`, "player", f.index);
      mk(`player-${{f.action}}`, "player", f.index);
    }});
    ["idle","run","jump","punch","hurt"].forEach((a, i) => {{
      const idx = playerFrames.length ? Math.min(i, playerFrames.length - 1) : 0;
      mk(`player-${{a}}`, "player", idx);
    }});
    const snakeFrames = Object.keys(fmap).filter((k) => k !== "player");
    const snakeKey = snakeFrames[0];
    const sframes = (snakeKey && fmap[snakeKey].frames) || [{{ index: 0, action: "move", facing: "right" }}];
    sframes.forEach((f) => mk(`snake-${{f.action}}`, "snake", f.index));
    mk("snake-move", "snake", sframes[0].index);
    this.registry.set("frameMap", fmap);
    this.scene.start("level", {{ levelIndex: 0 }});
  }}
}}

const config = {{
  type: Phaser.AUTO,
  parent: "game-parent",
  width: 960,
  height: 540,
  backgroundColor: "#87ceeb",
  physics: {{
    default: "arcade",
    arcade: {{
      gravity: {{ y: GAME_META.gameType === "side_scroller" ? 1000 : 0 }},
      debug: false,
    }},
  }},
  scene: [BootScene, LevelScene],
  scale: {{ mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }},
}};

window.addEventListener("load", () => {{
  // eslint-disable-next-line no-new
  new Phaser.Game(config);
}});
"""


def _player_js(game_type: str) -> str:
    side = game_type == "side_scroller"
    return f"""/* global Phaser, GAME_META */
class PlayerController {{
  constructor(scene, x, y, mechanics) {{
    this.scene = scene;
    this.m = mechanics;
    this.hp = mechanics.player.max_hp;
    this.punchBonus = 0;
    this.invulnUntil = 0;
    this.nextAttack = 0;
    this.facing = 1;

    this.sprite = scene.physics.add.sprite(x, y, "player", 0);
    this.sprite.setCollideWorldBounds(true);
    this.sprite.setBounce(0.05);
    this.sprite.body.setSize(28, 40);
    this.sprite.body.setOffset(18, 18);
    this.sprite.setDepth(10);
    if ({str(side).lower()}) {{
      this.sprite.body.setGravityY(0); // world gravity handles it
    }} else {{
      this.sprite.body.setAllowGravity(false);
    }}

    this.cursors = scene.input.keyboard.createCursorKeys();
    this.keys = scene.input.keyboard.addKeys("W,A,S,D,J,K,SPACE");
  }}

  get damage() {{
    return this.m.player.attack_damage + this.punchBonus;
  }}

  update(time) {{
    const speed = this.m.player.speed;
    const body = this.sprite.body;
    let ax = 0;
    let ay = 0;
    if (this.cursors.left.isDown || this.keys.A.isDown) ax = -1;
    else if (this.cursors.right.isDown || this.keys.D.isDown) ax = 1;

    if (GAME_META.gameType === "top_down") {{
      if (this.cursors.up.isDown || this.keys.W.isDown) ay = -1;
      else if (this.cursors.down.isDown || this.keys.S.isDown) ay = 1;
      body.setVelocity(ax * speed, ay * speed);
    }} else {{
      body.setVelocityX(ax * speed);
      const jumpPressed = Phaser.Input.Keyboard.JustDown(this.keys.SPACE)
        || Phaser.Input.Keyboard.JustDown(this.keys.W)
        || Phaser.Input.Keyboard.JustDown(this.cursors.up);
      if (jumpPressed && body.blocked.down) {{
        body.setVelocityY(this.m.player.jump_velocity);
      }}
    }}

    if (ax !== 0) {{
      this.facing = ax;
      // Prefer dedicated left/right frames; only flip if left anim missing
      this.sprite.setFlipX(false);
    }}

    const face = this.facing < 0 ? "left" : "right";
    const play = (action) => {{
      const keyed = `player-${{action}}-${{face}}`;
      if (this.scene.anims.exists(keyed)) {{
        this.sprite.anims.play(keyed, true);
      }} else if (this.scene.anims.exists(`player-${{action}}`)) {{
        this.sprite.anims.play(`player-${{action}}`, true);
        this.sprite.setFlipX(this.facing < 0);
      }}
    }};

    const attack = Phaser.Input.Keyboard.JustDown(this.keys.J)
      || Phaser.Input.Keyboard.JustDown(this.keys.K);
    if (attack && time >= this.nextAttack) {{
      this.nextAttack = time + this.m.player.attack_cooldown_ms;
      play("punch");
      this.scene.onPlayerAttack(this);
      return;
    }}

    if (time < this.invulnUntil) {{
      play("hurt");
      this.sprite.setAlpha(0.55);
      return;
    }}
    this.sprite.setAlpha(1);

    if (GAME_META.gameType === "side_scroller" && !body.blocked.down) {{
      play("jump");
    }} else if (ax !== 0 || (GAME_META.gameType === "top_down" && ay !== 0)) {{
      play("run");
    }} else {{
      play("idle");
    }}
  }}

  hurt(amount, time) {{
    if (time < this.invulnUntil) return false;
    this.hp -= amount;
    this.invulnUntil = time + this.m.player.invuln_ms;
    this.sprite.setVelocityY(GAME_META.gameType === "side_scroller" ? -220 : 0);
    this.sprite.setVelocityX(-this.facing * 180);
    return true;
  }}
}}
"""


def _level_scene_js(game_type: str) -> str:
    return r"""/* global Phaser, GAME_META, PlayerController */
class LevelScene extends Phaser.Scene {
  constructor() { super("level"); }

  init(data) {
    this.levelIndex = data.levelIndex || 0;
  }

  create() {
    this.concept = this.cache.json.get("concept");
    this.mechanics = this.cache.json.get("mechanics");
    this.levelsDoc = this.cache.json.get("levels");
    this.level = this.levelsDoc.levels[this.levelIndex];
    this.tileSize = this.levelsDoc.tile_size || 32;
    this.gameOver = false;

    const mapW = this.level.width * this.tileSize;
    const mapH = this.level.height * this.tileSize;
    this.physics.world.setBounds(0, 0, mapW, mapH);
    this.cameras.main.setBounds(0, 0, mapW, mapH);

    this.add.tileSprite(0, 0, mapW, mapH, "bg").setOrigin(0, 0).setScrollFactor(0.3).setDepth(-10);

    this.solid = this.physics.add.staticGroup();
    this.exits = this.physics.add.staticGroup();
    this.carrots = this.physics.add.staticGroup();
    this.eggs = this.physics.add.staticGroup();
    this.snakes = this.physics.add.group();

    let spawn = { x: 64, y: 64 };
    this.level.rows.forEach((row, ty) => {
      [...row].forEach((ch, tx) => {
        const x = tx * this.tileSize + this.tileSize / 2;
        const y = ty * this.tileSize + this.tileSize / 2;
        if (ch === "#" || ch === "=") {
          const frame = ch === "=" ? 2 : (ty > 0 && this.level.rows[ty - 1][tx] === "#" ? 1 : 0);
          const t = this.solid.create(x, y, "tiles", frame);
          t.refreshBody();
        } else if (ch === "S") {
          spawn = { x, y };
        } else if (ch === "X") {
          const e = this.exits.create(x, y, "items", 2);
          e.setScale(0.7);
          e.refreshBody();
        } else if (ch === "C") {
          const c = this.carrots.create(x, y, "items", 0);
          c.setScale(0.55);
          c.refreshBody();
        } else if (ch === "G") {
          const g = this.eggs.create(x, y, "items", 1);
          g.setScale(0.55);
          g.refreshBody();
        } else if (ch === "N") {
          const s = this.snakes.create(x, y, "snake", 0);
          s.setScale(0.85);
          s.body.setAllowGravity(GAME_META.gameType === "side_scroller");
          s.setCollideWorldBounds(true);
          s.setBounce(1, 0);
          s.setVelocityX(this.enemySpeed() * (Math.random() < 0.5 ? -1 : 1));
          s.anims.play("snake-move");
          s.hp = this.enemyHp();
        }
      });
    });

    this.player = new PlayerController(this, spawn.x, spawn.y, this.mechanics);
    this.cameras.main.startFollow(this.player.sprite, true, 0.12, 0.12);

    this.physics.add.collider(this.player.sprite, this.solid);
    this.physics.add.collider(this.snakes, this.solid);
    this.physics.add.overlap(this.player.sprite, this.carrots, this.collectCarrot, null, this);
    this.physics.add.overlap(this.player.sprite, this.eggs, this.collectEgg, null, this);
    this.physics.add.overlap(this.player.sprite, this.exits, this.reachExit, null, this);
    this.physics.add.overlap(this.player.sprite, this.snakes, this.touchSnake, null, this);

    this.hud = this.add.text(12, 10, "", {
      fontFamily: "Georgia, serif",
      fontSize: "18px",
      color: "#1b1b1b",
      backgroundColor: "#ffffffaa",
      padding: { x: 8, y: 6 },
    }).setScrollFactor(0).setDepth(100);

    this.banner = this.add.text(480, 40, `${GAME_META.title} — ${this.level.name}`, {
      fontFamily: "Georgia, serif",
      fontSize: "22px",
      color: "#fff",
      stroke: "#000",
      strokeThickness: 4,
    }).setOrigin(0.5).setScrollFactor(0).setDepth(100);

    this.status = this.add.text(480, 270, "", {
      fontFamily: "Georgia, serif",
      fontSize: "36px",
      color: "#fff",
      stroke: "#000",
      strokeThickness: 6,
      align: "center",
    }).setOrigin(0.5).setScrollFactor(0).setDepth(101).setVisible(false);
  }

  enemyStats() {
    const list = this.mechanics.enemies || [];
    return list.find((x) => String(x.id).includes("snake")) || list[0] || {
      speed: 70, hp: 1, damage: 1,
    };
  }

  enemySpeed() { return this.enemyStats().speed || 70; }
  enemyHp() { return this.enemyStats().hp || 1; }
  enemyDamage() { return this.enemyStats().damage || 1; }

  collectCarrot(_p, carrot) {
    carrot.destroy();
    const item = (this.mechanics.items || []).find((x) => x.id === "carrot");
    const heal = item ? item.value : 1;
    this.player.hp = Math.min(this.mechanics.player.max_hp, this.player.hp + heal);
  }

  collectEgg(_p, egg) {
    egg.destroy();
    const item = (this.mechanics.items || []).find((x) => x.id === "easter_egg");
    this.player.punchBonus += item ? item.value : 1;
  }

  reachExit() {
    if (this.gameOver) return;
    const next = this.levelIndex + 1;
    if (next < this.levelsDoc.levels.length) {
      this.scene.restart({ levelIndex: next });
    } else {
      this.endGame(true);
    }
  }

  touchSnake(playerSprite, snake) {
    if (this.gameOver) return;
    const time = this.time.now;
    const stomp = GAME_META.gameType === "side_scroller"
      && playerSprite.body.velocity.y > 0
      && playerSprite.y < snake.y - 8;
    if (stomp) {
      snake.hp -= 1;
      playerSprite.setVelocityY(-280);
      if (snake.hp <= 0) snake.destroy();
      return;
    }
    if (this.player.hurt(this.enemyDamage(), time) && this.player.hp <= 0) {
      this.endGame(false);
    }
  }

  onPlayerAttack(player) {
    const range = 42;
    const px = player.sprite.x + player.facing * 28;
    const py = player.sprite.y;
    this.snakes.getChildren().forEach((snake) => {
      if (!snake.active) return;
      const dx = snake.x - px;
      const dy = snake.y - py;
      if (Math.abs(dx) < range && Math.abs(dy) < 36) {
        snake.hp -= player.damage;
        snake.setVelocityX(player.facing * 120);
        if (snake.hp <= 0) snake.destroy();
      }
    });
  }

  endGame(won) {
    this.gameOver = true;
    this.status.setText(won ? GAME_META.winText : GAME_META.loseText);
    this.status.setVisible(true);
    this.player.sprite.setVelocity(0, 0);
    this.time.delayedCall(1800, () => {
      if (won) this.scene.restart({ levelIndex: 0 });
      else this.scene.restart({ levelIndex: this.levelIndex });
    });
  }

  update(time) {
    if (this.gameOver) return;
    this.player.update(time);
    if (GAME_META.gameType === "side_scroller" && this.player.sprite.y > this.physics.world.bounds.height + 40) {
      this.endGame(false);
      return;
    }
    this.snakes.getChildren().forEach((s) => {
      if (!s.body) return;
      if (s.body.blocked.left) s.setVelocityX(this.enemySpeed());
      if (s.body.blocked.right) s.setVelocityX(-this.enemySpeed());
    });
    this.hud.setText(
      `${GAME_META.hud.level}: ${this.level.name}\n` +
      `${GAME_META.hud.hp}: ${this.player.hp}/${this.mechanics.player.max_hp}   ` +
      `${GAME_META.hud.punch}: ${this.player.damage}\n` +
      `Move + ${GAME_META.gameType === "side_scroller" ? "Space jump" : "WASD"} · J/K punch · stomp snakes`
    );
  }
}
"""


def _readme(plan: AssemblerPlan, concept: ConceptDoc) -> str:
    tips = "\n".join(f"- {t}" for t in plan.notes_for_player) or "- Have fun"
    return f"""# {plan.html_title}

{plan.subtitle}

**Type:** {concept.game_type}

## Story
{concept.pitch}

## How to run
```bash
cd {plan.game_folder_name}
npx --yes serve .
```
Then open the printed localhost URL (do not use `file://`).

## Controls
- Move: arrows / WASD
- Jump (side-scroller): Space / W / Up
- Punch: J / K
- Stomp snakes from above (side-scroller)

## Tips
{tips}
"""
