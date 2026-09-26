"""Seat the four vertical flank batteries' armor on the source inner slot plane.

The v0.11.1 first sliders and folded leaves were offset outboard from the
original hull cheek. Measure the unedited lower inner slot facet and lip in
each mount's own frame, then replace the *visible armor skins* at that plane.
Refit the inner grates with the shells and update only the stowed bore depth
and slider lift. Preserve the fixed hull and other weapon geometry.
"""
import bpy, json, math, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

R = Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text().split('def fit_channel_nose')[0])
out = R/'work/v0112-review'; out.mkdir(exist_ok=True)
rows = json.loads((R/'docs/review/v0.11.0/side-batteries.json').read_text())
hull = bpy.data.objects['holo.001']
hp = np.array([inv @ hull.matrix_world @ v.co for v in hull.data.vertices])
report = {}


def outer_skin(name, rows, parent, to_model):
    """A flat crown and planar slope, with red only on the inward gauge face."""
    n = len(rows[0]); assert n == 3
    points = [list(to_model(np.array(p))) for row in rows for p in row]
    faces = [(i, i+1, i+n+1, i+n) for k in range(len(rows)-1) for i in range(k*n, k*n+n-1)]
    data = bpy.data.meshes.new(name); data.from_pydata(points, [], faces); data.update()
    obj = bpy.data.objects.new(name, data); s.collection.objects.link(obj); obj.parent = A
    data.materials.append(light); data.materials.append(red)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new('Armor gauge', 'SOLIDIFY')
    mod.thickness = .23; mod.offset = -1; mod.material_offset = 1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    keep(obj, parent)
    obj['sideBatteryMechanism'] = True
    obj['exteriorFinish'] = 'smooth hull paint, original inner-slot facet'
    obj['interiorPrimer'] = True
    return obj


def measured_slot(name, label, sign, C, Q, hq):
    """The original broad nose facet, its trailing lip and the long inner rail."""
    candidates = []
    for face in hull.data.polygons:
        if face.area < 10 or len(face.vertices) != 3:
            continue
        pts = hq[list(face.vertices)]; u = pts[:,0]*sign
        if not (u.min() > .2 and u.max() < 2.6 and pts[:,1].min() > 16
                and 27 < pts[:,1].max() < 31 and np.ptp(pts[:,1]) > 7
                and pts[:,2].min() > -2 and pts[:,2].max() < 4):
            continue
        plane = np.linalg.lstsq(np.c_[pts[:,:2], np.ones(3)], pts[:,2], rcond=None)[0]
        if 1.4 < abs(plane[0]) < 1.5 and abs(plane[1]) < .02:
            candidates.append((face.area, plane, pts))
    assert len(candidates) == 1, (name, label, 'source facet', len(candidates))
    _, plane, facet = candidates[0]
    crown = facet[np.argsort(facet[:,1])[1]].copy()
    root = facet[np.argmin(facet[:,1])].copy()
    target = root + np.array([0, -.16, 0])
    end = hq[np.argmin(np.linalg.norm(hq-target, axis=1))].copy()
    assert np.linalg.norm(end-target) < .02, (name, label, 'front lower rim')

    rails = []
    for face in hull.data.polygons:
        if len(face.vertices) != 4 or not 4 < face.area < 7:
            continue
        pts = hq[list(face.vertices)]; u = pts[:,0]*sign
        if (2.25 < u.min() < 2.7 and 2.8 < u.max() < 3.1
                and 8 < pts[:,1].min() < 11 and 16 < pts[:,1].max() < 20
                and -1.2 < pts[:,2].min() < -.6 and pts[:,2].max() < .05):
            inner = pts[u < 2.7]
            if len(inner) == 2:
                rails.append((face.area, inner[np.argsort(inner[:,1])]))
    assert len(rails) == 1, (name, label, 'source inner rail', len(rails))
    rail_rear, rail_front = rails[0][1]
    seed = np.array([sign*2.503, -.30, -.154])
    base = hq[np.argmin(np.linalg.norm(hq-seed, axis=1))].copy()
    if np.linalg.norm(base-seed) >= .035:
        # The opposite vertical half has a removed bearing strip here. Carry
        # the measured intact half's transverse station onto this same facet.
        base = np.array([sign*2.503, -.30,
                         plane[0]*sign*2.503 + plane[1]*-.30 + plane[2]])
    assert abs(plane[0]*sign + 1.43) < .02
    return plane, crown, end, base, rail_rear, rail_front


