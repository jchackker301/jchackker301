"""Collect the WASH PATTERN of real paver photos into a reusable library.

Each top-down photo -> tile found, squared, then split into colour-free maps:
  wash.png    light/dark clouds of the colour wash (0 = darkest, 1 = palest)
  accent.png  where the 2nd pigment sits (warm/yellow drifts)
  grain.jpg   sand grain speckle (0.5 = neutral)
  relief.jpg  riven ridges / undulation shading (0.5 = flat)
  scan.jpg    the squared photo itself
  info.json   sampled palette + how strong the accent is
Colours are thrown away on purpose: paver_texture.py --wash puts ANY palette on these patterns.

  python collect_wash.py --name desert-r --finish riven photo1.jpg photo2.jpg ...
  python collect_wash.py --name iris-f --finish flat FOLDER_OF_PHOTOS
Library layout (default: ../library next to this script):
  library/colors.json                     every product colour (palette + flat/riven)
  library/patterns/<finish>/<name>/<photo>/  the wash maps above
Needs: pip install numpy opencv-python-headless
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

RES = 2048


def find_tile(img):
    """4 corners of the slab: biggest non-white, non-yellow blob through the centre."""
    h, w = img.shape[:2]
    s = 800 / max(h, w)
    small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    # the slab = pixels whose colour is close to the middle of the photo
    lab = cv2.cvtColor(cv2.GaussianBlur(small, (0, 0), 2), cv2.COLOR_BGR2Lab).astype(np.float32)
    hh, ww = lab.shape[:2]
    core = lab[int(hh * .35):int(hh * .65), int(ww * .35):int(ww * .65)].reshape(-1, 3)
    med = np.median(core, 0)
    d = np.linalg.norm((lab - med) * (0.6, 1.0, 1.0), axis=2)
    d8 = np.clip(d * 4, 0, 255).astype(np.uint8)         # Otsu splits "slab" from "everything else"
    thr, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    near = d8[d8 <= thr]                                  # 2nd pass: drop far stuff (yellow boxes, bags)
    thr2, _ = cv2.threshold(near.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = (d8 <= thr2).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    n, lab_, stats, _ = cv2.connectedComponentsWithStats(mask)
    idx = lab_[hh // 2, ww // 2] or 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    blob = (lab_ == idx).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    quad = cv2.boxPoints(cv2.minAreaRect(hull)).astype(np.float32)   # photos are top-down
    # order TL, TR, BR, BL
    ssum, diff = quad.sum(1), np.diff(quad, axis=1).ravel()
    quad = np.array([quad[ssum.argmin()], quad[diff.argmin()], quad[ssum.argmax()], quad[diff.argmax()]])
    area = cv2.contourArea(quad) / (small.shape[0] * small.shape[1])
    return quad / s, area


def norm(x, lo=2, hi=98):
    a, b = np.percentile(x, [lo, hi])
    return np.clip((x - a) / max(b - a, 1e-6), 0, 1)


def save_gray(path, x, size=None):
    """Smooth maps -> small PNG; noisy maps (grain/relief) -> JPEG, which packs them 5x smaller."""
    im = np.clip(x * 255 + 0.5, 0, 255).astype(np.uint8)
    if size:
        im = cv2.resize(im, (size, size), interpolation=cv2.INTER_AREA)
    params = [cv2.IMWRITE_JPEG_QUALITY, 90] if path.endswith(".jpg") else []
    cv2.imwrite(path, im, params)


def process(path, out_dir, trim, flatten):
    img = cv2.imread(path)
    if img is None:
        return None, "cannot read"
    quad, area = find_tile(img)
    if area < 0.15:
        return None, f"tile not found (blob {area:.0%} of photo)"
    dst = np.float32([[0, 0], [RES, 0], [RES, RES], [0, RES]])
    sq = cv2.warpPerspective(img, cv2.getPerspectiveTransform(quad.astype(np.float32), dst), (RES, RES),
                             flags=cv2.INTER_CUBIC)
    t = int(RES * trim)                      # cut the arris / table edge
    sq = cv2.resize(sq[t:RES - t, t:RES - t], (RES, RES), interpolation=cv2.INTER_CUBIC)

    lab = cv2.cvtColor(sq.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    if flatten:                              # remove only a straight light fall-off, keep the wash
        yy, xx = np.mgrid[0:RES, 0:RES] / RES
        M = np.stack([np.ones_like(xx).ravel(), xx.ravel(), yy.ravel()], 1)
        coef, *_ = np.linalg.lstsq(M[::97], L.ravel()[::97], rcond=None)
        L = L - (M @ coef).reshape(L.shape) + coef[0] + 0.5 * (coef[1] + coef[2])

    big = cv2.GaussianBlur(L, (0, 0), RES * 0.012)
    wash = norm(big)
    chroma = cv2.GaussianBlur(B + 0.35 * A, (0, 0), RES * 0.006)   # yellow/orange pigment
    accent = norm(chroma, 5, 99.5)
    fine = L - cv2.GaussianBlur(L, (0, 0), 2.0)
    grain = np.clip(0.5 + fine / (6 * fine.std() + 1e-6), 0, 1)
    mid = cv2.GaussianBlur(L, (0, 0), 3.0) - cv2.GaussianBlur(L, (0, 0), 28.0)
    relief = np.clip(0.5 + mid / (6 * mid.std() + 1e-6), 0, 1)

    os.makedirs(out_dir, exist_ok=True)
    cv2.imwrite(os.path.join(out_dir, "scan.jpg"), cv2.resize(sq, (1024, 1024), interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    save_gray(os.path.join(out_dir, "wash.png"), wash, 1024)
    save_gray(os.path.join(out_dir, "accent.png"), accent, 1024)
    save_gray(os.path.join(out_dir, "grain.jpg"), grain)
    save_gray(os.path.join(out_dir, "relief.jpg"), relief)

    rgb = sq[..., ::-1].reshape(-1, 3).astype(np.float64)
    lum = rgb.mean(1)
    def band(lo, hi):
        m = (lum >= np.percentile(lum, lo)) & (lum <= np.percentile(lum, hi))
        return [int(v) for v in rgb[m].mean(0).round()]
    hot = chroma.ravel() > np.percentile(chroma, 97)        # strongest pigment only
    info = dict(
        source=os.path.abspath(path),
        palette=dict(grain_dark=band(0, 3), base_a=band(15, 40), base_b=band(55, 80),
                     accent=[int(v) for v in rgb[hot].mean(0).round()] if hot.any() else band(40, 60),
                     bloom=band(88, 97), grain_light=band(98.5, 100)),
        accent_strength=round(float(np.percentile(chroma, 97) - np.percentile(chroma, 5)), 2),
        wash_contrast=round(float(np.percentile(big, 98) - np.percentile(big, 2)), 2),
        tile_area=round(float(area), 3),
    )
    with open(os.path.join(out_dir, "info.json"), "w") as f:
        json.dump(info, f, indent=1)
    return info, "ok"


def contact_sheet(lib):
    rows = []
    pat = os.path.join(lib, "patterns")
    for root, dirs, files in sorted(os.walk(pat)):
        dirs.sort()
        if "wash.png" not in files:
            continue
        rel = os.path.relpath(root, pat).replace(os.sep, "/")
        finish, prod, s = (rel.split("/") + ["", "", ""])[:3]
        d = root
        if True:
            tiles = []
            for name in ("scan.jpg", "wash.png", "accent.png", "relief.jpg"):
                im = cv2.imread(os.path.join(d, name), cv2.IMREAD_UNCHANGED)
                if im.ndim == 2:
                    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
                tiles.append(cv2.resize(im, (256, 256), interpolation=cv2.INTER_AREA))
            row = np.hstack(tiles)
            label = np.full((256, 200, 3), 255, np.uint8)
            cv2.putText(label, prod, (8, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(label, finish, (8, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 160), 2)
            cv2.putText(label, f"{prod}/{s}"[:22], (8, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1)
            rows.append(np.hstack([label, row]))
    if rows:
        head = np.full((40, rows[0].shape[1], 3), 255, np.uint8)
        for i, t in enumerate(("photo", "wash", "accent", "relief")):
            cv2.putText(head, t, (200 + 256 * i + 90, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.imwrite(os.path.join(lib, "CONTACT_SHEET.jpg"), np.vstack([head] + rows), [cv2.IMWRITE_JPEG_QUALITY, 85])


def update_colors(lib, name, finish, infos):
    """Average the palettes of this product's scans into library/colors.json."""
    path = os.path.join(lib, "colors.json")
    data = json.load(open(path)) if os.path.exists(path) else {}
    keys = infos[0]["palette"].keys()
    pal = {k: [int(round(np.mean([i["palette"][k][c] for i in infos]))) for c in range(3)] for k in keys}
    acc = float(np.mean([i["accent_strength"] for i in infos]))
    entry = data.get(name, {})
    entry.update(finish=finish, palette=pal, accent_amt=round(min(0.85, max(0.15, acc / 25)), 2),
                 source=f"{len(infos)} photo(s) via collect_wash.py")
    data[name] = entry
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
    return pal


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="photos or folders")
    ap.add_argument("--name", required=True, help="product colour name, e.g. desert-r")
    ap.add_argument("--finish", required=True, choices=["riven", "flat"])
    ap.add_argument("--out", default=os.path.join(here, "..", "library"), help="library folder")
    ap.add_argument("--trim", type=float, default=0.02, help="edge cut, fraction of tile")
    ap.add_argument("--no-flatten", action="store_true", help="keep the photo's light fall-off")
    ap.add_argument("--no-color", action="store_true", help="collect pattern only, keep colors.json as is")
    a = ap.parse_args()
    lib = os.path.abspath(a.out)
    files = []
    for p in a.inputs:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))]
        else:
            files.append(p)
    infos = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        out = os.path.join(lib, "patterns", a.finish, a.name, stem)
        info, msg = process(f, out, a.trim, not a.no_flatten)
        print(("OK   " if info else "SKIP ") + f + ("" if info else "  -> " + msg))
        if info:
            infos.append(info)
    if infos and not a.no_color:
        pal = update_colors(lib, a.name, a.finish, infos)
        print("COLOR", a.name, a.finish, pal)
    contact_sheet(lib)
    print(f"DONE {len(infos)}/{len(files)} collected -> {os.path.join(lib, 'CONTACT_SHEET.jpg')}")
    return 0 if infos else 1


if __name__ == "__main__":
    sys.exit(main())
