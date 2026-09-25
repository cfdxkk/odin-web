import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
all_data={}
for n in ['holo.001','holo.014__bridge turret','holo.016__bridge turret','odin.021','odin.023']:
 o=bpy.data.objects[n];m=o.data;p=list(range(len(m.vertices)))
 def find(i):
  while p[i]!=i:p[i]=p[p[i]];i=p[i]
  return i
 for e in m.edges:
  a,b=e.vertices;p[find(a)]=find(b)
 groups={}
 for v in m.vertices:groups.setdefault(find(v.index),[]).append(v.index)
 result=[]
 for ids in groups.values():
  if len(ids)<10:continue
  pts=[m.vertices[i].co for i in ids];lo=[min(v[k] for v in pts) for k in range(3)];hi=[max(v[k] for v in pts) for k in range(3)]
  if n=='holo.001' and lo[2]<110:continue
  result.append({'ids':ids,'n':len(ids),'lo':lo,'hi':hi})
 all_data[n]=result
 print(n,[(c['n'],[round(x,2) for x in c['lo']],[round(x,2) for x in c['hi']]) for c in result],flush=True)
(root/'work/mesh-islands.json').write_text(json.dumps(all_data),encoding='utf8')
