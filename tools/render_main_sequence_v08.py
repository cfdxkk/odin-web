"""Render actual JS rig poses against the editable v0.8 Blender model.

Run after exporting public/models/odin.glb and running review_main_sequence_v08.mjs:
  blender -b assets/blender/odin_articulated_v0.8.0.blend \
    --python tools/render_main_sequence_v08.py

This script changes the in-memory scene for each still and never saves the Blend.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BLEND = (ROOT / 'assets/blender/odin_articulated_v0.8.0.blend').resolve()
POSES_PATH = ROOT / 'work/v08-review/poses.json'
OUT_DIR = ROOT / 'docs/review/v0.8/frames'
STAGES = [0, .05, .10, .16, .22, .30, .34, .45, .60, .75, .90, 1]

if Path(bpy.data.filepath).resolve() != EXPECTED_BLEND:
    raise RuntimeError(f'Open the v0.8 editable source first: {EXPECTED_BLEND}')
if not POSES_PATH.is_file():
    raise RuntimeError(f'Run node tools/review_main_sequence_v08.mjs first: {POSES_PATH}')
review = json.loads(POSES_PATH.read_text(encoding='utf8'))
if review.get('assetVersion') != '0.8.0':
    raise RuntimeError(f'Pose asset version is {review.get("assetVersion")}; expected 0.8.0')
poses = review.get('poses', [])
if len(poses) != len(STAGES) or any(abs(p['deployment'] - d) > 1e-8 for p, d in zip(poses, STAGES)):
    raise RuntimeError('Pose list does not match the required 12 review stages')
missing = sorted({j['name'] for pose in poses for j in pose['joints']} - set(bpy.data.objects.keys()))
if missing:
    raise RuntimeError(f'Editable Blend is missing GLB static joints: {missing[:15]}')
OUT_DIR.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1440
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_shadows = True
scene.display.shading.background_type = 'WORLD'
scene.world.color = (.045, .055, .07)

camera_data = bpy.data.cameras.new('V08_MainReviewCamera')
camera = bpy.data.objects.new('V08_MainReviewCamera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.clip_start = .01
camera_data.clip_end = 100
# Keep the aft hinge and forward tip visible throughout deployment. This is a
# wider version of render_rig_review.py's main-rear direction, held motionless.
center = Vector((0, 138, 50)) * .01
camera.location = center + Vector((1, 1.25, 1.25)) * 4
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.ortho_scale = 2.50

# Blender +Y/+Z => Three -Z/+Y, identical to render_rig_review.py.
basis = Quaternion((1, 0, 0), -math.pi / 2)


def apply_pose(pose):
    for joint in pose['joints']:
        obj = bpy.data.objects[joint['name']]
        x, y, z = joint['position']
        obj.location = (x, -z, y)
        q = joint['quaternion']
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = basis.inverted() @ Quaternion((q[3], q[0], q[1], q[2])) @ basis
    bpy.context.view_layer.update()


def belongs_to_dorsal_main(obj):
    while obj:
        if obj.name.startswith(('Main_Dorsal_', 'Hatch_Dorsal_')):
            return True
        obj = obj.parent
    return False


# Compute one common crop over every review pose. The camera never moves
# between frames, and all moving source parts remain in view even when the
# outer tubes extend fully or the forward cover shifts toward the bow.
tracked = [obj for obj in scene.objects if obj.type == 'MESH' and belongs_to_dorsal_main(obj)]
if not tracked:
    raise RuntimeError('No dorsal main-battery meshes found in the v0.8 Blender source')
bounds = [float('inf'), float('inf'), -float('inf'), -float('inf')]
bpy.context.view_layer.update()
camera_inverse = camera.matrix_world.inverted()
for pose in poses:
    apply_pose(pose)
    for obj in tracked:
        for corner in obj.bound_box:
            point = camera_inverse @ (obj.matrix_world @ Vector(corner))
            bounds[0] = min(bounds[0], point.x)
            bounds[1] = min(bounds[1], point.y)
            bounds[2] = max(bounds[2], point.x)
            bounds[3] = max(bounds[3], point.y)
mid_x, mid_y = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
camera.location += camera.rotation_euler.to_quaternion() @ Vector((mid_x, mid_y, 0))
span_x, span_y = bounds[2] - bounds[0], bounds[3] - bounds[1]
camera_data.ortho_scale = max(1.55, 1.14 * span_y * 1.50, 1.14 * span_x)
print(f'Fixed dorsal-main camera: {len(tracked)} meshes, scale {camera_data.ortho_scale:.3f}', flush=True)

for pose in poses:
    apply_pose(pose)
    scene.render.filepath = str(OUT_DIR / pose['file'])
    bpy.ops.render.render(write_still=True)
    print(f"REVIEW_FRAME {pose['index']:02d}/12 d={pose['deployment']:.2f} {scene.render.filepath}", flush=True)
print('12-frame main-battery review render complete; Blender source not saved.', flush=True)
