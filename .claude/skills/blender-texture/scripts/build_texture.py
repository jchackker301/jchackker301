"""Build a 100% procedural stone/concrete material + slab in Blender (any texture).

Run inside Blender (no image textures are used, everything is shader nodes):
  blender -b -P build_texture.py -- --preset presets/bella-r.json --out OUT_FOLDER [options]
  blender -b -P build_texture.py -- --preset all --out OUT_FOLDER --render

Options:
  --preset FILE|all   preset JSON from analyze_photo.py, or "all" for every file in presets/
  --out FOLDER        where the .blend (and renders) are written
  --render            also render a top-down preview PNG (Cycles)
  --patio N           also lay N x N pavers with 5 mm joints, every slab different
  --samples N         render samples (default 64)
  --res N             render size in px (default 1024)
  --bake N            also bake albedo/roughness/normal PNGs at N px (for Unreal, Unity, web)
  --seed N            texture variation seed (default 0)

Inside Blender every look control sits on ONE group node "Paver <name>" so you
can tweak it by hand (the same names as the "style" block of a preset):
Cloud Scale, Cloud Amount, Stretch, Direction, Accent Amount, Accent Scale,
Wisp Amount, Wisp Scale, Edge Mottle, Fleck Amount, Speckle, Grain Size, Riven Depth, Roughness, Seed.
Works in Blender 4.0+ (tested on 5.1).
"""
import glob
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
PRESET_DIR = os.path.join(os.path.dirname(HERE), "presets")


# ---------------------------------------------------------------- helpers
def args():
    import argparse
    # blender -b -P build_texture.py -- ARGS   or   python build_texture.py ARGS (pip install bpy)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--patio", type=int, default=0)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--bake", type=int, default=0)
    ap.add_argument("--seed", type=float, default=0.0)
    return ap.parse_args(argv)


def sock(node, name, out=False, kind=None):
    """Find a socket by name (and optional type) - socket indices change between versions."""
    for s in (node.outputs if out else node.inputs):
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in (node.outputs if out else node.inputs):
        if s.name == name:
            return s
    alias = {"Fac": "Factor", "Factor": "Fac"}.get(name)
    if alias:
        return sock(node, alias, out, kind)
    raise KeyError(f"{node.bl_idname} has no {'output' if out else 'input'} {name}")


def rgba(c):
    return (c[0], c[1], c[2], 1.0)


