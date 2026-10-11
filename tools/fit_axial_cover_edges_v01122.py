"""Fit stern/keel covers to complete receiver and shutter edge profiles.

Run on v0.11.21. The source blend, barrel geometry, film, carriage and all
joint transforms remain unchanged. Six missing original keel support faces
are restored from a read-only library; all existing fixed hulls stay intact.
"""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector

root=Path(__file__).resolve().parents[1]
asset=bpy.data.objects['Odin_Asset'];assert asset['version']=='0.11.21'
inv=asset.matrix_world.inverted()
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text())
review=root/'docs/review/v0.11.22';review.mkdir(parents=True,exist_ok=True)

def points(obj):
    return np.array([(inv@obj.matrix_world)@v.co for v in obj.data.vertices])

def digest(obj):
    h=hashlib.sha256();co=np.empty(len(obj.data.vertices)*3,dtype=np.float32)
    obj.data.vertices.foreach_get('co',co);h.update(co.tobytes())
    for f in obj.data.polygons:
        h.update(np.array(tuple(f.vertices),dtype=np.int32).tobytes())
        h.update(obj.data.materials[f.material_index].name.encode())
    return h.hexdigest()

before={o.name:digest(o) for o in bpy.context.scene.objects if o.type=='MESH'}
joints={o.name:np.array(o.matrix_local).copy() for o in bpy.context.scene.objects if o.get('staticJoint')}
report={'stations':{}}
allowed=set()

# This is fixed support, not the original deployed moving cap (which is a
# different disconnected component). Keep precisely the six omitted faces.
source_path=root.parent/'Odin 建模/odin.blend'
materials_before=set(bpy.data.materials.keys())
with bpy.data.libraries.load(str(source_path),link=False) as (src,dst):dst.objects=['holo.022']
source=dst.objects[0];bpy.context.scene.collection.objects.link(source)
bpy.context.view_layer.update()
source_matrix=source.matrix_world.copy()
source_points=np.array([source_matrix@v.co for v in source.data.vertices])
keel_frame=frames['Axial_Keel'];keel_axes=np.array(keel_frame['frameAxes'])
keel_base=np.array(keel_frame['frameOrigin'])
keel_local=(source_points-keel_base)@keel_axes
source_triangle=keel_local[list(source.data.polygons[1456].vertices)].copy()
support_ids={1456,2736,2737,3291,3293,3518}
assert len(support_ids)==6
fixed=bpy.data.objects['holo.022']
delta=np.array(bpy.data.objects['Axial_Keel_Mount']['fixedAssemblyOffsetModel'])
fixed_local=(points(fixed)-keel_base-delta)@keel_axes
face_key=lambda p:tuple(sorted(tuple(round(float(x),3) for x in v) for v in p))
existing={face_key(fixed_local[list(f.vertices)]) for f in fixed.data.polygons}
for i in support_ids:
    p=keel_local[list(source.data.polygons[i].vertices)]
    assert face_key(p) not in existing,('Source support already present',i)
    assert np.max(abs(p[:,0]))<2.9 and p[:,1].min()>15.7 and p[:,1].max()<25.8
support=source.copy();support.data=source.data.copy()
bpy.context.scene.collection.objects.link(support)
support.name='Axial_Keel_OriginalNoseSupport';support.data.name=support.name
mesh=bmesh.new();mesh.from_mesh(support.data);mesh.faces.ensure_lookup_table()
bmesh.ops.delete(mesh,geom=[f for f in mesh.faces if f.index not in support_ids],context='FACES')
bmesh.ops.delete(mesh,geom=[v for v in mesh.verts if not v.link_faces],context='VERTS')
mesh.to_mesh(support.data);mesh.free()
support.animation_data_clear();support.parent=bpy.data.objects['Axial_Keel_Mount']
support.matrix_parent_inverse=Matrix.Identity(4);support.matrix_local=Matrix.Identity(4)
bpy.context.view_layer.update()
transform=support.matrix_world.inverted()@asset.matrix_world@Matrix.Translation(Vector(delta))@source_matrix
support.data.transform(transform)
for i,m in enumerate(support.data.materials):
    label=m.name.lower() if m else ''
    target='Odin_Paint_Orange' if 'orange' in label else 'Odin_Paint_Dark.001' if 'dark' in label else 'Odin_Paint_Light'
    support.data.materials[i]=bpy.data.materials[target]
