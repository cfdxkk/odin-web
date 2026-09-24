"""v0.8.6: fit dorsal armor to the actual fixed-hull lip.

The former skin ended at the inner, upper crest of the toothed rim. A growing
outer bevel of the source hull remained visible and read as a widening gap.
The main leaves follow the original outer serration vertex chain, including
its longitudinal offset. The independent nose is re-tessellated between the
shared rear section, two crest rails, and the fitted toothed perimeter.
Its last two teeth include a shallow receiving return beneath the outer face
to close the oblique sightline while retaining 0.030 source-unit clearance.
The source hull, ventral geometry and all static animation joints are retained.
"""
import bpy, bmesh, hashlib, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/blender/odin_articulated_v0.8.5.blend'
OUT=ROOT/'assets/blender/odin_articulated_v0.8.6.blend'
assert Path(bpy.data.filepath).resolve()==BASE.resolve()
asset=bpy.data.objects['Odin_Asset']; inv=asset.matrix_world.inverted()
reference=json.loads((ROOT/'tools/main_armor_v081_boundaries.json').read_text(encoding='utf8'))
LOW_EDGE_IDS={'Port': [128059, 128067, 128069, 128068, 128071, 128070, 128073, 128072, 128075, 128074, 128077, 128076, 128079, 128078, 128081, 128080, 128083, 128082, 128085, 128084, 128087, 128086, 128089, 128088, 128091, 128090, 127709, 127710], 'Starboard': [144155, 144163, 144165, 144164, 144167, 144166, 144169, 144168, 144171, 144170, 144173, 144172, 144175, 144174, 144177, 144176, 144179, 144178, 144181, 144180, 144183, 144182, 144185, 144184, 144187, 144186, 143805, 143806]}
red=bpy.data.materials['Odin_Turret_Interior_DeepRed']
report={'revision':'0.8.6','baseline':BASE.name,'fixedHullUnchanged':True,'ventralGeometryUnchanged':True,'jointTransformsAndAnimationMetadataUnchanged':True,'noseTipReturnNormalClearance':.030,'parts':{}}

def geometry(obj):
 m=inv@obj.matrix_world;obj.data.calc_loop_triangles()
 return [m@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in obj.data.loop_triangles]

def bvh(obj):return BVHTree.FromPolygons(*geometry(obj),all_triangles=True,epsilon=.000001)

def ray_z(obj,x,y,direction):
 m=inv@obj.matrix_world;mi=m.inverted()
 hit,p,_,_=obj.ray_cast(mi@Vector((x,y,direction*100)),mi.to_3x3()@Vector((0,0,-direction)))
 return (m@p).z if hit else None

def boundary_edges(obj,direction):
 from collections import Counter
 m=inv@obj.matrix_world;nm=m.to_3x3().inverted().transposed();ps=[m@v.co for v in obj.data.vertices];edges=Counter()
 for face in obj.data.polygons:
  if (nm@face.normal).z*direction>.1:
   ids=list(face.vertices)
   for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))]+=1
 return [(ps[a],ps[b]) for (a,b),count in edges.items() if count==1]

def fit_planar_aft(parent,hull,direction,sign):
 obj=next(o for o in parent.children if o.name.endswith('GapFiller'))
 outline=list(parent['closedOutlineXY']);count=len(outline)//2
 free=[Vector((x,y,0)) for x,y in outline[:count]]
 outer=list(reversed([Vector((x,y,0)) for x,y in outline[count:]]))
 normal=Vector(parent['planeNormal']);vs,_=geometry(obj);anchor=vs[0]
 def point(x,y):return Vector((x,y,anchor.z-(normal.x*(x-anchor.x)+normal.y*(y-anchor.y))/normal.z))
 fixed=bvh(hull)
 from mathutils.kdtree import KDTree
 kd=KDTree(len(vs))
 for i,v in enumerate(vs):kd.insert(v,i)
 kd.balance();local=(inv@obj.matrix_world).inverted();changes=[];new_outer=[]
 for row,old in enumerate(outer):
  old=point(old.x,old.y);start=sign*old.x
  def valid(radius):
   p=point(sign*radius,old.y);bottom=p-normal*.025
   z=ray_z(hull,p.x,p.y,direction)
   gap=min(fixed.find_nearest(p)[3],fixed.find_nearest(bottom)[3])
   return gap>=.025 and (z is None or direction*(bottom.z-z)>=.012)
  # Recompute the plane/deck intersection, not a second curved filler strip.
  good=start;bad=None
  for step in range(1,101):
   trial=start+step*.01
   if not valid(trial):bad=trial;break
   good=trial
  if bad is not None:
   for _ in range(24):
    trial=(good+bad)*.5
    if valid(trial):good=trial
    else:bad=trial
  target=point(sign*good,old.y)
  # Retain the exact shared main/aft front point and taper into its scarf.
  blend=min(1,max(0,(outer[-1].y-old.y)/.5))
  target=old.lerp(target,blend)
  delta=target-old;new_outer.append(target)
  if delta.length<1e-7:continue
  for probe in [old,old-normal*.025]:
   _,index,distance=kd.find(probe)
   if distance>.08:raise RuntimeError('Aft edge vertex not found')
   obj.data.vertices[index].co=local@(vs[index]+delta)
  changes.append(delta.length)
 obj.data.update();bpy.context.view_layer.update()
 parent['closedOutlineXY']=[[p.x,p.y] for p in free+list(reversed(new_outer))]
 parent['sourceReference']='Single planar aft armor; lower edge refitted at actual hull-plane intersection with 0.025 clearance'
 report['parts'][parent.name]={'construction':'original-plane-refit','maximumOutwardExtension':max(changes,default=0),'newVertices':0,'planeNormal':list(normal),'closedHullPairs':len(bvh(obj).overlap(fixed))}
 print('PLANAR_AFT_FIT',parent.name,report['parts'][parent.name],flush=True)

