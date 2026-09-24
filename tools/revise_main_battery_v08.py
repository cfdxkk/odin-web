"""v0.8 static geometry for review only: fitted cap, hinged aft leaves, three bores.

Load v0.7 first. Preserve the original source and all fixed hull topology.
Animation remains exclusively in the Nuxt rig; this saves no actions.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
# Reuse the measured-curve and shell helpers, never the v0.7 rebuilding entrypoint.
helpers = root / 'tools/revise_main_battery_v07.py'
exec(compile(helpers.read_text(encoding='utf8').split('bay_material=')[0], str(helpers), 'exec'))
center_helper = root / 'tools/add_center_tubes_v08.py'
exec(compile(center_helper.read_text(encoding='utf8'), str(center_helper), 'exec'))

red = bpy.data.materials.new('Odin_Turret_Interior_DeepRed')
red.diffuse_color = (.19, .012, .022, 1)
red.use_nodes = True
bsdf = red.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = red.diffuse_color
bsdf.inputs['Metallic'].default_value = .32
bsdf.inputs['Roughness'].default_value = .48

def inside_red(obj, direction, threshold=-.12):
    materials = list(obj.data.materials)
    if red not in materials:
        obj.data.materials.append(red)
        materials.append(red)
    normal_matrix = (asset.matrix_world.inverted() @ obj.matrix_world).to_3x3()
    for face in obj.data.polygons:
        if direction * (normal_matrix @ face.normal).normalized().z < threshold:
            face.material_index = materials.index(red)

for bank, config in reference.items():
    direction = config['direction']; center = config['center']
    hull = bpy.data.objects[config['hull']]
    for side, sign in [('Port', -1), ('Starboard', 1)]:
        main = bpy.data.objects[f'Hatch_{bank}_{side}']
        depth = 6.4 if bank=='Dorsal' else 3.0
        main['clearanceLift'] = [0, 0, direction*(.8 if bank=='Dorsal' else 1.6)]
        main['guideExit'] = [sign * 9.6, 0, -direction * (depth-.6)]
        main['guidePocket'] = [0, 0, -direction * .6]
        main['slideVector'] = [sign * 9.6, 0, -direction * depth]
        main['sourceReference'] = 'v0.8 user endpoint: exposed beside bay, short outboard/downward guide'

        aft = bpy.data.objects[f'Hatch_{bank}_Aft_{side}']
        a, b = [Vector(p) for p in config[side]['aftLip']]
        # The rotation line follows the original inclined fixed-hull inner lip.
        # Rebase only the empty, retaining every skin vertex in its closed place.
        children = [(obj, obj.matrix_world.copy()) for obj in aft.children]
        aft.location = (a + b) * .5
        bpy.context.view_layer.update()
        for obj, matrix in children: obj.matrix_world = matrix
        aft['hingeAxis'] = list((b - a).normalized())
        aft['hingeEdge'] = [list(a), list(b)]
        aft['openingAngleDegrees'] = sign * direction * 130
        aft['slideVector'] = [0, 0, 0]
        for key in ['guideExit', 'guidePocket']:
            if key in aft: del aft[key]
        aft['construction'] = 'gap-filler-hinged-outward-130-degrees'

    nose = bpy.data.objects[f'Hatch_{bank}_Nose']
    for child in list(nose.children): bpy.data.objects.remove(child, do_unlink=True)
    start, end = config['noseStart'] + .12, config['noseEnd']
    # The sampled original perimeter retains every tooth/step at the foredeck.
    ys = sorted({start, end} | {p[1] for side in ['Port', 'Starboard'] for p in config[side]['lip'] if start < p[1] < end})
    dense = []
    for a, b in zip(ys, ys[1:]):
        count = max(1, math.ceil((b-a)/.35))
        dense.extend(a+(b-a)*i/count for i in range(count))
    ys = dense + [end]
    points = []
    for y in ys:
        t = (y-start)/(end-start)
        top = (48.98*(1-t)+48.25*t) if bank=='Dorsal' else (-55.68*(1-t)-53.50*t)
        edges = {}
        for side, sign in [('Port', -1), ('Starboard', 1)]:
            p = mix_curve(config[side]['lip'], y)
            edges[side] = (p.x-sign*(.10 if bank=='Dorsal' else .30), p.z+direction*.10)
        ridge = 1.4*(1-t)+1.1*t
        row = [(edges['Port'][0], edges['Port'][1]), (center-ridge, top), (center, top), (center+ridge, top), (edges['Starboard'][0], edges['Starboard'][1])]
        for x, z in row:
            hz = ray_surface(hull, x, y, direction)
            if hz is not None: z = direction*max(direction*z, direction*hz+.24)
            points.append((x, y, z))
    faces = [(r*5+c, r*5+c+1, (r+1)*5+c+1, (r+1)*5+c) for r in range(len(ys)-1) for c in range(4)]
    skin = shell(f'Hatch_{bank}_Nose_Wedge', points, faces, nose, direction, .16)
    clear_fixed_lip(skin, hull, direction)
    nose['closedOutlineXY'] = [[p[0], p[1]] for p in points[::5] + list(reversed(points[4::5]))]
    nose['liftVector'] = [0, 0, direction*(.95 if bank=='Dorsal' else 2.0)]
    nose['construction'] = 'fore-end-cap-with-original-serrated-perimeter'
    nose['sourceReference'] = 'Original fixed foredeck serrations, measured on each bank and side'

    bpy.context.view_layer.update()
    for obj in scene.objects:
        if obj.type=='MESH' and obj.name.startswith(f'Hatch_{bank}_'):
            inside_red(obj, direction)
    # Paint only inward-facing surfaces of the existing turret armor.
    names = ['odin.005','odin.006','odin.007','odin.008'] if bank=='Dorsal' else ['odin.013','odin.014','odin.015','odin.016']
    for name in names: inside_red(bpy.data.objects[name], direction, -.3)

aft_helper = root / 'tools/fit_aft_hinges_v08.py'
exec(compile(aft_helper.read_text(encoding='utf8'), str(aft_helper), 'exec'))
for bank, config in reference.items():
    for side in ['Port', 'Starboard']:
        aft = bpy.data.objects[f'Hatch_{bank}_Aft_{side}']
        aft['slideVector'] = [0, 0, 0]
        aft['construction'] = 'gap-filler-hinged-outward-130-degrees'
        skin = bpy.data.objects[f'Hatch_{bank}_Aft_{side}_GapFiller']
        bm = bmesh.new(); bm.from_mesh(skin.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(skin.data); bm.free(); skin.data.update()
        for face in skin.data.polygons: face.material_index = 0
        inside_red(skin, config['direction'])

for name, counts in original_hull.items():
    obj = bpy.data.objects[name]
    assert counts == (len(obj.data.vertices), len(obj.data.polygons))
for obj in scene.objects: obj.animation_data_clear()
for action in list(bpy.data.actions): bpy.data.actions.remove(action)
asset['version'] = '0.8.0'
scene.name = 'ODIN v0.8 - main battery review candidate'
bpy.data.orphans_purge(do_recursive=True)
dest = root / 'assets/blender/odin_articulated_v0.8.0.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest), compress=True)
print('SAVED', dest, flush=True)
