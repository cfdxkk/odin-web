import bpy, json, os
from mathutils import Vector
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/'work'
out.mkdir(exist_ok=True)
objects=[]
for o in bpy.data.objects:
    bounds=[o.matrix_world @ Vector(c) for c in o.bound_box] if o.type=='MESH' else []
    objects.append(dict(name=o.name,type=o.type,collections=[c.name for c in o.users_collection],parent=o.parent.name if o.parent else None,vertices=len(o.data.vertices) if o.type=='MESH' else 0,polygons=len(o.data.polygons) if o.type=='MESH' else 0,materials=[m.name if m else None for m in o.data.materials] if o.type=='MESH' else [],location=list(o.location),dimensions=list(o.dimensions),bounds=[[min(p[i] for p in bounds) for i in range(3)],[max(p[i] for p in bounds) for i in range(3)]] if bounds else [],hidden=o.hide_render,modifiers=[(m.name,m.type) for m in o.modifiers]))
materials=[]
for m in bpy.data.materials:
    materials.append(dict(name=m.name,users=m.users,diffuse=list(m.diffuse_color),nodes=[dict(name=n.name,type=n.type,image=n.image.name if n.type=='TEX_IMAGE' and n.image else None) for n in m.node_tree.nodes] if m.node_tree else []))
images=[dict(name=i.name,path=i.filepath,size=list(i.size),packed=bool(i.packed_file)) for i in bpy.data.images]
data=dict(objects=objects,materials=materials,images=images,collections=[dict(name=c.name,objects=len(c.all_objects)) for c in bpy.data.collections])
(out/'blend-inventory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print('INVENTORY',len(objects),'objects',len(materials),'materials',len(images),'images')
for c in data['collections']:print(c)
for o in sorted(objects,key=lambda o:o['vertices'],reverse=True)[:35]:print({k:o[k] for k in ['name','vertices','polygons','collections','dimensions','materials']})
