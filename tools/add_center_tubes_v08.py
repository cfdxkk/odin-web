"""Separate original centre telescopic tube islands without changing their shape.

Execute after loading the v0.7 editable asset, before saving the v0.8 copy.
This helper never saves a .blend file and never adds animation data. Source
faces, material assignments and UV coordinates move to a static child joint;
the Nuxt rig supplies the simultaneous three-bore telescopic motion.
"""


def add_center_tubes_v08():
    import bpy
    import bmesh
    import json
    import statistics
    from collections import Counter
    from mathutils import Vector

    asset = bpy.data.objects['Odin_Asset']
    asset_inverse = asset.matrix_world.inverted()
    audit = {}

    def connected_islands(obj):
        parents = list(range(len(obj.data.vertices)))

        def find(index):
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        for edge in obj.data.edges:
            a, b = edge.vertices
            parents[find(a)] = find(b)
        result = {}
        for vertex in obj.data.vertices:
            result.setdefault(find(vertex.index), set()).add(vertex.index)
        return list(result.values())

    def face_signatures(mesh):
        """Compare geometry/UV/material faces despite BMesh index renumbering."""
        result = Counter()
        for polygon in mesh.polygons:
            corners = []
            for loop_index in polygon.loop_indices:
                vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
                corners.append((tuple(vertex.co), tuple(
                    tuple(layer.data[loop_index].uv) for layer in mesh.uv_layers)))
            # Deletion preserves winding; canonicalise the starting corner only.
            first = min(range(len(corners)), key=lambda index: corners[index])
            result[(polygon.material_index, tuple(corners[first:] + corners[:first]))] += 1
        return result

    def delete_vertices(mesh, indices):
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in indices], context='VERTS')
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    for bank, source_name, rear_limit in [('Dorsal', 'odin.004', 107),
                                          ('Ventral', 'odin.012', 57)]:
        source = bpy.data.objects[source_name]
        parent = bpy.data.objects[f'Main_{bank}_Barrels']
        name = f'Main_{bank}_Tube_Center'
        if name in bpy.data.objects:
            raise RuntimeError(f'{name} already exists; load the unmodified v0.7 asset')
        bpy.context.view_layer.update()
        source_to_asset = asset_inverse @ source.matrix_world
        source_to_parent = parent.matrix_world.inverted() @ source.matrix_world
        selected = set()
        island_counts = []
        for indices in connected_islands(source):
            points = [source_to_asset @ source.data.vertices[i].co for i in indices]
            # This is the same longitudinal section isolated for the outer
            # tubes in v0.4: main sleeve plus the two original muzzle details.
            if min(p.y for p in points) > rear_limit and max(abs(p.x) for p in points) < 4:
                selected.update(indices)
                island_counts.append(len(indices))
        assert sorted(island_counts) == [384, 384, 16690], (bank, island_counts)

        # The source's centre tube has a slightly different inclination from
        # the outer bores. Long axial edges provide a less biased axis than
        # PCA on the complete tube, whose one-sided fittings skew its mass.
        slopes = []
        for edge in source.data.edges:
            a, b = edge.vertices
            if a not in selected or b not in selected:
                continue
            vector = source_to_parent.to_3x3() @ (source.data.vertices[b].co - source.data.vertices[a].co)
            if vector.y < 0:
                vector = -vector
            if vector.length > 20 and abs(vector.x) < .0001 and vector.y / vector.length > .98:
                slopes.append(vector.z / vector.y)
        assert len(slopes) > 30, (bank, len(slopes))
        bore_axis = Vector((0, 1, statistics.median(slopes))).normalized()

        before_vertices = len(source.data.vertices)
        before_faces = len(source.data.polygons)
        before_signatures = face_signatures(source.data)
        before_materials = list(source.data.materials)
        before_uv_names = [layer.name for layer in source.data.uv_layers]
        world = source.matrix_world.copy()

        tube = source.copy()
        tube.data = source.data.copy()
        tube.name = f'Main_{bank}_TubeMesh_Center'
        tube.data.name = tube.name
        bpy.context.scene.collection.objects.link(tube)
        delete_vertices(tube.data, set(range(before_vertices)) - selected)
        delete_vertices(source.data, selected)

        joint = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(joint)
        joint.parent = parent
        joint.location = (0, 0, 0)
        joint['staticJoint'] = True
        joint['system'] = 'main-telescope'
        joint['boreAxis'] = list(bore_axis)
        joint['stowTravel'] = 16.0
        joint['deployedOffset'] = [0.0, 0.0, 0.0]
        joint['sourceObject'] = source_name
        joint['axisMeasurement'] = 'Median source longitudinal tube edges in Main_*_Barrels local space'
        bpy.context.view_layer.update()
        tube.parent = joint
        tube.matrix_world = world
        tube['sourceObject'] = source_name
        tube['sourceIslandVertexCounts'] = sorted(island_counts)
        tube.animation_data_clear()

        assert len(source.data.vertices) + len(tube.data.vertices) == before_vertices
        assert len(source.data.polygons) + len(tube.data.polygons) == before_faces
        assert face_signatures(source.data) + face_signatures(tube.data) == before_signatures, \
            f'{bank}: source faces, UVs or material assignments changed'
        assert list(tube.data.materials) == before_materials
        assert [layer.name for layer in tube.data.uv_layers] == before_uv_names
        bpy.context.view_layer.update()
        assert max(abs(tube.matrix_world[i][j] - world[i][j]) for i in range(4) for j in range(4)) < 1e-6
        audit[bank] = {
            'sourceObject': source_name,
            'sourceIslands': sorted(island_counts),
            'vertices': len(tube.data.vertices),
            'polygons': len(tube.data.polygons),
            'boreAxis': list(bore_axis),
            'axisEdgesMeasured': len(slopes),
            'stowTravel': joint['stowTravel'],
            'deployedOffset': list(joint['deployedOffset']),
            'sourceGeometryUVMaterialsPreserved': True,
            'worldTransformPreserved': True,
            'parent': parent.name,
        }
    print('CENTRE TUBE AUDIT', json.dumps(audit, indent=2), flush=True)
    return audit


center_tube_v08_audit = add_center_tubes_v08()
