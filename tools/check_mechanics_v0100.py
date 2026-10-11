"""Diagnostic triangle contacts at sampled actual runtime poses."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];out=R/'work/v0100-review';A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted();basis=Quaternion((1,0,0),-math.pi/2)
exec((R/'tools/check_secondary_clearance_v090.py').read_text().split('def data(o):')[1].split('single=[o')[0].join(['def data(o):','']))
cache={};poses=json.loads((out/'candidate-poses.json').read_text());fixed=tree([bpy.data.objects[n]for n in ['holo.001','holo.013','holo.022']]);rows=[]
single=[o for o in bpy.context.scene.objects if o.get('singleBattery')]
for pose in poses:
 for j in pose['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update();row={'deployment':pose['deployment'],'singles':{},'quads':{},'twins':{},'main':{}}
 for j in single:
  gun=tree(children(j));covers=[o for o in bpy.context.scene.objects if o.get('barrelJoint')==j.name or o.get('barrel')==j.name];ct=tree([c for o in covers for c in children(o)])
  c=hits(gun,ct);f=hits(gun,fixed);h=hits(ct,fixed)
  if c or f or h:row['singles'][j.name]={'ownCovers':c,'gunHull':f,'coverHull':h}
 for side in ['Port','Starboard']:
  gun=tree(children(bpy.data.objects[f'PDC_{side}_Carriage']));petals=tree([c for o in bpy.context.scene.objects if o.name.startswith(f'PDC_{side}_HullPetal_')and o.get('staticJoint')for c in children(o)])
  row['quads'][side]={'petals':hits(gun,petals),'hull':hits(gun,fixed)}
 for i in range(5,9):
  name=f'Defense_{i:02}';gun=tree(children(bpy.data.objects[name+'_Carriage']));gate=tree(children(bpy.data.objects[name+'_NotchGate']));row['twins'][name]=hits(gun,gate)
 for bank in ['Dorsal','Ventral']:
  armor=tree([c for o in bpy.context.scene.objects if o.name.startswith('Hatch_'+bank)and o.get('staticJoint')for c in children(o)])
  row['main'][bank]=hits(armor,fixed)
 rows.append(row);print('POSE',pose['deployment'],'singles',len(row['singles']),'main',len(row['main']['Dorsal']),len(row['main']['Ventral']),flush=True)
(out/'contacts.json').write_text(json.dumps(rows,indent=2))
summary={
 'samples':len(rows),
 'singleGunOwnCoverEvents':sum(len(s['ownCovers']) for r in rows for s in r['singles'].values()),
 'quadGunHullOrPetalEvents':sum(len(h) for r in rows for s in r['quads'].values() for h in s.values()),
 'aftTwinGunGateEvents':sum(len(h) for r in rows for h in r['twins'].values()),
 'mainArmorHullEvents':sum(len(h) for r in rows for h in r['main'].values()),
}
print(json.dumps(summary),flush=True)
assert summary['samples']==101 and all(v==0 for k,v in summary.items() if k!='samples'),summary
