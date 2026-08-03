# slide_qa/

**Reveal Pixel Pass** working directory for lecture visual QA.

| Item | Purpose |
|------|---------|
| `NN.png` | Captured slides (gitignored) |
| `capture_slides.py` | Playwright full-deck capture |
| `overflow_check.py` | DOM overflow / bottom gap |
| `analyze_empty.py` | Pixel empty-space heuristic (noisy — see skill doc) |
| `measure_slides.py` | Legacy fill metrics |

Full skill: **`../SLIDE_VISUAL_QA.md`**  
Style tokens: **`../SLIDES_NOTES.md`**

```powershell
python slide_qa\capture_slides.py
python slide_qa\overflow_check.py
```
