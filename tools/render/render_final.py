"""Ray-trace the final robot in one game pose, with simplified field parts around it.

Needs Blender's Python module (bpy 5.x, Python 3.11). Reads the same data the site's 3D viewer uses:
public/robot-viewer/robot.json and robot.bin, written by tools/make_viewer_data.py.

    python3.11 tools/render/render_final.py <pose> <out.jpg> <width> <height> <samples>

Poses: start, station, l4, algae, net, climb.
Everything is built in CAD axes (X forward, Y left, Z up) in inches and scaled to metres at the root.
The robot is the real CAD. The field parts are stand-ins with the right sizes in the right places.
"""
import sys, os, json, math, glob, struct, array
import bpy, bmesh
from mathutils import Matrix, Vector

pose, out, W, H, SPP = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'public', 'robot-viewer')
IN = 0.0254
D2R = math.pi / 180

# carriage height (in), wrist angle, fork angle, tray angle: the same poses the site's viewer uses
POSES = {
    'start':   dict(c=0, th=-90, psi=90, tray=0, coral=8.3),
    'station': dict(c=1.25, th=-35, psi=90, tray=0),
    'l4':      dict(c=66, th=-52.8, psi=90, tray=0, coral=14.3),
    'algae':   dict(c=24.6, th=46, psi=90, tray=0, algae=True),
    'net':     dict(c=66, th=75, psi=90, tray=0, algae=True),
    'climb':   dict(c=1.25, th=0, psi=88, tray=90),
}
# camera position and target in CAD inches
CAMS = {
    'start':   dict(pos=(118, -92, 50), target=(0, 0, 18), lens=62),
    'station': dict(pos=(112, -116, 62), target=(-7, 0, 30), lens=50),
    'l4':      dict(pos=(-70, -190, 52), target=(11, 4, 46), lens=41),
    'algae':   dict(pos=(-56, -140, 56), target=(12, 0, 34), lens=46),
    'net':     dict(pos=(-90, -210, 34), target=(24, 0, 56), lens=30),
    'climb':   dict(pos=(-118, 132, 44), target=(-3, 2, 33), lens=46),
}
P = POSES[pose]
PIV_W, PIV_F, PIV_T = Vector((4.5, 0, 24.5)), Vector((-13.5, 0, 16.0)), Vector((0, -7.1, 27.5))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
root = bpy.data.objects.new('ROOT', None); scene.collection.objects.link(root); root.scale = (IN, IN, IN)
robot = bpy.data.objects.new('ROBOT', None); scene.collection.objects.link(robot); robot.parent = root


def about(p, rot):
    return Matrix.Translation(p) @ rot @ Matrix.Translation(-p)


def lin(hexv):
    def c(u):
        u /= 255.0
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    return (c((hexv >> 16) & 255), c((hexv >> 8) & 255), c(hexv & 255), 1.0)


def setin(bsdf, name, value):
    if name in bsdf.inputs: bsdf.inputs[name].default_value = value


def add_bump(mat, bsdf, scale, strength, detail=4.0, distance=0.0005, rough_var=None):
    nt = mat.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord'); noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = detail
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = strength; bump.inputs['Distance'].default_value = distance
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    if rough_var:
        ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.inputs['To Min'].default_value = rough_var[0]; ramp.inputs['To Max'].default_value = rough_var[1]
        nt.links.new(noise.outputs['Fac'], ramp.inputs['Value']); nt.links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])


