"""Procedural concrete paver (riven sandstone look) for Blender 4.2+ / 5.x.

Run from a terminal:
  blender --background --python paver_texture.py -- --preset desert --render out.png --save out.blend
Or paste into Blender's Text Editor and press Run (uses DEFAULTS below).

Options (after the lone --):
  --preset desert|monsoon|iris     look to build (default desert)
  --match PHOTO.jpg                re-colour the preset from a top-down photo of a real tile
  --crop x0,y0,x1,y1               pixel box of the tile face in PHOTO (default: centre 50%)
  --seed N                         variation (each seed = a different "pour")
  --size 0.6                       tile edge in metres (square)
  --thick 0.04                     tile thickness in metres
  --displace                       real geometry displacement (Cycles, slower) instead of bump only
  --grid N                         lay N x N tiles with 8 mm joints, each one different
  --render out.png                 top-down Cycles preview with raking light
  --res 1024                       render size in pixels
  --samples 48                     Cycles samples
  --bake DIR                       bake albedo/roughness/normal/height PNGs into DIR (for Unreal, SketchUp, etc.)
  --bake-res 2048                  bake size in pixels
  --save out.blend                 save the scene
"""
import argparse
import math
import os
import sys

import bpy

# ---------------------------------------------------------------- presets
# Colours are sRGB 0-255, sampled from photos of the real samples.
PRESETS = {
    # Desert-R: buff/ochre riven face, chalky pale blooms, wavy horizontal ridges
    "desert": dict(
        grain_dark=(139, 120, 87), base_a=(176, 152, 110), base_b=(190, 180, 163),
        accent=(204, 160, 92), accent_amt=0.45, bloom=(214, 208, 196), bloom_amt=0.55,
        grain_light=(226, 222, 212), riven=1.0, ridge_count=7.0, stretch=2.2,
        rough=0.92, grain_contrast=0.35,
    ),
    # Monsoon-R: charcoal riven face, salt-and-pepper grain, soft grey clouds
    "monsoon": dict(
        grain_dark=(48, 48, 51), base_a=(86, 86, 89), base_b=(112, 112, 114),
        accent=(128, 126, 122), accent_amt=0.25, bloom=(150, 149, 146), bloom_amt=0.4,
        grain_light=(190, 190, 186), riven=0.8, ridge_count=8.0, stretch=2.6,
        rough=0.9, grain_contrast=0.5,
    ),
    # Iris-F: flat face, grey base with mustard and beige drifts
    "iris": dict(
        grain_dark=(82, 82, 86), base_a=(122, 122, 126), base_b=(166, 160, 144),
        accent=(196, 158, 82), accent_amt=0.7, bloom=(182, 176, 160), bloom_amt=0.35,
        grain_light=(214, 210, 198), riven=0.0, ridge_count=6.0, stretch=1.8,
        rough=0.88, grain_contrast=0.4,
    ),
}


def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(t):
    return (*[srgb_to_lin(v) for v in t], 1.0)


# ---------------------------------------------------------------- photo matching
def palette_from_photo(path, crop, p):
    """Replace preset colours with percentiles of the real tile photo."""
    import numpy as np
    img = bpy.data.images.load(os.path.abspath(path))
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1, :, :3]          # Blender stores bottom-up
    if crop:
        x0, y0, x1, y1 = crop
    else:
        x0, y0, x1, y1 = w // 4, h // 4, 3 * w // 4, 3 * h // 4
    a = px[y0:y1, x0:x1].reshape(-1, 3)
    a = a * 255  # byte images (jpg/png) come back as stored sRGB values
    lum = a.mean(1)
    sat = a.max(1) - a.min(1)

    def band(lo, hi, sel=None):
        m = (lum >= np.percentile(lum, lo)) & (lum < np.percentile(lum, hi))
        if sel is not None:
            m &= sel
        return tuple(float(v) for v in a[m].mean(0)) if m.any() else None

    p = dict(p)
    p["grain_dark"] = band(0, 3)
    p["base_a"] = band(15, 40)
    p["base_b"] = band(55, 80)
    p["bloom"] = band(88, 97)
    p["grain_light"] = band(98.5, 100)
    warm = band(30, 90, sat > np.percentile(sat, 90))   # most saturated pixels = pigment accent
    if warm:
        p["accent"] = warm
    bpy.data.images.remove(img)
    print("PALETTE", {k: tuple(round(x) for x in v) for k, v in p.items() if isinstance(v, tuple)})
    return p


