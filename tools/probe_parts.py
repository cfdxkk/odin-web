import bpy,json
from pathlib import Path
names=['holo.010','holo.011','holo.013','holo.012','holo.020','holo.023','holo.024','holo.025','holo.026','odin.004','odin.005','odin.006','odin.007','odin.008','Empty.001','Empty','Empty.003','立方体','立方体.002','Cube','Cylinder']
data={}
for frame in [-52,1,50,100]:
    bpy.context.scene.frame_set(frame)
    data[frame]={n:{'pos':list(bpy.data.objects[n].matrix_world.translation),'rot':list(bpy.data.objects[n].matrix_world.to_euler())} for n in names if n in bpy.data.objects}
for n in names:
    o=bpy.data.objects.get(n)
    if o is None:continue
    print(n,'mat',[(m.name, [(i.name,list(i.default_value) if hasattr(i.default_value,'__len__') else i.default_value) for i in next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),m.node_tree.nodes[0]).inputs if i.name in ['Alpha','Base Color']]) for m in o.data.materials if m and m.node_tree] if o.type=='MESH' else '')
    for mod in o.modifiers:
        if mod.type=='NODES':print('MODIFIER',mod.name,'GROUP',mod.node_group.name if mod.node_group else None,dict(mod.items()))
Path(__file__).resolve().parents[1].joinpath('work/poses.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