SPEC = {
    'alu':           dict(color=0xc8ccd0, metallic=1.0, rough=0.34, bump=(6, 0.05), rv=(0.26, 0.42)),
    'alu_plate':     dict(color=0xb4b8bd, metallic=1.0, rough=0.4, bump=(5, 0.04), rv=(0.32, 0.48)),
    'alu_black':     dict(color=0x1c1f23, metallic=0.85, rough=0.42, bump=(8, 0.04), rv=(0.36, 0.5)),
    'steel':         dict(color=0xb4b9be, metallic=1.0, rough=0.24),
    'printed':       dict(color=0x17181a, rough=0.62, bump=(160, 0.25)),
    'plastic_black': dict(color=0x121315, rough=0.45),
    'polycarbonate': dict(color=0xeef6fa, rough=0.04, transmission=1.0, ior=1.58),
    'field_wall':    dict(color=0xf2f7fa, rough=0.03, transmission=1.0, ior=1.5),
    'bumper_blue':   dict(color=0x0d2f8a, rough=0.85, sheen=0.12, bump=(55, 0.5)),
    'plywood':       dict(color=0xb08a58, rough=0.7, bump=(14, 0.2)),
    'wheel_green':   dict(color=0x1f9a3e, rough=0.72, bump=(20, 0.2)),
    'rubber':        dict(color=0x101113, rough=0.78, bump=(30, 0.2)),
    'tread_blue':    dict(color=0x143a86, rough=0.8, bump=(30, 0.2)),
    'tpu_teal':      dict(color=0x1a7f8c, rough=0.6),
    'red_anodised':  dict(color=0xa3241f, metallic=0.7, rough=0.4),
    'yellow_strap':  dict(color=0xd9b81c, rough=0.8, bump=(60, 0.4)),
    'rope':          dict(color=0xc9a04a, rough=0.85),
    'pcb_green':     dict(color=0x1b6b34, rough=0.5),
    'pvc_white':     dict(color=0xeceae2, rough=0.38),
    'algae_ball':    dict(color=0x18a892, rough=0.42, coat=0.25, bump=(9, 0.12)),
    'reef_violet':   dict(color=0x6a2f95, rough=0.33, coat=0.5),
    'cage_blue':     dict(color=0x1a48b8, rough=0.36, coat=0.5),
    'hdpe_black':    dict(color=0x141517, rough=0.5, bump=(40, 0.15)),
    'diamond_plate': dict(color=0x9aa0a6, metallic=0.7, rough=0.55, bump=(90, 0.6)),
    'zinc':          dict(color=0xb9bdc2, metallic=1.0, rough=0.32),
    'white_paint':   dict(color=0xf2f2f2, rough=0.55),
    'net':           dict(color=0x1a48b8, rough=0.9, alpha=0.42),
}
MATS = {}


def mat(name):
    if name in MATS: return MATS[name]
    spec = SPEC[name]; m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    setin(b, 'Base Color', lin(spec['color'])); setin(b, 'Metallic', spec.get('metallic', 0.0)); setin(b, 'Roughness', spec['rough'])
    setin(b, 'Alpha', spec.get('alpha', 1.0))
    if 'transmission' in spec: setin(b, 'Transmission Weight', spec['transmission']); setin(b, 'IOR', spec['ior'])
    if 'coat' in spec: setin(b, 'Coat Weight', spec['coat']); setin(b, 'Coat Roughness', 0.12)
    if 'sheen' in spec: setin(b, 'Sheen Weight', spec['sheen'])
    if 'bump' in spec: add_bump(m, b, spec['bump'][0], spec['bump'][1], rough_var=spec.get('rv'))
    MATS[name] = m; return m


def material_for(color, sub, labels):
    """What a CAD colour is made of. The CAD colours some parts for clarity (stages, printed parts); here they get their real finish."""
    r, g, b, a = color
    text = ' '.join(labels)
    if 'polycarbonate' in text: return 'polycarbonate'
    if sub == 6: return 'plywood' if 'plywood' in text else ('bumper_blue' if 'padding' in text else 'alu_plate')
    if 'printed' in text and 'TPU' in text: return 'tpu_teal'
    if 'printed Onyx' in text or 'printed,' in text or ', printed' in text: return 'printed'
    if 'flex wheel' in text: return 'wheel_green'
    if 'rope' in text: return 'rope'
    if 'strap' in text: return 'yellow_strap'
    if g > r + 0.3 and g > b + 0.3: return 'pcb_green'
    if sub == 5 and ('Pigeon' in text or 'CANivore' in text): return 'plastic_black'
    if 'MAXPlanetary 25:1' in text or 'Power Distribution' in text: return 'red_anodised'
    if 'MK4i' in text:                                     # the vendor model's own colours say which piece this is
        if b > r + 0.2: return 'tread_blue'
        if max(r, g, b) < 0.1: return 'rubber'
        if max(r, g, b) < 0.35: return 'alu_black'
        if b > 0.9: return 'plastic_black'                  # encoder housing
        return 'alu' if b > r + 0.05 else 'steel'
    if 'sleeve' in text or 'neoprene' in text or 'belt' in text: return 'rubber'
    if max(r, g, b) < 0.3: return 'alu_black' if ('Kraken' in text or 'gearbox' in text) else 'plastic_black'
    if abs(r - g) < 0.05 and abs(g - b) < 0.08 and r < 0.5: return 'alu_plate'
    if abs(r - g) < 0.05 and abs(g - b) < 0.05 and 0.55 < r < 0.68: return 'steel'
    return 'alu'


