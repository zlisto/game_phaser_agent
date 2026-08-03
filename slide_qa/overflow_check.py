"""Detect content overflowing the scaled slide rect."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "lecture_sprites_with_ai.html").as_uri()

def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto(HTML, wait_until="networkidle")
        page.wait_for_function(
            "() => typeof Reveal !== 'undefined' && Reveal.isReady && Reveal.isReady()"
        )
        page.evaluate(
            "() => { Reveal.configure({ transition: 'none', backgroundTransition: 'none', margin: 0 }); Reveal.layout(); }"
        )
        page.wait_for_timeout(200)
        n = page.evaluate("() => Reveal.getTotalSlides()")
        for i in range(n):
            page.evaluate(f"() => Reveal.slide({i})")
            page.wait_for_timeout(100)
            m = page.evaluate(
                """() => {
                  const s = document.querySelector('.reveal .slides section.present');
                  const slide = s.getBoundingClientRect();
                  let overflowBottom = 0, overflowRight = 0;
                  let farthest = 0;
                  const walk = (el) => {
                    if (!el || el.nodeType !== 1) return;
                    // skip if hidden
                    const st = getComputedStyle(el);
                    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return;
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                      if (r.bottom > slide.bottom + 1) {
                        overflowBottom = Math.max(overflowBottom, r.bottom - slide.bottom);
                      }
                      if (r.right > slide.right + 2) {
                        overflowRight = Math.max(overflowRight, r.right - slide.right);
                      }
                      farthest = Math.max(farthest, r.bottom);
                    }
                    for (const c of el.children) walk(c);
                  };
                  walk(s);
                  const title = (s.querySelector('h1,h2')||{}).textContent || '';
                  const bottomGap = slide.bottom - farthest;
                  return {
                    title: title.trim().slice(0,60),
                    overflowBottom: Math.round(overflowBottom),
                    overflowRight: Math.round(overflowRight),
                    bottomGap: Math.round(bottomGap),
                    slideH: Math.round(slide.height),
                  };
                }"""
            )
            flags = []
            if m["overflowBottom"] > 2:
                flags.append(f"OVERFLOW_B={m['overflowBottom']}")
            if m["overflowRight"] > 4:
                flags.append(f"OVERFLOW_R={m['overflowRight']}")
            if m["bottomGap"] > 80:
                flags.append(f"GAP={m['bottomGap']}")
            if m["bottomGap"] < 8 and m["overflowBottom"] == 0:
                flags.append("TIGHT")
            fl = " ".join(flags) if flags else "ok"
            print(f"{i+1:02d} gap={m['bottomGap']:+4d} {fl} | {m['title']}")
        browser.close()

if __name__ == "__main__":
    main()
