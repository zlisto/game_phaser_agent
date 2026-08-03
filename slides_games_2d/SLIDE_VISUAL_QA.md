# Reveal Pixel Pass

**Skill name:** Reveal Pixel Pass  
**Canonical deck:** `lecture_sprites_with_ai.html`  
**Style guide:** `SLIDES_NOTES.md`  
**Screenshot folder:** `slide_qa/` (PNGs gitignored; capture scripts stay)

---

## Goal

For every horizontal reveal.js slide in a Sasin lecture deck:

1. Capture a true-to-board PNG (1280×720 content board)
2. Inspect the image for layout/readability defects
3. Apply **targeted HTML/CSS** fixes (keep teaching meaning)
4. Optionally recapture and re-check

Stop when the deck is dense, legible, and on-board — not pixel-perfect magazine design.

---

## Prerequisites

- Windows / PowerShell OK; path-safe scripts
- Python 3 + `playwright` (`pip install playwright` then `playwright install chromium`)
- Deck HTML opens with CDN reveal.js (needs network once for assets)
- Style conventions from `SLIDES_NOTES.md` (Dracula + shared utility classes)

---

## Capture recipe (Playwright)

Use production board size with **fade disabled** so prior slides do not ghost into the frame.

```python
# slide_qa/capture_slides.py — summary of the loop
from playwright.sync_api import sync_playwright
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "lecture_sprites_with_ai.html").as_uri()
out = Path(__file__).resolve().parent

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
    page.goto(html, wait_until="networkidle")
    page.wait_for_function(
        "() => typeof Reveal !== 'undefined' && Reveal.isReady && Reveal.isReady()"
    )
    page.evaluate("""() => {
      Reveal.configure({
        transition: 'none',
        backgroundTransition: 'none',
        margin: 0,   // capture fills 1280×720; live deck still uses margin: 0.08
      });
      document.querySelectorAll(
        '.reveal .controls, .reveal .progress, .reveal .slide-number'
      ).forEach(el => { el.style.visibility = 'hidden'; });
      Reveal.layout();
    }""")
    n = page.evaluate("() => Reveal.getTotalSlides()")
    for i in range(n):
        page.evaluate(f"() => Reveal.slide({i})")
        page.wait_for_timeout(200)
        # Hide non-present sections completely (extra anti-ghost)
        page.evaluate("""() => {
          document.querySelectorAll('.reveal .slides > section').forEach(s => {
            const on = s.classList.contains('present');
            s.style.visibility = on ? 'visible' : 'hidden';
            s.style.opacity = on ? '1' : '0';
          });
        }""")
        page.screenshot(path=str(out / f"{i+1:02d}.png"), full_page=False)
    browser.close()
```

Run:

```powershell
cd path\to\sprites
python slide_qa\capture_slides.py
```

**Capture pitfalls**

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `transition: 'fade'` mid-shot | Ghost text from previous slide | `transition: 'none'` + hide non-`.present` |
| Screenshot full viewport with `margin: 0.08` | Fake “empty margins” around board | Set `margin: 0` for capture **or** clip to `section.present` rect |
| Pixel “empty bottom” analyzer on card bg | False sparse (card `#21222c` ≈ slide `#282a36`) | Prefer DOM overflow checks + Read tool on PNG |
| Navigational chrome | Controls over bottom note | Hide `.controls`/`.progress`/`.slide-number` during capture |

Optional: `slide_qa/overflow_check.py` walks present-section DOM and flags bottom/right overflow.

---

## How to inspect each PNG

Use the **Read tool on the image path** (`slide_qa/01.png`, …). You get a vision description — use it for:

- Cut-off text / last line missing
- Images covering bottom chrome
- Giant empty regions or single floating cards
- Contrast / small type risk
- Inconsistent card borders (know: **one** `.soft` purple border per row is intentional)

Do **not** treat every “empty lower third” comment as a defect if the slide already has note + strip and overflow_check is clean under production margin; classroom projectors also letterbox slightly.

Then open the matching `<section>` in the HTML and patch only that slide (or shared CSS if many slides share the defect).

