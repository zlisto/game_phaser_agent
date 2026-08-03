"""Analyze PNG empty bottom / top regions vs Dracula background."""
from pathlib import Path
from PIL import Image
import statistics

OUT = Path(__file__).resolve().parent
# Dracula reveal bg approx
BG = (40, 42, 54)  # common #282a36

def is_bg(px, tol=18):
    return abs(px[0]-BG[0]) <= tol and abs(px[1]-BG[1]) <= tol and abs(px[2]-BG[2]) <= tol

def row_is_empty(im, y, tol=18, empty_ratio=0.98):
    w = im.width
    # sample every 4th pixel x
    empty = 0
    total = 0
    for x in range(0, w, 4):
        p = im.getpixel((x, y))
        if len(p) == 4:
            p = p[:3]
        total += 1
        if is_bg(p, tol):
            empty += 1
    return empty / total >= empty_ratio

def analyze(path: Path):
    im = Image.open(path).convert("RGB")
    h, w = im.height, im.width
    # bottom empty rows from bottom
    bottom_empty = 0
    for y in range(h - 1, h // 2, -1):
        if row_is_empty(im, y):
            bottom_empty += 1
        else:
            break
    # content bounding: first/last non-empty rows in content zone (skip edges for chrome)
    top_content = 0
    for y in range(0, h):
        if not row_is_empty(im, y, empty_ratio=0.96):
            top_content = y
            break
    bottom_content = h - 1
    for y in range(h - 1, 0, -1):
        if not row_is_empty(im, y, empty_ratio=0.96):
            bottom_content = y
            break
    used = bottom_content - top_content + 1
    fill = used / h * 100
    return bottom_empty, fill, top_content, bottom_content

def main():
    files = sorted(OUT.glob("*.png"))
    print(f"{'#':>3} {'botEmpty':>8} {'fill%':>6} title_guess")
    issues = []
    for f in files:
        try:
            be, fill, tc, bc = analyze(f)
        except Exception as e:
            print(f"{f.name} ERR {e}")
            continue
        flag = ""
        if be > 80:
            flag = "SPARSE_BOTTOM"
        elif be > 50:
            flag = "gap"
        if fill < 75:
            flag = (flag + " LOW_FILL").strip()
        print(f"{f.stem:>3} {be:8d} {fill:6.1f}  {flag}")
        if flag:
            issues.append((f.stem, be, fill, flag))
    print("\nIssues:", len(issues))
    for i in issues:
        print(" ", i)

if __name__ == "__main__":
    main()
