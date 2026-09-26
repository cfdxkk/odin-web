"""Versioned v0.11.5 static geometry: single-gun contact hinges and cool bridge paint.

Run against odin_articulated_v0.11.4.blend. All movement remains in the web rig.
The original odin.blend and the four accepted flank mounts are untouched.
"""
import bpy, bmesh, json, math, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

R = Path(__file__).resolve().parents[1]
exec((R/'tools/revise_secondary_bridge_v090.py').read_text(encoding='utf8').split('def fit_channel_nose')[0])
assert str(A['version']) == '0.11.4', A['version']
source = json.loads((R/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
review = R/'work/v0115-review'; review.mkdir(exist_ok=True)
changes = {'singleGuns': {}, 'defense': {}, 'bridge': {}, 'mainArmor': {}}

def vertices_model(o):
    M = inv@o.matrix_world
    return np.array([M@v.co for v in o.data.vertices])

def aabb(o):
    p=vertices_model(o)
    return [p.min(0).tolist(),p.max(0).tolist()]

def smooth_panel(name, closed, H, rot, parent, outward, thickness=.21):
    # Closed coordinates are measured against the existing bay; the editable
    # mesh is stored in the original deployed pose beneath a static hinge.
    opened=[Vector(H+rot.T@(np.array(p)-H)) for p in closed]
    if (opened[1]-opened[0]).cross(opened[2]-opened[0]).dot(Vector(rot.T@outward))<0:
        opened.reverse()
    result=prism(name,opened,thickness,parent,light,red)
    result['exteriorFinish']='smooth hull paint'
    result['interiorFinish']='red primer'
    return result

for name in [f'SideBattery_{i}_{side}' for i in (2,4) for side in ('Port','Starboard')] + [f'Axial_{station}' for station in ('Bow','Stern','Keel')]:
    row=source[name];C=np.array(row['frameOrigin']);Q=np.array(row['frameAxes']);X,B,N=Q.T
    gun=bpy.data.objects[name if name.startswith('Side') else name+'_Barrel']
    gun['stagedSingleBattery']=True
    if name.startswith('SideBattery_4_'):
        # Lift only the NAV attitude. The fully deployed muzzle and pitch stay
        # at their previous positions; both mirrored #4 mounts use this trim.
        gun['restLiftDegrees']=.9
        gun['stowSink']=.28
    elif name.startswith('SideBattery_2_'):
        gun['stowSink']=1.02
    if name.startswith('SideBattery_'):
        # Seating is across and down into the hull pocket, never fore/aft.
        # That keeps the complete #2/#4 barrel aligned with stationary rear leaves.
        seat=N.copy();seat[1]=0;seat/=np.linalg.norm(seat)
        gun['stowDirectionModel']=seat.tolist()
    elif name=='Axial_Bow':
        gun['stowSink']=2.08
    elif name=='Axial_Stern':
        gun['stowSink']=1.42
    cap=bpy.data.objects[name+'_FrontCap']
    cap['armorGroup']=1
    cap['stagedSingleBattery']=True
    if name=='Axial_Keel':
        cap['slideStart'],cap['slideEnd']=.22,.39
        cap['settleStart'],cap['settleEnd']=.40,.52
    elif name.startswith('Axial_'):
        cap['slideStart'],cap['slideEnd']=.08,.25
        cap['settleStart'],cap['settleEnd']=.26,.38
    else:
        cap['slideStart'],cap['slideEnd']=.08,.24
        cap['settleStart'],cap['settleEnd']=.25,.38
    leaves=[]
    for k in range(3):
        for label,sgn in [('Port',-1),('Starboard',1)]:
            j=bpy.data.objects[f'{name}_Shutter_{label}_{k:02}']
            skin=next(c for c in j.children if c.type=='MESH' and c.name.endswith('_Skin'))
            P=vertices_model(skin);q=(P-C)@Q
            # Source relief supplies the true long contact rail. Its inboard
            # seven percent is nearly a line; the old inverse-solved origin
            # floated away from that rail as each panel rotated.
            signed=sgn*q[:,0]
            edge=P[signed<np.percentile(signed,7)]
            axis=np.linalg.eigh(np.cov(edge.T))[1][:,-1]
            if axis@B<0:axis=-axis
            H=edge.mean(0)
            angle=-sgn*180.
            rot=np.array(Quaternion(Vector(axis),math.radians(angle)).to_matrix())
            closed=(P-H)@rot.T+H
            t=(closed-C)@Q
            hq=(H-C)@Q
            # A shallow flat crown and the original hull-contact boundary
            # form one continuous outer skin. Grate/brace detail is retained
            # on the inner face and painted the same red as its backing.
            inner=t[np.abs(t[:,0])<.85]
            if len(inner)<12:inner=t[np.abs(t[:,0])<1.3]
            assert len(inner)>8,(j.name,'no inner rail samples')
            y0,y1=np.percentile(t[:,1],[1,99]);mid=(y0+y1)/2
            crest=float(np.percentile(inner[:,2],87))+.08
            outer=float(hq[2])+.08
            slope=float(axis@N/max(axis@B,.1))
            width=abs(float(hq[0]));flat=.28
            def roof(x,y):
                z=(crest if x<=flat else crest+(outer-crest)*(x-flat)/(width-flat))
                return z+slope*(y-mid)
            def point(x,y):return C+Q@np.array([sgn*x,y,roof(x,y)])
            outer_dir=N.copy()
            if sgn<0:outer_dir=-outer_dir
            # Winding is checked in smooth_panel against the real exterior N.
            for part,a,b in [('Crown',.025,flat),('Slope',flat,width)]:
                shape=[point(a,y0+.015),point(b,y0+.015),point(b,y1-.015),point(a,y1-.015)]
                smooth_panel(j.name+'_'+part+'_Exterior',shape,H,rot,j,N)
            move_origin(j,H)
            j['hingeAxisModel']=axis.tolist()
            j['closedAngleDegrees']=angle
            j['physicalHinge']=True
            j['sourceHingeLine']=H.tolist()
            j['armorGroup']=4-k
            j['stagedSingleBattery']=True
            if name=='Axial_Keel':
                j['openStart']=.25+k*.035;j['openEnd']=.50+k*.055
            else:
                j['openStart']=.26+k*.035;j['openEnd']=.53+k*.055
            skin.data.materials.clear()
            skin.data.materials.append(light)
            skin.data.materials.append(red)
            # The recovered source cover includes both a broad exposed plate
            # and its inward grate. Keep the broad outward-facing faces gray;
            # color the inward-facing ribs and returns red.
            for face in skin.data.polygons:
                p=P[list(face.vertices)]
                n=np.cross(p[1]-p[0],p[2]-p[0]);size=np.linalg.norm(n)
                outward=np.dot(rot@n/size,N) if size>.000001 else 0
                face.material_index=0 if outward>.1 else 1
            skin['interiorPrimer']=True
            leaves.append({'name':j.name,'group':4-k,'hinge':H.tolist(),'axis':axis.tolist(),
              'crest':crest,'hullContact':outer,'span':[float(y0),float(y1)]})
    changes['singleGuns'][name]={'leaves':leaves,'cap':cap.name,
      'stationaryForeAft':name.startswith('SideBattery_'),'keelFinalDiagonal':name=='Axial_Keel',
      'restLiftDegrees':float(gun.get('restLiftDegrees',0))}

# Aft defense twins should use the original lateral stow distance. Only the
# last 20 percent drops their complete carriage (and attached tubes) beneath
# the hull. Earlier twin mounts are unchanged.
for i in range(5,9):
    j=bpy.data.objects[f'Defense_{i:02}_Carriage']
    j.pop('extraStowVector',None)
    j['finalStowDrop']=1.45
    changes['defense'][j.name]={'extraStowVector':None,'finalStowDrop':1.45}

def recolor(mat,rgb):
    old=np.array(mat.diffuse_color[:3],dtype=float)
    mat.diffuse_color=(*rgb,1)
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*rgb,1)
    for link in bsdf.inputs['Base Color'].links:
        if link.from_node.type!='TEX_IMAGE':continue
        im=link.from_node.image
        pixels=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(pixels)
        p=pixels.reshape(-1,4)
        # Dedicated bridge albedo images preserve their small wear variation.
        variation=np.clip(np.mean(p[:,:3],axis=1)/max(float(old.mean()),.001),.80,1.15)
        p[:,:3]=variation[:,None]*np.array(rgb,dtype=np.float32)
        im.pixels.foreach_set(pixels);im.pack()

tower=bpy.data.materials['Odin_Bridge_Armor'];trim=bpy.data.materials['Odin_Bridge_Trim']
recolor(tower,(.365,.382,.399));recolor(trim,(.245,.257,.270))
hull=bpy.data.objects['holo.001'];M=inv@hull.matrix_world
ti=next(i for i,m in enumerate(hull.data.materials) if m==tower)
di=next(i for i,m in enumerate(hull.data.materials) if m==trim)
newfaces=0
for f in hull.data.polygons:
    pts=[M@hull.data.vertices[i].co for i in f.vertices]
    c=sum(pts,Vector())/len(pts)
    old=hull.data.materials[f.material_index]
    if not old or old.name not in ('Odin_Paint_Light','Odin_Paint_Dark.001'):continue
    if not(-174<c.y<-12 and abs(c.x)<(62 if c.z>100 else 46) and min(p.z for p in pts)>51.2):continue
    f.material_index=di if 'Dark' in old.name else ti
    newfaces+=1
changes['bridge']['newHullFaces']=newfaces
changes['bridge']['palette']={'armor':[.365,.382,.399],'trim':[.245,.257,.270]}

# Flush pigment ribbons on the two upright / gently inclined outer walls of
# the bridge pedestal. Ray hits use the existing hull, so these lines track
# its changing planform rather than floating at a constant X coordinate.
hull.data.calc_loop_triangles()
P=[M@v.co for v in hull.data.vertices]
tree=BVHTree.FromPolygons(P,[tuple(t.vertices) for t in hull.data.loop_triangles],all_triangles=True)
stripe=bpy.data.materials.get('Odin_Bridge_Pinstripe')
if not stripe:stripe=palette('Odin_Bridge_Pinstripe',bpy.data.materials['Odin_Paint_Orange'],(.57,.055,.045),.10,.78)
strips=[]
for sign in (-1,1):
    run=[]
    def flush():
        if len(run)<8:return
        verts=[];faces=[]
        for a,b in run:verts.extend((a,b))
        for k in range(len(run)-1):faces.append((2*k,2*k+1,2*k+3,2*k+2))
        me=bpy.data.meshes.new('Bridge_Pinstripe_Paint');me.from_pydata(verts,[],faces);me.update();me.materials.append(stripe)
        obj=bpy.data.objects.new(f'Bridge_Pinstripe_{"Port" if sign<0 else "Starboard"}_{len(strips):02}',me)
        s.collection.objects.link(obj);obj.parent=A;strips.append(obj.name)
    for y in np.arange(-143,-29,.75):
        pair=[]
        for z in (58.00,58.14):
            origin=Vector((sign*48,float(y),z));direction=Vector((-sign,0,0))
            hit,normal,_,_=tree.ray_cast(origin,direction,42)
            if hit is None:break
            n=normal.normalized()
            if abs(n.z)>.65:break
            pair.append(hit+n*.018)
        if len(pair)<2 or (run and (pair[0]-run[-1][0]).length>1.8):
            flush();run=[]
        if len(pair)==2:run.append(tuple(pair))
    flush()
changes['bridge']['pinstripeObjects']=strips

# Clear the two needle-like points on the large dorsal hatch leaves by
# snapping only isolated front-edge vertices to the line of their neighbours.
# The main armor's long fitted edges, thickness and animation stay intact.
for side in ('Port','Starboard'):
    o=bpy.data.objects[f'Hatch_Dorsal_{side}_FittedSkin'];P=vertices_model(o);M=inv@o.matrix_world;Mi=M.inverted()
    # A single rear-outline vertex on each broad skin runs almost a full
    # unit bow-aft beyond its neighbours. It creates the pointed triangle
    # marked in the reference image. Put both sides of the armor gauge on
    # the straight chord between the adjacent contour vertices.
    target_x=-2.4065 if side=='Port' else 2.5935
    n=len(P)//2
    indices=[i for i,p in enumerate(P[:n]) if abs(p[0]-target_x)<.012 and 112<p[1]<114 and 50.9<p[2]<51.3]
    assert len(indices)==1,(side,'tip vertex',indices)
    changed=0
    for i in (indices[0],indices[0]+n):
        q=P[i].copy();q[1]=114.604
        o.data.vertices[i].co=Mi@Vector(q);changed+=1
    o.data.update();changes['mainArmor'][side]={'tipVerticesChamfered':changed}

for o in s.objects:o.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
A['version']='0.11.5'
A['secondaryRevision']='physical hinge rails; smooth skins and red inner stiffeners; no 2/4 fore-aft carriage; keel final diagonal; aft twin final sink'
s.name='ODIN v0.11.5 — secondary batteries and cool gray bridge'
bpy.context.view_layer.update()
(review/'geometry-build.json').write_text(json.dumps(changes,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/blender/odin_articulated_v0.11.5.blend'),compress=True)
print('SAVED v0.11.5',json.dumps({k:len(v) if isinstance(v,dict) else v for k,v in changes.items()}),flush=True)
