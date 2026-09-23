import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
s=bpy.context.scene
print('FRAME',s.frame_current,'RANGE',s.frame_start,s.frame_end)
def layers(l,depth=0):
    print('LAYER',' '*depth,l.name,'excluded',l.exclude,'hidden',l.hide_viewport,l.collection.hide_render,l.collection.hide_viewport)
    for c in l.children:layers(c,depth+1)
layers(bpy.context.view_layer.layer_collection)
for o in bpy.data.objects:
    if 'perseus' in [c.name for c in o.users_collection]:continue
    if o.type=='EMPTY' or o.name.startswith('holo.') or (o.type=='MESH' and not o.hide_render):
        print('OBJ',o.name,'visible',o.visible_get(),'hidden',o.hide_get(),'instance',o.instance_collection.name if o.instance_collection else None,'parent',o.parent.name if o.parent else None,'anim',bool(o.animation_data),'mods',[(m.type,m.show_render) for m in o.modifiers])
def nodes(nt,seen):
    if not nt:return
    if nt.name in seen:return
    seen.add(nt.name)
    for n in nt.nodes:
        if n.type=='GROUP':nodes(n.node_tree,seen)
        if n.type=='TEX_IMAGE' and n.image: print('TEX',n.image.name,n.image.filepath,list(n.image.size),bool(n.image.packed_file),Path(bpy.path.abspath(n.image.filepath)).exists())
        if n.type=='BSDF_PRINCIPLED':print('BSDF',[(i.name,list(i.default_value) if hasattr(i.default_value,'__len__') else i.default_value,i.is_linked) for i in n.inputs if i.name in ['Base Color','Metallic','Roughness','Normal','Emission Color','Emission Strength']])
for m in bpy.data.materials:
    if m.name.startswith('holo_') or m.name in ['Material','材质']:
        print('MATERIAL',m.name); nodes(m.node_tree,set())
dg=bpy.context.evaluated_depsgraph_get()
inst=[]
for i in dg.object_instances:
    o=i.object.original
    if o.type!='MESH' or 'perseus' in [c.name for c in o.users_collection]:continue
    if o.hide_render:continue
    inst.append(dict(name=o.name,instance=i.is_instance,parent=i.parent.original.name if i.parent else None,matrix=[list(r) for r in i.matrix_world]))
(root/'work'/'instances.json').write_text(json.dumps(inst,ensure_ascii=False,indent=2),encoding='utf8')
print('INSTANCES',len(inst))