# ---------------------------------------------------------------- node helpers
class NB:
    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.x = -2400

    def add(self, kind, x=None, y=0, **props):
        node = self.n.new(kind)
        node.location = (x if x is not None else self.x, y)
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.t.links.new(a, b)

    def noise(self, vec, scale, detail, rough, distort=0.0, x=0, y=0):
        n = self.add("ShaderNodeTexNoise", x, y)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distort
        self.link(vec, n.inputs["Vector"])
        return n

    def ramp(self, fac, stops, x=0, y=0, interp="LINEAR"):
        r = self.add("ShaderNodeValToRGB", x, y)
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        els[0].position, els[0].color = stops[0]
        els[1].position, els[1].color = stops[-1]
        for pos, col in stops[1:-1]:
            e = els.new(pos)
            e.color = col
        self.link(fac, r.inputs["Fac"])
        return r

    def mix(self, fac, a, b, blend="MIX", x=0, y=0, fac_value=None):
        m = self.add("ShaderNodeMix", x, y)
        m.data_type = "RGBA"
        m.blend_type = blend
        if fac is None:
            m.inputs[0].default_value = fac_value
        elif isinstance(fac, float):
            m.inputs[0].default_value = fac
        else:
            self.link(fac, m.inputs[0])
        for sock, v in ((m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(v, tuple):
                sock.default_value = v
            else:
                self.link(v, sock)
        return m

    def math(self, op, a, b=None, x=0, y=0, clamp=False):
        m = self.add("ShaderNodeMath", x, y, operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m


def grey(v):
    return (v, v, v, 1.0)


# ---------------------------------------------------------------- material
def build_material(name, p, seed):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    b = NB(t)
    try:
        mat.displacement_method = "BOTH"
    except AttributeError:
        mat.cycles.displacement_method = "BOTH"

    # coordinates in metres, offset per object so every tile is a new pour
    tc = b.add("ShaderNodeTexCoord", -2600, 0)
    oi = b.add("ShaderNodeObjectInfo", -2600, -300)
    off = b.math("MULTIPLY", oi.outputs["Random"], 100.0 + seed * 13.7, -2400, -300)
    offv = b.add("ShaderNodeCombineXYZ", -2250, -300)
    b.link(off.outputs[0], offv.inputs[0])
    b.link(off.outputs[0], offv.inputs[1])
    offv.inputs[2].default_value = seed * 7.31
    base = b.add("ShaderNodeVectorMath", -2100, 0, operation="ADD")
    b.link(tc.outputs["Object"], base.inputs[0])
    b.link(offv.outputs[0], base.inputs[1])
    P = base.outputs[0]

    # stretched coords: pigment drifts run along the tile (horizontal streaks)
    st = b.add("ShaderNodeMapping", -1900, 200)
    st.inputs["Scale"].default_value = (1.0 / p["stretch"], 1.0, 1.0)
    b.link(P, st.inputs["Vector"])
    S = st.outputs[0]

    st2 = b.add("ShaderNodeMapping", -1900, 0)
    st2.inputs["Scale"].default_value = (1.0 / (p["stretch"] * 1.8), 1.0, 1.0)
    b.link(P, st2.inputs["Vector"])
    S2 = st2.outputs[0]

    # sand grains: voronoi cells ~1.2 mm, each cell its own value
    vor = b.add("ShaderNodeTexVoronoi", -1700, -800)
    vor.inputs["Scale"].default_value = 800.0
    vor.inputs["Randomness"].default_value = 1.0
    b.link(P, vor.inputs["Vector"])
    gval = b.add("ShaderNodeSeparateColor", -1500, -800)
    b.link(vor.outputs["Color"], gval.inputs[0])
    g = gval.outputs[0]
    grain_fac = g

    # 1. large cloudy patches between two base colours
    n_patch = b.noise(S, 2.2, 6, 0.62, 0.3, -1700, 400)
    r_patch = b.ramp(n_patch.outputs["Fac"], [(0.35, rgba(p["base_a"])), (0.65, rgba(p["base_b"]))], -1450, 400)

    # 2. pigment accent drifts (ochre / mustard), ragged edges from a fine noise
    n_acc = b.noise(S2, 3.0, 8, 0.7, 0.6, -1700, 100)
    n_fine = b.noise(P, 60.0, 4, 0.6, 0.0, -1700, -150)
    acc_edge = b.math("ADD", n_acc.outputs["Fac"], b.math("MULTIPLY", n_fine.outputs["Fac"], 0.25, -1500, -150).outputs[0], -1300, 100)
    acc_edge = b.math("ADD", acc_edge.outputs[0], b.math("MULTIPLY", grain_fac, 0.18, -1500, -50).outputs[0], -1250, 100)
    acc_mask = b.ramp(acc_edge.outputs[0], [(0.70, grey(0)), (0.80, grey(1))], -1100, 100)
    acc_amt = b.math("MULTIPLY", acc_mask.outputs["Color"], p["accent_amt"], -850, 100)
    col = b.mix(acc_amt.outputs[0], r_patch.outputs["Color"], rgba(p["accent"]), "MIX", -650, 300)

    # 3. pale "bloom" (efflorescence) blotches, broken up by the fine noise
    n_bl = b.noise(P, 1.6, 7, 0.65, 0.8, -1700, -400)
    bl_edge = b.math("ADD", n_bl.outputs["Fac"], b.math("MULTIPLY", n_fine.outputs["Fac"], 0.35, -1500, -500).outputs[0], -1300, -400)
    bl_edge = b.math("ADD", bl_edge.outputs[0], b.math("MULTIPLY", grain_fac, 0.15, -1500, -600).outputs[0], -1250, -400)
    bl_mask = b.ramp(bl_edge.outputs[0], [(0.74, grey(0)), (0.84, grey(1))], -1100, -400)
    bl_amt = b.math("MULTIPLY", bl_mask.outputs["Color"], p["bloom_amt"], -850, -400)
    col = b.mix(bl_amt.outputs[0], col.outputs[2], rgba(p["bloom"]), "MIX", -450, 200)

    # dark and light speckles
    dark = b.ramp(g, [(0.0, grey(1)), (0.10, grey(1)), (0.13, grey(0))], -1300, -750, "CONSTANT")
    light = b.ramp(g, [(0.0, grey(0)), (0.94, grey(0)), (0.95, grey(1))], -1300, -1000, "CONSTANT")
    # per-grain value jitter (salt-and-pepper)
    jit = b.mix(p["grain_contrast"], col.outputs[2], (0.5, 0.5, 0.5, 1), "OVERLAY", -250, 200)
    b.link(vor.outputs["Color"], jit.inputs[7])
    col = b.mix(dark.outputs["Color"], jit.outputs[2], rgba(p["grain_dark"]), "MIX", -50, 200)
    col = b.mix(light.outputs["Color"], col.outputs[2], rgba(p["grain_light"]), "MIX", 150, 200)

    # 5. riven ridges: wavy horizontal steps (the mould's split-stone pattern)
    wv = b.add("ShaderNodeTexWave", -1700, -1300)
    wv.wave_type = "BANDS"
    wv.bands_direction = "Y"
    wv.wave_profile = "SAW"
    wv.inputs["Scale"].default_value = p["ridge_count"] / 2.0
    wv.inputs["Distortion"].default_value = 6.0
    wv.inputs["Detail"].default_value = 3.0
    wv.inputs["Detail Scale"].default_value = 1.5
    b.link(P, wv.inputs["Vector"])
    ridge = b.ramp(wv.outputs["Fac"], [(0.0, grey(0)), (0.85, grey(1)), (1.0, grey(0))], -1450, -1300)
    n_rm = b.noise(S, 2.5, 3, 0.5, 0.0, -1700, -1600)
    ridge_mask = b.ramp(n_rm.outputs["Fac"], [(0.42, grey(0)), (0.6, grey(1))], -1450, -1600)
    ridges = b.math("MULTIPLY", ridge.outputs["Color"], ridge_mask.outputs["Color"], -1150, -1400)
    ridges = b.math("MULTIPLY", ridges.outputs[0], p["riven"], -950, -1400)
    undul = b.noise(S, 1.2, 4, 0.5, 0.0, -1700, -1900)

    # height (metres): ridges 1.5 mm, undulation 1 mm, grains 0.3 mm
    h = b.math("MULTIPLY", ridges.outputs[0], 0.0015, -750, -1400)
    h2 = b.math("MULTIPLY", undul.outputs["Fac"], 0.001 * max(p["riven"], 0.2), -750, -1700)
    h3 = b.math("MULTIPLY", vor.outputs["Distance"], -0.0003, -750, -1000)
    h = b.math("ADD", h.outputs[0], h2.outputs[0], -550, -1500)
    h = b.math("ADD", h.outputs[0], h3.outputs[0], -350, -1300)
    H = h.outputs[0]

    # shade the low side of each ridge a touch darker (dust settles there)
    cav = b.math("MULTIPLY", ridges.outputs[0], 0.05, -550, -1100)
    col = b.mix(cav.outputs[0], col.outputs[2], rgba(p["grain_dark"]), "MULTIPLY", 350, 200)

    bump = b.add("ShaderNodeBump", 350, -600)
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = 1.0
    b.link(H, bump.inputs["Height"])

    rough = b.math("ADD", b.math("MULTIPLY", g, 0.08, 150, -300).outputs[0], p["rough"] - 0.04, 350, -300, clamp=True)

    bsdf = b.add("ShaderNodeBsdfPrincipled", 650, 200)
    b.link(col.outputs[2], bsdf.inputs["Base Color"])
    b.link(rough.outputs[0], bsdf.inputs["Roughness"])
    b.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.3

    disp = b.add("ShaderNodeDisplacement", 650, -500)
    disp.inputs["Scale"].default_value = 1.0
    disp.inputs["Midlevel"].default_value = 0.0
    b.link(H, disp.inputs["Height"])

    out = b.add("ShaderNodeOutputMaterial", 950, 0)
    b.link(bsdf.outputs[0], out.inputs["Surface"])
    b.link(disp.outputs[0], out.inputs["Displacement"])
    # stash for baking
    mat["_albedo"] = col.name
    mat["_rough"] = rough.name
    mat["_height"] = h.name
    return mat



# ---------------------------------------------------------------- real wash patterns (library)
LIB_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "library")


def load_library(lib):
    import json
    colors, patterns = {}, []
    cp = os.path.join(lib, "colors.json")
    if os.path.exists(cp):
        with open(cp) as f:
            colors = json.load(f)
    pat = os.path.join(lib, "patterns")
    for root, dirs, files in os.walk(pat):
        dirs.sort()
        if "wash.png" in files:
            finish, name, stem = os.path.relpath(root, pat).replace(os.sep, "/").split("/")[:3]
            patterns.append(dict(finish=finish, name=name, id=f"{name}/{stem}", dir=root))
    return colors, patterns


def color_to_params(entry, base):
    p = dict(base)
    for k, v in entry["palette"].items():
        p[k] = tuple(v)
    p["accent_amt"] = entry.get("accent_amt", p["accent_amt"])
    return p


def load_img(path, color=False):
    img = bpy.data.images.load(os.path.abspath(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return img


def build_pattern_material(name, p, pdir, riven, size):
    """Base colour = YOUR palette painted through the real wash silhouettes of one scanned slab."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    b = NB(t)
    try:
        mat.displacement_method = "BOTH"
    except AttributeError:
        mat.cycles.displacement_method = "BOTH"

    # tile face -> 0..1, random 180 deg turn per tile so a reused scan never looks repeated
    tc = b.add("ShaderNodeTexCoord", -2200, 0)
    oi = b.add("ShaderNodeObjectInfo", -2200, -250)
    turn = b.math("ROUND", oi.outputs["Random"], None, -2000, -250)
    turn = b.math("MULTIPLY", turn.outputs[0], math.pi, -1850, -250)
    rot = b.add("ShaderNodeCombineXYZ", -1700, -250)
    b.link(turn.outputs[0], rot.inputs[2])
    mp = b.add("ShaderNodeMapping", -1500, 0)
    mp.inputs["Scale"].default_value = (1.0 / size, 1.0 / size, 1.0)
    mp.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    b.link(tc.outputs["Object"], mp.inputs["Vector"])
    b.link(rot.outputs[0], mp.inputs["Rotation"])
    UV = mp.outputs[0]

    def tex(file, y):
        n = b.add("ShaderNodeTexImage", -1250, y)
        n.image = load_img(os.path.join(pdir, file))
        n.extension = "EXTEND"
        b.link(UV, n.inputs["Vector"])
        return n.outputs["Color"]

    wash, accent = tex("wash.png", 400), tex("accent.png", 100)
    grain, relief = tex("grain.jpg", -200), tex("relief.jpg", -500)

    col = b.ramp(wash, [(0.0, rgba(p["base_a"])), (0.55, rgba(p["base_b"])), (1.0, rgba(p["bloom"]))], -950, 400)
    acc = b.ramp(accent, [(0.45, grey(0)), (0.98, grey(1))], -950, 100)
    acc_amt = b.math("MULTIPLY", acc.outputs["Color"], p["accent_amt"], -700, 100)
    c = b.mix(acc_amt.outputs[0], col.outputs["Color"], rgba(p["accent"]), "MIX", -500, 350)
    jit = b.mix(p["grain_contrast"], c.outputs[2], (0.5, 0.5, 0.5, 1), "OVERLAY", -300, 350)
    b.link(grain, jit.inputs[7])
    dark = b.ramp(grain, [(0.0, grey(1)), (0.12, grey(1)), (0.16, grey(0))], -700, -200, "CONSTANT")
    light = b.ramp(grain, [(0.0, grey(0)), (0.9, grey(0)), (0.91, grey(1))], -700, -450, "CONSTANT")
    c = b.mix(dark.outputs["Color"], jit.outputs[2], rgba(p["grain_dark"]), "MIX", -100, 350)
    c = b.mix(light.outputs["Color"], c.outputs[2], rgba(p["grain_light"]), "MIX", 100, 350)

    # relief map -> height; flat finish keeps only a whisper of it
    rc = b.math("SUBTRACT", relief, 0.5, -900, -700)
    h = b.math("MULTIPLY", rc.outputs[0], 0.0016 * riven + 0.0002, -700, -700)
    gc = b.math("SUBTRACT", grain, 0.5, -900, -900)
    h2 = b.math("MULTIPLY", gc.outputs[0], 0.00025, -700, -900)
    h = b.math("ADD", h.outputs[0], h2.outputs[0], -500, -800)

    bump = b.add("ShaderNodeBump", 100, -500)
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 1.0
    b.link(h.outputs[0], bump.inputs["Height"])
    rough = b.math("ADD", b.math("MULTIPLY", grain, 0.08, -100, -250).outputs[0], p["rough"] - 0.04, 100, -250, clamp=True)
    bsdf = b.add("ShaderNodeBsdfPrincipled", 400, 200)
    b.link(c.outputs[2], bsdf.inputs["Base Color"])
    b.link(rough.outputs[0], bsdf.inputs["Roughness"])
    b.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    disp = b.add("ShaderNodeDisplacement", 400, -500)
    disp.inputs["Midlevel"].default_value = 0.0
    b.link(h.outputs[0], disp.inputs["Height"])
    out = b.add("ShaderNodeOutputMaterial", 700, 0)
    b.link(bsdf.outputs[0], out.inputs["Surface"])
    b.link(disp.outputs[0], out.inputs["Displacement"])
    mat["_albedo"] = c.name
    mat["_rough"] = rough.name
    mat["_height"] = h.name
    return mat


def parse_hex_overrides(text, p):
    """--set base_a=#aabbcc,accent=#c89a50,accent_amt=0.5"""
    p = dict(p)
    for part in text.split(","):
        k, v = part.split("=")
        k, v = k.strip(), v.strip()
        if v.startswith("#"):
            p[k] = tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
        else:
            p[k] = float(v)
    return p


# ---------------------------------------------------------------- geometry & scene
def make_tile(name, size, thick, mat, loc, displace):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], thick / 2))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (size, size, thick)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = ob.modifiers.new("Arris", "BEVEL")
    bev.width = 0.002
    bev.segments = 2
    if displace:
        sub = ob.modifiers.new("Subdiv", "SUBSURF")
        sub.subdivision_type = "SIMPLE"
        sub.levels = 3
        sub.render_levels = 8
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth() if displace else None
    bpy.ops.mesh.uv_texture_add() if not ob.data.uv_layers else None
    return ob


def setup_scene(args, span):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = args.res
    sc.view_settings.view_transform = "Standard"   # keeps sampled colours true
    if args.displace:
        try:
            sc.cycles.feature_set = "EXPERIMENTAL"
        except Exception:
            pass
    # top-down ortho camera
    bpy.ops.object.camera_add(location=(0, 0, 3 * span))
    cam = bpy.context.active_object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = span * 1.08
    sc.camera = cam
    # soft key from low angle (shows riven ridges) + dim fill
    k = span / 0.608   # light rig was tuned on one 600 mm tile
    bpy.ops.object.light_add(type="AREA", location=(0, -2.5 * k, 1.6 * k))
    key = bpy.context.active_object
    key.data.energy = 380 * span * span
    key.data.size = 1.5 * k
    key.rotation_euler = (math.radians(57), 0, 0)
    w = bpy.data.worlds.new("World") if not sc.world else sc.world
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.8, 0.8, 0.82, 1)
    bg.inputs["Strength"].default_value = 0.25
    # white table
    bpy.ops.mesh.primitive_plane_add(size=span * 3, location=(0, 0, -0.0005))
    tbl = bpy.context.active_object
    tm = bpy.data.materials.new("Table")
    tm.use_nodes = True
    tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
    tbl.data.materials.append(tm)


