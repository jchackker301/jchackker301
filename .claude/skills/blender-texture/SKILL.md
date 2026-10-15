---
name: blender-texture
description: Replicates any real surface texture (concrete pavers, stone, sandstone, terrazzo, plaster) as a 100% PROCEDURAL Blender material from a top-down photo. It measures the photo (colours, clouds, streak direction, accent, wisps, grain, flecks, riven face), builds a shader-node material + slab, renders it, compares the render with the photo and auto-tunes until they match. Ships the decoded Ducon style DNA and presets for Iris-F, Bella-R, Misty-R, Ivory-R, Monsoon-R, Slate-R and Desert-R. Use when Jayson says blender texture, procedural texture, replicate this texture, gawin sa blender, make this paver in 3D, Ducon texture/colour, decode the style, or sends paver/stone photos and wants them in Blender. Built so even a small model (Haiku) can run it: Python does the work, the AI looks at pictures and fills a short style card.
---

# Blender Texture (/blender-texture)

Reply to Jayson in short Taglish. Follow the steps EXACTLY. Do not write new code and do not change the scripts. Everything is already built.

## What it makes
- A **procedural** material (shader nodes only, no image files) called `Paver <name>`. All controls sit on ONE group node, so Jayson can tweak them by hand in Blender.
- A slab at real size (default 600×600×50 mm) with arris bevel. Every copy looks different (Object Info → Random).
- Optional: a top-down render, an N×N patio with 5 mm joints, and baked PNG maps (albedo/roughness/normal) for Unreal, Unity or web.
- `references/ducon-style-dna.md` is the decoded Ducon recipe (7 layers, range table, how to invent new colours). **Read it before the first job.**

## Commands
`SK` = folder of this SKILL.md (Windows: `$HOME/.claude/skills/blender-texture`).
`BL` = the Blender program:
- Windows: `"C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"` (check the version folder)
- Mac: `/Applications/Blender.app/Contents/MacOS/Blender`
- No Blender installed? `python -m pip install bpy` (Python 3.11+) works too. Then replace `BL -b -P script --` with `python script`. All scripts accept both.

Python scripts need `python -m pip install numpy pillow` (once).

| Step | Command |
|---|---|
| analyse photo(s) | `python "SK/scripts/analyze_photo.py" "PHOTO1.jpg" "PHOTO2.jpg" --name "Bella-R" --finish riven --out "SK/presets/bella-r.json"` |
| build + render | `BL -b -P "SK/scripts/build_texture.py" -- --preset "SK/presets/bella-r.json" --out "OUT" --render` |
| compare + auto-tune | `python "SK/scripts/compare.py" "PHOTO1.jpg" "OUT/bella-r_render.png" --preset "SK/presets/bella-r.json" --apply --sheet "OUT/bella-r_sheet.jpg"` |
| whole range | `--preset all` (every JSON in `SK/presets/`) |
| patio | add `--patio 4` |
| bake maps | add `--bake 2048` |

Options: `--finish flat` for `-F` names (smooth face) and `riven` for `-R` names. For coping/steps add `--size 1000x250x50` (real mm) to analyze_photo.

## Workflow (one texture)
1. **Photos.** Use 1–3 top-down photos of the same colour. The tile must fill at least a third of the frame. Hands and paper beside it are fine, because the script finds the tile and crops it.
2. **Analyse.** Run the analyse command, then Read `..._crop.jpg` next to the JSON. It must show ONLY stone. If paper or board shows, crop the photo to the stone and run again.
3. **Style card.** Look at the photo, then open the JSON and fill these two fields with the Write tool. Keep every other field.
   - `"style_notes"`: one line in the style of the DNA table (body, clouds, accent, wisps, grain, face).
   - `"style"`: only sliders you are sure about, using the meanings below. Leave out what you are not sure of.
4. **Build + render** with `--render`.
5. **Compare** with `--apply --sheet`, then Read the sheet (photo left, render right).
   - It prints `MATCH nn%` and writes colour and slider fixes into the JSON by itself.
   - Then fix BY EYE only what the numbers cannot see. Change one slider per round:
     - streaks going the wrong way → `Direction` (0 = sideways, 90 = top-to-bottom)
     - blobs vs bands → `Stretch` (1.3 blobs, 3+ long bands)
     - pale veils too big/small/many → `Wisp Scale` / `Wisp Amount`
     - riven ledges too strong/weak → `Riven Depth`
     - gold patches too big → raise `Accent Scale`
6. Repeat steps 4–5 until MATCH is 85%+ and the sheet looks like the same stone (usually 3–4 rounds). Stop after 6 rounds.
7. Tell Jayson: the MATCH %, where the `.blend` is, and one line saying what the style is.

## Style sliders (the "style" block = group node inputs)
| Slider | 0 / low | high | Typical |
|---|---|---|---|
| Cloud Amount | plain body | lots of dark cloud | 0.15 light colours – 0.8 Bella |
| Cloud Scale | huge clouds | small clouds | 1.6 |
| Stretch | round blobs | long bands | 1.3–3.5 |
| Direction | sideways (0) | top-to-bottom (90) | 0, coping 90 |
| Accent Amount | no gold | lots of gold | 0 cool, 0.4–0.55 warm |
| Accent Scale | big patches | small sprinkled | 1.2 Bella, 3.5 Iris |
| Wisp Amount | none | heavy pale veils | 0.15–0.6 |
| Wisp Scale | wide veils | fine veils | 3–5 |
| Edge Mottle | airbrushed edges | grainy edges | 0.6–0.9 (Ducon) |
| Speckle | smooth paste | strong sand grain | 0.4–0.9 |
| Grain Size | fine sand | coarse chips | 1 |
| Fleck Amount | no white chips | many white chips | 0.05 – 0.6 Monsoon |
| Riven Depth | flat (-F) | deep riven ledges | 0 / 0.6–1 |
| Roughness | glossy | matte | 0.85–0.92 |
| Seed | — | — | any number, new random layout |

Colours (`base`, `dark`, `accent`, `light`) are **linear RGB 0–1**, the way Blender's colour picker shows them. Do not paste sRGB/hex values straight in.

## Presets included
`presets/` has iris-f, bella-r, misty-r, ivory-r (measured from photos and auto-tuned), plus monsoon-r, slate-r, desert-r. Those last three were **estimated by eye**: when their photos are on this PC, run steps 2–6 on them to replace the guesses.
`examples_ducon_range.jpg` is a render of the whole range.

## Troubleshooting
- Render all white or black: never change the Sun (2.75) or the Standard view transform. They keep the colours true to the photo.
- `has no input X` error: the Blender version is too old. Use 4.0 or newer.
- MATCH stays low but the sheet looks right: trust the sheet. MATCH is a guide, and lighting differences in the photo lower it.
