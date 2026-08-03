"""Measure slide overflow and empty space for visual QA."""
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
            "() => Reveal.configure({ transition: 'none', backgroundTransition: 'none' })"
        )
        n = page.evaluate("() => Reveal.getTotalSlides()")
        rows = []
        for i in range(n):
            page.evaluate(f"() => Reveal.slide({i})")
            page.wait_for_timeout(120)
            metrics = page.evaluate(
                """() => {
                  const s = document.querySelector('.reveal .slides section.present');
                  if (!s) return null;
                  const r = s.getBoundingClientRect();
                  // Reveal scales slides; content height vs available
                  let maxBottom = 0;
                  let minTop = Infinity;
                  const kids = s.querySelectorAll(':scope > *');
                  kids.forEach(el => {
                    const cr = el.getBoundingClientRect();
                    if (cr.height < 1 && cr.width < 1) return;
                    maxBottom = Math.max(maxBottom, cr.bottom);
                    minTop = Math.min(minTop, cr.top);
                  });
                  const title = (s.querySelector('h1,h2') || {}).textContent || '';
                  const slideH = r.height;
                  const usedH = maxBottom - r.top;
                  const fillPct = Math.round((usedH / slideH) * 100);
                  const overflowPx = Math.round(maxBottom - r.bottom);
                  return {
                    title: title.trim().slice(0, 70),
                    fillPct,
                    overflowPx,
                    childCount: kids.length,
                    classes: s.className,
                  };
                }"""
            )
            flag = ""
            if metrics["overflowPx"] > 4:
                flag = "OVERFLOW"
            elif metrics["fillPct"] < 72 and "title-slide" not in metrics["classes"]:
                flag = "SPARSE"
            elif metrics["fillPct"] > 98:
                flag = "TIGHT"
            mark = f"  [{flag}]" if flag else ""
            line = (
                f"{i+1:02d} fill={metrics['fillPct']:3d}% overflow={metrics['overflowPx']:+4d}px "
                f"{metrics['title']}{mark}"
            )
            print(line)
            rows.append(metrics)
        browser.close()


if __name__ == "__main__":
    main()
