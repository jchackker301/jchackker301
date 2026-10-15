#!/usr/bin/env python3
"""Shot Finder: find the guaranteed-usable shots in a folder of long videos.

Python does all the heavy work: decode, measure sharpness/exposure/shake,
drop bad and repeated parts, cut 10 s max clips, name files, write reports.
The AI only looks at the collage page(s) of each video and fills a short
form (reviews/NN_*.txt) using fixed menu words.

Commands
  doctor
  scan   FOLDER [--out DIR] [--min S] [--max S] [--tiles N] [--fps F] [--loose] [--recursive] [--workers N]
  check  OUT
  status OUT
  export OUT [--all] [--copy]   (writes clips/, REPORT.txt, report.csv)

Needs: Python 3.9+, numpy, opencv-python-headless, and ffmpeg
(ffmpeg on PATH, or `pip install imageio-ffmpeg`).
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    sys.exit("ERROR: OpenCV missing. Run: pip install opencv-python-headless numpy")

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".mts", ".m2ts", ".mxf",
             ".webm", ".wmv", ".3gp", ".mpg", ".mpeg"}
OUT_NAME = "_shotfinder"
AW = 640  # analysis width in px

# Quality gates. STRICT is the default ("guaranteed"). LOOSE is the fallback.
STRICT = dict(sharp_floor=45.0, sharp_rel=0.55, dark=35, bright=220, clip=0.30,
              contrast=18.0, whip=10.0, jerk=1.2)
LOOSE = dict(sharp_floor=25.0, sharp_rel=0.40, dark=25, bright=232, clip=0.45,
             contrast=12.0, whip=16.0, jerk=2.5)


# ---------------------------------------------------------------- helpers
def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ERROR: ffmpeg not found. Run: pip install imageio-ffmpeg  (or install ffmpeg)")


def run(cmd, **kw):
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW on Windows
    return subprocess.run(cmd, creationflags=flags, **kw)


def imwrite(path, img, quality=88):
    """cv2.imwrite fails on non-ASCII Windows paths, so encode then write."""
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if ok:
        Path(path).write_bytes(buf.tobytes())


def mmss(t):
    t = max(0, int(round(t)))
    return f"{t // 60:02d}:{t % 60:02d}"


def safe(s, n=40):
    keep = "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
    return keep[:n].strip("_") or "video"


def probe(ff, path):
    """Return (width, height, duration) after rotation, using one decoded frame."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    dur = n / fps if fps > 0 and n > 0 else 0.0
    r = run([ff, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "image2pipe",
             "-vcodec", "png", "-"], capture_output=True)
    img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_GRAYSCALE) if r.stdout else None
    if img is None:
        return None
    h, w = img.shape[:2]
    if dur <= 0:  # fall back to ffmpeg's own duration line
        err = run([ff, "-i", str(path)], capture_output=True, text=True, errors="ignore").stderr
        for line in err.splitlines():
            if "Duration:" in line:
                hh, mm, ss = line.split("Duration:")[1].split(",")[0].strip().split(":")
                dur = int(hh) * 3600 + int(mm) * 60 + float(ss)
                break
    return w, h, dur


# ---------------------------------------------------------------- pass 1: measure
def measure(ff, path, fps, w, h):
    rows = _measure(ff, path, fps, w, h, ["-hwaccel", "auto"])  # GPU decode when there is one
    return rows if len(rows) > 2 else _measure(ff, path, fps, w, h, [])


