"""Triangle contact sweep for the four revised vertical flank mechanisms."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];out=R/'work/v0110-review';A=bpy.data.objects['Odin_Asset'];inv=A.matrix_world.inverted();basis=Quaternion((1,0,0),-math.pi/2)
exec((R/'tools/check_secondary_clearance_v090.py').read_text().split('def data(o):')[1].split('single=[o')[0].join(['def data(o):','']))
cache={};poses=json.loads((out/'candidate-poses.json').read_text());results=[]
names=[f'SideBattery_{i}_{side}'for i in [1,3]for side in ['Starboard','Port']]
def fixed(o):
 p=o.parent
 while p:
  if p.get('staticJoint'):return False
  p=p.parent
 return True
fixedHull=tree([o for o in bpy.context.scene.objects if o.type=='MESH'and fixed(o)])
fairings={name:tree([o for o in bpy.context.scene.objects if o.name.startswith(name+'_Fairing_')])for name in names}
for pose in poses:
 for j in pose['joints']:
  o=bpy.data.objects[j['name']];x,y,z=j['position'];o.location=(x,-z,y);q=j['quaternion'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis.inverted()@Quaternion((q[3],q[0],q[1],q[2]))@basis
 bpy.context.view_layer.update();row={'deployment':pose['deployment'],'mounts':{}}
 for name in names:
  gun=tree(children(bpy.data.objects[name]));covers=[o for o in bpy.context.scene.objects if o.get('barrelJoint')==name or (o.get('battery')==name and o.get('system')=='side-front-slider')]
  armor=tree([c for j in covers for c in children(j)])
  gunContacts=hits(gun,armor)
  # Group 2 versus the two independently moving neighbors, excluding the
  # intentionally overlapping edge returns belonging to the same rigid leaf.
  group2=tree([c for j in covers if j.get('armorGroup')==2 for c in children(j)])
  sliders=tree([c for j in covers if j.get('armorGroup')==1 for c in children(j)])
  group3=tree([c for j in covers if j.get('armorGroup')==3 for c in children(j)])
  seamContacts=hits(group2,group3);sliderContacts=hits(group2,sliders)
  fairingContacts=hits(armor,fairings[name])
  hullContacts=hits(sliders,fixedHull)if 'Battery_1_'in name else {}
  if gunContacts or seamContacts or sliderContacts or fairingContacts or hullContacts:row['mounts'][name]={'gun':gunContacts,'seam':seamContacts,'slider':sliderContacts,'fairing':fairingContacts,'firstPairHull':hullContacts}
 results.append(row)
 if round(pose['deployment']*100)%10==0:print('SWEEP',pose['deployment'],{k:{x:len(y)for x,y in v.items()}for k,v in row['mounts'].items()},flush=True)
(out/'side-contacts.json').write_text(json.dumps(results,indent=2))
summary={'samples':len(results),'gunArmorEvents':sum(len(v['gun'])for r in results for v in r['mounts'].values()),'group23Events':sum(len(v['seam'])for r in results for v in r['mounts'].values()),'group12Events':sum(len(v['slider'])for r in results for v in r['mounts'].values())}
summary['armorFairingEvents']=sum(len(v['fairing'])for r in results for v in r['mounts'].values())
summary['forwardSliderHullEvents']=sum(len(v['firstPairHull'])for r in results for v in r['mounts'].values())
(out/'side-contact-summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
assert not any(v for k,v in summary.items()if k!='samples'),summary