class G:
    """Tiny node-building helper for a node tree."""

    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links
        self.x = 0

    def add(self, kind, loc=None, **props):
        nd = self.n.new(kind)
        nd.location = loc or (self.x, 0)
        self.x += 40
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.l.new(a, b)

    def math(self, op, a, b=None, loc=None, clamp=False):
        nd = self.add("ShaderNodeMath", loc, operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def mix_col(self, fac, a, b, loc=None, blend="MIX"):
        nd = self.add("ShaderNodeMix", loc, data_type="RGBA", blend_type=blend, clamp_factor=True)
        f = sock(nd, "Factor", kind="VALUE")
        if isinstance(fac, (int, float)):
            f.default_value = fac
        else:
            self.link(fac, f)
        for name, v in (("A", a), ("B", b)):
            s = sock(nd, name, kind="RGBA")
            if isinstance(v, tuple):
                s.default_value = v
            else:
                self.link(v, s)
        return sock(nd, "Result", out=True, kind="RGBA")

    def ramp(self, src, stops, loc=None, interp="LINEAR"):
        nd = self.add("ShaderNodeValToRGB", loc)
        cr = nd.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position, cr.elements[0].color = stops[0][0], stops[0][1]
        for p, c in stops[1:]:
            e = cr.elements.new(p)
            e.color = c
        self.link(src, nd.inputs[0])
        return nd.outputs[0]


# ---------------------------------------------------------------- the material
GROUP_INPUTS = [
    # name, default, min, max
    ("Cloud Scale", 1.6, 0.1, 20.0),
    ("Cloud Amount", 0.5, 0.0, 1.0),
    ("Stretch", 1.3, 1.0, 5.0),
    ("Accent Amount", 0.1, 0.0, 1.0),
    ("Speckle", 0.6, 0.0, 1.0),
    ("Grain Size", 1.0, 0.2, 5.0),
    ("Riven Depth", 0.0, 0.0, 1.0),
    ("Roughness", 0.88, 0.0, 1.0),
    ("Seed", 0.0, -1000.0, 1000.0),
    ("Direction", 0.0, -180.0, 180.0),
    ("Accent Scale", 2.2, 0.2, 10.0),
    ("Wisp Amount", 0.5, 0.0, 1.0),
    ("Edge Mottle", 0.5, 0.0, 1.0),
    ("Fleck Amount", 0.3, 0.0, 1.0),
    ("Wisp Scale", 5.0, 0.5, 20.0),
]


def build_group(p):
    """Node group: Vector in -> Color, Roughness, Height, Normal out."""
    name = f"Paver {p['name']}"
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new(name, "ShaderNodeTree")
    iface = ng.interface
    iface.new_socket("Vector", in_out="INPUT", socket_type="NodeSocketVector")
    for nm, dv, lo, hi in GROUP_INPUTS:
        s = iface.new_socket(nm, in_out="INPUT", socket_type="NodeSocketFloat")
        s.default_value, s.min_value, s.max_value = dv, lo, hi
    for nm in ("Base", "Dark", "Accent", "Light"):
        s = iface.new_socket(f"{nm} Color", in_out="INPUT", socket_type="NodeSocketColor")
    iface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    iface.new_socket("Roughness", in_out="OUTPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Height", in_out="OUTPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Normal", in_out="OUTPUT", socket_type="NodeSocketVector")

    g = G(ng)
    gi = g.add("NodeGroupInput", (-1800, 0))
    go = g.add("NodeGroupOutput", (1400, 0))
    I = lambda n: sock(gi, n, out=True)

    # --- coordinates: vector is in metres; seed shifts the pattern per slab
    seed_vec = g.add("ShaderNodeCombineXYZ", (-1600, -300))
    for ax, mul in (("X", 1.0), ("Y", 1.7), ("Z", 2.3)):
        g.link(g.math("MULTIPLY", I("Seed"), mul * 13.37), sock(seed_vec, ax))
    vec = g.add("ShaderNodeVectorMath", (-1400, 0), operation="ADD")
    g.link(I("Vector"), vec.inputs[0])
    g.link(seed_vec.outputs[0], vec.inputs[1])
    V = vec.outputs[0]

    # rotate so the streak direction matches the photo (0 = sideways, 90 = top-to-bottom)
    rot = g.add("ShaderNodeVectorRotate", (-1300, 150), rotation_type="Z_AXIS")
    g.link(V, sock(rot, "Vector"))
    g.link(g.math("RADIANS", I("Direction")), sock(rot, "Angle"))
    # stretched coords: clouds run along the streak direction
    st = g.add("ShaderNodeCombineXYZ", (-1400, 300))
    g.link(g.math("DIVIDE", 1.0, I("Stretch")), sock(st, "X"))
    sock(st, "Y").default_value = 1.0
    sock(st, "Z").default_value = 1.0
    vs = g.add("ShaderNodeVectorMath", (-1200, 300), operation="MULTIPLY")
    g.link(sock(rot, "Vector", out=True), vs.inputs[0])
    g.link(st.outputs[0], vs.inputs[1])
    VS = vs.outputs[0]

    def noise(vec_in, scale, detail, rough, distort, loc, scale_socket=None, mult=1.0):
        nd = g.add("ShaderNodeTexNoise", loc, noise_dimensions="3D")
        g.link(vec_in, sock(nd, "Vector"))
        if scale_socket is not None:
            g.link(g.math("MULTIPLY", scale_socket, mult), sock(nd, "Scale"))
        else:
            sock(nd, "Scale").default_value = scale
        sock(nd, "Detail").default_value = detail
        sock(nd, "Roughness").default_value = rough
        sock(nd, "Distortion").default_value = distort
        return sock(nd, "Fac", out=True)

    # fine mottle: makes cloud edges grainy like real pigment, not airbrushed
    fine = noise(V, 380, 3, 0.6, 0.0, (-1000, 700))
    dith = g.math("MULTIPLY", g.math("SUBTRACT", fine, 0.5), g.math("MULTIPLY", I("Edge Mottle"), 0.6))

    def band(n, center, width):
        """Soft mask: 0 below center, 1 above. Noise Fac sits around 0.5 +- 0.1."""
        n = g.math("ADD", n, dith)
        return g.math("ADD", g.math("DIVIDE", g.math("SUBTRACT", n, center), width), 0.5, clamp=True)

    # --- big colour clouds (dark vs base); more amount = lower threshold = more cloud
    cl = noise(VS, 0, 8, 0.6, 0.35, (-1000, 400), I("Cloud Scale"), 1.0)
    cl_m = band(cl, g.math("SUBTRACT", 0.58, g.math("MULTIPLY", I("Cloud Amount"), 0.14)), 0.10)
    col = g.mix_col(cl_m, I("Base Color"), I("Dark Color"), (-400, 400))

    # --- accent patches (gold), smaller and more broken up
    ac = noise(VS, 0, 10, 0.65, 0.9, (-1000, 100), g.math("MULTIPLY", I("Cloud Scale"), I("Accent Scale")), 1.0)
    ac_m = band(ac, g.math("SUBTRACT", 0.64, g.math("MULTIPLY", I("Accent Amount"), 0.30)), 0.05)
    # broken edges: multiply by fine noise so patches look sprinkled, not painted
    ac_fine = noise(V, 260, 4, 0.6, 0.0, (-1000, -100))
    ac_m = g.math("MULTIPLY", ac_m, g.math("MULTIPLY", g.math("SUBTRACT", ac_fine, 0.25), 3.5, clamp=True), clamp=True)
    col = g.mix_col(ac_m, col, I("Accent Color"), (-200, 300))

    # --- pale cloud wisps
    lt = noise(VS, 0, 9, 0.62, 0.8, (-1000, -300), g.math("MULTIPLY", I("Cloud Scale"), I("Wisp Scale")), 1.0)
    lt_m = band(lt, g.math("SUBTRACT", 0.68, g.math("MULTIPLY", I("Wisp Amount"), 0.26)), 0.03)
    lt_m = g.math("MULTIPLY", lt_m, g.math("MULTIPLY", g.math("SUBTRACT", ac_fine, 0.25), 2.0, clamp=True), clamp=True)
    col = g.mix_col(lt_m, col, I("Light Color"), (0, 200))

    # --- aggregate grain: voronoi cells = sand / stone chips (~1-3 mm)
    vo = g.add("ShaderNodeTexVoronoi", (-1000, -600), voronoi_dimensions="3D", feature="F1")
    g.link(V, sock(vo, "Vector"))
    g.link(g.math("DIVIDE", 1100.0, I("Grain Size")), sock(vo, "Scale"))
    sock(vo, "Randomness").default_value = 1.0
    cell = g.add("ShaderNodeSeparateColor", (-800, -600))
    g.link(sock(vo, "Color", out=True), cell.inputs[0])
    rnd = sock(cell, "Red", out=True)
    # each grain: mostly matches paste, some dark chips, some light quartz
    dark_chip = g.math("MULTIPLY", g.math("LESS_THAN", rnd, 0.10), g.math("MULTIPLY", I("Speckle"), 0.6))
    light_chip = g.math("GREATER_THAN", rnd, g.math("SUBTRACT", 0.997, g.math("MULTIPLY", I("Fleck Amount"), 0.025)))
    tint = g.math("SUBTRACT", sock(cell, "Green", out=True), 0.5)  # small per-grain value jitter
    jit = g.math("ADD", 1.0, g.math("MULTIPLY", tint, g.math("MULTIPLY", I("Speckle"), 0.7)))
    jit_col = g.add("ShaderNodeCombineColor", (-400, -500))
    for ch in ("Red", "Green", "Blue"):
        g.link(jit, sock(jit_col, ch))
    col = g.mix_col(1.0, col, jit_col.outputs[0], (200, 100), blend="MULTIPLY")
    darkc = g.mix_col(0.55, I("Dark Color"), (0.02, 0.02, 0.02, 1), (200, -100))
    col = g.mix_col(dark_chip, col, darkc, (400, 100))
    lightc = g.mix_col(0.6, I("Light Color"), (0.8, 0.79, 0.76, 1), (200, -250))
    col = g.mix_col(light_chip, col, lightc, (600, 100))

    # --- height: grain pits + riven split-stone ledges
    pits = g.math("POWER", sock(vo, "Distance", out=True), 0.5)  # 0 at grain centre -> rounded bumps
    pits = g.math("SUBTRACT", 1.0, pits)
    # riven: terraced noise (constant ramp = layered ledges) blurred by a little noise
    rv = noise(VS, 0, 6, 0.55, 0.8, (-1000, -900), I("Cloud Scale"), 1.3)
    rv_t = g.ramp(rv, [(0.0, (0, 0, 0, 1)), (0.40, (0.2, 0.2, 0.2, 1)), (0.47, (0.45, 0.45, 0.45, 1)),
                       (0.53, (0.62, 0.62, 0.62, 1)), (0.60, (0.85, 0.85, 0.85, 1)), (0.68, (1, 1, 1, 1))],
                  (-700, -900), interp="EASE")
    rv_soft = g.math("ADD", g.math("MULTIPLY", rv_t, 0.8), g.math("MULTIPLY", rv, 0.4))
    riven = g.math("MULTIPLY", rv_soft, I("Riven Depth"))
    height = g.math("ADD", g.math("MULTIPLY", pits, 0.08), riven)

    # bump normal (works in Eevee and Cycles without displacement)
    bump_g = g.add("ShaderNodeBump", (800, -500))
    sock(bump_g, "Strength").default_value = 0.35
    sock(bump_g, "Distance").default_value = 0.0006
    g.link(g.math("MULTIPLY", pits, 1.0), sock(bump_g, "Height"))
    bump_r = g.add("ShaderNodeBump", (1000, -500))
    sock(bump_r, "Strength").default_value = 0.7
    sock(bump_r, "Distance").default_value = 0.0025
    g.link(riven, sock(bump_r, "Height"))
    g.link(sock(bump_g, "Normal", out=True), sock(bump_r, "Normal"))

    # roughness: chips are a bit smoother, riven tops slightly polished
    rough = g.math("SUBTRACT", I("Roughness"), g.math("MULTIPLY", light_chip, 0.15))
    rough = g.math("SUBTRACT", rough, g.math("MULTIPLY", riven, 0.05), clamp=True)

    g.link(col, sock(go, "Color"))
    g.link(rough, sock(go, "Roughness"))
    g.link(height, sock(go, "Height"))
    g.link(sock(bump_r, "Normal", out=True), sock(go, "Normal"))
    return ng


def build_material(p, seed=0.0):
    name = f"Paver {p['name']}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    try:  # real displacement in Cycles, bump fallback elsewhere
        mat.displacement_method = "BOTH"
    except Exception:
        try:
            mat.cycles.displacement_method = "BOTH"
        except Exception:
            pass
    nt = mat.node_tree
    nt.nodes.clear()
    g = G(nt)
    tc = g.add("ShaderNodeTexCoord", (-900, 0))
    oi = g.add("ShaderNodeObjectInfo", (-900, -300))
    grp = g.add("ShaderNodeGroup", (-500, 0))
    grp.node_tree = build_group(p)
    grp.label = name
    g.link(sock(tc, "Object", out=True), sock(grp, "Vector"))
    # every slab looks different: seed = preset seed + object random
    g.link(g.math("ADD", g.math("MULTIPLY", sock(oi, "Random", out=True), 100.0), seed, (-700, -300)), sock(grp, "Seed"))

    vals = {
        "Cloud Scale": 1.6,
        "Cloud Amount": p["cloud"],
        "Stretch": p["stretch"],
        "Direction": p.get("direction_deg", 0.0),
        "Accent Amount": min(1.0, p["accent_share"] * 4.0),
        "Accent Scale": 2.2,
        "Wisp Amount": p.get("wisp", 0.5),
        "Edge Mottle": p.get("mottle", 0.5),
        "Fleck Amount": p.get("fleck", 0.3),
        "Wisp Scale": 5.0,
        "Speckle": p["speckle"],
        "Grain Size": 1.0,
        "Riven Depth": min(1.0, p.get("riven_depth_mm", 0) / 2.5),
        "Roughness": p["roughness"],
    }
    # the style card (filled by the AI after looking at the photo) wins over measured numbers
    vals.update({k: v for k, v in p.get("style", {}).items() if k in vals})
    for k, v in vals.items():
        sock(grp, k).default_value = v
    for role in ("Base", "Dark", "Accent", "Light"):
        sock(grp, f"{role} Color").default_value = rgba(p[role.lower()])

    bsdf = g.add("ShaderNodeBsdfPrincipled", (-100, 0))
    g.link(sock(grp, "Color", out=True), sock(bsdf, "Base Color"))
    g.link(sock(grp, "Roughness", out=True), sock(bsdf, "Roughness"))
    g.link(sock(grp, "Normal", out=True), sock(bsdf, "Normal"))
    out = g.add("ShaderNodeOutputMaterial", (250, 0))
    g.link(sock(bsdf, "BSDF", out=True), sock(out, "Surface"))
    disp = g.add("ShaderNodeDisplacement", (-100, -400))
    g.link(sock(grp, "Height", out=True), sock(disp, "Height"))
    sock(disp, "Scale").default_value = 0.0025 if p["finish"] == "riven" else 0.0004
    sock(disp, "Midlevel").default_value = 0.0
    g.link(sock(disp, "Displacement", out=True), sock(out, "Displacement"))
    return mat


# ---------------------------------------------------------------- geometry & scene
def make_slab(p, mat, loc=(0, 0, 0), name=None):
    sx, sy, sz = [v / 1000.0 for v in p.get("size_mm", [600, 600, 50])]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], loc[2] + sz / 2))
    ob = bpy.context.active_object
    ob.name = name or f"{p['name']} slab"
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    bev = ob.modifiers.new("Arris", "BEVEL")
    bev.width, bev.segments = 0.003, 2
    sub = ob.modifiers.new("Detail", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels, sub.render_levels = 2, 6  # enough faces for Cycles displacement on riven faces
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def setup_scene(p, res, samples, span, aspect=1.0):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x = res
    sc.render.resolution_y = max(64, int(res * aspect))
    sc.view_settings.view_transform = "Standard"  # keep measured colours true
    # top-down orthographic camera like the photo booth
    cam_d = bpy.data.cameras.new("TopCam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = span * 1.08
    cam = bpy.data.objects.new("TopCam", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (0, 0, 3)
    sc.camera = cam
    # calibrated light: sun ~= pi W/m2 total so a surface with albedo A renders ~= A
    # (keeps the colours measured from the photo). Low 20 deg side tilt shows riven ledges.
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy, ld.angle = 2.75, math.radians(12)
    lo = bpy.data.objects.new("Sun", ld)
    lo.rotation_euler = (math.radians(20), math.radians(8), 0)
    sc.collection.objects.link(lo)
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    sock(world.node_tree.nodes["Background"], "Color").default_value = (0.8, 0.8, 0.8, 1)
    sock(world.node_tree.nodes["Background"], "Strength").default_value = 0.2


def bake(ob, mat, out_dir, px, tag):
    """Bake the procedural look to PNGs (for engines that cannot read Blender nodes)."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 8
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_remove(modifier="Detail")
    bpy.ops.object.modifier_remove(modifier="Arris")
    # top face UVs fill 0..1
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=0.6, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    grp = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeGroup")
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
    files = {}
    for kind in ("albedo", "roughness", "normal"):
        img = bpy.data.images.new(f"{tag}_{kind}", px, px, float_buffer=False)
        if kind != "albedo":
            img.colorspace_settings.name = "Non-Color"
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
        bake_type = {"albedo": "EMIT", "roughness": "EMIT", "normal": "NORMAL"}[kind]
        emit = None
        if bake_type == "EMIT":
            emit = nt.nodes.new("ShaderNodeEmission")
            src = sock(grp, "Color" if kind == "albedo" else "Roughness", out=True)
            nt.links.new(src, sock(emit, "Color"))
            nt.links.new(emit.outputs[0], sock(out, "Surface"))
        bpy.ops.object.bake(type=bake_type, margin=4)
        path = os.path.join(out_dir, f"{tag}_{kind}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        files[kind] = path
        if emit:
            nt.nodes.remove(emit)
            nt.links.new(sock(bsdf, "BSDF", out=True), sock(out, "Surface"))
        nt.nodes.remove(tex)
    return files


def run_one(preset_path, a):
    with open(preset_path) as f:
        p = json.load(f)
    tag = os.path.splitext(os.path.basename(preset_path))[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat = build_material(p, a.seed)
    size = p.get("size_mm", [600, 600, 50])[0] / 1000.0
    if a.patio > 1:
        joint, n = 0.005, a.patio
        step = size + joint
        off = (n - 1) * step / 2
        for i in range(n):
            for j in range(n):
                make_slab(p, mat, (i * step - off, j * step - off, 0), f"{p['name']} {i}-{j}")
        span = n * step
    else:
        make_slab(p, mat)
        span = size
    sx, sy = p.get("size_mm", [600, 600, 50])[:2]
    setup_scene(p, a.res, a.samples, span, 1.0 if a.patio > 1 else sy / sx)
    os.makedirs(a.out, exist_ok=True)
    blend = os.path.join(os.path.abspath(a.out), f"{tag}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("SAVED", blend)
    if a.render:
        bpy.context.scene.render.filepath = os.path.join(os.path.abspath(a.out), f"{tag}_render.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", bpy.context.scene.render.filepath)
    if a.bake:
        ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
        for k, v in bake(ob, mat, os.path.abspath(a.out), a.bake, tag).items():
            print("BAKED", k, v)


def main():
    a = args()
    if a.preset == "all":
        paths = sorted(glob.glob(os.path.join(PRESET_DIR, "*.json")))
    else:
        paths = [a.preset]
    for pth in paths:
        run_one(pth, a)
    print("DONE", len(paths))


if __name__ == "__main__":
    main()
