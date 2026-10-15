---
name: shot-finder
description: Finds the best usable shots in a folder of long raw videos (5-10 min) and cuts them into clips of 10 s max, named by shot type and use (WIDE_ESTABLISHING, CLOSE_DETAIL, ...), plus a REPORT.txt saying what each video shows. Use when Jayson says shot finder, find the good shots, best shots, usable shots, cut the raw footage, extract b-roll, sort footage, "kunin ang magagandang shot", or gives a folder of videos to go through. Built so even a small model (Haiku) runs it: Python does all the work, the AI only looks at pictures and fills a short form.
---

# Shot Finder (/shot-finder)

Reply to Jayson in short Taglish. Follow the steps EXACTLY. Do not write code. Do not change the script. Do not run other ffmpeg or python commands. Everything is already built.

## How it works (read once)
- Python opens every video, measures every quarter second, and throws away blurry, dark, burnt, shaky, whip-pan and near-duplicate parts. What is left are the TILES (shots of 3 to 10 s).
- For each video Python makes 1 or 2 pictures (collage pages). Page 1 has 16 overview frames of the WHOLE video, plus up to 6 tiles. Each tile shows its start, middle and end frame.
- You look at the pictures and fill one text form per video. Then Python cuts and names the clips.

`SF` below means the script: `python "<folder of this SKILL.md>/scripts/shotfinder.py"`.
- Windows (Git Bash or PowerShell): `python "$HOME/.claude/skills/shot-finder/scripts/shotfinder.py"`
- If `python` is not found, use `py` (Windows) or `python3` (Mac).
- Always put "quotes" around paths. Folder names have spaces.

## Step 0: setup (only once per PC)
Run `SF doctor`. If it prints READY, go to step 1.
If it fails, run this line, then `SF doctor` again:
`python -m pip install numpy opencv-python-headless imageio-ffmpeg`

## Step 1: scan
Ask Jayson for the folder if he did not give it. Then run:
`SF scan "FOLDER"`
- It prints `OUT = ...`. Remember OUT. It is `FOLDER/_shotfinder`.
- It prints, for each video, the page picture(s) to look at and the form to fill.
- Speed: about 30-60 s per 8-min video. Set the Bash timeout to 600000. For many videos, run it in the background and wait.
- Optional: add `--recursive` for subfolders. If a video gets 0 tiles and Jayson needs more, run again with `--loose`.

## Step 2: review, ONE video at a time
For each video printed in step 1:
1. Read every page picture of that video (Read tool on the .jpg).
2. Read its form (`OUT/reviews/NN_name.txt`).
3. Write the WHOLE form back with the Write tool. Replace every `?`. Keep the `TILE` lines exactly as they are. Do not add or remove tiles. Each tile keeps its 5 lines (KEEP, TYPE, SUBJECT, USE, WHY), one of each.
   - KEEP: NO tile: fill KEEP and WHY, and write `-` for TYPE, SUBJECT and USE.
   - KEEP: YES tile: fill all 5.
4. Go to the next video. Do not read old pictures again.

### Video lines: describe exactly
Fill the video lines for EVERY video, even when all its tiles are NO.
Use the 16 overview frames (they cover the whole video, times printed under each) and the tiles.
- Write only what you SEE. No guessing brand names, places or what people say. If you cannot tell, write `unclear`.
- Be concrete: colors, materials, count of people, clothes, machines, products, indoor or outdoor, weather, time of day.
- WHAT-HAPPENS: in time order with times from the overview, for example `00:15 worker cuts paver, 02:30 wide view of finished patio, 06:40 close of texture`.

### Tile lines: the editor checklist
Python already checked focus, light, shake and duplicates. You check what a picture shows.

KEEP: YES only if ALL are true:
1. The subject is clear and you know what the shot is about.
2. Nothing blocks the lens or the subject (hand, pole, person walking in front, lens dirt).
3. The framing is clean: the subject is not cut in a bad place, the horizon is level, no messy junk in the main part of the frame.
4. Something worth seeing: a nice view, a product, a detail, a real action. A plain wall, floor, sky or ground does not count.
5. It looks good enough for a client video (cinematic: nice light, good angle, clean background).
6. It is not a near-copy of another tile you already said YES to. If two tiles show the same thing, keep the better one (higher Q, nicer framing) and set the other to NO with REPEAT.

Otherwise KEEP: NO, and WHY is ONE of these words:
| WHY | when |
|---|---|
| BLOCKED | something covers the lens or subject |
| BORING | nothing to see: plain wall, floor, sky, empty frame, nothing happens |
| REPEAT | same as another kept tile |
| NOT-CINEMATIC | ugly angle, flat look, messy background |
| BAD-FRAMING | subject cut off, tilted horizon, subject too far at the edge |
| BAD-FACE | person blinking, mouth open mid-word, awkward pose, looking at camera by mistake |
| OFF-TOPIC | camera pointed at feet, accident, setup, crew, not part of the shoot |
| SCREEN-TEXT | phone screen, recording UI, text overlay, watermark |
| SHAKY / BLURRY / BAD-LIGHT | you still see one of these in the frames |

