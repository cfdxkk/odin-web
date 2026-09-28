"""Check actual aft twin mesh intersections with their closed hull gates.

Run in Blender with odin_articulated_v0.11.10.blend. A deliberately unsunk
carriage must intersect each gate, proving the mesh test is sensitive; the
authored four-unit sink must clear every gun and shared rail.
"""

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


asset = bpy.data.objects['Odin_Asset']
assert str(asset['version']) == '0.11.10'


def mesh_descendants(parent):
    return [obj for obj in parent.children_recursive if obj.type == 'MESH']


def bvh(obj):
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons, epsilon=0.0001)


def intersections(objects, gate):
    gate_tree = bvh(gate)
    return sum(len(bvh(obj).overlap(gate_tree)) for obj in objects)


for number in range(5, 9):
    carriage = bpy.data.objects[f'Defense_{number:02}_Carriage']
    gate = bpy.data.objects[f'Defense_{number:02}_NotchGate_Skin']
    side = 'Starboard' if carriage['side'] > 0 else 'Port'
    rail = bpy.data.objects[f'DefenseRail_Aft_{side}']
    gun_meshes = mesh_descendants(carriage)
    rail_meshes = mesh_descendants(rail)
    assert gun_meshes and rail_meshes

    carriage_rest = carriage.location.copy()
    rail_rest = rail.location.copy()
    sign = float(carriage['side'])
    inward = float(carriage['finalStowInward'])
    drop = float(carriage['finalStowDrop'])
    assert inward == 2.3 and drop == 4.0
    assert float(rail['finalStowInward']) == inward
    assert float(rail['finalStowDrop']) == drop

    def seat(sink):
        delta = Vector((-sign * inward, 0, -sink))
        carriage.location = carriage_rest + delta
        rail.location = rail_rest + delta
        bpy.context.view_layer.update()

    seat(0)
    assert intersections(gun_meshes, gate) > 0, f'{number}: unsunk control must hit gate'
    seat(drop)
    assert intersections(gun_meshes, gate) == 0, f'{number}: gun intersects closed gate'
    assert intersections(rail_meshes, gate) == 0, f'{number}: rail intersects closed gate'
    carriage.location = carriage_rest
    rail.location = rail_rest
    bpy.context.view_layer.update()
    print(f'AFT_GATE_CLEAR {number}: original {drop:g}-unit sink, no mesh overlap', flush=True)
