"""Record independent Blender reference samples from the untouched odin.blend.

Run with Blender opening D:/星际公民相关/Odin/Odin 建模/odin.blend. This reads
the original animation only; the web asset still exports zero animation clips.
"""

import bpy
import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
gun = bpy.data.objects['odin.002']
samples = []
for frame in (30, 37, 43, 50, 56):
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
destination = root / 'tests/fixtures/bow-source-motion-v01114.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(samples, indent=2), encoding='utf-8')
print('BOW_SOURCE_SAMPLES', destination, flush=True)
