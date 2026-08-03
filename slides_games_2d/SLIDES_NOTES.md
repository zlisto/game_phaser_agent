# Slide style notes (Sasin lectures)

Conventions for Tauhid Zaman lecture decks. Canonical reference: `lecture_sprites_with_ai.html`. Copy its `<style>` block and stack; keep this aesthetic for other topics.

---

## Stack & Reveal config

- **reveal.js 5.2.1** via jsDelivr CDN:
  - `reset.css` → `reveal.css` → `theme/dracula.css` (`id="theme"`)
  - `reveal.js` script at bottom
- Custom overrides in one `<style>` block **on top of** Dracula — do not invent a second visual system
- Init (copy verbatim unless you have a reason):

```js
Reveal.initialize({
  hash: true,
  slideNumber: "c/t",
  showNotes: false,
  transition: "fade",
  backgroundTransition: "fade",
  width: 1280,
  height: 720,
  margin: 0.08,
  center: false,          // content top-left, not vertically centered
  controls: true,
  progress: true,
});
```

- Navigation: arrows / Space; slide numbers as `c/t`
- `center: false` is load-bearing — with `center: true`, dense `.fill` slides look wrong

---

## Global typography & layout chrome

Set on `.reveal` (not per-slide hacks):

| Token | Value | Notes |
|-------|--------|--------|
| Base font | `28px` | Classroom-readable |
| Slide text align | `left` | Title slide overrides to center |
| `h1` / `h2` / `h3` | `text-transform: none`, `letter-spacing: -0.02em` | No shouty ALL CAPS titles |
| `h1` | `2.4em` | Title slide uses `2.2em` via `.title-slide h1` |
| `h2` | `1.45em`, `margin-bottom: 0.3em` | One claim per slide |
| `h3` | `1.02em`, color `#bd93f9` | Card / section subheads |
| `p` / `li` | `line-height: 1.35` | Tight but readable |
| `ul` | `display: block`, `margin-left: 1.05em` | |

**Do not** use Dracula’s default uppercase headings. Override them.

---

## Color tokens (Dracula accents)

Use these as utility classes and component colors. Prefer the named utilities over one-off hex in markup.

| Role | Hex | Class / where |
|------|-----|----------------|
| Eyebrow / accents / block-foot | `#8be9fd` | `.eyebrow`, `.block-foot` |
| Headings in cards / byline | `#bd93f9` | `h3`, `.purple`, `.byline`, `.card.soft` border |
| Emphasis / don’t / note border | `#ff79c6` | `.pink`, `.note` border, `.vs` circle |
| Success / do | `#50fa7b` | `.green`, parallel `.box.para` border |
| Warm labels / kickers | `#ffb86c` | `.orange`, `.kicker` |
| Quotes / strip titles | `#f1fa8c` | `.quote`, `strip .card strong` |
| Muted / labels | `#6272a4` | `.muted`, `.label` |
| Danger / hard don’t | `#ff5555` | `.red` |
| Body text | `#f8f8f2` | notes, codeish |
| Card bg | `#21222c` | `.card`, `.sheet`, `.codeish`, flow steps |
| Soft / parallel bg | `#282a36` | `.card.soft`, `.box.para` |
| Borders | `#44475a` | cards, sheets, strip dividers |
| Diagram void | `#191a21` | `.game-diagram` bg, thumb bg |

Utility classes already in the CSS: `.muted` `.pink` `.red` `.green` `.orange` `.purple`.

---

## Spatial aesthetic (fill the slide)

Default content slides should feel **dense**, not sparse. Avoid a big empty lower third.

- Mark content slides with **`class="fill"`** on `<section>` — this unlocks grid min-heights and stretch behavior
- Prefer **taller cards with several bullets** over one short sentence floating in space
- Almost every content slide ends with a **strip** and/or a **note** so the bottom edge isn’t empty
- One idea per slide; densify with **structure** (grids, strips, pairs), not more topics

### Preferred anatomy (content slide)

1. **`.eyebrow`** — short section label (cyan), uppercase, tracked; no lecture clocks  
2. **`h2`** — one clear claim  
3. Optional one-line **`.muted`** lede (small) if a term needs a reminder  
4. **Main grid** — `grid-2` / `grid-3` / `grid-4` of **`.card`**s that stretch and fill  
5. Optional **`.strip`** (default 4 cols) or **`.strip.cols-3`** — compact recap / sequence  
6. Optional **`.note`** — one pink left-border takeaway at the bottom  

