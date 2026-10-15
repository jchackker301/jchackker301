# Ducon style DNA (decoded from the sample photos)

Every Ducon colour is the SAME recipe with different numbers. Learn the recipe once and you can rebuild any range, or invent a new one that still looks like Ducon.

## The recipe: 7 layers, bottom to top

| # | Layer | What it is in real life | Shader slider(s) |
|---|---|---|---|
| 1 | Body | the main cement + pigment colour | `base` colour |
| 2 | Clouds | a second, darker pigment mixed in loosely, so it drifts in large soft clouds | `dark`, Cloud Amount, Cloud Scale |
| 3 | Streak direction | the mix is poured and spread one way, so clouds stretch into bands | Stretch, Direction |
| 4 | Accent | a tinted oxide (gold/ochre) that shows as sprinkled patches with broken edges, not painted blobs | `accent`, Accent Amount, Accent Scale |
| 5 | Wisps | pale cream/white veils of very light pigment, mostly on the cooler colours | `light`, Wisp Amount, Wisp Scale |
| 6 | Grain | exposed sand + stone chips (about 1 mm), plus a few white quartz flecks | Speckle, Grain Size, Fleck Amount, Edge Mottle |
| 7 | Face | `-F` = flat pressed face; `-R` = riven, cast from split-stone moulds, so it shows low ledges and swirl lines | Riven Depth |

Two rules make it look like Ducon instead of generic concrete:
1. **Edges are grainy, never airbrushed.** Every colour change dissolves into the sand grain (Edge Mottle 0.6–0.9).
2. **Patterns run along the piece.** Slabs mostly streak sideways (Direction 0). Long coping/step pieces band across their short side (Slate-R: Direction 90).

## The range, decoded

| Range | Family | Body | Clouds | Accent | Wisps | Grain/flecks | Face | Pattern in one line |
|---|---|---|---|---|---|---|---|---|
| Ivory-R | cool light | near-white cream grey | very faint | none | faint | fine, few flecks | riven, subtle | calm, almost plain light stone |
| Misty-R | cool mid | mid grey | grey bands | none | strong, sideways | medium | riven, soft | grey sky with white mist bands |
| Iris-F | warm mid | warm grey-beige | grey patches | gold, sprinkled, sideways | light | medium-coarse | flat | grey with gold streaks running sideways |
| Bella-R | warm dark | charcoal-brown | dark | cream-gold big blobs | medium | coarse | riven | dark stone with golden clouds breaking through |
| Monsoon-R | cool dark | charcoal | soft | none | faint pale bands | many white flecks | riven, strong | storm grey, salt-and-pepper |
| Slate-R | cool darkest | near-black | soft | none | pale bands top-to-bottom | white flecks | riven, light | black slate with pale vertical bands (coping) |
| Desert-R | warm light | sandstone ochre | slight | orange-gold | cream | medium | riven, strong swirls | yellow sandstone with swirl ledges (coping) |

Colour logic across the range:
- **Two families.** Warm = gold/ochre oxide accent (Iris, Bella, Desert). Cool = no accent, pale wisps instead (Ivory, Misty, Monsoon, Slate).
- **Lightness ladder:** Ivory → Desert → Misty → Iris → Bella → Monsoon → Slate.
- The accent is always **warmer and more saturated** than the body, never a different hue family (no blues or reds).
- In cool colours the "accent" is just the light colour, so set Accent Amount 0 and use wisps.

## Make a NEW Ducon-style colour (no photo needed)
1. Copy the closest preset from `presets/` and rename it.
2. Pick the family (warm = accent on, cool = accent 0, wisps on).
3. Set `base` (linear RGB). Make `dark` about 0.7× base and `light` about 1.4× base (keep it under 0.8). For warm colours, `accent` = base with more red and less blue.
4. Pick a pattern: sideways streaks (Stretch 2.5–3.5, Direction 0), big blobs (Stretch 1.3–1.8), or bands across a coping (Direction 90).
5. Pick the face: `-F` gives Riven Depth 0, `-R` gives Riven Depth 0.6–1.0.
6. Build and render, then look at it. Adjust only one slider at a time.

## Make ANY other texture (not Ducon)
The same 7 layers cover most concrete, sandstone, limestone, terrazzo-like and render/plaster surfaces:
- terrazzo: high Fleck Amount (0.8–1), Grain Size 3–5, Cloud Amount 0
- limestone/sandstone: warm base, low clouds, Riven Depth 0.3–1
- polished concrete: Roughness 0.3–0.5, Speckle 0.3, Riven 0
- exposed aggregate: Speckle 1, Grain Size 2–4, Fleck Amount 0.6
Run `analyze_photo.py` on any top-down photo and it fills in the numbers for you.