---

## Rubric of visual defects

### Blockers (must fix)

1. **Content cut off** at bottom or right edge of the board  
2. **Images** overflowing or shoving text off-slide  
3. **Unreadable contrast** (e.g. muted body on dark card for a critical example line)  
4. **Overlapping** teaching text (not UI chrome)

### Should fix

5. **Sparse** content slide: only 1–2 short bullets and huge void; no strip/note  
6. **Stacked overflow risk**: compare + tall sheet + note with no `max-height` on images  
7. **Pipeline/seq** with thumbs: stage 6 or footer clipped  
8. **Long monospace** lines blowing card width  

### Intentional / do not treat as bugs

- Title slide (`.title-slide`): name + title + hero only — empty sides OK  
- One `.card.soft` purple border in a row (punchline)  
- `#6272a4` muted for secondary labels  
- Soft kickers / Dracula accents  

---

## Fix tactics (by defect)

| Defect | Tactic | Pattern in this deck |
|--------|--------|----------------------|
| Tall image under cards | `max-height` + `object-fit: contain` on `.sheet img` | HUD (`.hud-preview`); also default `.sheet img` |
| Compare + sheet | Shorter compare min-height; **only** tall when `:has(.game-diagram)` | Sprites slide |
| Sheet then grid cards | `.sheet:has(+ .grid-2) img { max-height: … }` | Tileset / items / BG |
| Seq pipeline + thumbs | Smaller `.thumb` height, tighter `.seq .box` padding | Pipeline + Orchestrator |
| Note under overflowing seq | Move note after seq; shrink thumbs first | Orchestrator |
| Horizontal code overflow | `overflow-wrap: anywhere` on `pre.codeish` / `code`; shorten display paths | Wire-sound slide |
| Sparse grid-only slide | Add strip + note; fill anatomy from style guide | Story elements |
| Low-contrast example under quote | Body color `#f8f8f2` not `.muted` for the key sample sentence | Concept tips “Best pitch” |
| Title near top edge | `.title-slide` padding; larger hero width | Title slide |
| Dense multi-block overflow | Drop card `min-height` inline (`style="min-height:0"`), shorten lede | jsfxr params |

**Reference “done well”:** HUD slide — image constrained, cards alongside, note still fully on board.

---

## Loop structure

```
for each slide index 1..N:
  Capture PNG → Read(image) + optional overflow_check
  If defects:
    Patch that section and/or shared CSS
    Recapture that slide (or full deck if CSS global)
    Re-inspect
Done when:
  - No bottom/right overflow across all slides
  - No cut-off notes/assembler rows
  - Sheet slides keep images + cards + note visible
  - Teaching claims unchanged unless shortened for length only
```

Batch recapture after global CSS; spot-check risky slides after one-off HTML edits.

---

## What NOT to change

- Reveal init tokens: `center: false`, `1280×720`, `fade` for **live** delivery, `margin: 0.08` in file (capture may override temporarily)
- Brand system: Dracula theme + utility colors in `SLIDES_NOTES.md`
- Class names (don’t invent a second design system)
- Curriculum claims / pipeline order / artifact names unless layout forces a shorter paraphrase
- Clock times, “yap”, coding-session logistics (style ban)

---

## Done criteria for a deck

- [ ] Every horizontal slide captured to `slide_qa/NN.png`  
- [ ] Overflow check reports no `OVERFLOW_B` / material cut-off  
- [ ] Asset slides use max-height image rules (HUD pattern generalized)  
- [ ] Pipeline/orchestrator include stage 6 fully + optional note  
- [ ] Dense content slides use `.fill` + cards ± strip/note  
- [ ] Soft card = punchline, not all cards purple  
- [ ] Style still matches `SLIDES_NOTES.md`  

---

## Repo hygiene

```
slide_qa/*.png     # gitignored bulk screenshots
slide_qa/*.py      # capture + measure helpers — keep
slide_qa/README.md # pointer for humans
```

See `slide_qa/README.md` for one-screen recall.