for bank,cfg in reference.items():
 if bank!='Dorsal':continue
 direction=cfg['direction'];hull=bpy.data.objects[cfg['hull']];fixed=bvh(hull)
 main_front_profiles={}
 for side,sign in [('Port',-1),('Starboard',1)]:
  fit_planar_aft(bpy.data.objects[f'Hatch_{bank}_Aft_{side}'],hull,direction,sign)
 # Reshape each actual skin and its ribs, creating one mating edge. There is
 # no overlapping seam strip, extra skirt or alteration to the fixed hull.
 for kind,side in [('Main','Port'),('Main','Starboard'),('Nose',None)]:
  parent=bpy.data.objects[f'Hatch_{bank}_{side}' if kind=='Main' else f'Hatch_{bank}_Nose']
  skin=bpy.data.objects[parent.name+('_FittedSkin' if kind=='Main' else '_Wedge')]
  boundaries=boundary_edges(skin,direction);edge_cache={};source_skin_tree=bvh(skin)
  original_vertices,_=geometry(skin)
  front_indices=[]
  if kind=='Main':
   top_vertices={v for f in skin.data.polygons if ((inv@skin.matrix_world).to_3x3().inverted().transposed()@f.normal).z*direction>.1 for v in f.vertices}
   front_indices=[i for i in top_vertices if abs(original_vertices[i].y-cfg['noseStart'])<.001]
  def real_edge(y,sgn):
   key=(round(y,5),sgn)
   if key not in edge_cache:
    candidates=[]
    for a,b in boundaries:
     if min(a.y,b.y)-.0001<=y<=max(a.y,b.y)+.0001:
      if abs(b.y-a.y)<.000001:candidates.extend([a,b])
      else:candidates.append(a.lerp(b,max(0,min(1,(y-a.y)/(b.y-a.y)))))
    edge_cache[key]=max(candidates,key=lambda p:p.x*sgn).copy() if candidates else None
   return edge_cache[key]
  hm=inv@hull.matrix_world
  low_chains={role:[hm@hull.data.vertices[i].co for i in LOW_EDGE_IDS[role]] for role in ['Port','Starboard']} if bank=='Dorsal' else None
  def base_mapping(p):
   sgn=1 if p.x>=cfg['center'] else -1;e=real_edge(p.y,sgn)
   if e is None:return p
   distance=sgn*(e.x-p.x);band=min(2.0,max(.2,abs(e.x-cfg['center'])-1.6));weight=max(0,min(1,1-distance/band))
   if weight==0:return p
   if bank=='Dorsal':
    role='Starboard' if sgn>0 else 'Port';high=cfg[role]['lip'];low=low_chains[role]
    target=None
    for i in range(min(len(high),len(low))-1):
     if high[i][1]<=p.y<=high[i+1][1]:
      target=low[i].lerp(low[i+1],(p.y-high[i][1])/(high[i+1][1]-high[i][1]));break
    if target is None:return p
    growth=max(0,min(1,(p.y-126)/10));growth=growth*growth*(3-2*growth)
    taper=max(0,min(1,(166.5-p.y)/6.5));taper=taper*taper*(3-2*taper)
    factor=growth*taper*weight
    delta=target-e;delta.z+=direction*.085
    return p+delta*factor
   return p
  def mapping(p):
   q=base_mapping(p)
   if kind!='Nose':return q
   rear_y=cfg['noseStart']+.035
   fade=max(0,min(1,1-(p.y-rear_y)/4.0));fade=fade*fade*(3-2*fade)
   if not fade:return q
   role='Starboard' if p.x>=cfg['center'] else 'Port'
   points=main_front_profiles[role]
   if p.x<points[0][0]-.001 or p.x>points[-1][0]+.001:return q
   desired=None
   for (xa,pa),(xb,pb) in zip(points,points[1:]):
    if xa-.001<=p.x<=xb+.001:
     desired=pa.lerp(pb,max(0,min(1,(p.x-xa)/(xb-xa))));break
   if desired is None:return q
   original=source_skin_tree.ray_cast(Vector((p.x,rear_y+.0001,direction*100)),Vector((0,0,-direction)))[0]
   if original is None:return q
   original.y=rear_y
   desired=desired+Vector((0,.035,0))
   return q+(desired-base_mapping(original))*fade
  changes={}
  for obj in sorted(parent.children,key=lambda o:o!=skin):
   if obj.type!='MESH':continue
   m=inv@obj.matrix_world;mi=m.inverted();maximum=0.;changed=0;source_count=len(obj.data.vertices)
   for vertex in obj.data.vertices:
    p=m@vertex.co;q=mapping(p)
    if obj!=skin:
     original=source_skin_tree.ray_cast(Vector((p.x,p.y,direction*100)),Vector((0,0,-direction)))[0]
     current=ray_z(skin,q.x,q.y,direction)
     if original is not None and current is not None:q.z=current+p.z-original.z
    delta=(q-p).length
    if delta>.000001:vertex.co=mi@q;changed+=1;maximum=max(maximum,delta)
   obj.data.update()
   fitting={}
   if obj==skin:
    if kind=='Nose':
     # The old dense XY grid folds where the serrated edge moves along Y.
     # Re-tessellate the same boundary and the two preserved crest rails.
     # This forms ruled armor facets, not a stretched/overlapping grid.
     from collections import Counter
     from mathutils.geometry import delaunay_2d_cdt
     from mathutils.kdtree import KDTree
     coords=[m@v.co for v in obj.data.vertices];half=len(coords)//2
     counts=Counter()
     for face in obj.data.polygons:
      if all(i<half for i in face.vertices):
       ids=list(face.vertices)
       for a,b in zip(ids,ids[1:]+ids[:1]):counts[tuple(sorted((a,b)))]+=1
     adjacency={}
     for (a,b),count in counts.items():
      if count==1:adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
     loop=[next(iter(adjacency))];previous=None
     while True:
      nxt=next(i for i in adjacency[loop[-1]] if i!=previous)
      if nxt==loop[0]:break
      previous=loop[-1];loop.append(nxt)
     outline=[coords[i] for i in loop];samples=[]
     for a,b in zip(outline,outline[1:]+outline[:1]):
      tip_edge=min(a.y,b.y)>163.4 and min(abs(a.x-cfg['center']),abs(b.x-cfg['center']))>1.7
      steps=max(1,math.ceil((b-a).length/.16)) if tip_edge else 1
      for k in range(steps):
       p=a.lerp(b,k/steps)
       samples.append(p)
     boundary_count=len(samples);constraints=[]
     for sgn in [-1,1]:
      rail=[]
      for k in range(25):
       t=k/24;y=cfg['noseStart']+.036+(cfg['noseEnd']-1.2-cfg['noseStart']-.036)*t
       x=cfg['center']+sgn*(1.4-.3*t)
       hit=source_skin_tree.ray_cast(Vector((x,y,100)),Vector((0,0,-1)))[0]
       if hit is not None:rail.append(len(samples));samples.append(mapping(hit))
      constraints.extend(zip(rail,rail[1:]))
     xy=[Vector((p.x,p.y)) for p in samples]
     vertices,_,faces,_,_,_=delaunay_2d_cdt(xy,list(constraints),[list(range(boundary_count))],1,.000001)
     kd=KDTree(len(samples))
     for i,p in enumerate(samples):kd.insert(Vector((p.x,p.y,0)),i)
     kd.balance();top=[]
     for v in vertices:
      _,i,distance=kd.find(Vector((v.x,v.y,0)))
      if distance>.002:raise RuntimeError('Unexpected new nose CDT intersection')
      top.append(Vector((v.x,v.y,samples[i].z)))
     n=len(top);all_points=top+[p-Vector((0,0,.025)) for p in top]
     fs=[tuple(f) for f in faces];ec=Counter()
     for f in fs:
      for a,b in zip(f,f[1:]+f[:1]):ec[tuple(sorted((a,b)))]+=1
     fs=fs+[tuple(i+n for i in reversed(f)) for f in fs]+[(a,b,b+n,a+n) for (a,b),c in ec.items() if c==1]
     mesh=bpy.data.meshes.new(obj.name+'_RuledFacets');mesh.from_pydata([tuple(mi@p) for p in all_points],[],fs);mesh.update()
     for material in obj.data.materials:mesh.materials.append(material)
     bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
     red_index=next(i for i,mat in enumerate(mesh.materials) if mat==red)
     for face in mesh.polygons:
      face.material_index=red_index if face.normal.z<-.1 else 0
      face.use_smooth=True
     old=obj.data;obj.data=mesh
     if not old.users:bpy.data.meshes.remove(old)
    before_fit=[m@v.co for v in obj.data.vertices]
    obj.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in obj.data.loop_triangles]
    xy_groups={}
    for v in obj.data.vertices:
     p=m@v.co;xy_groups.setdefault((round(p.x,4),round(p.y,4)),[]).append(v.index)
    for iteration in range(100):
     overlaps=bvh(obj).overlap(fixed)
     if not overlaps:break
     touched={i for t,_ in overlaps for i in triangles[t]}
     keys={(round((m@obj.data.vertices[i].co).x,4),round((m@obj.data.vertices[i].co).y,4)) for i in touched}
     for key in keys:
      for i in xy_groups[key]:
       v=obj.data.vertices[i];p=m@v.co;p.z+=direction*.015;v.co=mi@p;fitting[i]=fitting.get(i,0)+.015
     obj.data.update()
    else:raise RuntimeError('Outer skin fit failed to clear fixed hull')
    # Spread the required contact clearance into a continuous field instead
    # of stair-stepping individual dense vertices on the nose cover.
    from mathutils.kdtree import KDTree
    kd=KDTree(len(fitting))
    samples=[]
    for i,height in fitting.items():
     p=before_fit[i];samples.append((p,height));kd.insert(Vector((p.x,p.y,0)),len(samples)-1)
    kd.balance()
    if samples:
     for i,v in enumerate(obj.data.vertices):
      p=before_fit[i];neighbors=kd.find_range(Vector((p.x,p.y,0)),1.6)
      lift=max(((samples[index][1]+.01)*math.exp(-distance*distance/(2*.40**2)) for _,index,distance in neighbors),default=0)
      v.co=mi@(p+Vector((0,0,direction*lift)))
    obj.data.update()
    if kind=='Main':
     main_front_profiles[side]=sorted([(original_vertices[i].x,m@obj.data.vertices[i].co) for i in front_indices],key=lambda pair:pair[0])
    else:
     # A shallow machined return on the final two teeth closes the oblique
     # line of sight under the cover. Its outside surface stays unchanged;
     # only the existing lower perimeter follows the receiving hull lip.
     nose_border={i for edge,c in ec.items() if c==1 for i in edge}
     for i in nose_border:
      p=m@obj.data.vertices[i].co
      if p.y<163.4 or abs(p.x-cfg['center'])<1.7:continue
      hit,normal,_,distance=fixed.find_nearest(p)
      if .065<distance<.4:
       q=hit+(p-hit).normalized()*.030
       weight=max(0,min(1,(p.y-163.4)/1.2));weight=weight*weight*(3-2*weight)
       old=m@obj.data.vertices[i+n].co
       obj.data.vertices[i+n].co=mi@old.lerp(q,weight)
     obj.data.update()
   obj.data.set_sharp_from_angle(angle=math.radians(30))
   changes[obj.name]={'changedSourceVertices':changed,'sourceVertexCount':source_count,'finalVertexCount':len(obj.data.vertices),'maximumSourceDisplacementXYZ':maximum,'localHullFitVertices':len(fitting),'localHullFitMaximum':max(fitting.values(),default=0),'closedHullPairs':len(bvh(obj).overlap(fixed))}
  outline=[]
  for x,y in parent['closedOutlineXY']:
   e=real_edge(y,1 if x>=cfg['center'] else -1)
   if e is None:outline.append([x,y])
   else:
    q=mapping(Vector((x,y,e.z)));outline.append([q.x,q.y])
  parent['closedOutlineXY']=outline
  parent['outerSeamReference']='Skin and ribs conformed to outer fixed-hull bevel, single continuous mating edge'
  report['parts'][parent.name]={'construction':'shared-section-ruled-nose-with-receiving-return' if kind=='Nose' else 'existing-skin-and-ribs-refit','maximumSourceDisplacementXYZ':max(c['maximumSourceDisplacementXYZ'] for c in changes.values()),'nominalVerticalThickness':.055 if kind=='Main' else .025,'targetEdgeTopSurfaceOffset':.085,'meshes':changes}
  print('SKIN_REFIT',parent.name,report['parts'][parent.name],flush=True)
asset['version']='0.8.6';bpy.context.scene.name='ODIN v0.8.6 - armor edges fitted to complete hull-lip section'
assert not bpy.data.actions
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
report['blendSha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
path=ROOT/'work/v086-review/armor-seam-fit.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf8')