# ---------------------------------------------------------------- baking
def bake_maps(ob, mat, out_dir, res):
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    sc.cycles.samples = 16
    t = mat.node_tree
    out = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL")
    surf_link = out.inputs["Surface"].links[0].from_socket
    disp_link = out.inputs["Displacement"].links[0].from_socket
    t.links.remove(out.inputs["Displacement"].links[0])
    for m in ob.modifiers:
        m.show_render = m.type == "BEVEL"
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    em = t.nodes.new("ShaderNodeEmission")
    tex = t.nodes.new("ShaderNodeTexImage")
    t.nodes.active = tex

    def run(tag, socket, kind, colorspace):
        img = bpy.data.images.new(f"{mat.name}_{tag}", res, res, float_buffer=(tag == "height"))
        img.colorspace_settings.name = colorspace
        tex.image = img
        if socket is not None:
            t.links.new(socket, em.inputs["Color"])
            t.links.new(em.outputs[0], out.inputs["Surface"])
        else:
            t.links.new(surf_link, out.inputs["Surface"])
        bpy.ops.object.bake(type=kind, margin=8)
        path = os.path.join(out_dir, f"{mat.name}_{tag}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        if tag == "height":
            img.use_half_precision = False
        img.save()
        print("BAKED", path)

    t.links.new(t.nodes[mat["_height"]].outputs[0], em.inputs["Color"])
    # height comes out in metres; rescale so 0..2.5 mm -> 0..1
    norm = t.nodes.new("ShaderNodeMapRange")
    norm.inputs["From Min"].default_value = -0.0003
    norm.inputs["From Max"].default_value = 0.0025
    t.links.new(t.nodes[mat["_height"]].outputs[0], norm.inputs["Value"])
    run("albedo", t.nodes[mat["_albedo"]].outputs[2], "EMIT", "sRGB")
    run("roughness", t.nodes[mat["_rough"]].outputs[0], "EMIT", "Non-Color")
    run("height", norm.outputs[0], "EMIT", "Non-Color")
    run("normal", None, "NORMAL", "Non-Color")
    t.links.new(surf_link, out.inputs["Surface"])
    t.links.new(disp_link, out.inputs["Displacement"])
    t.nodes.remove(em)
    t.nodes.remove(tex)
    t.nodes.remove(norm)


def bake_plane(mat, args):
    """Bake on a flat 1-tile plane so the maps fill 0..1 UV exactly."""
    bpy.ops.mesh.primitive_plane_add(size=args.size, location=(0, 0, 5))
    pl = bpy.context.active_object
    pl.name = "BakePlane"
    pl.data.materials.append(mat)
    bake_maps(pl, mat, args.bake, args.bake_res)
    bpy.data.objects.remove(pl)


# ---------------------------------------------------------------- main
def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="desert", choices=sorted(PRESETS))
    ap.add_argument("--match")
    ap.add_argument("--crop")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--size", type=float, default=0.6)
    ap.add_argument("--thick", type=float, default=0.04)
    ap.add_argument("--displace", action="store_true")
    ap.add_argument("--grid", type=int, default=1)
    ap.add_argument("--render")
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--bake")
    ap.add_argument("--bake-res", type=int, default=2048)
    ap.add_argument("--save")
    ap.add_argument("--keep-scene", action="store_true", help="do not clear the open scene")
    ap.add_argument("--library", default=LIB_DEFAULT)
    ap.add_argument("--color", help="colour name from library/colors.json (e.g. monsoon-r)")
    ap.add_argument("--finish", choices=["riven", "flat"], help="override the colour's own finish")
    ap.add_argument("--pattern", help="wash pattern: random (default with --color), none, a name (desert-r) or name/photo (desert-r/4)")
    ap.add_argument("--set", help="tweak colours: base_a=#aabbcc,accent=#c89a50,accent_amt=0.5")
    ap.add_argument("--list", action="store_true", help="list library colours and patterns, then stop")
    return ap.parse_args(argv)


