# 2D Games with AI Agents — slides

Standalone Reveal.js (Dracula) deck for classroom use.

## Open

`ash
# from this folder
npx --yes serve .
# or: python -m http.server 8000
`

Then open the printed URL → lecture_sprites_with_ai.html

(CDN loads reveal.js; local images must be served or same-folder relative paths work with many Live Server setups too.)

## Contents

| File | Role |
|------|------|
| `lecture_sprites_with_ai.html` | Full slide deck |
| `*_sheet.png` / `rabbit_spritesheet.png` / `snake_spritesheet.png` | Art examples in pipeline slides |
| `lecture_rabbit_*.png` / `lecture_snake_*.png` | Scope diagram sprites (top-down vs side-scroller) |
| `hud_example.png` | HUD teaching screenshot |
| `SLIDES_NOTES.md` | Style guide for editing this deck |
| `SLIDE_VISUAL_QA.md` | Reveal Pixel Pass — visual QA skill |

Copy this whole folder into the other repo; keep relative paths as-is.
