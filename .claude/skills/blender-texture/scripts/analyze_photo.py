"""Measure a top-down paver photo and write a preset JSON for build_texture.py.

Usage:
  python analyze_photo.py PHOTO.jpg [PHOTO2.jpg ...] --name "Bella-R" --finish riven --out presets/bella-r.json

Several photos of the same colour are averaged (better palette).
Needs: numpy, pillow (pip install numpy pillow).

What it measures (all from the centre 80% of the detected tile):
  base/dark/accent/light   the 4 colour roles (linear RGB, what Blender wants)
  accent_share             how much of the surface is the tinted (gold) colour
  speckle      contrast of the fine aggregate grain (0..1)
  cloud        contrast of the big colour clouds (0..1)
  stretch      how long the clouds are (1 = round blobs, 5 = long streaks)
  direction    which way the streaks run (0 = sideways, 90 = top-to-bottom)
  wisp         pale cloud patches, fleck = single white chips, mottle = grainy cloud edges
  roughness    suggested roughness from brightness
It also saves a _crop.jpg next to the JSON so you can check the tile was found.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def find_tile(img):
    """Return (x0, y0, x1, y1) of the tile. The tile is the big, least-saturated,
    textured square in the middle; the board around it is smooth."""
    small = img.copy()
    small.thumbnail((800, 800))
    s = small.size[0] / img.size[0]
    a = np.asarray(small.convert("L"), dtype=np.float64)
    # local texture: concrete grain is busy, painted board is smooth
    blur = np.asarray(small.convert("L").filter(ImageFilter.GaussianBlur(3)), dtype=np.float64)
    tex = np.abs(a - blur)
    tex = np.asarray(Image.fromarray(np.clip(tex * 20, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(6)), dtype=np.float64)
    h, w = tex.shape
    # start from the centre and grow while rows/cols stay textured
    thr = np.median(tex[h // 3: 2 * h // 3, w // 3: 2 * w // 3]) * 0.45
    cy, cx = h // 2, w // 2

    def grow(profile, c):
        lo = c
        while lo > 0 and profile[lo - 1] > thr:
            lo -= 1
        hi = c
        while hi < len(profile) - 1 and profile[hi + 1] > thr:
            hi += 1
        return lo, hi

    band = max(10, h // 6)
    col_prof = np.median(tex[cy - band: cy + band, :], axis=0)
    x0, x1 = grow(col_prof, cx)
    row_prof = np.median(tex[:, max(x0, cx - band): min(x1, cx + band)], axis=1)
    y0, y1 = grow(row_prof, cy)
    if (x1 - x0) < w * 0.25 or (y1 - y0) < h * 0.25:  # detection failed: centre crop
        x0, x1, y0, y1 = int(w * 0.25), int(w * 0.75), int(h * 0.2), int(h * 0.8)
    return tuple(int(v / s) for v in (x0, y0, x1, y1))


def palette_roles(px):
    """Split pixels into the 4 roles the Blender shader uses.
    base   = the main body colour (middle brightness, normal warmth)
    dark   = the darker clouds
    accent = the warm/gold (or any tinted) patches
    light  = the pale cream/white flecks and clouds
    Returns colours (4x3) and accent share (0..1)."""
    lum = px @ np.array([0.2126, 0.7152, 0.0722])
    warm = (px[:, 0] - px[:, 2]) / np.maximum(lum, 1e-3)
    w_med, w_mad = np.median(warm), np.median(np.abs(warm - np.median(warm))) + 1e-4
    accent_mask = warm > w_med + 2.5 * w_mad
    lo, hi = np.percentile(lum, [15, 92])
    dark = px[lum <= lo].mean(0)
    light = px[(lum >= hi) & ~accent_mask].mean(0) if np.any((lum >= hi) & ~accent_mask) else px[lum >= hi].mean(0)
    mid = (lum > lo) & (lum < hi) & ~accent_mask
    base = np.median(px[mid], axis=0)
    # the warmest 5% give the true pigment colour (average of all warm pixels is muddied by grain)
    top = warm >= np.percentile(warm, 95)
    accent = px[top & accent_mask].mean(0) if (top & accent_mask).sum() > 50 else base
    return np.array([base, dark, accent, light]), float(accent_mask.mean())


def measure(path):
    img = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = find_tile(img)
    mx, my = int((x1 - x0) * 0.1), int((y1 - y0) * 0.1)
    crop = img.crop((x0 + mx, y0 + my, x1 - mx, y1 - my))
    crop.thumbnail((1024, 1024))
    rgb = np.asarray(crop, dtype=np.float64) / 255.0
    lin = srgb_to_linear(rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])

    # flatten uneven studio light so it is not mistaken for colour clouds
    lum_img = Image.fromarray(np.clip(lum * 255, 0, 255).astype(np.uint8))
    light = np.asarray(lum_img.filter(ImageFilter.GaussianBlur(crop.size[0] / 4)), dtype=np.float64) / 255.0
    flat = lin * (lum.mean() / np.maximum(light, 1e-3))[..., None]
    flat_lum = flat @ np.array([0.2126, 0.7152, 0.0722])

    fl_img = Image.fromarray(np.clip(flat_lum * 255, 0, 255).astype(np.uint8))
    fine = np.asarray(fl_img.filter(ImageFilter.GaussianBlur(2)), dtype=np.float64) / 255.0
    big = np.asarray(fl_img.filter(ImageFilter.GaussianBlur(crop.size[0] / 40)), dtype=np.float64) / 255.0
    m = max(flat_lum.mean(), 1e-3)
    speckle = float(np.std(flat_lum - fine) / m)
    cloud = float(np.std(big - big.mean()) / m)
    # streak direction + length from the structure tensor of the cloud layer
    gy, gx = np.gradient(big)
    jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
    tr, det = jxx + jyy, jxx * jyy - jxy * jxy
    l1 = tr / 2 + np.sqrt(max(tr * tr / 4 - det, 0))
    l2 = max(tr - l1, 1e-12)
    stretch = float(np.clip(np.sqrt(l1 / l2), 1.0, 5.0))
    # gradient points ACROSS the streaks; streaks run 90 deg from it. 0 = sideways, 90 = top-to-bottom
    grad_ang = 0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy))
    direction = float(((grad_ang + 90 + 90) % 180) - 90)
    # wisps: pale cloud patches (not single grains)
    mid = np.asarray(fl_img.filter(ImageFilter.GaussianBlur(crop.size[0] / 120)), dtype=np.float64) / 255.0
    wisp = float((mid > np.percentile(mid, 50) + 2.2 * mid.std()).mean())
    # flecks: single bright grains (white quartz chips, typical on charcoal)
    hp = flat_lum - fine
    fleck = float((hp > 4 * hp.std()).mean())
    # mottle: grainy cloud edges = energy between grain size and cloud size
    mottle = float(np.std(fine - mid) / m)

    px = flat.reshape(-1, 3)[:: 3]
    pal, accent_share = palette_roles(px)
    extra = {"direction_deg": direction, "wisp": wisp, "fleck": fleck, "mottle": mottle}
    return crop, pal, accent_share, speckle, cloud, stretch, float(flat_lum.mean()), extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--name", required=True)
    ap.add_argument("--finish", choices=["flat", "riven"], default="flat",
                    help="flat = smooth face (Iris-F), riven = split-stone ridges (Bella-R, Misty-R, Ivory-R)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="600x600x50", help="real size in mm, W x D x H (coping/steps e.g. 1000x250x50)")
    a = ap.parse_args()

    res = [measure(p) for p in a.photos]
    pal = np.mean([r[1] for r in res], axis=0)
    share = np.mean([r[2] for r in res], axis=0)
    speckle = float(np.mean([r[3] for r in res]))
    cloud = float(np.mean([r[4] for r in res]))
    stretch = float(np.mean([r[5] for r in res]))
    bright = float(np.mean([r[6] for r in res]))
    ex = {k: float(np.mean([r[7][k] for r in res])) for k in res[0][7]}
    # direction: average on the half-circle (doubled angles) so 89 and -89 do not cancel to 0
    dang = np.radians([2 * r[7]["direction_deg"] for r in res])
    ex["direction_deg"] = float(np.degrees(np.arctan2(np.sin(dang).mean(), np.cos(dang).mean())) / 2)

    rnd = lambda c: [round(float(v), 4) for v in c]
    preset = {
        "name": a.name,
        "finish": a.finish,
        "base": rnd(pal[0]),
        "dark": rnd(pal[1]),
        "accent": rnd(pal[2]),
        "light": rnd(pal[3]),
        "accent_share": round(float(share), 3),
        "speckle": round(min(speckle * 4, 1.0), 3),
        "cloud": round(min(cloud * 6, 1.0), 3),
        "stretch": round(min(5.0, 1.0 + (stretch - 1.0) * 3.0 + 0.5), 2),
        "direction_deg": round(ex["direction_deg"], 1),
        "wisp": round(float(np.clip(ex["wisp"] * 25, 0, 1)), 3),
        "fleck": round(float(np.clip(ex["fleck"] * 60, 0, 1)), 3),
        "mottle": round(float(np.clip(ex["mottle"] * 12, 0, 1)), 3),
        "roughness": round(float(np.clip(0.95 - bright * 0.3, 0.75, 0.95)), 3),
        "riven_depth_mm": 2.5 if a.finish == "riven" else 0.0,
        "size_mm": [int(v) for v in a.size.lower().split("x")],
        "source_photos": [os.path.basename(p) for p in a.photos],
        "style": {},
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(preset, f, indent=2)
    res[0][0].save(os.path.splitext(a.out)[0] + "_crop.jpg", quality=85)
    print(json.dumps(preset, indent=2))
    print("SAVED", a.out)


if __name__ == "__main__":
    sys.exit(main())
