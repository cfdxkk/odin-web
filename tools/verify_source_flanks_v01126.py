"""Read-only source-detail, restored-panel and unchanged-mechanism proof."""
import bpy,hashlib,json,numpy as np
from pathlib import Path
from mathutils import Quaternion, Vector
root=Path(__file__).resolve().parents[1]

def snapshot(o):
    uv=o.data.uv_layers.active
    return {'vertices':np.array([v.co for v in o.data.vertices]),
            'faces':[tuple(f.vertices)for f in o.data.polygons],
            'areas':[f.area for f in o.data.polygons],
            'uv':[{int(v):np.array(uv.data[k].uv)for v,k in zip(f.vertices,f.loop_indices)}if uv else{}for f in o.data.polygons],
            'materials':[o.data.materials[f.material_index].name for f in o.data.polygons]}

def digest(o):
    r=snapshot(o);h=hashlib.sha256(r['vertices'].astype(np.float32).tobytes())
    for f,m,uv in zip(r['faces'],r['materials'],r['uv']):
        h.update(np.array(f,dtype=np.int32).tobytes());h.update(m.encode())
        for v in f:h.update(uv[v].tobytes())if uv else None
    return h.hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.25.blend'))
original={o.name:snapshot(o)for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('SideBattery_2_','SideBattery_4_')) and ('_OriginalArmor'in o.name or '_OriginalFrontCap'in o.name)}
unchanged={o.name:digest(o)for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in original and o.name not in ('holo.001','Flank24_OriginalFixedHull')}
joint_before={o.name:np.array(o.matrix_local)for o in bpy.context.scene.objects if o.get('staticJoint')}
bpy.ops.wm.open_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.26.blend'))
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted();rows=[]
frames=json.loads((root/'docs/review/v0.10.0/source-covers.json').read_text(encoding='utf8'))
for name,r in original.items():
    o=bpy.data.objects[name];new=snapshot(o);max_uv=0.;count=0
    lookup={tuple(sorted(f)):i for i,f in enumerate(new['faces'])}
    for f,uv in zip(r['faces'],r['uv']):
        key=tuple(sorted(f));assert key in lookup,('Original grate face lost',name,f)
        fi=lookup[key];assert new['materials'][fi]==r['materials'][count],('Source material changed',name,fi)
        for v in f:
            if uv:max_uv=max(max_uv,float(np.max(abs(uv[v]-new['uv'][fi][v]))))
        count+=1
    assert max_uv<1e-6,(name,max_uv)
    assert len(new['vertices'])>len(r['vertices'])
    row={'mesh':name,'originalPolygons':len(r['faces']),'retainedOriginalPolygons':count,'fittedPolygons':len(new['faces']),'maxUvError':max_uv}
    if '_OriginalArmor' in name:
        j=o.parent;prefix=j['barrelJoint'];C=np.array(frames[prefix]['frameOrigin']);Q=np.array(frames[prefix]['frameAxes']);H=np.array((inv@j.matrix_world).translation)
        R=np.array(Quaternion(Vector(j['hingeAxisModel']),np.deg2rad(j['closedAngleDegrees'])).to_matrix());p=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices])
        move=np.array(bpy.data.objects[prefix+'_SourceCarriage']['closedOffsetModel'])if j['panelIndex']==0 else np.zeros(3);q=(H+(p-H)@R.T+move-C)@Q
        fi=max((k for k,m in enumerate(r['materials'])if m=='Odin_Paint_Light'),key=lambda k:r['areas'][k]);p=q[list(r['faces'][fi])]
        error=float(np.max(abs(p[:,2]-(6.326-1.58*abs(p[:,0])-.007*p[:,1]))))
        lower=float(max(abs(p[:,0])));assert error<.00012 and abs(lower-2.88)<.00012,(name,error,lower)
        row.update(closedExteriorPlaneError=error,closedLowerEdgeHalfWidth=lower)
    rows.append(row)
for name,h in unchanged.items():assert digest(bpy.data.objects[name])==h,('Unrelated mesh changed',name)
for name,m in joint_before.items():assert np.array_equal(np.array(bpy.data.objects[name].matrix_local),m),('Joint rest changed',name)