### Title slide exception

```html
<section class="center-slide title-slide">
  <h1>…</h1>
  <p class="byline">Tauhid Zaman</p>   <!-- name only, purple -->
  <div class="title-hero">…optional SVG/img…</div>
</section>
```

- Centered: **title**, **name only**, optional hero visual (`.title-hero`, max ~620px)
- No agenda chips, no timing, no course logistics, no eyebrow, no strip, no note
- Hero should feel playful / on-theme, not a stock photo collage

---

## Component classes (copy these, don’t rename)

### `.eyebrow`
- Cyan `#8be9fd`, `0.52em`, uppercase, `letter-spacing: 0.08em`, bold
- Section / stage label: `Foundations`, `Stage 2 · Mechanics Agent`, `Recap`
- Never put clock times here

### `.kicker`
- Orange monospace label **inside** a card: `DECIDES`, `OUTPUTS`, `DO`, `DON’T`, `CDN = …`
- `font-size: 0.68em`, `ui-monospace`, bold, slight letter-spacing
- Use instead of a second `h3` when the card is a labeled panel

### `.card` / `.card.soft`
- Unit of layout: bg `#21222c`, border `#44475a`, radius `10px`, padding `0.65em 0.75em`, `font-size: 0.72em`, flex column
- Under `.fill`: `min-height: 9.5em` (grid-2); `7.2em` for grid-3/4
- **`.soft`**: bg `#282a36`, border `#bd93f9` — punchline / output / preferred-option card
- Convention: left = input/decides/do; **right or last = `.soft`** for outputs / preferred / payoff
- Card lists: `ul { flex: 1 }` so `.block-foot` pins to the bottom

### `.block-foot`
- Inside a card, after bullets: top border, cyan, short goal/summary (“Feeds mechanics next”)
- `margin-top: auto` — keeps footers aligned across a row

### `.strip` / `.strip.cols-3`
- Bottom sequence or pillar recap: `repeat(4, 1fr)` or `.cols-3` → 3
- Mini-cards: centered, tiny (`0.56em`), **no** min-height
- Markup pattern: `<strong>Yellow title</strong>muted subtitle` (strong is yellow `#f1fa8c`; rest is body)

### `.note`
- Full-width takeaway under the grid/strip
- `border-left: 3px solid #ff79c6`, `font-size: 0.7em`
- One sentence (maybe two). Pink spans for the spike word.

### `.quote`
- Big yellow one-liner (`#f1fa8c`, bold, ~`1.05em`)
- Often lives inside a `.card.soft`; sometimes alone under a recap grid

### `.compare` + `.vs`
- Two tall options: `1fr auto 1fr`
- Middle `.vs` is a pink circle with short text (`or` / `vs`)
- Cards get tall min-height (~14em when diagrams are inside)
- Great for Zelda-like vs Mario-like, sprite vs sheet, etc.

### `.flow` + `.step` + `.n`
- Horizontal 5-step scaffold (default `repeat(5, 1fr)`)
- Each `.step`: card-like panel; `.n` = pink monospace step number (`01`, `02`…)
- Use for pipelines that are **process steps**, not agent stages (agent stages → `.seq`)

### `.seq` / `.box` / `.box.para` / `.row` / `.mini`
- Vertical pipeline of stages
- `.label` = muted uppercase stage number
- Stage name colored with utility (pink / orange / purple / red / green)
- **`.box.para`**: green border + darker bg — marks **parallel** fan-out
- Inside para: `.row` of three `.mini` (yellow title + optional `.thumb` img/svg + muted caption)

### `.sheet` + `.cell-labels`
- Framed image panel for sprite/tileset examples
- Img full-width on black; labels under in muted monospace grid (often 4 cols, or one spanning line)
- HUD teaching slide uses `hud_example.png` (in-game top bar: HP / score / punch / level) right after Mechanics

