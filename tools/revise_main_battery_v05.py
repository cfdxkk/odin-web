"""Rebuild the two main-battery sliding armor plates from the source contour.

Run on odin_articulated_v0.4.0.blend. ``odin.blend`` is never opened for write.
The source coordinates below were measured at frame 0 from objects 立方体 and
立方体.002 in that file. No actions or animation clips are saved in this asset:
Nuxt's odin-rig.ts owns all articulation.
"""
import bpy
import bmesh
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
scene = bpy.context.scene
asset = bpy.data.objects['Odin_Asset']
light = bpy.data.materials['Odin_Paint_Light']

# Rear outside / rear inside / forward outside / forward inside, for each side.
# These are the actual source skin corners, rather than the v0.4 rectangular
# substitute. The source center bridge is divided between the two plates.
SOURCE = {
    'Dorsal': {
        'Port': [(-13.5369, 76.7555, 41.5070), (-2.1583, 76.7555, 54.1070),
                 (-8.6524, 173.4188, 36.0668), (-1.0496, 178.1694, 47.4691)],
        'Starboard': [(13.7367, 76.7555, 41.5070), (2.3581, 76.7555, 54.1070),
                      (8.8522, 173.4188, 36.0668), (1.2494, 178.1694, 47.4691)],
        'center': [(0.0999, 76.7555, 54.1070), (0.0999, 178.1694, 47.4691)],
        'source': '立方体', 'face': 'source face 0-1-3-2 / 4-6-7-5',
    },
    'Ventral': {
        'Port': [(-13.6368, 27.7027, -54.6747), (-2.2582, 28.8009, -67.2268),
                 (-10.4892, 89.4515, -45.7533), (-1.1495, 129.2503, -51.7754)],
        'Starboard': [(13.6368, 27.7027, -54.6747), (2.2582, 28.8009, -67.2268),
                      (10.4892, 89.4515, -45.7533), (1.1495, 129.2503, -51.7754)],
        'center': [(0.0, 28.8009, -67.2268), (0.0, 129.2503, -51.7754)],
        'source': '立方体.002', 'face': 'source face 0-1-3-2 / 4-6-7-5',
    },
}

def mesh(name, verts, faces, parent, material=light, bevel=0.0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.parent = asset
    data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new('Panel edge break', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world
    return obj

def interpolate(a, b, t):
    return Vector(a).lerp(Vector(b), t)

def add_leaf(bank, side, data):
    outer_rear, inner_rear, outer_front, inner_front = map(Vector, data[side])
    center_rear, center_front = map(Vector, data['center'])
    pivot = bpy.data.objects.new(f'Hatch_{bank}_{side}', None)
    scene.collection.objects.link(pivot)
    pivot.parent = asset
    pivot.location = (outer_rear + outer_front) / 2
    pivot['staticJoint'] = True
    pivot['system'] = 'main-hatch'
    sign = -1 if side == 'Port' else 1
    direction = 1 if bank == 'Dorsal' else -1
    # CIG's close-up shows nearly parallel translation: about 3–4 source
    # units outboard and 12–13 into the deck cassette. The source file's
    # shrinking, 90-unit forward slide is only a coarse placeholder action.
    pivot['slideVector'] = [sign * 4.0, 0.0, -direction * 13.0]
    pivot['sourceObject'] = data['source']
    pivot['sourceFace'] = data['face']
    pivot['outsideGuideEdge'] = [list(outer_rear), list(outer_front)]

    # The source wedge has a steep outboard roof and a narrower, nearly flat
    # bridge against the center seam. Each remains a single continuous plate.
    top = [outer_rear, inner_rear, center_rear,
           outer_front, inner_front, center_front]
    thickness = Vector((0, 0, -direction * .38))
    verts = [tuple(p) for p in top] + [tuple(p + thickness) for p in top]
    roof = [(0, 3, 4, 1), (1, 4, 5, 2)]
    bottom = [tuple(i + 6 for i in reversed(face)) for face in roof]
    rim = [(0, 1, 7, 6), (1, 2, 8, 7), (2, 5, 11, 8),
           (5, 4, 10, 11), (4, 3, 9, 10), (3, 0, 6, 9)]
    skin = mesh(f'Hatch_{bank}_{side}_OriginalContour', verts,
                roof + bottom + rim, pivot, bevel=.09)
    skin['continuousLeaf'] = True

    # The official close-up shows closely spaced relief ribs on the near-side
    # exterior. Each rib is shallow detail on the same moving *whole* plate,
    # not an independently opening rectangular door segment.
    for index in range(25 if bank == 'Dorsal' else 17):
        count = 25 if bank == 'Dorsal' else 17
        lo = (index + .12) / count
        hi = (index + .83) / count
        # Keep the short rib bars on the sloping source roof, leaving its
        # narrow center strip and outside hinge line clean.
        def rib_edge(t, fraction):
            outer = interpolate(outer_rear, outer_front, t)
            inner = interpolate(inner_rear, inner_front, t)
            # The source quad is slightly twisted along its 100-unit run.
            # Its triangulated roof can stand ~0.7 above bilinear points;
            # account for that twist so the relief actually clears the skin.
            return outer.lerp(inner, fraction) + Vector((0, 0, direction * .95))
        r = [rib_edge(lo, .10), rib_edge(lo, .91),
             rib_edge(hi, .91), rib_edge(hi, .10)]
        raised = Vector((0, 0, direction * .085))
        rib_verts = [tuple(p) for p in r] + [tuple(p + raised) for p in r]
        mesh(f'Hatch_{bank}_{side}_Relief_{index:02}', rib_verts,
             [(0, 1, 2, 3), (7, 6, 5, 4),
              (0, 4, 5, 1), (1, 5, 6, 2),
              (2, 6, 7, 3), (3, 7, 4, 0)], pivot)
    return pivot

# Delete only v0.4's four artificial banks, preserving every gun, secondary,
# PDC, bridge-armor and stern-door joint in the existing articulated source.
for obj in list(scene.objects):
    if obj.name.startswith('Hatch_'):
        bpy.data.objects.remove(obj, do_unlink=True)

for bank, data in SOURCE.items():
    for side in ('Port', 'Starboard'):
        add_leaf(bank, side, data)

for obj in scene.objects:
    obj.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
asset['version'] = '0.5.0'
scene.name = 'ODIN v0.5 — original-contour twin main bay doors'
bpy.data.orphans_purge(do_recursive=True)
dest = root / 'assets/blender/odin_articulated_v0.5.0.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest), compress=True)
print('SAVED', dest, flush=True)
