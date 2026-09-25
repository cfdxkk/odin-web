"""Verify and render systems outside the revised main battery.

blender -b --python-exit-code 1 --python tools/check_unrelated_systems.py -- 0.8.1 0.8.2
"""
import array
import argparse
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Quaternion, Vector

root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('old');parser.add_argument('new')
parser.add_argument('--allow-fixed-main-bay',action='store_true',help='Permit the explicitly revised dorsal hull receiver, while checking all other objects exactly')
args=parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
old,new=args.old,args.new
baseline = root / f'assets/blender/odin_articulated_v{old}.blend'
candidate = root / f'assets/blender/odin_articulated_v{new}.blend'
output = root / f'work/v{new.replace(".", "")}-review'
output.mkdir(parents=True, exist_ok=True)

def digest(collection, field, kind, count):
    values = array.array(kind, [0]) * count
    collection.foreach_get(field, values)
    return hashlib.sha256(values.tobytes()).hexdigest()

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.view_layer.update()
    result = {}
    for obj in bpy.data.objects:
        parent = obj
        main = False
        while parent:
            main |= parent.name.startswith(('Main_', 'Hatch_'))
            parent = parent.parent
        if main:
            continue
        row = {'type': obj.type, 'parent': obj.parent.name if obj.parent else None,
               'matrix': [x for row in obj.matrix_world for x in row],
               'joint': bool(obj.get('staticJoint')), 'system': obj.get('system')}
        if obj.type == 'MESH':
            mesh = obj.data
            row['mesh'] = {
                'vertices': digest(mesh.vertices, 'co', 'f', len(mesh.vertices)*3),
                'loops': digest(mesh.loops, 'vertex_index', 'i', len(mesh.loops)),
                'faceStarts': digest(mesh.polygons, 'loop_start', 'i', len(mesh.polygons)),
                'faceSizes': digest(mesh.polygons, 'loop_total', 'i', len(mesh.polygons)),
                'faceMaterials': digest(mesh.polygons, 'material_index', 'i', len(mesh.polygons)),
                'materials': [mat.name if mat else None for mat in mesh.materials],
                'uv': {uv.name: digest(uv.data, 'uv', 'f', len(uv.data)*2) for uv in mesh.uv_layers}}
        result[obj.name] = row
    return result

a, b = snapshot(baseline), snapshot(candidate)
removed, added = sorted(a.keys() - b.keys()), sorted(b.keys() - a.keys())
changed = [name for name in a.keys() & b.keys() if a[name] != b[name]]
allowed={'holo.001','MainBay_Dorsal_Port_FixedReceiver','MainBay_Dorsal_Starboard_FixedReceiver'} if args.allow_fixed_main_bay else set()
permitted=sorted(set(removed+added+changed)&allowed)
removed=[n for n in removed if n not in allowed];added=[n for n in added if n not in allowed];changed=[n for n in changed if n not in allowed]
report = {'baseline': baseline.name, 'candidate': candidate.name,
          'candidateSha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
          'scope': 'All objects outside Main_* and Hatch_* ancestry; exact effective world transform and mesh/UV/material equality',
          'objectsCompared': len(a.keys() & b.keys()),
          'jointSystems': sorted({row['system'] for row in b.values() if row['system']}),
          'removed': removed, 'added': added, 'changed': changed,
          'explicitlyRevisedFixedMainBayObjects':permitted,
          'passed': not (removed or added or changed)}
(output/'unchanged-systems.json').write_text(json.dumps(report, indent=2), encoding='utf8')
if not report['passed']:
    raise RuntimeError(f'Unrelated systems changed: {removed}, {added}, {changed}')

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 960
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world.color = (.045, .055, .07)
camera = bpy.data.objects.new('OtherSystemsReview', bpy.data.cameras.new('OtherSystemsReview'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.clip_end = 100
basis = Quaternion((1, 0, 0), -math.pi/2)
poses = json.loads((root/'work/rig-review/poses.json').read_text(encoding='utf8'))
views = [('bridge-quads', (19,-38,111), (1,1,.5), 1.6, 1),
         ('defense', (35,-48,56), (1,.35,.8), 1.2, 1),
         ('single', (0,240,44), (1,1,.6), .85, 1),
         ('stern-door', (0,-174,-20), (.5,-1,-.65), 2.1, 0)]
for name, target, direction, extent, d in views:
    pose = min(poses, key=lambda p: abs(p['deployment']-d))
    for joint in pose['joints']:
        obj = bpy.data.objects[joint['name']]
        x,y,z = joint['position']; obj.location = (x,-z,y)
        q = joint['quaternion']; obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = basis.inverted() @ Quaternion((q[3],q[0],q[1],q[2])) @ basis
    bpy.context.view_layer.update()
    aim = Vector(target)*.01
    camera.location = aim+Vector(direction)*4
    camera.rotation_euler = (aim-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = extent
    scene.render.filepath = str(output/f'unchanged-{name}.png')
    bpy.ops.render.render(write_still=True)
print('Unrelated systems preserved; four runtime-pose images rendered', flush=True)
