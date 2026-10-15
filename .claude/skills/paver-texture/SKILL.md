---
name: paver-texture
description: Paver colour + wash-pattern LIBRARY for Blender. Collects the real wash silhouettes (patterns) of Jayson's slab photos, keeps a library of existing colours (Desert-R, Monsoon-R, Iris-F...) tagged flat or riven, then paints any colour through any real pattern. Use when Jayson says paver texture, tile texture, sandstone texture, replicate this stone/tile in Blender, Desert-R, Monsoon-R, Iris-F, make the paver material, bake paver maps, or sends top-down photos of a paving slab and wants it in Blender, add a colour to the library, collect wash pattern, palit kulay, flat or riven. Can also re-colour from a new photo and bake albedo/roughness/normal/height PNGs.
---

# Paver Texture (/paver-texture)

## The library (main way to use it)
```
library/colors.json                          every existing colour: palette + flat/riven
library/patterns/<riven|flat>/<name>/<photo>/  real wash silhouettes from one slab photo
   wash.png (light/dark clouds) accent.png (2nd pigment) grain.jpg relief.jpg (ridges) scan.jpg
library/CONTACT_SHEET.jpg                    all collected patterns at a glance
```
Colours and patterns are separate, so ANY colour can go on ANY pattern (palit-palit ng kulay).

`CW` = `python "<folder of this SKILL.md>/scripts/collect_wash.py"` (needs `pip install numpy opencv-python-headless`)

1. **Collect** slab photos (top-down, on the white table, one slab per photo):
   `CW --name monsoon-r --finish riven "FOLDER_OF_PHOTOS"`
   `CW --name iris-f --finish flat "FOLDER_OF_PHOTOS"`
   → saves the patterns + writes the averaged colour into `colors.json`. Open `CONTACT_SHEET.jpg` to check every crop is the slab only.
   Pattern only, keep the colour: add `--no-color`.
2. **Use** in Blender:
   - `PT --list` shows the colours and patterns
   - `PT --color monsoon-r --grid 4 --render patio.png` = Monsoon colour on random real patterns of its own finish
   - `PT --color iris-f --pattern desert-r` = Iris colour on the Desert wash silhouettes
   - `PT --color desert-r --pattern desert-r/4` = one exact slab
   - `PT --color desert-r --finish flat` = same colour, flat finish
   - `PT --color monsoon-r --set base_b=#7a7a7c,accent=#c9a25a,accent_amt=0.4` = quick colour tweak
   - New colour with no photo: add an entry by hand to `colors.json` (copy one, change the RGB numbers).

Now in the library: colours desert-r (5 photos), monsoon-r and iris-f (estimated: collect their photos to refine); patterns riven/desert-r 1-5 (2=3 and 4=5 are the same slab shot twice).
Preview: `previews/library_color_swap.png` (Desert / Monsoon / Iris colours on the same Desert patterns).

## Procedural mode (no library)

One script builds everything: material, 600x600x40 mm tile(s) with 2 mm arris, light, camera, render, baked maps.

`PT` = `blender --background --python "<folder of this SKILL.md>/scripts/paver_texture.py" --`
(Windows: `"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"`; no Blender? `pip install bpy` and run `python paver_texture.py -- ...`)

## Presets (colours sampled from the real slabs)
| preset  | sample   | look |
|---------|----------|------|
| desert  | Desert-R | buff/ochre, chalky pale blooms, wavy riven ridges |
| monsoon | Monsoon-R| charcoal salt-and-pepper, soft grey clouds, faint ridges |
| iris    | Iris-F   | flat face, grey base, mustard + beige horizontal drifts |

Previews: `previews/*.png`.

## Commands
- Preview one tile: `PT --preset desert --render desert.png`
- Patio of 4x4, every tile a different pour: `PT --preset monsoon --grid 4 --render patio.png --save patio.blend`
- Match a NEW sample photo (top-down, even light): `PT --preset desert --match slab.jpg --crop x0,y0,x1,y1 --render check.png`
  Crop = pixel box of the tile face; omit to use the centre 50%. Prints `PALETTE` it used.
- Real 3D ridges (close-ups): add `--displace` (Cycles, slower).
- Export maps for Unreal/Twinmotion/SketchUp/Substance: `PT --preset iris --bake maps --bake-res 4096`
  → `albedo` (sRGB), `roughness`, `normal` (OpenGL), `height` (0..1 = -0.3..2.5 mm). Tiles 1:1 on a 600 mm plane.
- New look: `--seed 7` (any number).
- Inside Blender GUI: open the script in Text Editor, Run (desert defaults; it clears the scene unless `--keep-scene`).

## Tuning (edit `PRESETS` in the script)
- `base_a/base_b` the two cloud colours · `accent` + `accent_amt` pigment drifts · `bloom` + `bloom_amt` pale efflorescence
- `riven` 0 = flat (F), 1 = full riven (R) · `ridge_count` ridges per tile · `stretch` how horizontal the drifts run
- `grain_contrast` salt-and-pepper strength · `rough` surface roughness
New product = copy a preset, rename, run `--match` on its photo, paste the printed PALETTE in.

## Pro tips
- Judge colour with the built-in **Standard** view transform (set by the script); AgX/Filmic desaturates sandstone.
- Ridges only read under low raking light; the rig uses a 57° area light from the front edge, same as a showroom photo.
- In a big render, use Object Info › Random already wired in: duplicates (Alt+D) auto-vary, no extra materials.
