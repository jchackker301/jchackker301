---
name: paver-texture
description: Builds a procedural concrete paver / riven sandstone tile material in Blender that copies Jayson's real paver samples (Desert-R buff sandstone, Monsoon-R charcoal, Iris-F grey + mustard). Use when Jayson says paver texture, tile texture, sandstone texture, replicate this stone/tile in Blender, Desert-R, Monsoon-R, Iris-F, make the paver material, bake paver maps, or sends top-down photos of a paving slab and wants it in Blender. Can also re-colour from a new photo and bake albedo/roughness/normal/height PNGs.
---

# Paver Texture (/paver-texture)

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