# ---- the robot, from the viewer data ----
J = json.load(open(os.path.join(DATA, 'robot.json')))
raw = open(os.path.join(DATA, 'robot.bin'), 'rb').read()
q = J['q']
labels = {}
for p in J['parts']: labels.setdefault(p['m'], []).append(p['l'])
c = P['c']
M = {
    'frame': Matrix.Identity(4), 'stage_a': Matrix.Translation((0, 0, c / 3)), 'stage_b': Matrix.Translation((0, 0, 2 * c / 3)),
    'carriage': Matrix.Translation((0, 0, c)),
    'wrist': Matrix.Translation((0, 0, c)) @ about(PIV_W, Matrix.Rotation((-P['th'] - 90) * D2R, 4, 'Y')),
    'fork': about(PIV_F, Matrix.Rotation((P['psi'] - 90) * D2R, 4, 'Y')),
    'tray': about(PIV_T, Matrix.Rotation(P['tray'] * D2R, 4, 'X')),
}
for mi, m in enumerate(J['meshes']):
    pos = array.array('h'); pos.frombytes(raw[m['v0'] * 6:(m['v0'] + m['nv']) * 6])
    idx = array.array('H' if m['w'] == 2 else 'I'); idx.frombytes(raw[J['idx_offset'] + m['i0']:J['idx_offset'] + m['i0'] + m['ni'] * m['w']])
    verts = [(pos[i] * q, pos[i + 1] * q, pos[i + 2] * q) for i in range(0, len(pos), 3)]
    faces = [(idx[i], idx[i + 1], idx[i + 2]) for i in range(0, len(idx), 3)]
    me = bpy.data.meshes.new(f'm{mi}'); me.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002); bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.use_smooth = True
    try: me.set_sharp_from_angle(angle=math.radians(35))
    except Exception: pass
    me.materials.append(mat(material_for(m['color'], m['sub'], labels.get(mi, []))))
    ob = bpy.data.objects.new(f'robot_{mi}', me); scene.collection.objects.link(ob); ob.parent = robot; ob.matrix_local = M[m['group']]

# ---- helpers for the stand-in field parts ----
def box(parent, material, size, centre, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1); ob = bpy.context.active_object
    ob.parent = parent; ob.matrix_local = Matrix.Translation(centre) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1))
    ob.data.materials.append(mat(material))
    bev = ob.modifiers.new('bevel', 'BEVEL'); bev.width = min(0.12, 0.2 * min(size)) * IN; bev.segments = 2
    return ob


def tube(parent, material, a, b, radius, caps=True):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=radius, depth=d.length, end_fill_type='NGON' if caps else 'NOTHING'); ob = bpy.context.active_object
    ob.parent = parent; ob.matrix_local = Matrix.Translation((a + b) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    ob.data.materials.append(mat(material))
    for poly in ob.data.polygons: poly.use_smooth = len(poly.vertices) == 4
    return ob


def ball(parent, material, centre, radius):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=radius); ob = bpy.context.active_object
    ob.parent = parent; ob.matrix_local = Matrix.Translation(centre); ob.data.materials.append(mat(material))
    for poly in ob.data.polygons: poly.use_smooth = True
    return ob


