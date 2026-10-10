"""Fit the four aft twin covers to measured hull rims and shell thickness.

Run on v0.11.34. Only the four existing eight-vertex gate skins change. Their
joint frames, translation vectors and the complete gun/rail animations remain
unchanged. The original odin.blend is never written.
"""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
review=root/'docs/review/v0.11.35';review.mkdir(parents=True,exist_ok=True)
fixture=json.loads((root/'tests/fixtures/aft-twin-hull-rims-v01135.json').read_text())
asset=bpy.data.objects['Odin_Asset'];inv=asset.matrix_world.inverted()
hull=bpy.data.objects['holo.001'];hp=np.array([(inv@hull.matrix_world)@v.co for v in hull.data.vertices])
report={'version':'0.11.35','sourceSha256':fixture['sourceSha256'],'covers':[],'edgeClearance':.012}

for row in fixture['starboardApertures']:
    for number,sign in [(row['station'],1),(row['station']+2,-1)]:
        raw=np.array(row['outerCorners'])*[sign,1,1]
        if sign<0:raw=raw[::-1]
        corner_ids=[]
        for p in raw:
            dist=np.linalg.norm(hp-p,axis=1);i=int(dist.argmin())
            assert dist[i]<.00001,(number,p,dist[i])
            corner_ids.append(i)
        centre=raw.mean(0)
        _,_,vectors=np.linalg.svd(raw-centre);normal=vectors[-1]
        if normal[0]*sign<0:normal=-normal
        flat=raw-np.outer((raw-centre)@normal,normal)
        longitudinal=(flat[1]-flat[0]);longitudinal/=np.linalg.norm(longitudinal)
        across=np.cross(normal,longitudinal)
        basis=np.column_stack((longitudinal,across))
        uv=(flat-centre)@basis
        fitted=[]
        for i in range(4):
            a,b,c=uv[(i-1)%4],uv[i],uv[(i+1)%4]
            e1=b-a;e2=c-b
            n1=np.array([-e1[1],e1[0]])/np.linalg.norm(e1)
            n2=np.array([-e2[1],e2[0]])/np.linalg.norm(e2)
            q=np.linalg.solve(np.array([n1,n2]),[n1@a+.012,n2@b+.012])
            fitted.append(centre+basis@q)
        # The source rim has tiny non-planar ridges. Seat the planar skin at
        # their exterior envelope, with a small tolerance for GLB quantization,
        # so the fixed serrated lip cannot flicker through the closed face.
        normal_clearance=float(((raw-centre)@normal).max())+.01
        outer=np.array(fitted)+normal*normal_clearance
        measurements=[];pair_ids=[]
        for pair in row['shellThicknessPairs']:
            ps=np.array(pair)*[sign,1,1]
            measurements.append(float((ps[0]-ps[1])@normal))
            ids=[]
            for p in ps:
                dist=np.linalg.norm(hp-p,axis=1);i=int(dist.argmin())
                assert dist[i]<.00001
                ids.append(i)
            pair_ids.append(ids)
        thickness=float(np.mean(measurements))
        assert .50<thickness<.56,(number,thickness)
        joint=bpy.data.objects[f'Defense_{number:02}_NotchGate'];skin=joint.children[0]
        M=inv@skin.matrix_world;old=np.array([M@v.co for v in skin.data.vertices])
        assert len(old)==8 and len(skin.data.polygons)==6
        coords=np.concatenate((outer,outer-normal*thickness))
        for v,p in zip(skin.data.vertices,coords):v.co=M.inverted()@Vector(p)
        skin.data.update()
        skin['matchedHullRim']=True;skin['matchedHullThickness']=thickness
        skin['hullFitNormalModel']=normal.tolist();skin['hullFitEdgeClearance']=.012
        skin['hullFitNormalClearance']=normal_clearance
        skin['hullFitSource']='odin.blend / holo.001'
        skin['hullFitPlaneModel']=[*normal.tolist(),float(-normal@outer[0])]
        old_normal=np.cross(old[1]-old[0],old[2]-old[0]);old_normal/=np.linalg.norm(old_normal)
        report['covers'].append({'station':number,'joint':joint.name,'mesh':skin.name,
          'hullOuterCornerVertices':corner_ids,'hullThicknessPairVertices':pair_ids,
          'originalHullCorners':raw.tolist(),'closedOuterCorners':outer.tolist(),
          'normal':normal.tolist(),'planeOrigin':centre.tolist(),
          'normalClearance':normal_clearance,
          'referenceShellThicknessSamples':measurements,'shellThickness':thickness,
          'originalCoverThickness':float(abs((old[4]-old[0])@old_normal)),
          'originalCoverTwist':float(abs((old[:4]-old[0])@old_normal).max()),
          'angleCorrectionDegrees':float(np.degrees(np.arccos(np.clip(old_normal@normal,-1,1)))),
          'maxSourceCornerPlaneDeviation':float(abs((raw-centre)@normal).max()),
          'jointFrameAndMotionUnchanged':True})
asset['version']='0.11.35'
assert not bpy.data.actions
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'assets/blender/odin_articulated_v0.11.35.blend'),compress=True)
(review/'cover-fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('AFT_TWIN_COVER_FIT',[(r['station'],r['shellThickness'],r['angleCorrectionDegrees'])for r in report['covers']],flush=True)
