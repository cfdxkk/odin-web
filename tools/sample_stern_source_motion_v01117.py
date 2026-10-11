"""Sample odin.026's untouched frame-11–37 action in the original odin.blend."""

import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
gun = bpy.data.objects['odin.026']
samples = []
for frame in (11, 14, 20, 24, 30, 37):
    bpy.context.scene.frame_set(frame)
    matrix = gun.matrix_world.copy()
    samples.append({
        'frame': frame,
        'origin': list(matrix.translation),
        'rotationWXYZ': list(matrix.to_quaternion()),
        'vertices': {
            str(index): list(matrix @ gun.data.vertices[index].co)
            for index in (0, 100)
        },
    })
destination = root / 'tests/fixtures/stern-source-motion-v01117.json'
destination.write_text(json.dumps(samples, indent=2), encoding='utf-8')
print('STERN_SOURCE_SAMPLES', destination, flush=True)
