"""Fit continuous exterior armor to the remaining seven single batteries.

Run after revise_secondary_bridge_v0115.py. The original source grates were
useful for locating the contact rails, but their irregular exposed faces do
not close into a clean hull surface. Each is replaced with a smooth outer
shell and a red inward rib grid at the same physical hinge line.
"""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

R=Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8').split('def fit_channel_nose')[0])
assert str(A['version'])=='0.11.5'
build=json.loads((R/'work/v0115-review/geometry-build.json').read_text())
new={}
ribmat=bpy.data.materials.get('Odin_Armor_Reinforcement')
if not ribmat:ribmat=palette('Odin_Armor_Reinforcement',red,(.37,.036,.041),.11,.69)

def erase(o):
    for child in list(o.children):erase(child)
    bpy.data.objects.remove(o,do_unlink=True)

for name,row in build['singleGuns'].items():
    frame=json.loads((R/'docs/review/v0.10.0/source-covers.json').read_text())[name]
    C=np.array(frame['frameOrigin']);Q=np.array(frame['frameAxes']);X,B,N=Q.T
    created=[]
    for label,sgn in [('Port',-1),('Starboard',1)]:
        data=sorted([x for x in row['leaves'] if f'_Shutter_{label}_' in x['name']],key=lambda x:-x['group'])
        assert len(data)==3
        raw=[]
        for info in data:
            H=np.array(info['hinge']);axis=np.array(info['axis']);q=(H-C)@Q;a=axis@Q
            y0,y1=info['span']
            def at(y):return q+a/a[1]*(y-q[1])
            raw.append((at(y0),at(y1),y0,y1))
        # Average the neighbouring source contact rails at a common seam.
        # This gives every pair identical end coordinates while preserving
        # the measured hull lip at the two ends of the complete sequence.
        boundary=[raw[0][0]]
        for k in range(2):
            y=(raw[k][3]+raw[k+1][2])*.5
            q=(raw[k][1]+raw[k+1][0])*.5
            q[1]=y
            boundary.append(q)
        boundary.append(raw[2][1])
        # The raised aft contact rail on the upper flank pockets used to give
        # group 4 a much higher crown than groups 3/2. Carry one ridge line
        # from that aft leaf to the existing front receiver across all three.
        aft_ridge=np.mean([x['crest'] for x in row['leaves'] if x['group']==4])
        receiver_ridge=float(frame['closedSeat']['ridge'])
        aft_y,receiver_y=boundary[0][1],boundary[-1][1]
        for k,info in enumerate(data):
            j=bpy.data.objects[info['name']]
            for child in list(j.children):
                if child.type=='MESH':erase(child)
            a,b=boundary[k:k+2]
            H=C+Q@a
            axis=(Q@(b-a));axis/=np.linalg.norm(axis)
            angle=-sgn*180.
            rot=np.array(Quaternion(Vector(axis),math.radians(angle)).to_matrix())
            rise=2.68
            flat=.30
            def qpoint(x,t,drop=0):
                y=(1-t)*a[1]+t*b[1]
                outer=(1-t)*a[2]+t*b[2]
                width=(1-t)*abs(a[0])+t*abs(b[0])
                x=width if x is None else x
                if name.startswith('SideBattery_'):
                    u=(y-aft_y)/(receiver_y-aft_y)
                    ridge=(1-u)*aft_ridge+u*receiver_ridge
                    profile_rise=ridge-outer
                else:profile_rise=rise
                z=outer+profile_rise*(1-max(0,x-flat)/(width-flat))-drop
                return C+Q@np.array([sgn*x,y,z])
            def face(suffix,quad,material=light,gauge=.21):
                pts=[Vector(H+rot.T@(p-H)) for p in quad]
                outward=Vector(rot.T@N)
                if (pts[1]-pts[0]).cross(pts[2]-pts[0]).dot(outward)<0:pts.reverse()
                # The shell itself stays hull-gray on both faces. The red is
                # the separate inward reinforcement, so a shallow view along
                # a panel edge can never reveal a red shell return outside.
                obj=prism(j.name+'_'+suffix,pts,gauge,j,material,material)
                created.append(obj.name)
                return obj
            # The two halves meet at one straight, barely open ridge. A
            # single section profile is reused at both ends of each leaf.
            for suffix,x0,x1 in [('Crown',0,flat),('Slope',flat,None)]:
                face(suffix,[qpoint(x0,0),qpoint(x1,0),qpoint(x1,1),qpoint(x0,1)])
            # Stiffener grid is entirely inward of the opaque outer shell.
            # Both directions are red; a slightly brighter primer on the rib
            # faces lets the detail read when the leaf unfolds.
            for t in np.arange(.10,.96,.105):
                lo,hi=t-.009,t+.009
                wlo=(1-lo)*abs(a[0])+lo*abs(b[0]);whi=(1-hi)*abs(a[0])+hi*abs(b[0])
                face('Crossrib_%02d'%round(t*100),[qpoint(.16,lo,.50),qpoint(wlo-.10,lo,.50),qpoint(whi-.10,hi,.50),qpoint(.16,hi,.50)],ribmat,.042)
            for frac in (.28,.50,.72):
                lo,hi=.025,.975
                wlo=(1-lo)*abs(a[0])+lo*abs(b[0]);whi=(1-hi)*abs(a[0])+hi*abs(b[0])
                xlo=flat+(wlo-flat)*frac;xhi=flat+(whi-flat)*frac
                face('Longrib_%02d'%round(frac*100),[qpoint(xlo-.035,lo,.49),qpoint(xlo+.035,lo,.49),qpoint(xhi+.035,hi,.49),qpoint(xhi-.035,hi,.49)],ribmat,.042)
            move_origin(j,H)
            j['hingeAxisModel']=axis.tolist()
            j['closedAngleDegrees']=angle
            j['sourceHingeLine']=H.tolist()
            j['hingeEdgeModel']=[H.tolist(),(C+Q@b).tolist()]
            j['physicalHinge']=True
            j['exteriorFinish']='smooth hull paint'
            j['innerStiffeners']='red'
    new[name]={'pieces':created,'movingCarriage':False if name.startswith('SideBattery_') else None}

for obj in s.objects:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
A['secondaryRevision']='seven remaining singles fitted to continuous physical contact rails, red inside; keel final stroke preserved'
bpy.context.view_layer.update()
(R/'work/v0115-review/fitted-single-armor.json').write_text(json.dumps(new,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.5.blend'),compress=True)
print('FITTED v0.11.5',sum(len(v['pieces']) for v in new.values()),flush=True)
