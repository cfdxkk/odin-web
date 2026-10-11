import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { createHash } from 'node:crypto'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { reviewStrokeSeconds, retimeReviewCycle } from '../app/lib/turret-tempo.ts'

function scene() {
  const bytes=fs.readFileSync(new URL('../public/models/odin.glb',import.meta.url))
  const g=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString())
  const objects=g.nodes.map(n=>{
    const o=new THREE.Object3D();o.name=n.name;o.userData=n.extras||{}
    if(n.matrix)new THREE.Matrix4().fromArray(n.matrix).decompose(o.position,o.quaternion,o.scale)
    if(n.translation)o.position.fromArray(n.translation)
    if(n.rotation)o.quaternion.fromArray(n.rotation)
    if(n.scale)o.scale.fromArray(n.scale)
    return o
  })
  g.nodes.forEach((n,i)=>n.children?.forEach(j=>objects[i].add(objects[j])))
  const root=new THREE.Group();g.scenes[g.scene||0].nodes.forEach(i=>root.add(objects[i]))
  return {root,objects,rig:createOdinRig(root)}
}

function measure(rig,o) {
  rig.apply(0,0);const start=o.position.clone()
  rig.apply(1,0);const end=o.position.clone(),stroke=start.distanceTo(end)
  let previous=start,peak=0,tenth,ninetieth
  for(let n=0;n<=1000;n++) {
    rig.apply(n/1000,0)
    const fraction=o.position.distanceTo(start)/stroke
    if(tenth===undefined&&fraction>=.1)tenth=n*.0065
    if(ninetieth===undefined&&fraction>=.9)ninetieth=n*.0065
    if(n)peak=Math.max(peak,o.position.distanceTo(previous)/.0065)
    previous=o.position.clone()
  }
  return {peak,span:ninetieth-tenth}
}

test('quad release and carriage have comparable speeds; aft covers slow down while complete turrets move faster',()=>{
  const {root,rig}=scene()
  for(const side of ['Port','Starboard']) {
    const carriage=measure(rig,root.getObjectByName(`PDC_${side}_Carriage`))
    for(let i=0;i<4;i++) {
      const tube=measure(rig,root.getObjectByName(`PDC_${side}_Arm_${i}`))
      assert.ok(tube.peak<11&&tube.peak/carriage.peak<1.25,'Tube release no longer races ahead of the carriage')
      assert.ok(tube.span>2.3&&tube.span<2.5,'The longer seating stroke uses enough time to retain the accepted speed limit')
    }
  }
  for(let i=5;i<=8;i++) {
    const prefix=`Defense_0${i}`
    const cover=measure(rig,root.getObjectByName(prefix+'_NotchGate'))
    const body=measure(rig,root.getObjectByName(prefix+'_Carriage'))
    assert.ok(cover.span>.95&&cover.span<1.15,'The cover no longer crosses 10–90% of its travel in 0.2 seconds')
    assert.ok(body.span>1.5&&body.span<1.85,'Complete carriage travel is quicker than the previous 2.08-second 10–90% interval')
  }
})

test('retimed handoffs retain cover clearance and exact held endpoints on both sides',()=>{
  const {root,rig}=scene()
  for(const side of ['Port','Starboard']) {
    const c=root.getObjectByName(`PDC_${side}_Carriage`),g=root.getObjectByName(`PDC_${side}_Gimbal`)
    rig.apply(0,0);const shut=c.position.clone(),neutral=g.quaternion.clone()
    rig.apply(1,0);const open=c.position.clone(),armor=Array.from({length:4},(_,i)=>root.getObjectByName(`PDC_${side}_HullPetal_${i}`).position.clone())
    for(const p of [.33,.35]) {
      rig.apply(p,0)
      assert.ok(c.position.distanceTo(shut)<1e-9)
      armor.forEach((v,i)=>assert.ok(root.getObjectByName(`PDC_${side}_HullPetal_${i}`).position.distanceTo(v)<1e-9))
    }
    for(const p of [.67,.69]) {
      rig.apply(p,0)
      assert.ok(c.position.distanceTo(open)<1e-9)
      assert.ok(g.quaternion.angleTo(neutral)<1e-7)
    }
  }
  for(let i=5;i<=8;i++) {
    const prefix=`Defense_0${i}`,c=root.getObjectByName(prefix+'_Carriage'),gate=root.getObjectByName(prefix+'_NotchGate')
    rig.apply(0,0);const shut=c.position.clone()
    rig.apply(1,0);const open=c.position.clone(),coverOpen=gate.position.clone()
    rig.apply(.26,0)
    assert.ok(c.position.distanceTo(shut)<1e-9)
    assert.ok(gate.position.distanceTo(coverOpen)<1e-9)
    rig.apply(.64,0)
    assert.ok(c.position.distanceTo(open)<1e-9)
    assert.ok(gate.position.distanceTo(coverOpen)<1e-9)
  }
})