def refit_grate(obj, H, rot, shift, C, Q, sign, plane, flat, profile,
                old_half, old_flat, old_ridge, old_base):
    """Warp the original relief with its shell, preserving all grid detail."""
    M = inv @ obj.matrix_world; Mi = M.inverted()
    for v in obj.data.vertices:
        world = np.array(M @ v.co)
        q = ((world-H) @ rot.T + H-C) @ Q + shift
        old_x=abs(q[0]); target_half=profile(q[1])
        if old_x <= old_flat:
            new_x=old_x*flat/old_flat
        else:
            new_x=flat+(old_x-old_flat)*(target_half-flat)/(old_half-old_flat)
        old_roof=old_base+(old_ridge-old_base)*min(1,(old_half-old_x)/(old_half-old_flat))
        new_roof=plane[0]*sign*max(new_x,flat)+plane[1]*q[1]+plane[2]
        q[0]=sign*new_x;q[2]+=new_roof-old_roof
        world = H + rot.T @ (C + Q @ (q-shift) - H)
        v.co = Mi @ Vector(world)
    obj.data.update()
    return len(obj.data.vertices)


for name, row in rows.items():
    C = np.array(row['frameOrigin']); Q = np.array(row['frameAxes']); X,B,N = Q.T
    hq = (hp-C) @ Q
    old_half = np.mean([abs(((np.array(l['hinge'])-C)@Q)[0]) for l in row['leaves'] if l['group']==2])
    old_flat = np.mean([r['halfWidth'] for r in row['ridge'] if r['group']==2])
    old_ridge = np.mean([r['height'] for r in row['ridge'] if r['group']==2])
    old_base = np.mean([bpy.data.objects[l['name']]['backingSeatLift'] for l in row['leaves'] if l['group']==2])
    carriage = bpy.data.objects[name+'_Carriage']
    shift = (np.array(carriage['slideVector']) + np.array(carriage['liftVector'])) @ Q
    mount = {}
    for label,sign in [('Port',-1),('Starboard',1)]:
        plane,crown,end,base,rail_rear,rail_front = measured_slot(name,label,sign,C,Q,hq)
        flat = abs(crown[0]); source = sorted([base,rail_rear,rail_front,end],key=lambda p:p[1])
        def profile(y):
            if y <= source[0][1]: return abs(source[0][0])
            for p,q in zip(source,source[1:]):
                if y <= q[1]: return abs(p[0])+(abs(q[0])-abs(p[0]))*(y-p[1])/(q[1]-p[1])
            return abs(source[-1][0])
        def height(x,y): return plane[0]*sign*max(x,flat)+plane[1]*y+plane[2]
        def row_at(crown_y,outer_y,outer_x):
            return [[sign*x,y,height(x,y)] for x,y in [(.025,crown_y),(flat,crown_y),(outer_x,outer_y)]]
        def ordered(rows): return [list(reversed(r)) for r in rows] if sign<0 else rows
        def solved_outer(crown_y):
            y = crown_y-.42*(profile(crown_y)-flat)
            for _ in range(5): y = crown_y-.42*(profile(y)-flat)
            return y,profile(y)
        leaf_edges = {}
        for leaf in row['leaves']:
            if (('_Shutter_Port_' in leaf['name']) != (label=='Port')): continue
            joint = bpy.data.objects[leaf['name']]
            group = leaf['group']; H = np.array(leaf['hinge'])
            rot = np.array(Quaternion(Vector(leaf['axis']), math.radians(joint['closedAngleDegrees'])).to_matrix())
            d = shift if group>=3 else np.zeros(3)
            def to_model(q): return H + rot.T @ (C + Q @ (q-d) - H)
            lo,hi = joint['closedLongitudinalRange']
            new_rows=[]; edges=[]
            for y0 in [lo,hi]:
                crown_y = y0+.42*(old_half-old_flat)
                outer_y,outer_x = solved_outer(crown_y)
                edge = row_at(crown_y,outer_y,outer_x)
                new_rows.append(edge); edges.append(edge)
            old = bpy.data.objects[joint.name+'_FittedBacking']
            bpy.data.objects.remove(old,do_unlink=True)
            outer_skin(joint.name+'_FittedBacking', ordered(new_rows), joint, to_model)
            grate = bpy.data.objects[joint.name+'_Skin']
            bars = refit_grate(grate,H,rot,d,C,Q,sign,plane,flat,profile,
                              old_half,old_flat,old_ridge,old_base)
            local = joint.matrix_world.inverted() @ A.matrix_world
            joint['ridgeHalfWidth'] = float(flat)
            joint['fittedHullFacetPlane'] = plane.tolist()
            joint['crownSeamsLocal'] = [[list(local@Vector(to_model(np.array(p)))) for p in edge[:2]] for edge in edges]
            if group in (2,3):
                edge = edges[0 if group==2 else 1][1:]
                joint['closedSeamEdgeModel'] = [list(C+Q@np.array(p)) for p in edge]
                joint['seamEdgeLocal'] = [list(local@Vector(to_model(np.array(p)))) for p in edge]
            leaf_edges[group] = {'rear':edges[0], 'front':edges[1], 'redGrateVertices':bars}

        slider = bpy.data.objects[name+'_Slider_'+label]
        source_front = leaf_edges[2]['front']
        rear_crown_y = source_front[1][1]+.080
        rear_outer_y, rear_outer_x = solved_outer(rear_crown_y)
        rear = row_at(rear_crown_y,rear_outer_y,rear_outer_x)
        front = row_at(float(crown[1]),float(end[1]),abs(end[0]))
        # The bevel's own rim vertex is a fraction off the large facet's
        # infinite plane. The actual visible tip must touch that vertex,
        # not stop at the mathematical extrapolation of its neighbor.
        front[0][2]=front[1][2]=float(crown[2]);front[2][2]=float(end[2])
        mid_outer = rail_front
        t = (mid_outer[1]-rear_outer_y)/(end[1]-rear_outer_y)
        assert .5<t<1, (name,label,'measured rail station',t)
        mid_crown_y = rear_crown_y+t*(crown[1]-rear_crown_y)
        middle = row_at(float(mid_crown_y),float(mid_outer[1]),abs(mid_outer[0]))
        for child in list(slider.children):
            if child.name.endswith('_TrapezoidSkin') or '_InnerRimReturn_' in child.name:
                bpy.data.objects.remove(child,do_unlink=True)
        outer_skin(slider.name+'_TrapezoidSkin',ordered([rear,middle,front]),slider,
                   lambda q:C+Q@q)
        rake = (crown[1]-end[1])/(abs(end[0])-flat)
        slider['frontEdgeRake'] = float(rake)
        slider['frontReceiverEdgeModel'] = [list(C+Q@p) for p in [crown,end]]
        slider['closedOutlineModel'] = [list(C+Q@np.array(p)) for p in rear+front[::-1]]
        slider['frontFit'] = 'visible first armor itself seats on original lower inner rim'
        slider['fittedHullFacetPlane'] = plane.tolist()
        slider['liftVector'] = list(np.array(slider['liftVector'])+N*1.10)
        mount[label] = {
            'sourcePlaneSigned':plane.tolist(),
            'sourceFrontRim': [crown.tolist(),end.tolist()],
            'sourceLongRail': [p.tolist() for p in source[:-1]],
            'newSliderRear':rear,
            'newSliderMid':middle,
            'newSliderFront':front,
            'leaves':leaf_edges,
        }
        print('FITTED',name,label,'rim',np.round([crown,end],3).tolist(),flush=True)
    report[name]=mount
    # The measured hull roof is roughly one unit farther inboard. Let the
    # complete, already-centered bore settle deeper only while NAV is closed;
    # SCM returns to the accepted firing location after the leaves clear.
    bpy.data.objects[name]['stowSink']=1.80

A['version']='0.11.2'
A['sideBatteryRevision']='four vertical flank armor pairs on measured lower inner slot plane and continuous rail'
bpy.context.view_layer.update()
basis=Matrix.Rotation(-math.pi/2,4,'X'); nodes=[]
for o in [A]+[o for o in s.objects if o.get('staticJoint')]:
    m=basis@o.matrix_local@basis.inverted()
    nodes.append({'name':o.name,'parent':o.parent.name if o.parent else None,
                  'matrix':[m[r][c]for c in range(4)for r in range(4)],'extras':dict(o.items())})
(out/'rig-nodes.json').write_text(json.dumps(nodes,default=lambda v:list(v)))
(out/'armor-fit.json').write_text(json.dumps(report,indent=2))
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.2.blend'),compress=True)
