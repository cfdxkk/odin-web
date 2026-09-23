"""Preserve engine geometry while restoring local origins for runtime exhaust anchors."""
import bpy
from mathutils import Vector, Matrix
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.name.startswith('EngineCore_'):
        continue
    # The earlier mesh consolidation baked vertices into asset space, leaving
    # all 13 origins at zero. A bounding-box center recovers each physical nozzle.
    center = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
    world = obj.matrix_world.copy()
    obj.data.transform(Matrix.Translation(-center))
    obj.matrix_world = world @ Matrix.Translation(center)
    obj['exhaustAnchor'] = True
    print(obj.name, tuple(round(v, 4) for v in obj.matrix_world.translation))
bpy.context.view_layer.update()
bpy.data.objects['Odin_Asset']['version'] = '0.2.1'
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'assets/blender/odin_articulated_v0.2.1.blend'), compress=True)
