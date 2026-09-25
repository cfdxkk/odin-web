"""Render the actual JS poses without saving or animating the editable Blend.

1. node tools/review_animation_poses.mjs --version 0.8.1
2. blender -b assets/blender/odin_articulated_v0.8.1.blend --python-exit-code 1 \
     --python tools/render_animation_preview.py -- --version 0.8.1
3. python tools/encode_animation_preview.py --version 0.8.1 --ffmpeg /path/to/ffmpeg

Large intermediate PNGs stay in ignored work/preview-vVERSION. The encoder puts
the small playable MP4 and its provenance in docs/review/vVERSION by default.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', required=True)
parser.add_argument('--work-dir')
parser.add_argument('--width', type=int, default=768)
parser.add_argument('--height', type=int, default=512)
parser.add_argument('--view', choices=['legacy', 'official'], default='legacy')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
if min(args.width, args.height) < 64 or args.width % 2 or args.height % 2:
    parser.error('Width and height must be positive even dimensions of at least 64 pixels')
work = (ROOT / (args.work_dir or f'work/preview-v{args.version}')).resolve()
poses_path = work / 'poses.json'
review = json.loads(poses_path.read_text(encoding='utf8'))
expected_blend = (ROOT / f"assets/blender/odin_articulated_v{review['assetVersion']}.blend").resolve()
if Path(bpy.data.filepath).resolve() != expected_blend:
    raise RuntimeError(f'Open the matching editable source first: {expected_blend}')
if review.get('reviewVersion', review['assetVersion']) != args.version:
    raise RuntimeError('Pose review version differs from requested version')
for key, path in [('glbSha256', ROOT / 'public/models/odin.glb'),
                  ('rigSha256', ROOT / 'app/lib/odin-rig.ts'), ('blendSha256', expected_blend)]:
    if review.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
        raise RuntimeError(f'{key} differs from captured poses; regenerate poses before rendering')
poses = review['poses']
if len(poses) != 101 or any(abs(p['deployment'] - i / 100) > 1e-8 for i, p in enumerate(poses)):
    raise RuntimeError('Expected 101 uniformly sampled runtime deployment poses')
missing = sorted({j['name'] for pose in poses for j in pose['joints']} - set(bpy.data.objects.keys()))
if missing:
    raise RuntimeError(f'Editable Blend is missing GLB static joints: {missing[:15]}')
out_dir = work / 'frames'
out_dir.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = args.width
scene.render.resolution_y = args.height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_shadows = True
scene.display.shading.background_type = 'WORLD'
if not scene.world:
    scene.world = bpy.data.worlds.new('PreviewWorld')
scene.world.color = (.045, .055, .07)
camera_data = bpy.data.cameras.new('AnimationReviewCamera')
camera = bpy.data.objects.new('AnimationReviewCamera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.clip_start = .01
camera_data.clip_end = 100
center = Vector((0, 138, 50)) * .01
camera.location = center + Vector((1, 1.25, 1.25)) * 4
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.ortho_scale = 2.50
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


# One common crop over every pose, using the same camera direction as v0.8.
# No tracking/panning that could conceal seam or collision problems.
tracked = [obj for obj in scene.objects if obj.type == 'MESH' and belongs_to_dorsal_main(obj)]
if not tracked:
    raise RuntimeError('No dorsal main-battery meshes found')
bounds = [float('inf'), float('inf'), -float('inf'), -float('inf')]
bpy.context.view_layer.update()
camera_inverse = camera.matrix_world.inverted()
for pose in poses:
    apply_pose(pose)
    for obj in tracked:
        for corner in obj.bound_box:
            point = camera_inverse @ (obj.matrix_world @ Vector(corner))
            bounds[0], bounds[1] = min(bounds[0], point.x), min(bounds[1], point.y)
            bounds[2], bounds[3] = max(bounds[2], point.x), max(bounds[3], point.y)
mid_x, mid_y = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
camera.location += camera.rotation_euler.to_quaternion() @ Vector((mid_x, mid_y, 0))
span_x, span_y = bounds[2] - bounds[0], bounds[3] - bounds[1]
camera_data.ortho_scale = max(1.55, 1.14 * span_y * args.width / args.height, 1.14 * span_x)
if args.view == 'official':
    center = Vector((0, 138, 47)) * .01
    camera.location = center + Vector((-1, 1.25, 1.0)) * 4
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = 1.75
print(f'Fixed dorsal-main camera: {len(tracked)} meshes, scale {camera_data.ortho_scale:.3f}', flush=True)

for pose in poses:
    apply_pose(pose)
    scene.render.filepath = str(out_dir / pose['file'])
    bpy.ops.render.render(write_still=True)
    print(f"PREVIEW_FRAME {pose['index'] + 1:03d}/{len(poses)} d={pose['deployment']:.2f}", flush=True)
report = {key: value for key, value in review.items() if key != 'poses'}
report.update({'poseSha256': hashlib.sha256(poses_path.read_bytes()).hexdigest(),
               'view': args.view,
               'frameCount': len(poses), 'width': args.width, 'height': args.height,
               'cameraLocation': list(camera.location), 'cameraRotation': list(camera.rotation_euler),
               'cameraOrthoScale': camera_data.ortho_scale,
               'frames': [{'file': p['file'], 'sha256': hashlib.sha256((out_dir / p['file']).read_bytes()).hexdigest()}
                          for p in poses]})
(work / 'render-manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('Animation frames complete. Editable Blender source was not saved.', flush=True)