def coral(parent, matrix):
    """A coral: 4.5 in PVC pipe, 11.875 in long, lying along local X."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=2.25, depth=11.875, end_fill_type='NOTHING'); ob = bpy.context.active_object
    ob.parent = parent; ob.matrix_local = matrix @ Matrix.Rotation(math.pi / 2, 4, 'Y'); ob.data.materials.append(mat('pvc_white'))
    sol = ob.modifiers.new('wall', 'SOLIDIFY'); sol.thickness = 0.25; sol.offset = -1
    for poly in ob.data.polygons: poly.use_smooth = True
    return ob


def wrist_point(a, b, y=0.0):
    """A point given along the wrist (a) and above it when level (b), in robot coordinates for this pose."""
    stow = Vector((PIV_W.x + b, y, PIV_W.z - a, 1))
    return (M['wrist'] @ stow).to_3d()


def wrist_axis():
    return (wrist_point(1, 0) - wrist_point(0, 0)).normalized()


def april_tag(parent, centre, facing_x):
    """A tag panel on a wall, facing along -X (facing_x = -1) or +X."""
    box(parent, 'white_paint', (0.25, 10.5, 10.5), centre)
    cells = ['011010', '100110', '010011', '110100', '001101', '101010']
    x = centre[0] + facing_x * 0.14
    box(parent, 'plastic_black', (0.05, 8.125, 8.125), (x, centre[1], centre[2]))
    s = 8.125 / 8
    for r, row in enumerate(cells):
        for k, v in enumerate(row):
            if v == '1': box(parent, 'white_paint', (0.05, s, s), (x + facing_x * 0.03, centre[1] + (k - 2.5) * s * -facing_x, centre[2] + (2.5 - r) * s))


field = bpy.data.objects.new('FIELD', None); scene.collection.objects.link(field); field.parent = root


def reef(algae_low=False, scored=True):
    XF = 17.25; XM = XF + 12.84
    for size, centre in (((0.5, 37.8, 17.88), (XF + 0.25, 0, 8.94)), ((16, 37.8, 0.5), (XF + 8.5, 0, 0.6)), ((0.25, 37.8, 10), (XF + 9.6, 0, 17.9)),
                         ((7, 37.8, 0.25), (XF + 13.1, 0, 22.8)), ((9.2, 37.8, 11.6), (XF + 5.1, 0, 6.4)), ((7, 37.8, 21.9), (XF + 13.1, 0, 11.55))):
        box(field, 'hdpe_black', size, centre)
    box(field, 'hdpe_black', (9.6, 37.8, 0.25), (XF + 5.0, 0, 14.6), Matrix.Rotation(0.34, 4, 'Y'))
    april_tag(field, (XF - 0.14, 0, 12.13), -1)
    for y in (6.47, -6.47):
        tube(field, 'reef_violet', (XM, y, 0.63), (XM, y, 53.8), 0.83)
        tube(field, 'reef_violet', (XM, y, 23.7), (XF + 1.61, y, 31.72), 0.83)
        tube(field, 'reef_violet', (XM, y, 39.55), (XF + 1.61, y, 47.59), 0.83)
        tube(field, 'reef_violet', (XM, y, 53.8), (XF + 1.18, y, 61.96), 0.83)
        tube(field, 'reef_violet', (XF + 1.18, y, 61.96), (XF + 1.18, y, 71.87), 0.83)
        ball(field, 'reef_violet', (XM, y, 53.8), 0.83); ball(field, 'reef_violet', (XF + 1.18, y, 61.96), 0.83)
    if algae_low: ball(field, 'algae_ball', (XF + 6.65, 0, 35.0), 8.125)
    if scored: coral(field, Matrix.Translation((XF + 1.18, 6.47, 66.4)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))


def station():
    XS = -17.5
    box(field, 'diamond_plate', (0.5, 76, 37.5), (XS, 0, 18.75))
    box(field, 'field_wall', (0.3, 76, 31), (XS, 0, 60))
    slope = Matrix.Rotation(55 * D2R, 4, 'Y')
    box(field, 'hdpe_black', (16.5, 76, 0.5), (XS - 4.73, 0, 44.26), slope)
    april_tag(field, (XS + 0.35, 0, 58.5), 1)
    coral(field, Matrix.Translation((XS - 4.6, -4, 48.6)) @ slope)


def net():
    XN = 18.5
    tube(field, 'zinc', (XN, -40, 88.5), (XN, 40, 88.5), 0.6); tube(field, 'zinc', (XN + 48, -40, 88.5), (XN + 48, 40, 88.5), 0.6)
    box(field, 'alu', (12, 80, 12), (XN + 24, 0, 68))
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=14, y_subdivisions=2, size=1); n = bpy.context.active_object
    for v in n.data.vertices:
        px = v.co.x * 2; v.co.z = -12.5 * (1 - px * px)
    n.parent = field; n.matrix_local = Matrix.Translation((XN + 24, 0, 88.5)) @ Matrix.Diagonal((48, 80, 1, 1)); n.data.materials.append(mat('net'))
    for poly in n.data.polygons: poly.use_smooth = True


def cage(parent, matrix):
    """A deep cage standing upright with its bottom at local Z = 0: four pipes, two end plates, an eye bolt on top."""
    g = bpy.data.objects.new('CAGE', None); scene.collection.objects.link(g); g.parent = parent; g.matrix_local = matrix
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)): tube(g, 'cage_blue', (sx * 3.03, sy * 3.03, 0), (sx * 3.03, sy * 3.03, 24), 0.66)
    box(g, 'cage_blue', (6.75, 6.75, 0.14), (0, 0, 0.07)); box(g, 'cage_blue', (6.75, 6.75, 0.14), (0, 0, 23.93))
    tube(g, 'zinc', (0, 0, 24), (0, 0, 25.6), 0.3)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.16); ring = bpy.context.active_object
    ring.parent = g; ring.matrix_local = Matrix.Translation((0, 0, 26.1)) @ Matrix.Rotation(math.pi / 2, 4, 'X'); ring.data.materials.append(mat('zinc'))
    return g


# ---- game pieces the robot is holding ----
if 'coral' in P:
    ax = wrist_axis(); centre = wrist_point(P['coral'], 0)
    coral(robot, Matrix.Translation(centre) @ ax.to_track_quat('X', 'Y').to_matrix().to_4x4())
if P.get('algae'):
    # touching both claw rollers and the backstop: see tools/render/README.md
    ball(robot, 'algae_ball', wrist_point(14.15, -12.30), 8.125)

# ---- the scene around the robot ----
if pose == 'l4':
    # the robot lines up on one branch, 6.47 in to one side of the tag: slide the reef so that branch is dead ahead
    reef(algae_low=True); field.location = (0, 6.47, 0)
elif pose == 'algae': reef(scored=False)
elif pose == 'station':
    station()
    # a coral on its way down the tray, which slopes 30.5 degrees down toward the front
    s = 30.5 * D2R; on_tray = Vector((-7.0, 0, 26.84 + 6.0 * math.tan(s))) + 2.35 * Vector((math.sin(s), 0, math.cos(s)))
    coral(robot, Matrix.Translation(on_tray) @ Matrix.Rotation(s, 4, 'Y'))
elif pose == 'net': net()
elif pose == 'climb':
    # With the fork level the cage hangs upright 7.5 in behind the pivot, its bottom 3.1 in off the carpet.
    # Winding the fork to psi turns the cage with it, about the pivot.
    hanging = Matrix.Translation((PIV_F.x - 7.5, 0, 3.1))
    c_obj = cage(robot, about(PIV_F, Matrix.Rotation(P['psi'] * D2R, 4, 'Y')) @ hanging)
    # the robot hangs 2.5 degrees nose up with its wheels 3.9 in off the carpet (the climber drawing's estimate)
    robot.matrix_local = Matrix.Translation((0, 0, 3.9)) @ Matrix.Rotation(-2.5 * D2R, 4, 'Y')
    bpy.context.view_layer.update()
    eye = (robot.matrix_local @ c_obj.matrix_local @ Vector((0, 0, 26.6, 1))).to_3d()
    tube(field, 'zinc', eye, (eye.x, eye.y, 62), 0.28)
    box(field, 'alu', (12, 70, 12), (eye.x, eye.y, 68))

# team number on the bumpers
font_obs = []
for loc, rz in (((17.3, 0, 4.5), 90), ((-17.3, 0, 4.5), -90), ((0, 17.3, 4.5), 180), ((0, -17.3, 4.5), 0)):
    cu = bpy.data.curves.new('num', 'FONT'); cu.body = '4206'; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = 3.6; cu.extrude = 0.03; cu.shear = 0.25
    t = bpy.data.objects.new('num', cu); scene.collection.objects.link(t); t.parent = robot
    t.matrix_local = Matrix.Translation(loc) @ Matrix.Rotation(rz * D2R, 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X')
    cu.materials.append(mat('white_paint'))

# carpet
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); floor = bpy.context.active_object
fm = bpy.data.materials.new('carpet'); fm.use_nodes = True
fb = next(n for n in fm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
setin(fb, 'Base Color', lin(0x4a5058)); setin(fb, 'Roughness', 0.95); setin(fb, 'Sheen Weight', 0.1)
add_bump(fm, fb, 900, 0.7, detail=6.0, distance=0.002); floor.data.materials.append(fm)

# ---- lights, world, camera ----
def at(p): return Vector(p) * IN


def area(name, loc, target, size, power, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'SQUARE'; ld.size = size; ld.energy = power; ld.color = color
    lo = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo); lo.location = at(loc)
    lo.rotation_euler = (at(target) - lo.location).to_track_quat('-Z', 'Y').to_euler()


cam = CAMS[pose]; cx, cy, cz = cam['pos']; tx, ty, tz = cam['target']
area('key', (tx + 0.35 * (cx - tx) + 60, ty + 0.35 * (cy - ty) - 40, 190), cam['target'], 2.6, 1500, (1.0, 0.97, 0.93))
area('fill', (cx * 0.9 - 40, cy * 0.9 + 30, 70), cam['target'], 2.0, 300, (0.88, 0.93, 1.0))
area('rim', (tx - (cx - tx) * 0.8, ty - (cy - ty) * 0.8, 130), (tx, ty, tz + 10), 1.6, 900, (0.92, 0.96, 1.0))

world = bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
wn = world.node_tree; wn.nodes.clear()
outn = wn.nodes.new('ShaderNodeOutputWorld'); bg_light = wn.nodes.new('ShaderNodeBackground'); bg_cam = wn.nodes.new('ShaderNodeBackground')
bg_cam.inputs['Color'].default_value = (0.012, 0.016, 0.022, 1)
mix = wn.nodes.new('ShaderNodeMixShader'); lp = wn.nodes.new('ShaderNodeLightPath')
exr = glob.glob(os.path.dirname(bpy.__file__) + '/**/studiolights/world/*.exr', recursive=True)
pick = next((e for e in exr if 'interior' in e), None) or next((e for e in exr if 'studio' in e), None) or (exr[0] if exr else None)
if pick:
    env = wn.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(pick)
    wn.links.new(env.outputs['Color'], bg_light.inputs['Color']); bg_light.inputs['Strength'].default_value = 0.4
else:
    bg_light.inputs['Color'].default_value = (0.5, 0.55, 0.62, 1); bg_light.inputs['Strength'].default_value = 0.35
wn.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac']); wn.links.new(bg_light.outputs['Background'], mix.inputs[1])
wn.links.new(bg_cam.outputs['Background'], mix.inputs[2]); wn.links.new(mix.outputs['Shader'], outn.inputs['Surface'])

cd = bpy.data.cameras.new('cam'); cd.lens = cam['lens']; cd.sensor_width = 36
co = bpy.data.objects.new('cam', cd); scene.collection.objects.link(co); co.location = at(cam['pos'])
d = at(cam['target']) - co.location; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cd.dof.use_dof = True; cd.dof.focus_distance = d.length; cd.dof.aperture_fstop = 8
scene.camera = co

scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = SPP
scene.cycles.use_adaptive_sampling = True; scene.cycles.adaptive_threshold = 0.03; scene.cycles.use_denoising = True
try: scene.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception as e: print('denoiser', e)
scene.cycles.max_bounces = 8; scene.cycles.transmission_bounces = 8; scene.cycles.glossy_bounces = 4
scene.render.resolution_x = W; scene.render.resolution_y = H; scene.render.resolution_percentage = 100
try: scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception as e: print('view', e)
scene.view_settings.exposure = -0.7
scene.render.image_settings.file_format = 'JPEG'; scene.render.image_settings.quality = 92
scene.render.filepath = os.path.abspath(out)
bpy.ops.render.render(write_still=True)
print('DONE', out)
