"""Match aft twin gates to the complete source hull, through all shell layers.

The v36 first-layer return stopped halfway through the visible roof rim. Use
the innermost source edge for the inner skin, retaining both intermediate
laminae along the four border faces. The outside fit and gate motion stay put.
"""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
review=root/'docs/review/v0.11.37';review.mkdir(parents=True,exist_ok=True)
fixture=json.loads((root/'tests/fixtures/aft-twin-full-shell-v01137.json').read_text())
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
hull=bpy.data.objects['holo.001'];hp=np.array([(inv@hull.matrix_world)@v.co for v in hull.data.vertices])
labels=['outer','middle','middle2','inner']
report={'version':'0.11.37','sourceSha256':fixture['sourceSha256'],'endSeamClearance':.008,'covers':[]}

def curve(p,s):
    heights=(p[0,2]-p[:,2])/(p[0,2]-p[-1,2])
    return np.array([np.interp(s,heights,p[:,i])for i in range(3)])

for row in fixture['apertures']:
    points={int(i):np.array(p)for i,p in row['points'].items()}
    for i,p in points.items():
        if i>=0:assert np.linalg.norm(hp[i]-p)<.000001,(i,hp[i],p)
        else:
            edge=row['edgeInterpolations'][str(i)];a,b=[hp[j]for j in edge['edge']]
            assert np.linalg.norm(p-(a+(b-a)*edge['factor']))<.000001
    curves={label+key:np.array([points[i]for i in row[label+key]])
            for label in labels for key in['Fore','Aft','Bottom']}
    bottom=curves['outerBottom'];ts=(bottom[0,1]-bottom[:,1])/(bottom[0,1]-bottom[-1,1])
    assert np.all(np.diff(ts)>0)
    levels={0.,.92,1.}
    for label in labels:
        for key in['Fore','Aft']:
            p=curves[label+key];levels.update((p[0,2]-p[:,2])/(p[0,2]-p[-1,2]))
    ss=np.array(sorted(levels));nt,ns=len(ts),len(ss);count=nt*ns
    patches={}
    for label in labels:
        fore,aft,lower=[curves[label+key]for key in['Fore','Aft','Bottom']]
        patch=[]
        for s in ss:
            f,a=curve(fore,s),curve(aft,s)
            for t,b in zip(ts,lower):
                rim=np.clip((s-.92)/.08,0,1);rim=rim*rim*(3-2*rim)
                p=(1-t)*f+t*a+rim*(b-((1-t)*fore[-1]+t*aft[-1]))
                p[1]+=.008*(2*t-1)
                patch.append(p)
        patches[label]=np.array(patch)
    border=[*range(nt),*[j*nt+nt-1 for j in range(1,ns)],
            *range(count-2,count-nt-1,-1),*[j*nt for j in range(ns-2,0,-1)]]
    nb=len(border)
    # Only the outer and innermost skins need broad surfaces. Intermediate
    # layers are perimeter rings, making the complete top lip and end cuts
    # continuous without internal faces or unused vertices.
    coords=np.concatenate([patches['outer'],patches['inner'],
                           patches['middle'][border],patches['middle2'][border]])
    rings=[border,list(range(2*count,2*count+nb)),
           list(range(2*count+nb,2*count+2*nb)),[i+count for i in border]]
    faces=[];materials=[]
    for layer in[0,1]:
        for j in range(ns-1):
            for i in range(nt-1):
                quad=[j*nt+i,j*nt+i+1,(j+1)*nt+i+1,(j+1)*nt+i]
                if layer:quad=quad[::-1]
                faces.append([v+layer*count for v in quad]);materials.append(layer)
    for a,b in zip(rings,rings[1:]):
        for i in range(nb):
            j=(i+1)%nb
            faces.append([a[i],b[i],b[j],a[j]]);materials.append(0)
    for number,sign in[(row['station'],1),(row['station']+2,-1)]:
        skin=bpy.data.objects[f'Defense_{number:02}_NotchGate_Skin'];M=inv@skin.matrix_world
        old=skin.data;slots=list(old.materials)
        mesh=bpy.data.meshes.new(skin.name+'_FullHullSection')
        world=coords*[sign,1,1]
        mesh.from_pydata([M.inverted()@Vector(p)for p in world],[],
                         [f if sign>0 else f[::-1]for f in faces]);mesh.update()
        mesh.materials.append(next(m for m in slots if m.name=='Odin_Paint_Light'))
        mesh.materials.append(next(m for m in slots if m.name=='Odin_Bay_Primer'))
        patch_faces=2*(ns-1)*(nt-1)
        for f,k in zip(mesh.polygons,materials):
            f.material_index=k;f.use_smooth=f.index<patch_faces
        skin.data=mesh
        if old.users==0:bpy.data.meshes.remove(old)
        skin['matchedFullHullThickness']=True
        skin['hullFitSource']='odin.blend / holo.001 / all four shell boundary layers'
        skin['receiverGridColumns']=nt;skin['receiverGridRows']=ns
        skin['receiverOuterVertexCount']=count
        skin['receiverShellLayers']=4;skin['receiverBorderVertexCount']=nb
        skin['receiverInnerForeSourceVertices']=row['innerFore']
        skin['receiverInnerAftSourceVertices']=row['innerAft']
        skin['receiverInnerFloorSourceVertices']=row['innerBottom']
        skin['receiverRoofForeSourceVertices']=row['sourceRoofFore']
        skin['receiverRoofAftSourceVertices']=row['sourceRoofAft']
        top=patches['outer'][:nt]-patches['inner'][:nt]
        lower=patches['outer'][-nt:]-patches['inner'][-nt:]
        report['covers'].append({'station':number,'mesh':skin.name,'vertices':len(coords),'faces':len(faces),
            'gridColumns':nt,'gridRows':ns,'gridLevels':ss.tolist(),'sourceShellLayers':4,
            'sourceReceiverPoints':len(points),'floorSections':nt,'sourceStation':row['station'],
            'upperRimSectionLengths':np.linalg.norm(top,axis=1).tolist(),
            'lowerRimSectionLengths':np.linalg.norm(lower,axis=1).tolist(),
            'endSeamClearance':.008,'jointFrameAndMotionUnchanged':True})
asset['version']='0.11.37'
assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.37.blend'),compress=True)
(review/'cover-fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_FULL_HULL_SECTIONS',[(r['station'],r['sourceShellLayers'],min(r['upperRimSectionLengths']),max(r['upperRimSectionLengths']))for r in report['covers']],flush=True)