test('retimed mechanisms retrace exactly when reversed and remain continuous at every stage boundary',()=>{
  const {rig,objects}=scene(),affected=objects.filter(o=>o.userData.staticJoint&&/^(PDC_|Defense_0[5-8]_|DefenseRail_Aft_)/.test(o.name))
  const pose=()=>affected.map(o=>[...o.position.toArray(),...o.quaternion.toArray()])
  const forward=[]
  for(let n=0;n<=200;n++){rig.apply(n/200,20);forward.push(pose())}
  for(let n=200;n>=0;n--){rig.apply(n/200,20);assert.deepEqual(pose(),forward[n])}
  for(const p of [.08,.26,.33,.35,.64,.66,.67,.69,.98]) {
    const delta=epsilon=>{
      rig.apply(p-epsilon,20);const a=pose()
      rig.apply(p+epsilon,20);const b=pose()
      return Math.max(...a.flatMap((row,i)=>row.map((v,j)=>Math.abs(v-b[i][j]))))
    }
    const broad=delta(1e-7),narrow=delta(1e-8)
    assert.ok(narrow<2e-6&&narrow<=broad*.11+1e-9,'Motion differences must shrink with the sampling interval, without a discontinuity')
  }
})

test('affected review shots use the full stroke duration and switching shots retains direction, progress and endpoint hold',()=>{
  for(const i of [12,13,18,19,20,21])assert.equal(reviewStrokeSeconds(i),6.5)
  for(const i of [0,2,14,15,16,17,22,28,29])assert.equal(reviewStrokeSeconds(i),3)
  for(const [a,b]of [[1.5,3.25],[3.5,7],[5.5,10.75],[7.5,14.5]]) {
    assert.equal(retimeReviewCycle(a,3,6.5),b)
    assert.equal(retimeReviewCycle(b,6.5,3),a)
  }
})

test('tempo evidence binds unchanged native geometry and actual bidirectional mesh checks to the shipped assets',()=>{
  const read=name=>JSON.parse(fs.readFileSync(new URL(`../docs/review/v0.11.43/${name}.json`,import.meta.url)))
  const native=read('source-geometry'),hashes=read('asset-hashes'),tempo=read('tempo-verification')
  for(const [key,path]of [['native','../assets/blender/odin_articulated_v0.11.43.blend'],['high','../public/models/odin.glb'],['lite','../public/models/odin-lite.glb']])
    assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[key].sha256)
  assert.equal(native.nativeSha256,hashes.native.sha256)
  assert.equal(native.allMeshesUnchanged,550);assert.equal(native.allStaticRestFramesUnchanged,215)
  assert.ok(native.allJointPropertiesUnchanged&&native.originalSourceUnchanged)
  assert.equal(tempo.affectedJoints,54);assert.equal(tempo.unaffectedJoints,161)
  assert.equal(tempo.samples,1203);assert.equal(tempo.maxPosePathError,0);assert.equal(tempo.maxUnaffectedWorldError,0)
  for(const r of Object.values(read('mesh-clearance'))) {
    assert.equal(r.poses,442)
    for(const key of ['barrelPetalContacts','cradlePairContacts','tubePairContacts'])assert.deepEqual(r[key],[])
    assert.equal(r.maxArmorVertexXChange,0);assert.equal(r.maxArmorRotationRadians,0)
  }
  for(const r of Object.values(read('aft-twin-mesh-clearance'))) {
    assert.equal(r.poses,442);assert.deepEqual(r.gunCoverContacts,[]);assert.deepEqual(r.railCoverContacts,[])
    assert.ok(r.unsunkControlContacts>0)
  }
})