### Sound pipeline slides
- Teach SFX in Mechanics (`sfx[]`: id, trigger, mood) and BGM in Levels (`background_music[]`)
- Sound Agent stage: jsfxr-style recipes → `sfx_*.wav` / `bgm_*.wav` (procedural, not gen-AI music)
- Assembler: `load.audio` + `sound.play` on the same events as juice/score; note browser autoplay unlock
- Pipeline seq is 1 Concept → 2 Mechanics → 3 Levels → 4 Art → 5 Sound → 6 Assembler


### `.codeish` (`pre.codeish`)
- Fake terminal / prompt / file tree — **not** reveal’s highlight plugin
- Same card chrome; small font (`~0.46–0.62em`); `white-space: pre-wrap`
- Use for: paste-to-agent prompts, file trees, short shell snippets
- Prefer this over screenshots of code

### `.game-diagram`
- Inline SVG teaching diagrams inside compare cards
- Full width, dark void bg `#191a21`, border, radius 8px
- Keep labels monospace and tiny; use Dracula accents in the drawing

### `.label`
- Muted uppercase micro-label (used in `.seq` boxes for stage numbers)

### `.fill`
- Marks a dense content slide; required for grid min-heights / stretch

### Layout grids
- `.grid-2` / `.grid-3` / `.grid-4` — only styled under `.fill`
- `gap: 0.55em`, `align-items: stretch`
- Mobile (`max-width: 900px`): grids, flow, compare, seq row, strip → single column; `.vs` hidden; card min-heights dropped

---

## Recurring slide layouts (steal these)

| Pattern | Structure |
|---------|-----------|
| **Outline** | eyebrow + h2 → `grid-2` (foundations card + soft agent card) → 4-step strip → note |
| **Definition / pillars** | eyebrow + h2 → `grid-3` of short cards (h3 + muted + block-foot) → strip (core loop) → note |
| **Checklist + punchline** | `grid-2`: long DO list (green strongs) + soft card with `.quote` + bullets → optional `strip.cols-3` |
| **Compare two worlds** | `.compare` with kickers + optional `.game-diagram` + bullets + block-foots + `.vs` |
| **Agent stage** | eyebrow `Stage N · Name` → Decides/Outputs or Needs/Makes or Specify/Output → strip → optional note |
| **Tips Do/Don’t** | `grid-2` kickers DO / DON’T → optional full-width soft quote card under |
| **Beats / progression** | `grid-3` with BEAT kickers; last card `.soft` |
| **Pipeline** | stacked `.seq` boxes; art = `.box.para` with mini thumbs |
| **Asset showcase** | `.sheet` + cell-labels → supporting `grid-2`/`grid-3` |
| **Process steps** | main cards + `.flow` of 5 `.step`s |
| **Prompt / scaffold** | `grid-2`: explain card + soft card with `pre.codeish` prompt |
| **File tree** | soft card with `pre.codeish` tree + sibling “how to run” card + strip Wrong/Right/Then |
| **Recap** | `grid-3` Design / Art / Assemble → closing `.quote` |

Pair columns that recur: **Decides / Outputs**, **Do / Don’t**, **Needs / Makes**, **Great for / Awkward for**, **You already have / Still need**, **Prefer / Use sparingly**.

---

## Voice & copy conventions

### Do

- Punchy, classroom-clear; short clauses; concrete nouns
- Teach with **named artifacts**: `concept.json`, `mechanics.json`, `levels.json`, `*_sheet.png`
- Define jargon inline once (HP, i-frames, HUD, juice, CDN, GDD) — bold term + parenthetical
- Concrete running example (boxing rabbit, night market, Zelda-like / Mario-like)
- Middle-dot lists in strips: `move · punch`, `sprites · tiles · items`
- Paste-ready agent instructions in `.codeish` (“PASTE THIS TO YOUR AGENT”)
- One idea per slide; densify with structure

### Don’t

- Mention **clock times** (`80 min`, `~8 min`, `0–15`, agenda minutes)
- Use the word **yap**
- Outline or advertise a separate **coding / build session** as logistics on lecture slides
- Leave sparse two-bullet slides with huge empty space
- Invent new class names / purple-gradient themes / Inter-on-cream looks
- Put agenda chips or timing on the title slide
- Use reveal fragments unless you truly need them — this deck is mostly static dense slides

### Pipeline order (when the topic is this course)

