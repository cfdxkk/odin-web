"""Read source articulation for reconstruction; never save the source file."""
import bpy, json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
names=[o.name for o in bpy.data.objects if (o.visible_get() and o.type in {'MESH','EMPTY'} and not any(c.name=='perseus' for c in o.users_collection)) or o.name in ['odin.072','odin.073','odin.074','Empty.018','Empty.006','Empty.007','holo.014','holo.016']]
data={}
for name in names:
 o=bpy.data.objects[name]
 a=o.animation_data.action if o.animation_data else None
 curves=[]
 if a:
  for layer in a.layers:
   for strip in layer.strips:
    for slot in a.slots:
     bag=strip.channelbag(slot)
     if bag:
      for f in bag.fcurves:
       curves.append({'path':f.data_path,'index':f.array_index,'keys':[[round(k.co.x,3),round(k.co.y,5)] for k in f.keyframe_points]})
 data[name]={'parent':o.parent.name if o.parent else None,'action':a.name if a else None,'curves':curves,'poses':{}}
for frame in [-100,-52,0,25,50,75,100,150,200,250]:
 scene.frame_set(frame)
 for name,d in data.items():
  o=bpy.data.objects[name]
  d['poses'][frame]={'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'world':[list(r) for r in o.matrix_world],'local':[list(r) for r in o.matrix_local]}
  if frame==-52 and o.type=='MESH':
   pts=[o.matrix_world@Vector(c) for c in o.bound_box]
   d['bounds']=[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]
(root/'work/source-articulation.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
print('ARTICULATION',len(data),'objects',flush=True)
for n,d in data.items():
 if d['curves']:print(n,d['parent'],d['curves'],flush=True)