When unsure between YES and NO, choose NO. Only sure shots are kept.

If KEEP is YES, fill all of these:
- TYPE (pick one):
  - WIDE: whole place or whole subject with lots of space around it (yard, building, room)
  - MEDIUM: person from the waist up, or one object filling about half the frame
  - CLOSE: face, hands working, or one object filling most of the frame
  - DETAIL: very close on texture, material, logo, small part
  - AERIAL: from a drone, high above
  - POV: seen through the eyes of the person doing it
  - OTS: over the shoulder of a person
  - TOP: straight down from above (not a drone)
- SUBJECT: 2 to 5 plain words, for example `grey pavers pool deck`. No `#`.
- USE (pick one):
  - ESTABLISHING: wide opener that shows where we are
  - BROLL: general nice footage to cover talking or music
  - DETAIL: texture, material, finish close-up
  - ACTION: someone doing work, something moving
  - PRODUCT: the product is the hero of the shot
  - PEOPLE: people are the focus (team, client, smiling, talking)
  - TRANSITION: strong movement or pass-by that fits between scenes
  - ENDING: calm, wide or beautiful shot to close a video
- WHY: 3 to 8 words on what makes it good, for example `smooth slide reveals full patio`.

The `cam` and `action` words in each TILE line help: `cam STATIC` = tripod-like, `SLOW-MOVE` / `MOVING` = smooth camera move (good for TRANSITION and ESTABLISHING), `action NONE` = nothing moves in the scene (fine for DETAIL and PRODUCT, BORING if there is also nothing to see).

### Filled example
```
VIDEO 03 | backyard day2.mp4 | length 07:42
SUMMARY: Finished backyard with grey pavers around a pool, filmed in daylight.
PLACE: outdoor backyard of a house, pool area
PEOPLE: none
OBJECTS: grey pavers, pool, white wall, plants, outdoor chairs
WHAT-HAPPENS: 00:14 wide of yard from the house, 01:56 slow walk along the pool edge, 04:30 close of paver joints, 07:00 pool from a corner
LIGHT: bright daylight, good
BEST-FOR: project showcase reel, before/after post

TILE 01 | 00:10-00:20 | 10s | cam SLOW-MOVE | action NONE | Q93
KEEP: YES
TYPE: WIDE
SUBJECT: backyard pool grey pavers
USE: ESTABLISHING
WHY: full yard, clean, smooth slow push

TILE 02 | 01:50-02:00 | 10s | cam STATIC | action NONE | Q88
KEEP: NO
TYPE: -
SUBJECT: -
USE: -
WHY: BORING
```

## Step 3: check
Run `SF check "OUT"`.
- `ALL OK` = go to step 4.
- Otherwise it lists each problem and the form path. Read that form, fix ONLY the listed lines, Write it back, run check again. Repeat until ALL OK.

## Step 4: export
Run `SF export "OUT"` (the default; use the options below only if Jayson asks).
- Clips go to `OUT/clips/`, max 10 s each, sharp re-encode, several at once.
- Name format: `03_WIDE_ESTABLISHING_backyard-pool-grey-pavers_t01_00m10s.mp4` (video number, type, use, subject, tile, start time).
- `OUT/REPORT.txt` = what every video shows + every shot kept or dropped and why. `OUT/report.csv` = the same as a table for Excel.
- Jayson wants it instant and does not mind a cut up to 1-2 s early: `SF export "OUT" --copy`.
- Jayson wants clips now without review: `SF export "OUT" --all` (unreviewed shots get generic names).
- Running export again rebuilds `clips/` from the forms (old clips in it are replaced).

## Step 5: tell Jayson (short)
Example: `Tapos na. 12 videos, 41 clips kept sa OUT/clips. Report: OUT/REPORT.txt. Pinaka-ok: 03 WIDE ESTABLISHING backyard pool.` Name 2 or 3 of the best clips.
If 0 clips were kept, say so and give the main reason, for example: `Tapos na. 2 videos, 0 clips: puro pader at sahig (BORING). Report: OUT/REPORT.txt.`

## If something fails
| Message | Do this |
|---|---|
| `No module named cv2` / `OpenCV missing` | `python -m pip install numpy opencv-python-headless imageio-ffmpeg` |
| `ffmpeg not found` | `python -m pip install imageio-ffmpeg` |
| `no videos in` | wrong folder. Ask Jayson for the right one |
| `cannot decode` on one video | the file is broken or still copying. Skip it and tell Jayson |
| `shots.json not found` | run step 1 first, or the OUT path is wrong |
| a video has 0 tiles | it is all bad footage. Say so. Run `SF scan "FOLDER" --loose` only if Jayson wants more |
| `python` not found | try `py`, then `python3` |
| scan is slow | normal for 4K. Leave it running; do not stop it |

Scan options (only if Jayson asks): `--min 3` shortest shot, `--max 10` longest shot (never above 10), `--tiles 12` tiles per video (6 per page), `--workers N` videos at the same time, `--fps 4` checks per second.