1. **Concept** — story, characters, style, level *beats*  
2. **Mechanics** — verbs, damage, feedback, win/lose  
3. **Levels** — maps, spawns → **art shopping list**  
4. **Parallel art** — sprites / tiles/BG / items/UI (last on purpose)  
5. **Assemble / orchestrator** — **Phaser 3** (CDN) + wire-up  

Class standard: **Phaser only** for the build (no React / Godot / Unity). Prefer **HTML/SVG sprite pipelines** over raw image gen when teaching cost/control/editability.

Art after verbs/damage/map needs. Shopping-list art, not vibes-only briefs.

---

## Topic-specific structural patterns (from later slides)

Reuse these shapes for other technical decks, not only games:

### Prompt slides
- Left: plain-English explanation of the tool/pattern  
- Right **`.soft`**: `pre.codeish` with a pasteable agent brief  
- Bottom strip: Wrong / Right / Must (3-col)

### File-tree slides
- Soft card = full tree in `.codeish` with short `←` comments  
- Sibling card = how to run / common failure (`file://` vs local server)  
- Strip: Wrong · Right · Then

### Orchestrator / pipeline slides
- Prefer `.seq` over a flat bullet list  
- Parallel work = one `.box.para` with a `.row` of minis (thumbs optional)  
- Color-code stage names consistently across the deck

### Framework / “what’s missing” slides
- **Have / Need** pair (ingredients vs oven)  
- Loop strip: Input → Update → Draw → Repeat  

### Asset / diagram slides
- Show the artifact (`.sheet` or `.game-diagram`) **above or inside** the explanation cards  
- Label cells; don’t assume the audience can read the PNG alone  

---

## Things vibe coders guess wrong

1. **Sparse “keynote” slides** — wrong. Fill with cards; pin a strip/note to the bottom.  
2. **`center: true`** — wrong for content; only title uses center classes.  
3. **New CSS system per deck** — wrong. Port the same utility block.  
4. **Cards without `.block-foot`** — looks unfinished; add a one-line foot.  
5. **Soft border on every card** — soft is the *punchline* card, usually one per row.  
6. **Strip titles in cyan** — wrong; strip `<strong>` is **yellow**. Kickers are orange monospace.  
7. **Eyebrow = slide title** — wrong; eyebrow is the section crumb, `h2` is the claim.  
8. **Using `<pre><code>` + highlight.js** — this aesthetic uses `.codeish` panels instead.  
9. **Title slide with outline / “Today” chips** — strip those; name + title + hero only.  
10. **Min-height fights** — if you nest a strip inside a card, set `min-height: 0` on that card (the reference deck does this).  
11. **Forgetting `.fill`** — grids won’t get stretch/min-heights.  
12. **Clock / session logistics in eyebrows** — banned.

---

## When adding new slides

1. Copy an existing `.fill` section from `lecture_sprites_with_ai.html` as the template  
2. Keep eyebrow → h2 → grid → strip/note anatomy  
3. Fill cards until the slide feels full; add `.block-foot`s  
4. Soft-border the output / preferred / payoff card  
5. Re-read copy: no times, no “yap”, no coding-session logistics  
6. Keep Dracula + these utilities — don’t invent a new visual system per lecture  

### Checklist before “done”

- [ ] `Reveal.initialize` matches (esp. `center: false`, `1280×720`, fade, `c/t`)  
- [ ] Same CSS utility block (or additive-only tweaks)  
- [ ] Title slide: title + byline + optional hero only  
- [ ] Content slides use `.fill` + cards that reach the lower third  
- [ ] Kickers uppercase monospace; eyebrows cyan section labels  
- [ ] One clear `h2` claim; one idea  
- [ ] Strip and/or note on dense teaching slides  
- [ ] Color utilities for emphasis — not random hex soup in HTML  

---

## Visual QA skill (for agents & humans)

After structural checks above, run a **visual** pass: capture every slide as an image, inspect for cut-off/sparse/overflow, then patch.

→ Full skill: **[SLIDE_VISUAL_QA.md](SLIDE_VISUAL_QA.md)** (“Reveal Pixel Pass”)  
→ Tooling: `slide_qa/capture_slides.py`, `slide_qa/overflow_check.py`  
