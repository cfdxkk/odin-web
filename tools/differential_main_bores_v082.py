"""Keep the centre bore high and nest the flanking complete gun assemblies.

Run on the v0.8.1 editable asset. Source connected islands, UVs and materials
are only regrouped under static carriage joints; Nuxt supplies all movement.
This helper deliberately neither saves nor exports a file.
"""


def differential_main_bores_v082():
    import bpy
    import bmesh
    from collections import Counter

    asset = bpy.data.objects['Odin_Asset']
    asset_inverse = asset.matrix_world.inverted()
    audit = {}

    def islands(mesh):
        parents = list(range(len(mesh.vertices)))

        def find(i):
            while parents[i] != i:
                parents[i] = parents[parents[i]]
                i = parents[i]
            return i

        for edge in mesh.edges:
            a, b = edge.vertices
            parents[find(a)] = find(b)
        groups = {}
        for vertex in mesh.vertices:
            groups.setdefault(find(vertex.index), set()).add(vertex.index)
        return list(groups.values())

    def signatures(mesh):
        result = Counter()
        for face in mesh.polygons:
            corners = []
            for index in face.loop_indices:
                vertex = mesh.vertices[mesh.loops[index].vertex_index]
                corners.append((tuple(vertex.co), tuple(tuple(layer.data[index].uv) for layer in mesh.uv_layers)))
            first = min(range(len(corners)), key=lambda i: corners[i])
            result[(face.material_index, tuple(corners[first:] + corners[:first]))] += 1
        return result

    def retain(mesh, ids):
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in ids], context='VERTS')
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    for bank, source_name, direction in [('Dorsal', 'odin.004', 1), ('Ventral', 'odin.012', -1)]:
        source = bpy.data.objects[source_name]
        parent = bpy.data.objects[f'Main_{bank}_Barrels']
        if f'Main_{bank}_Carrier_Center' in bpy.data.objects:
            raise RuntimeError('The bore-carriage split has already been applied')
        transform = asset_inverse @ source.matrix_world
        selections = {role: set() for role in ('Port', 'Center', 'Starboard')}
        counts = {role: [] for role in selections}
        for ids in islands(source.data):
            xs = [(transform @ source.data.vertices[i].co).x for i in ids]
            center = (min(xs) + max(xs)) / 2
            role = 'Port' if center < -3 else 'Starboard' if center > 3 else 'Center'
            # No connected component may bridge two independently moving bores.
            assert max(xs) - min(xs) < 6, (bank, role, min(xs), max(xs))
            selections[role].update(ids)
            counts[role].append(len(ids))

        original_signatures = signatures(source.data)
        original_vertices = len(source.data.vertices)
        original_faces = len(source.data.polygons)
        original_materials = list(source.data.materials)
        original_uv_names = [layer.name for layer in source.data.uv_layers]
        original_world = source.matrix_world.copy()
        source_copy = source.data.copy()
        pieces = []
        for role in ('Port', 'Center', 'Starboard'):
            joint = bpy.data.objects.new(f'Main_{bank}_Carrier_{role}', None)
            bpy.context.scene.collection.objects.link(joint)
            joint.parent = parent
            joint.location = (0, 0, 0)
            joint['staticJoint'] = True
            joint['system'] = 'main-bore-carriage'
            joint['boreRole'] = role
            # The common cradle already lowers the outer pair. Additional
            # descent would cross the ventral hull lip; the centre carriage
            # compensates that descent to sit below its upper guide instead.
            # The source ventral lip narrows further during the levelling
            # sweep; its mirrored pair needs a little more lateral nesting.
            inward = 1.6 if bank == 'Dorsal' else 2.4
            joint['stowOffset'] = [0.0 if role == 'Center' else inward if role == 'Port' else -inward,
                                   0.0, direction * (10.25 if role == 'Center' else 0.0)]
            joint['motionBasis'] = 'Main barrels local axes; translation only; identity at full deployment'
            joint['sourceObject'] = source_name
            bpy.context.view_layer.update()

            piece = source.copy()
            piece.data = source_copy.copy()
            piece.name = f'Main_{bank}_CarrierMesh_{role}'
            piece.data.name = piece.name
            bpy.context.scene.collection.objects.link(piece)
            retain(piece.data, selections[role])
            piece.parent = joint
            piece.matrix_world = original_world
            piece.animation_data_clear()
            piece['sourceObject'] = source_name
            piece['sourceIslandVertexCounts'] = counts[role]
            pieces.append(piece)

            tube = bpy.data.objects[f'Main_{bank}_Tube_{role}']
            tube_world = tube.matrix_world.copy()
            tube.parent = joint
            tube.matrix_world = tube_world
            bpy.context.view_layer.update()
            assert max(abs(tube.matrix_world[i][j] - tube_world[i][j]) for i in range(4) for j in range(4)) < 1e-6
            assert list(piece.data.materials) == original_materials
            assert [layer.name for layer in piece.data.uv_layers] == original_uv_names

        assert sum(len(o.data.vertices) for o in pieces) == original_vertices
        assert sum(len(o.data.polygons) for o in pieces) == original_faces
        total = Counter()
        for piece in pieces:
            total.update(signatures(piece.data))
        assert total == original_signatures, f'{bank}: source geometry, materials or UVs changed'
        bpy.data.objects.remove(source, do_unlink=True)
        bpy.data.meshes.remove(source_copy)
        audit[bank] = {
            'source': source_name, 'sourceVertices': original_vertices,
            'sourceFaces': original_faces, 'sourceGeometryUVMaterialsPreserved': True,
            'fullDeploymentPreserved': True,
            'carriages': {role: {
                'vertices': len(pieces[i].data.vertices),
                'islands': counts[role],
                'stowOffset': list(bpy.data.objects[f'Main_{bank}_Carrier_{role}']['stowOffset']),
                'tube': f'Main_{bank}_Tube_{role}',
            } for i, role in enumerate(('Port', 'Center', 'Starboard'))},
        }
    bpy.context.view_layer.update()
    return audit


differential_main_bores_v082_audit = differential_main_bores_v082()