support.data.update();support['stationarySourceSupport']=True
support['restoredFrom']='odin.blend/holo.022';support['sourceFaceIndices']=sorted(support_ids)
source_data=source.data;bpy.data.objects.remove(source,do_unlink=True)
if source_data.users==0:bpy.data.meshes.remove(source_data)
for m in list(bpy.data.materials):
    if m.name not in materials_before and m.users==0:bpy.data.materials.remove(m)
report['keelRestoredFixedSupportFaces']=sorted(support_ids)

rear_ids={0,1,4,7,8,11,12,14,16,20,21,23,24,26}
front_ids=set(range(28))-rear_ids
for station in ('Stern','Keel'):
    prefix='Axial_'+station;frame=frames[prefix]
    axes=np.array(frame['frameAxes']);origin=np.array(frame['frameOrigin'])
    if station=='Keel':origin+=delta
    width=2.46 if station=='Stern' else 2.298
    center=.015*width/2.46;flat=.45*width/2.46
    outer_z=2.49 if station=='Stern' else 1.95
    shift_y=0 if station=='Stern' else .14
    housing=bpy.data.objects['odin.027' if station=='Stern' else 'odin.030']
    housing_local=(points(housing)-origin)@axes
    breech_end=float(housing_local[:,1].max())+.02
    segments=[(-16.25+shift_y,-6.525+shift_y),(-6.525+shift_y,1.90+shift_y),(1.90+shift_y,10.53+shift_y)]
    station_report={'leafWidth':2*width,'centerSeam':2*center,'breechCrownRear':breech_end}
    for side,sign in [('Port',-1),('Starboard',1)]:
        for index,(y0,y1) in enumerate(segments):
            joint=bpy.data.objects[f'{prefix}_Shutter_{side}_{index:02d}']
            hinge=np.array((inv@joint.matrix_world).translation)
            R=np.array(Quaternion(Vector(joint['hingeAxisModel']),math.radians(joint['closedAngleDegrees'])).to_matrix())
            backing=bpy.data.objects[joint.name+'_FittedBacking']
            matrix=inv@backing.matrix_world;inverse=matrix.inverted()
            closed=hinge+(points(backing)-hinge)@R.T
            old=(closed-origin)@axes;target=old.copy()
            assert len(old)==12
            for k in range(6):
                cross=k%3;x=[width,flat,center][cross]
                u=(x-center)/(width-center)
                y=y1 if k>=3 else (y0+(breech_end-y0)*(1-u) if index==0 else y0)
                ridge=5.22+(.20*(y-shift_y+16.25)/26.78)-(0 if station=='Stern' else .54)
                z=outer_z if cross==0 else ridge
                target[k]=[sign*x,y,z]
                target[k+6]=target[k]+old[k+6]-old[k]
            opened=hinge+((origin+target@axes.T)-hinge)@R
            for v,p in zip(backing.data.vertices,opened):v.co=inverse@Vector(p)
            backing.data.update();allowed.add(backing.name)
            joint['closedEndEdgesModel']=[[(origin+axes@target[k]).tolist() for k in pair] for pair in ((0,2),(3,5))]
            joint['fittedCrownWidthModel']=2*flat
            if index==0:
                # Remove the old artificial 0.8-unit retreat at the gun-root
                # crown; the complete red relief follows the fitted rear edge.
                skin=bpy.data.objects[joint.name+'_Skin'];matrix=inv@skin.matrix_world;inverse=matrix.inverted()
                closed_skin=hinge+(points(skin)-hinge)@R.T
                old_skin=(closed_skin-origin)@axes;new_skin=old_skin.copy()
                for k,p in enumerate(old_skin):
                    u=np.clip((abs(p[0])-center)/(width-center),0,1)
                    rear_old=y0+.80*(1-u)
                    t=(p[1]-rear_old)/(y1-rear_old)
                    rear_new=y0+(breech_end-y0)*(1-u)
                    new_skin[k,1]=rear_new+(y1-rear_new)*t
                    new_skin[k,2]+=.20*(new_skin[k,1]-p[1])/26.78
                opened_skin=hinge+((origin+new_skin@axes.T)-hinge)@R
                for v,p in zip(skin.data.vertices,opened_skin):v.co=inverse@Vector(p)
                skin.data.update();allowed.add(skin.name)

    cap=bpy.data.objects[prefix+'_FrontCap'];skin=bpy.data.objects[prefix+'_FrontCap_Skin']
    offset=np.array(cap['slideVector'])+np.array(cap['settleVector'])
    matrix=inv@skin.matrix_world;inverse=matrix.inverted()
    local=(points(skin)+offset-origin)@axes
    assert len(local)==56 and len(skin.data.polygons)==66
    old=local.copy();target=old.copy()
    ridge_rear=5.42-(0 if station=='Stern' else .54)
    rear=np.array([[center,segments[-1][1]+.02,ridge_rear],[flat,segments[-1][1]+.02,ridge_rear],[width,segments[-1][1]+.02,outer_z]])
    if station=='Stern':
        wall=(points(bpy.data.objects['Axial_Stern_OriginalNoseSupport'])-origin)@axes
        outer=wall[np.argmin(np.linalg.norm(wall-[2.4624,15.6811,2.8622],axis=1))].copy()
        crest=wall[np.argmin(np.linalg.norm(wall-[.4093,18.696,5.8276],axis=1))].copy()
        hull=bpy.data.objects['holo.001'];p=(points(hull)-origin)@axes
        strip=p[list(hull.data.polygons[166349].vertices)]
        crown=strip[np.argmin(strip[:,1])].copy()
    else:
        # Endpoints of the restored original triangle 1456 and the retained
        # center strip define the entire diagonal receiver contact line.
        triangle=source_triangle.copy()
        outer=triangle[np.argmax(triangle[:,0])].copy();crest=triangle[np.argmax(triangle[:,2])].copy()
        p=(points(fixed)-origin)@axes;strip=p[list(fixed.data.polygons[24539].vertices)]
        crown=strip[np.argmin(strip[:,1])].copy()
    crown[0]=center
    fore=np.array([crown,crest,outer]);fore[:,1]-=.02
    for side in (-1,1):
        base=0 if side==1 else 28
        for section,ids,anchors,new_profile in [('rear',rear_ids,[0,8,4],rear),('front',front_ids,[3,9,5],fore)]:
            src=old[np.array(anchors)+base].copy();src[:,0]=abs(src[:,0])
            for k in ids:
                i=base+k;p=old[i].copy();x=abs(p[0])
                segment=0 if x<=src[1,0] else 1
                t=(x-src[segment,0])/(src[segment+1,0]-src[segment,0])
                old_surface=src[segment]+t*(src[segment+1]-src[segment])
                new_surface=new_profile[segment]+t*(new_profile[segment+1]-new_profile[segment])
                residual=p-old_surface;residual[0]=0
                target[i]=new_surface+residual;target[i,0]*=side
    for v,p in zip(skin.data.vertices,target):v.co=inverse@Vector(origin+axes@p-offset)
    skin.data.update();allowed.add(skin.name)
    cap['receiverForeSeamLocal']=fore.tolist();cap['receiverForeSeamGap']=.02
    cap['closedRearProfileModel']=[(origin+axes@p).tolist() for p in rear]
    cap['closedForeProfileModel']=[(origin+axes@p).tolist() for p in fore]
    cap['originalClosedBounds']=[target.min(0).tolist(),target.max(0).tolist()]
    opened=target-offset@axes
    cap['originalOpenBounds']=[opened.min(0).tolist(),opened.max(0).tolist()]
    cap['fullReceiverEdgeFit']=True
    station_report.update(capWidthBefore=2*float(np.max(abs(old[:,0]))),capWidthAfter=2*float(np.max(abs(target[:,0]))),capCenterGapBefore=2*float(np.min(abs(old[:,0]))),capCenterGapAfter=2*float(np.min(abs(target[:,0]))),rearProfile=rear.tolist(),foreProfile=fore.tolist())
    report['stations'][station]=station_report

bpy.context.view_layer.update()
for name,h in before.items():
    if name not in allowed:assert digest(bpy.data.objects[name])==h,('Unintended mesh change',name)
for name,m in joints.items():assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Unintended joint transform',name)
report['unchangedMeshes']=len(before)-len(allowed);report['unchangedJointTransforms']=len(joints)
report['changedMeshes']=sorted(allowed)
asset['version']='0.11.22'
(review/'geometry-fit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
output=root/'assets/blender/odin_articulated_v0.11.22.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
print('FITTED_AXIAL_CAPS',json.dumps(report),flush=True)
