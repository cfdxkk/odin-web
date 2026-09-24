import bpy,json,hashlib,struct,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1]
base=r/'assets/blender/odin_articulated_v0.5.0.blend'
version=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '0.7.0'
candidate=r/f'assets/blender/odin_articulated_v{version}.blend'
output=r/'docs/review/v0.8/hull-preservation.json' if version=='0.8.0' else r/'docs/review/hull-preservation-v07.json'
output.parent.mkdir(parents=True,exist_ok=True)
def read(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));result={}
 for name in ('holo.001','holo.013'):
  o=bpy.data.objects[name];m=o.data
  coords=[tuple(v.co) for v in m.vertices];faces=[tuple(f.vertices) for f in m.polygons];edges=[tuple(e.vertices) for e in m.edges]
  result[name]={'coordinates':coords,'faces':faces,'edges':edges,'matrix':tuple(v for row in o.matrix_world for v in row),'materialIndices':[f.material_index for f in m.polygons],'materials':[x.name if x else None for x in m.materials]}
 return result
a=read(base);b=read(candidate);result={'baseline':base.name,'candidate':candidate.name,'baselineSha256':hashlib.sha256(base.read_bytes()).hexdigest(),'candidateSha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'comparison':'Exact per-index float coordinates, polygon vertex order, mesh edge endpoints and object world transform; material changes allowed','objects':{}}
def digest(data):return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()
for name,x in a.items():
 y=b[name];changed=[i for i,(p,q) in enumerate(zip(x['coordinates'],y['coordinates'])) if p!=q]
 info={'vertexCount':len(y['coordinates']),'polygonCount':len(y['faces']),'edgeCount':len(y['edges']),'vertexCoordinatesIdentical':x['coordinates']==y['coordinates'],'polygonTopologyIdentical':x['faces']==y['faces'],'edgeTopologyIdentical':x['edges']==y['edges'],'worldTransformIdentical':x['matrix']==y['matrix'],'changedCoordinateIndices':changed,'vertexSha256':digest(y['coordinates']),'polygonSha256':digest(y['faces']),'edgeSha256':digest(y['edges']),'materialIndexChanges':sum(p!=q for p,q in zip(x['materialIndices'],y['materialIndices'])),'baselineMaterials':x['materials'],'candidateMaterials':y['materials']}
 result['objects'][name]=info
result['passed']=all(all(v[k] for k in ['vertexCoordinatesIdentical','polygonTopologyIdentical','edgeTopologyIdentical','worldTransformIdentical']) for v in result['objects'].values())
output.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2),flush=True)
if not result['passed']:raise RuntimeError('Hull geometry differs')
