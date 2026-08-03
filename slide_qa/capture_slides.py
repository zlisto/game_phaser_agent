"""Capture each horizontal reveal.js slide as 1280x720 PNG for visual QA."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "lecture_sprites_with_ai.html").as_uri()
OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        page.goto(HTML, wait_until="networkidle")
        page.wait_for_function(
            "() => typeof Reveal !== 'undefined' && Reveal.isReady && Reveal.isReady()"
        )
        # Production size board, no fade ghosting
        page.evaluate(
            """() => {
              Reveal.configure({
                transition: 'none',
                backgroundTransition: 'none',
                margin: 0,
              });
              document.querySelectorAll(
                '.reveal .controls, .reveal .progress, .reveal .slide-number'
              ).forEach(el => { el.style.visibility = 'hidden'; });
              Reveal.layout();
            }"""
        )
        page.wait_for_timeout(400)
        n = page.evaluate("() => Reveal.getTotalSlides()")
        print(f"Total slides: {n}")
        for i in range(n):
            page.evaluate(f"() => Reveal.slide({i})")
            page.wait_for_timeout(180)
            page.evaluate(
                """() => {
                  document.querySelectorAll('.reveal .slides > section').forEach(s => {
                    if (s.classList.contains('present')) {
                      s.style.visibility = 'visible';
                      s.style.opacity = '1';
                      s.style.display = 'block';
                    } else {
                      s.style.visibility = 'hidden';
                      s.style.opacity = '0';
                    }
                  });
                }"""
            )
            page.wait_for_timeout(80)
            path = OUT / f"{i + 1:02d}.png"
            page.screenshot(path=str(path), full_page=False)
            h2 = page.evaluate(
                """() => {
                  const s = document.querySelector('.reveal .slides section.present');
                  if (!s) return '';
                  const h = s.querySelector('h1,h2');
                  return h ? h.textContent.trim().slice(0, 90) : s.className;
                }"""
            )
            safe = h2.encode("ascii", "replace").decode("ascii")
            print(f"{i + 1:02d}  {safe}")
        browser.close()
    print("Done ->", OUT)


if __name__ == "__main__":
    main()