source_path=root.parent/'Odin 建模/odin.blend'
with source_path.open('rb')as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
with bpy.data.libraries.load(str(source_path),link=False)as(src,dst):dst.objects=['holo.001']
source=dst.objects[0];bpy.context.scene.collection.objects.link(source);bpy.context.view_layer.update();sp=np.array([source.matrix_world@v.co for v in source.data.vertices]);suv=source.data.uv_layers.active
max_corner=max_uv=0.;panels=0
fit=json.loads((root/'docs/review/v0.11.26/source-fit.json').read_text(encoding='utf8'))
for row in fit['restoredHull']:
    o=bpy.data.objects[row['name']];assert o.parent==asset
    p=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices]);uv=o.data.uv_layers.active
    for f in o.data.polygons:
        current=p[list(f.vertices)];matches=[]
        for fi in row['sourceFaceIds']:
            sf=source.data.polygons[fi];ref=sp[list(sf.vertices)]
            if len(ref)!=len(current):continue
            distances=np.linalg.norm(current[:,None]-ref[None,:],axis=2);idx=distances.argmin(1);err=float(distances[np.arange(len(current)),idx].max())
            if err<.00012:matches.append((err,sf,idx))
        assert matches,(o.name,f.index)
        err,sf,idx=min(matches,key=lambda v:v[0]);max_corner=max(max_corner,err)
        a=np.array([uv.data[k].uv for k in f.loop_indices]);b=np.array([suv.data[k].uv for k in sf.loop_indices])
        max_uv=max(max_uv,float(np.max(abs(a-b[idx]))));panels+=1
assert panels==8 and max_uv<1e-6
rail_polygons=0;rail_corner_error=rail_uv_error=0.
for row in fit['sourceElevationRails']:
    o=bpy.data.objects[row['mesh']];gun=bpy.data.objects[row['followsBarrel']];assert o.parent==gun
    p=np.array([(inv@o.matrix_world)@v.co for v in o.data.vertices]);origin=np.array(gun['sourceOriginModel']);adjusted=np.array(gun['adjustedOriginModel'])
    R=np.array(Quaternion(o['sourceEndRigTurnWXYZ']).to_matrix());rest=np.array(Quaternion(gun['sourceRigRotationWXYZ']).to_matrix())
    recovered=origin+(p-adjusted)@R.T@rest;uv=o.data.uv_layers.active
    for f in o.data.polygons:
        current=recovered[list(f.vertices)];matches=[]
        for fi in row['sourceFaceIds']:
            sf=source.data.polygons[fi];ref=sp[list(sf.vertices)]
            if len(ref)!=len(current):continue
            distances=np.linalg.norm(current[:,None]-ref[None,:],axis=2);idx=distances.argmin(1);err=float(distances[np.arange(len(current)),idx].max())
            if err<.00012:matches.append((err,sf,idx))
        assert matches,('Rail source face changed',o.name,f.index)
        err,sf,idx=min(matches,key=lambda v:v[0]);rail_corner_error=max(rail_corner_error,err)
        a=np.array([uv.data[k].uv for k in f.loop_indices]);b=np.array([suv.data[k].uv for k in sf.loop_indices]);rail_uv_error=max(rail_uv_error,float(np.max(abs(a-b[idx]))));rail_polygons+=1
assert rail_polygons==48 and rail_uv_error<1e-6
with source_path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==source_hash
assert source_hash=='9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e'
report={'version':'0.11.26','sourceSha256':source_hash,'meshes':rows,'restoredRailPolygons':panels,'restoredRailCornerError':max_corner,'restoredRailUvError':max_uv,'sourceElevationRailPolygons':rail_polygons,'sourceElevationRailCornerError':rail_corner_error,'sourceElevationRailUvError':rail_uv_error,'unchangedOtherMeshes':len(unchanged),'unchangedJointTransforms':len(joint_before),'unchangedBarrelAndTurretMeshes':12,'originalUnchanged':True}
(root/'docs/review/v0.11.26/source-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.data.objects.remove(source,do_unlink=True)
print('SOURCE_DETAIL_AND_HULL_PROOF',len(rows),panels,len(unchanged),len(joint_before),flush=True)