def _measure(ff, path, fps, w, h, hw):
    ah = int(round(h * AW / w / 2)) * 2
    cmd = [ff, "-v", "error", *hw, "-i", str(path), "-an", "-vf",
           f"fps={fps},scale={AW}:{ah}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         creationflags=0x08000000 if os.name == "nt" else 0)
    size = AW * ah
    rows, prev_small, prev_hist = [], None, None
    win = None
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        g = np.frombuffer(buf, np.uint8).reshape(ah, AW)
        lap = float(cv2.Laplacian(g, cv2.CV_64F).var())
        mean, std = float(g.mean()), float(g.std())
        clip = float(((g < 8) | (g > 247)).mean())
        small = cv2.resize(g, (160, int(160 * ah / AW)), interpolation=cv2.INTER_AREA).astype(np.float32)
        hist = cv2.calcHist([g], [0], None, [32], [0, 256]).ravel()
        hist /= hist.sum() + 1e-9
        shift, cut, diff, dxp, dyp = 0.0, False, 0.0, 0.0, 0.0
        if prev_small is not None:
            if win is None:
                win = cv2.createHanningWindow(small.shape[::-1], cv2.CV_32F)
            # copies: some OpenCV builds apply the window to the inputs in place
            (dx, dy), _ = cv2.phaseCorrelate(prev_small.copy(), small.copy(), win)
            dxp, dyp = dx / 160 * 100, dy / 160 * 100  # camera move, % of frame width
            shift = float(np.hypot(dxp, dyp))
            # action = change left after removing the camera move
            m = np.float32([[1, 0, dx], [0, 1, dy]])
            moved = cv2.warpAffine(prev_small, m, small.shape[::-1], borderMode=cv2.BORDER_REPLICATE)
            b = 6
            diff = float(np.abs(small[b:-b, b:-b] - moved[b:-b, b:-b]).mean())
            corr = float(np.minimum(hist, prev_hist).sum())  # histogram intersection
            cut = diff > 28 and corr < 0.55
        rows.append(dict(t=len(rows) / fps, lap=lap, mean=mean, std=std, clip=clip,
                         shift=shift, dx=dxp, dy=dyp, diff=diff, cut=cut, hist=hist))
        prev_small, prev_hist = small, hist
    p.wait()
    return rows


# ---------------------------------------------------------------- pick candidates
def candidates(rows, fps, g, min_len, max_len):
    if len(rows) < 3:
        return [], []
    lap = np.array([r["lap"] for r in rows])
    # blur is judged against the footage around it (+-20 s), so one very
    # detailed scene does not make every other scene look blurry
    win = int(20 * fps)
    local = np.array([np.percentile(lap[max(0, i - win):i + win + 1], 85) for i in range(len(lap))])
    sharp_min = np.maximum(g["sharp_floor"], g["sharp_rel"] * local)
    # shake = the camera move keeps changing direction/speed (a smooth pan does not)
    vec = np.array([[r["dx"], r["dy"]] for r in rows])
    k = max(2, int(fps))  # +-1 s window
    jerk = np.array([float(np.sqrt(vec[max(0, i - k):i + k + 1].var(axis=0).sum())) for i in range(len(rows))])
    cuts = [i for i, r in enumerate(rows) if r["cut"]]
    near_cut = np.zeros(len(rows), bool)
    for i in cuts:
        near_cut[max(0, i - 1):i + 2] = True

    good = np.array([
        r["lap"] >= sharp_min[i] and g["dark"] <= r["mean"] <= g["bright"]
        and r["clip"] <= g["clip"] and r["std"] >= g["contrast"]
        and r["shift"] <= g["whip"] and jerk[i] <= g["jerk"] and not near_cut[i]
        for i, r in enumerate(rows)])

    # runs of good samples
    runs, start = [], None
    for i, ok in enumerate(list(good) + [False]):  # cut samples are never good, so cuts split runs
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            runs.append((start, i - 1)); start = None

    step = 1.0 / fps
    segs = []
    for a, b in runs:
        t0, t1 = rows[a]["t"] + step * 0.5, rows[b]["t"] + step * 0.5  # trim edges
        length = t1 - t0
        if length < min_len:
            continue
        parts = max(1, int(np.ceil(length / max_len)))
        piece = length / parts
        for k in range(parts):
            s0, s1 = t0 + k * piece, t0 + (k + 1) * piece
            idx = [i for i in range(a, b + 1) if s0 <= rows[i]["t"] <= s1] or [a]
            sl = lap[idx]
            sharp_n = min(1.0, float(np.median(sl)) / (float(np.median(local[idx])) + 1e-9))
            stab = 1.0 - min(1.0, float(jerk[idx].mean()) / g["jerk"])
            expo = 1.0 - min(1.0, abs(float(np.mean([rows[i]["mean"] for i in idx])) - 125) / 125)
            best = idx[int(np.argmax(sl))]
            move = float(np.mean([rows[i]["shift"] for i in idx]))
            act = float(np.mean([rows[i]["diff"] for i in idx]))
            cam = "STATIC" if move < 0.3 else ("SLOW-MOVE" if move < 2 else "MOVING")
            action = "NONE" if act < 1.5 else ("LOW" if act < 5 else "HIGH")
            segs.append(dict(start=round(s0, 2), end=round(s1, 2), dur=round(s1 - s0, 2),
                             score=int(round(100 * (0.55 * sharp_n + 0.25 * stab + 0.20 * expo))),
                             cam=cam, action=action,
                             thumb_t=round(rows[best]["t"], 2), _hist=rows[best]["hist"]))
    return segs, good.tolist()


def diverse_top(segs, n):
    chosen = []
    for s in sorted(segs, key=lambda s: -s["score"]):
        if len(chosen) >= n:
            break
        if any(float(np.minimum(s["_hist"], c["_hist"]).sum()) > 0.93
               and abs(s["thumb_t"] - c["thumb_t"]) < 30 for c in chosen):
            continue  # near-duplicate of a shot already chosen
        chosen.append(s)
    chosen.sort(key=lambda s: s["start"])
    for i, s in enumerate(chosen, 1):
        s["tile"] = i
        s.pop("_hist", None)
    return chosen



# ---------------------------------------------------------------- collage pages
# Claude shrinks any image to about 1568 px on the long side, so pages are
# drawn at that size: nothing gets shrunk, every frame stays readable.
PW = 1560                 # page width
FW, FH = 250, 141         # one frame inside a tile (16:9 box)
TILE_W = FW * 3 + 12      # start | middle | end
TILE_H = FH + 40
COLS, ROWS = 2, 3         # 6 tiles per page
OV_N, OV_W, OV_H = 16, 191, 108  # overview: 16 frames of the whole video (2 rows of 8), page 1 only


def grab(ff, path, t):
    r = run([ff, "-v", "error", "-ss", f"{max(0.0, t):.2f}", "-i", str(path), "-frames:v", "1",
             "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR) if r.stdout else None


def fit(img, W, H):
    canvas = np.full((H, W, 3), 20, np.uint8)
    if img is None:
        return canvas
    h, w = img.shape[:2]
    s = min(W / w, H / h)
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    y, x = (H - nh) // 2, (W - nw) // 2
    canvas[y:y + nh, x:x + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    return canvas


def text(img, s, org, scale, color, thick=1, outline=False):
    if outline:  # only needed on top of a picture
        cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def header(ff, path, vno, name, dur, shots, good, page, pages):
    """Title, green/red timeline, and an 8-frame overview of the WHOLE video."""
    per_row = OV_N // 2
    h = 70 + (2 * (OV_H + 28) if page == 1 else 0)
    img = np.full((h, PW, 3), 28, np.uint8)
    text(img, f"VIDEO {vno:02d}  page {page}/{pages}  {name[:55]}", (10, 26), 0.75, (255, 255, 255), 2)
    text(img, f"length {mmss(dur)}  usable shots: {len(shots)}", (10, 54), 0.6, (180, 230, 180))
    x0, x1, y0 = 520, PW - 10, 38
    if good:
        n = len(good)
        for i, ok in enumerate(good):
            a = x0 + int((x1 - x0) * i / n); b = x0 + int((x1 - x0) * (i + 1) / n)
            cv2.rectangle(img, (a, y0), (max(a, b - 1), y0 + 16), (60, 170, 60) if ok else (50, 50, 170), -1)
        for s in shots:
            a = x0 + int((x1 - x0) * s["start"] / max(dur, 1e-6))
            cv2.line(img, (a, y0 - 6), (a, y0 + 22), (255, 255, 255), 2)
            text(img, str(s["tile"]), (a + 2, y0 - 8), 0.4, (255, 255, 255))
        text(img, "green=usable red=bad", (x0 - 200, y0 + 14), 0.45, (200, 200, 200))
    if page != 1:
        return img
    gap = (PW - per_row * OV_W) // (per_row + 1)
    for k in range(OV_N):
        t = dur * (k + 0.5) / OV_N
        r, c = divmod(k, per_row)
        x, y = gap + c * (OV_W + gap), 70 + r * (OV_H + 28)
        img[y:y + OV_H, x:x + OV_W] = fit(grab(ff, path, t), OV_W, OV_H)
        text(img, f"overview {mmss(t)}", (x + 4, y + OV_H + 19), 0.45, (210, 210, 210))
    return img


def tile(ff, path, s):
    img = np.full((TILE_H, TILE_W, 3), 40, np.uint8)
    pad = 0.15
    times = [s["start"] + pad, s["thumb_t"], s["end"] - pad]
    for k, t in enumerate(times):
        x = k * (FW + 6)
        img[0:FH, x:x + FW] = fit(grab(ff, path, t), FW, FH)
        text(img, ("start", "mid", "end")[k], (x + FW - 52, FH - 8), 0.45, (230, 230, 230), outline=True)
    cv2.rectangle(img, (4, 4), (60, 46), (0, 200, 255), -1)
    cv2.putText(img, f"{s['tile']:02d}", (8, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3, cv2.LINE_AA)
    text(img, f"TILE {s['tile']:02d}  {mmss(s['start'])}-{mmss(s['end'])}  {s['dur']:.0f}s  "
              f"cam {s['cam']}  action {s['action']}  Q{s['score']}", (6, FH + 28), 0.55, (240, 240, 240))
    return img


def collage_pages(ff, path, vno, name, dur, shots, good, out):
    per = COLS * ROWS
    groups = [shots[i:i + per] for i in range(0, len(shots), per)] or [[]]
    files = []
    for p, grp in enumerate(groups, 1):
        head = header(ff, path, vno, name, dur, shots, good, p, len(groups))
        nrows = max(1, -(-len(grp) // COLS))
        body = np.full((nrows * (TILE_H + 10), PW, 3), 28, np.uint8)
        gx = (PW - COLS * TILE_W) // (COLS + 1)
        for k, s in enumerate(grp):
            r, c = divmod(k, COLS)
            x, y = gx + c * (TILE_W + gx), r * (TILE_H + 10)
            body[y:y + TILE_H, x:x + TILE_W] = tile(ff, path, s)
        if not grp:
            text(body, "NO USABLE SHOT. Rescan with --loose if needed.", (10, 60), 0.9, (80, 80, 255), 2)
        f = Path(out) / "collages" / f"{vno:02d}_{safe(Path(name).stem)}_p{p}.jpg"
        imwrite(f, np.vstack([head, body]))
        files.append(str(f))
    return files


# ---------------------------------------------------------------- review form
TYPES = ["WIDE", "MEDIUM", "CLOSE", "DETAIL", "AERIAL", "POV", "OTS", "TOP"]
USES = ["ESTABLISHING", "BROLL", "DETAIL", "ACTION", "PRODUCT", "PEOPLE", "TRANSITION", "ENDING"]
NO_WHY = ["BLOCKED", "BORING", "REPEAT", "NOT-CINEMATIC", "BAD-FRAMING", "BAD-FACE", "OFF-TOPIC",
          "SCREEN-TEXT", "SHAKY", "BLURRY", "BAD-LIGHT"]
VIDEO_FIELDS = ["SUMMARY", "PLACE", "PEOPLE", "OBJECTS", "WHAT-HAPPENS", "LIGHT", "BEST-FOR"]
TILE_FIELDS = ["KEEP", "TYPE", "SUBJECT", "USE", "WHY"]

MENU = f"""# ---------------- MENU (copy words exactly) ----------------
# KEEP: YES | NO
# TYPE: {' | '.join(TYPES)}
# USE:  {' | '.join(USES)}
# WHY when KEEP is NO: {' | '.join(NO_WHY)}
# WHY when KEEP is YES: 3 to 8 words, what makes it good
# SUBJECT: 2 to 5 plain words, what is in the shot (ex: grey pavers backyard pool)
"""


def review_path(out, v):
    return Path(out) / "reviews" / f"{v['no']:02d}_{safe(Path(v['name']).stem)}.txt"


def write_form(out, v):
    lines = [f"VIDEO {v['no']:02d} | {v['name']} | length {mmss(v['duration'])}",
             "# Pages: " + ", ".join(Path(c).name for c in v["collages"]),
             "# Replace every ? . Describe ONLY what you can see in the pictures. Unsure = write unclear.",
             "SUMMARY: ?        # 1-2 sentences, what this video is",
             "PLACE: ?          # where (indoor/outdoor, type of place)",
             "PEOPLE: ?         # how many, what they wear/do, or none",
             "OBJECTS: ?        # main things seen (products, tools, machines)",
             "WHAT-HAPPENS: ?   # in time order, use overview times: 00:30 ..., 02:10 ...",
             "LIGHT: ?          # daylight / indoor / night, good or poor",
             "BEST-FOR: ?       # what kind of edit this footage fits", ""]
    for s in v["shots"]:
        lines += [f"TILE {s['tile']:02d} | {mmss(s['start'])}-{mmss(s['end'])} | {s['dur']:.0f}s | "
                  f"cam {s['cam']} | action {s['action']} | Q{s['score']}",
                  "KEEP: ?", "TYPE: ?", "SUBJECT: ?", "USE: ?", "WHY: ?", ""]
    if not v["shots"]:
        lines += ["# No usable tile in this video. Fill only the video lines above.", ""]
    lines.append(MENU)
    p = review_path(out, v)
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def parse_form(path):
    """Return (video_info, {tile: fields}, errors)."""
    info, tiles, errs, cur = {}, {}, [], None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.upper().startswith("TILE "):
            try:
                cur = int(line.split("|")[0].split()[1]); tiles[cur] = {}
            except (IndexError, ValueError):
                errs.append(f"line {n}: bad TILE line")
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip().upper(), val.strip()
        target = info if cur is None and key in VIDEO_FIELDS else (
            tiles[cur] if cur is not None and key in TILE_FIELDS else None)
        if target is not None and (target.get(key, "?") in ("", "?", "-") or val not in ("", "?", "-")):
            target[key] = val  # a later "?" never wipes a real answer
    for k in VIDEO_FIELDS:
        if info.get(k, "?") in ("", "?"):
            errs.append(f"{k} not filled")
    for t, f in tiles.items():
        keep = f.get("KEEP", "?").upper()
        if keep not in ("YES", "NO"):
            errs.append(f"TILE {t:02d}: KEEP must be YES or NO"); continue
        f["KEEP"] = keep
        why = f.get("WHY", "?")
        if why in ("", "?"):
            errs.append(f"TILE {t:02d}: WHY not filled")
        if keep == "NO":
            if why.upper() not in NO_WHY:
                errs.append(f"TILE {t:02d}: WHY for NO must be one of {', '.join(NO_WHY)}")
            continue
        if f.get("TYPE", "?").upper() not in TYPES:
            errs.append(f"TILE {t:02d}: TYPE must be one of {', '.join(TYPES)}")
        if f.get("USE", "?").upper() not in USES:
            errs.append(f"TILE {t:02d}: USE must be one of {', '.join(USES)}")
        if f.get("SUBJECT", "?") in ("", "?"):
            errs.append(f"TILE {t:02d}: SUBJECT not filled")
    return info, tiles, errs


# ---------------------------------------------------------------- scan worker
def scan_one(args):
    path, vno, out, o = args
    ff = ffmpeg_exe()
    info = probe(ff, path)
    if not info:
        return dict(no=vno, file=str(path), name=path.name, error="cannot decode")
    w, h, dur = info
    rows = measure(ff, path, o["fps"], w, h)
    if not dur and rows:
        dur = rows[-1]["t"]
    g = LOOSE if o["loose"] else STRICT
    segs, good = candidates(rows, o["fps"], g, o["min"], o["max"])
    shots = diverse_top(segs, o["tiles"])
    pages = collage_pages(ff, path, vno, path.name, dur, shots, good, out)
    usable = round(sum(good) / o["fps"], 1) if good else 0
    return dict(no=vno, file=str(path), name=path.name, width=w, height=h, duration=round(dur, 2),
                usable_seconds=usable, candidates_found=len(segs), collages=pages,
                shots=shots, mode="loose" if o["loose"] else "strict")


# ---------------------------------------------------------------- commands
def load(out):
    p = Path(out) / "shots.json"
    if not p.exists():
        sys.exit(f"ERROR: {p} not found. Run scan first.")
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_scan(a):
    folder = Path(a.folder).expanduser().resolve()
    if not folder.is_dir():
        sys.exit(f"ERROR: not a folder: {folder}")
    out = Path(a.out).resolve() if a.out else folder / OUT_NAME
    (out / "collages").mkdir(parents=True, exist_ok=True)
    walk = folder.rglob("*") if a.recursive else folder.iterdir()
    vids = sorted(p for p in walk if p.is_file() and p.suffix.lower() in VIDEO_EXT
                  and OUT_NAME not in p.parts and not p.name.startswith("._"))
    if not vids:
        sys.exit(f"ERROR: no videos in {folder}")
    o = dict(fps=a.fps, min=a.min, max=a.max, tiles=a.tiles, loose=a.loose)
    print(f"Scanning {len(vids)} video(s), {a.workers} at a time. About 1 min per 8-min 1080p video.")
    jobs = [(p, i, str(out), o) for i, p in enumerate(vids, 1)]
    results = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(scan_one, j): j for j in jobs}
        for f in as_completed(futs):
            try:
                r = f.result()
            except Exception as e:  # keep going on one bad file
                j = futs[f]
                r = dict(no=j[1], file=str(j[0]), name=j[0].name, error=str(e)[:200])
            results.append(r)
            print(f"  [{r['no']:02d}] {r['name']}: {r.get('error') or str(len(r['shots'])) + ' tile(s)'}", flush=True)
    results.sort(key=lambda r: r["no"])
    (out / "shots.json").write_text(json.dumps(dict(folder=str(folder), settings=o, videos=results), indent=1),
                                    encoding="utf-8")
    print(f"\nOUT = {out}\n\nTO DO, one video at a time:")
    for r in results:
        if r.get("error"):
            continue
        form = review_path(out, r)
        if form.exists() and not parse_form(form)[2]:
            print(f"  VIDEO {r['no']:02d}: already reviewed, form kept: {form}")
            continue
        write_form(out, r)
        print(f"  VIDEO {r['no']:02d}: look at {' + '.join(r['collages'])}\n            then fill {form}")
    print("\nWhen all forms are filled: check OUT, then export OUT")


def cmd_check(a):
    data, bad = load(a.out), 0
    for v in data["videos"]:
        if v.get("error"):
            continue
        p = review_path(a.out, v)
        if not p.exists():
            print(f"VIDEO {v['no']:02d}: form missing, run scan again"); bad += 1; continue
        _, tiles, errs = parse_form(p)
        missing = [s["tile"] for s in v["shots"] if s["tile"] not in tiles]
        errs += [f"TILE {t:02d} missing" for t in missing]
        if errs:
            bad += 1
            print(f"VIDEO {v['no']:02d}: FIX {p}")
            for e in errs[:12]:
                print(f"   - {e}")
        else:
            print(f"VIDEO {v['no']:02d}: OK")
    print("\nALL OK, run export." if not bad else f"\n{bad} form(s) to fix.")


def cmd_status(a):
    data, todo = load(a.out), 0
    for v in data["videos"]:
        if v.get("error"):
            print(f"VIDEO {v['no']:02d}: ERROR {v['error']}"); continue
        p = review_path(a.out, v)
        done = p.exists() and not parse_form(p)[2]
        todo += not done
        print(f"VIDEO {v['no']:02d}: {'done' if done else 'TO REVIEW'} | {len(v['shots'])} tiles | {p}")
    print(f"\n{todo} video(s) still to review.")


def slug(s, n=28):
    s = "".join(c if c.isalnum() else "-" for c in s.lower())
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")[:n].strip("-") or "shot"


def cmd_export(a):
    data = load(a.out)
    ff = ffmpeg_exe()
    out = Path(a.out)
    for old in (out / "clips").glob("*.mp4") if (out / "clips").exists() else []:
        old.unlink()  # clips/ always matches the latest forms
    clips = out / "clips"
    clips.mkdir(exist_ok=True)
    rows, n, report, jobs = [], 0, [], []
    report += ["SHOT FINDER REPORT", f"Folder: {data['folder']}", "=" * 60, ""]
    for v in data["videos"]:
        if v.get("error"):
            report += [f"VIDEO {v['no']:02d} {v['name']}: ERROR {v['error']}", ""]; continue
        form = review_path(out, v)
        info, tiles, errs = parse_form(form) if form.exists() else ({}, {}, ["no form"])
        reviewed = not errs
        if not reviewed and not a.all:
            print(f"  skip VIDEO {v['no']:02d}: form not complete (run check, or export --all)")
            report += [f"VIDEO {v['no']:02d} {v['name']}: NOT REVIEWED", ""]; continue
        report += [f"VIDEO {v['no']:02d}: {v['name']}  ({mmss(v['duration'])}, usable {v['usable_seconds']:.0f}s)"]
        for k in VIDEO_FIELDS:
            if reviewed:
                report.append(f"  {k}: {info.get(k, '')}")
        report.append("  SHOTS:")
        for s in v["shots"]:
            f = tiles.get(s["tile"], {}) if reviewed else {"KEEP": "YES"}
            line = f"    tile {s['tile']:02d} {mmss(s['start'])}-{mmss(s['end'])} {s['dur']:.0f}s cam {s['cam']} action {s['action']} Q{s['score']}"
            if f.get("KEEP") != "YES":
                report.append(f"{line}  -> DROP ({f.get('WHY', '')})"); continue
            typ, use = f.get("TYPE", "SHOT").upper(), f.get("USE", "BROLL").upper()
            subj = f.get("SUBJECT", "unreviewed")
            name = (f"{v['no']:02d}_{typ}_{use}_{slug(subj)}_t{s['tile']:02d}_"
                    f"{mmss(s['start']).replace(':', 'm')}s.mp4")
            enc = ["-c", "copy"] if a.copy else ["-c:v", "libx264", "-crf", "18", "-preset", "superfast",
                                                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
            cmd = [ff, "-v", "error", "-y", "-ss", f"{s['start']:.2f}", "-i", v["file"], "-t", f"{s['dur']:.2f}",
                   "-map", "0:v:0", "-map", "0:a?", *enc, "-movflags", "+faststart", str(clips / name)]
            report.append(f"{line}  -> KEEP {typ} {use}: {subj} | {f.get('WHY', '')} | {name}")
            rows.append(dict(video_no=v["no"], source=v["name"], tile=s["tile"], start=mmss(s["start"]),
                             end=mmss(s["end"]), seconds=s["dur"], shot_type=typ, use=use, subject=subj,
                             camera=s["cam"], action=s["action"], quality=s["score"], note=f.get("WHY", ""),
                             clip=name))
            jobs.append((cmd, len(report) - 1, rows[-1]))
        report.append("")

    def cut(job):
        cmd, ri, row = job
        dst = Path(cmd[-1])
        r = run(cmd, capture_output=True, text=True, errors="ignore")
        return job, r.returncode == 0 and dst.exists() and dst.stat().st_size > 0, r.stderr.strip()[:150]

    print(f"Cutting {len(jobs)} clip(s), {a.workers} at a time...")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:  # ffmpeg does the work, threads just wait
        for (cmd, ri, row), ok, err in ex.map(cut, jobs):
            n += ok
            print(f"  {'OK ' if ok else 'ERR'} {row['clip']}" + ("" if ok else f"  {err}"))
            if not ok:
                report[ri] = report[ri].replace(row["clip"], "EXPORT FAILED"); row["clip"] = "FAILED"
    (out / "REPORT.txt").write_text("\n".join(report), encoding="utf-8")
    with open(out / "report.csv", "w", newline="", encoding="utf-8-sig") as fh:
        cols = ["video_no", "source", "tile", "start", "end", "seconds", "shot_type", "use", "subject",
                "camera", "action", "quality", "note", "clip"]
        wr = csv.DictWriter(fh, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    print(f"\nDONE: {n} clip(s) in {clips}\nReport: {out / 'REPORT.txt'}  and  {out / 'report.csv'}")


def cmd_doctor(a):
    print(f"python {sys.version.split()[0]} OK" if sys.version_info >= (3, 9) else "python TOO OLD, need 3.9+")
    print(f"numpy {np.__version__} OK")
    print(f"opencv {cv2.__version__} OK")
    ff = ffmpeg_exe()
    r = run([ff, "-version"], capture_output=True, text=True, errors="ignore")
    print(("ffmpeg OK: " + ff) if r.returncode == 0 else "ffmpeg BROKEN, run: pip install imageio-ffmpeg")
    print("READY")


def main():
    for stream in (sys.stdout, sys.stderr):  # Windows consoles choke on names like "ñ"
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Find guaranteed-usable shots in long videos.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("folder")
    s.add_argument("--out"); s.add_argument("--min", type=float, default=3.0, help="shortest shot, seconds")
    s.add_argument("--max", type=float, default=10.0, help="longest shot, seconds (10 = max clip)")
    s.add_argument("--tiles", type=int, default=12, help="max tiles per video (6 per page)")
    s.add_argument("--fps", type=float, default=4.0, help="analysis samples per second")
    s.add_argument("--loose", action="store_true", help="lower quality bar")
    s.add_argument("--recursive", action="store_true")
    s.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) // 2)))
    sub.add_parser("doctor")
    for c in ("check", "status"):
        sub.add_parser(c).add_argument("out")
    e = sub.add_parser("export"); e.add_argument("out")
    e.add_argument("--all", action="store_true", help="also export unreviewed videos (every tile, generic names)")
    e.add_argument("--copy", action="store_true", help="instant stream copy (start may snap to a keyframe)")
    e.add_argument("--workers", type=int, default=max(2, min(6, (os.cpu_count() or 2) // 2)))
    a = ap.parse_args()
    a.max = min(a.max, 10.0) if a.cmd == "scan" else None
    {"scan": cmd_scan, "check": cmd_check, "status": cmd_status, "export": cmd_export,
     "doctor": cmd_doctor}[a.cmd](a)


if __name__ == "__main__":
    main()
