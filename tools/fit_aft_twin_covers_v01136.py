"""Close the actual hull apertures, including their tapered return sections.

The source receiver is not a rectangle with a normal extrusion: both end cuts
are faceted and its serrated lower return is wider than the roof rim. Loft the
outer and inner skins independently through those immutable source sections.
Only four gate meshes change; original odin.blend and all motions stay intact.
"""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
review=root/'docs/review/v0.11.36';review.mkdir(parents=True,exist_ok=True)
fixture=json.loads((root/'tests/fixtures/aft-twin-receiver-profiles-v01136.json').read_text())
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
hull=bpy.data.objects['holo.001'];hp=np.array([(inv@hull.matrix_world)@v.co for v in hull.data.vertices])
report={'version':'0.11.36','sourceSha256':fixture['sourceSha256'],'endSeamClearance':.008,'covers':[]}

def curve(p,s):
    heights=(p[0,2]-p[:,2])/(p[0,2]-p[-1,2])
    return np.array([np.interp(s,heights,p[:,i])for i in range(3)])

for row in fixture['apertures']:
    points={int(i):np.array(p)for i,p in row['points'].items()}
    for i,p in points.items():assert np.linalg.norm(hp[i]-p)<.000001,(i,hp[i],p)
    curves={key:np.array([points[i]for i in row[key]])for key in
        ['outerFore','innerFore','outerAft','innerAft','outerBottom','innerBottom']}
    bottom=curves['outerBottom'];ts=(bottom[0,1]-bottom[:,1])/(bottom[0,1]-bottom[-1,1])
    assert np.all(np.diff(ts)>0)
    levels={0.,.92,1.}
    for key in ['outerFore','innerFore','outerAft','innerAft']:
        p=curves[key];levels.update((p[0,2]-p[:,2])/(p[0,2]-p[-1,2]))
    ss=np.array(sorted(levels));nt,ns=len(ts),len(ss)
    patches=[]
    for label in ['outer','inner']:
        fore,aft,lower=[curves[label+key]for key in ['Fore','Aft','Bottom']]
        patch=[]
        for s in ss:
            f,a=curve(fore,s),curve(aft,s)
            for t,b in zip(ts,lower):
                # Keep the broad cover smooth. The source serrations affect
                # only its narrow lower rim, rather than corrugating the face.
                rim=max(0,min(1,(s-.92)/.08));rim=rim*rim*(3-2*rim)
                p=(1-t)*f+t*a+rim*(b-((1-t)*fore[-1]+t*aft[-1]))
                # A narrow longitudinal joint, without lifting or projecting
                # either skin away from the adjoining source cross section.
                p[1]+=.008*(2*t-1)
                patch.append(p)
        patches.append(np.array(patch))
    coords=np.concatenate(patches);count=nt*ns
    faces=[];materials=[]
    for layer in [0,1]:
        for j in range(ns-1):
            for i in range(nt-1):
                quad=[j*nt+i,j*nt+i+1,(j+1)*nt+i+1,(j+1)*nt+i]
                if layer:quad=quad[::-1]
                faces.append([v+layer*count for v in quad]);materials.append(layer)
    border=[*range(nt),*[j*nt+nt-1 for j in range(1,ns)],
        *range(count-2,count-nt-1,-1),*[j*nt for j in range(ns-2,0,-1)]]
    for i,j in zip(border,border[1:]+border[:1]):
        faces.append([i,i+count,j+count,j]);materials.append(0)
    for number,sign in [(row['station'],1),(row['station']+2,-1)]:
        skin=bpy.data.objects[f'Defense_{number:02}_NotchGate_Skin'];M=inv@skin.matrix_world
        old=skin.data;slots=list(old.materials)
        mesh=bpy.data.meshes.new(skin.name+'_ReceiverSection')
        world=coords*[sign,1,1]
        mesh.from_pydata([M.inverted()@Vector(p)for p in world],[],
            [f if sign>0 else f[::-1]for f in faces]);mesh.update()
        # Retain the established gray exterior and red inward material.
        light=next(m for m in slots if m.name=='Odin_Paint_Light')
        red=next(m for m in slots if m.name=='Odin_Bay_Primer')
        mesh.materials.append(light);mesh.materials.append(red)
        patch_faces=2*(ns-1)*(nt-1)
        for f,k in zip(mesh.polygons,materials):
            f.material_index=k;f.use_smooth=f.index<patch_faces
        skin.data=mesh
        if old.users==0:bpy.data.meshes.remove(old)
        for key in ['matchedHullThickness','hullFitNormalModel','hullFitPlaneModel',
                    'hullFitNormalClearance','hullFitEdgeClearance']:
            if key in skin:del skin[key]
        skin['matchedHullRim']=True;skin['matchedHullSection']=True
        skin['hullFitSource']='odin.blend / holo.001 / complete receiver sections'
        skin['hullFitEndClearance']=.008
        skin['receiverGridColumns']=nt;skin['receiverGridRows']=ns
        skin['receiverOuterVertexCount']=count
        skin['receiverForeSourceVertices']=row['outerFore']
        skin['receiverAftSourceVertices']=row['outerAft']
        skin['receiverFloorSourceVertices']=row['outerBottom']
        skin['receiverInnerFloorSourceVertices']=row['innerBottom']
        report['covers'].append({'station':number,'mesh':skin.name,'vertices':len(coords),
           'faces':len(faces),'gridColumns':nt,'gridRows':ns,'gridLevels':ss.tolist(),
           'sourceReceiverPoints':len(points),'floorSections':nt,'sourceStation':row['station'],
           'endSeamClearance':.008,'jointFrameAndMotionUnchanged':True})
asset['version']='0.11.36'
assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.36.blend'),compress=True)
(review/'cover-fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_RECEIVER_SECTIONS',[(r['station'],r['floorSections'],r['vertices'])for r in report['covers']],flush=True)