def main():
    import random
    args = parse()
    colors, patterns = load_library(args.library)
    if args.list:
        print("COLOURS:")
        for k, v in colors.items():
            print(f"  {k:14s} {v.get('finish', '?'):6s} {v.get('source', '')}")
        print("PATTERNS:")
        for pt in patterns:
            print(f"  {pt['finish']:6s} {pt['id']}")
        return
    if not args.keep_scene:
        bpy.ops.wm.read_factory_settings(use_empty=True)

    # colour: library colour > preset; then photo match; then hand tweaks
    p = PRESETS[args.preset]
    finish = "flat" if p["riven"] == 0 else "riven"
    label = args.preset
    if args.color:
        if args.color not in colors:
            sys.exit(f"unknown colour {args.color}; have: {', '.join(colors)}")
        p = color_to_params(colors[args.color], PRESETS["desert"])
        finish = colors[args.color].get("finish", finish)
        label = args.color
    if args.finish:
        finish = args.finish
    p = dict(p, riven=1.0 if finish == "riven" else 0.0)
    if args.match:
        crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
        p = palette_from_photo(args.match, crop, p)
    if args.set:
        p = parse_hex_overrides(args.set, p)

    # pattern pool: real scans (same finish first) or procedural
    want = args.pattern or ("random" if args.color else "none")
    pool = []
    if want != "none":
        if want == "random":
            pool = [pt for pt in patterns if pt["finish"] == finish] or patterns
        else:
            pool = [pt for pt in patterns if pt["id"] == want or pt["name"] == want]
        if not pool:
            print(f"no pattern '{want}' in library, using procedural wash")
    rng = random.Random(args.seed)
    mats = []
    if pool:
        for pt in pool:
            mats.append(build_pattern_material(f"Paver_{label}_{finish}_{pt['id'].replace('/', '_')}",
                                               p, pt["dir"], p["riven"], args.size))
        print("PATTERNS", [pt["id"] for pt in pool])
    else:
        mats.append(build_material(f"Paver_{label}", p, args.seed))
    print("COLOUR", label, finish)

    joint = 0.008
    pitch = args.size + joint
    n = max(1, args.grid)
    span = n * pitch
    shuffled = []
    for i in range(n):
        for j in range(n):
            if not shuffled:
                shuffled = mats[:]
                rng.shuffle(shuffled)
            loc = ((i - (n - 1) / 2) * pitch, (j - (n - 1) / 2) * pitch)
            make_tile(f"Paver_{i}_{j}", args.size, args.thick, shuffled.pop(), loc, args.displace)
    setup_scene(args, span)
    if args.bake:
        for m in mats:
            bake_plane(m, args)
    if args.render:
        bpy.context.scene.cycles.samples = args.samples
        bpy.context.scene.render.filepath = os.path.abspath(args.render)
        bpy.ops.render.render(write_still=True)
        print("RENDERED", args.render)
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))
        print("SAVED", args.save)


if __name__ == "__main__":
    main()
