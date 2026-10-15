"""Compare a Blender render against the real photo and say which slider to move.

Usage:
  python compare.py PHOTO.jpg RENDER.png --preset presets/x.json [--sheet OUT.jpg]

It measures BOTH images with the same code as analyze_photo.py, prints a table
(photo vs render), a match score, and the exact style changes to try next.
--sheet writes a side-by-side picture (photo crop left, render right) to look at.
Needs: numpy, pillow.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_photo import measure  # noqa: E402

# measured key -> (style slider, how strongly the slider moves the measurement, tolerance)
# Wisp Amount / Wisp Scale / Direction / Riven Depth are NOT auto-tuned: judge them by eye on the --sheet.
RULES = {
    "cloud": ("Cloud Amount", 1.0, 0.08),
    "speckle": ("Speckle", 1.0, 0.10),
    "accent_share": ("Accent Amount", 3.0, 0.04),
    "fleck": ("Fleck Amount", 1.0, 0.12),
    "mottle": ("Edge Mottle", 1.0, 0.12),
    "stretch": ("Stretch", 1.0, 0.5),
}


def stats(path):
    crop, pal, accent_share, speckle, cloud, stretch, bright, ex = measure(path)
    return crop, {
        "base": pal[0], "dark": pal[1], "accent": pal[2], "light": pal[3],
        "accent_share": accent_share, "speckle": min(speckle * 4, 1),
        "cloud": min(cloud * 6, 1), "stretch": min(5.0, 1.0 + (stretch - 1.0) * 3.0 + 0.5),
        "wisp": float(np.clip(ex["wisp"] * 25, 0, 1)), "fleck": float(np.clip(ex["fleck"] * 60, 0, 1)),
        "mottle": float(np.clip(ex["mottle"] * 12, 0, 1)), "bright": bright,
    }


def current_default(p, slider):
    """Same defaults build_texture.py uses when the style card has no value."""
    return {
        "Cloud Amount": p.get("cloud", 0.5), "Speckle": p.get("speckle", 0.6),
        "Accent Amount": min(1.0, p.get("accent_share", 0.1) * 4.0), "Wisp Amount": p.get("wisp", 0.5),
        "Fleck Amount": p.get("fleck", 0.3), "Edge Mottle": p.get("mottle", 0.5), "Stretch": p.get("stretch", 1.5),
    }[slider]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("render")
    ap.add_argument("--preset", required=True)
    ap.add_argument("--sheet")
    ap.add_argument("--apply", action="store_true", help="write the suggested changes into the preset")
    a = ap.parse_args()
    p = json.load(open(a.preset))
    style = p.get("style", {})

    pc, ps = stats(a.photo)
    rc, rs = stats(a.render)

    print(f"{'measure':<14}{'photo':>9}{'render':>9}   action")
    score, n, todo = 0.0, 0, {}
    for k in ("base", "dark", "accent", "light"):
        d = np.array(ps[k]) - np.array(rs[k])
        err = float(np.abs(d).max() / max(np.array(ps[k]).max(), 1e-3))
        score += max(0, 1 - err * 3)
        n += 1
        act = "ok"
        if err > 0.08:
            # colours are linear RGB: scale preset colour by photo/render ratio
            ratio = np.array(ps[k]) / np.maximum(np.array(rs[k]), 1e-4)
            new = np.clip(np.array(p[k]) * ratio, 0, 1)
            todo[k] = [round(float(v), 4) for v in new]
            act = f'set "{k}": {todo[k]}'
        print(f"{k:<14}{np.round(ps[k], 3)!s:>9} {np.round(rs[k], 3)!s:>9}   {act}")
    for k, (slider, gain, tol) in RULES.items():
        d = ps[k] - rs[k]
        score += max(0, 1 - abs(d) / (tol * 4))
        n += 1
        act = "ok"
        if abs(d) > tol:
            if k == "accent_share" and (ps["accent"][0] - ps["accent"][2]) - (ps["base"][0] - ps["base"][2]) < 0.02:
                print(f"{k:<14}{ps[k]:>9.3f}{rs[k]:>9.3f}   ok (no tinted colour in photo)")
                continue
            cur = style.get(slider, current_default(p, slider))
            hi = 5.0 if slider == "Stretch" else 1.0
            new = float(np.clip(cur + d * gain * (0.7 if slider != "Stretch" else 0.6), 0 if slider != "Stretch" else 1, hi))
            todo[slider] = round(new, 3)
            act = f'{"raise" if d > 0 else "lower"} style "{slider}" {cur} -> {todo[slider]}'
        print(f"{k:<14}{ps[k]:>9.3f}{rs[k]:>9.3f}   {act}")
    print(f"\nMATCH {100 * score / n:.0f}%  (85%+ = good, 92%+ = very close)")
    if todo:
        print("NEXT CHANGES (put colours at top level, sliders inside \"style\"):")
        print(json.dumps(todo, indent=2))
    else:
        print("NEXT CHANGES: none - only look at the sheet for shape (direction, blob vs streak, riven).")

    if a.apply and todo:
        for k, v in todo.items():
            if k in ("base", "dark", "accent", "light"):
                p[k] = v
            else:
                p.setdefault("style", {})[k] = v
        p["last_match"] = round(100 * score / n, 1)
        with open(a.preset, "w") as f:
            json.dump(p, f, indent=2)
        print("APPLIED to", a.preset, "- now build + render again")

    if a.sheet:
        w = 600
        sheet = Image.new("RGB", (w * 2 + 10, w), (255, 255, 255))
        for i, im in enumerate((pc, rc)):
            im = im.copy()
            im.thumbnail((w, w))
            sheet.paste(im, (i * (w + 10), 0))
        sheet.save(a.sheet, quality=88)
        print("SHEET", a.sheet)


if __name__ == "__main__":
    main()
