// Compare the retimed runtime against the complete accepted v42 pose path.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'
import path from 'node:path'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { turretPoseProgress } from '../app/lib/turret-tempo.ts'

// Recover the comparison runtime and asset from the immutable accepted tag,
// including its helper modules. No uncommitted baseline is required.
const baselineDir='work/v01143-review/baseline'
fs.mkdirSync(baselineDir,{recursive:true})
for(const name of ['odin-rig.ts','odin-motion.ts','bridge-quad-source-motion.ts','bow-source-motion.ts','stern-source-motion.ts','flank-source-motion.ts'])
  fs.writeFileSync(`${baselineDir}/${name}`,execFileSync('git',['show',`v0.11.42-rc.1:app/lib/${name}`],{maxBuffer:32*1024*1024}))
fs.writeFileSync(`${baselineDir}/odin.glb`,execFileSync('git',['show','v0.11.42-rc.1:public/models/odin.glb'],{maxBuffer:32*1024*1024}))
const {createOdinRig:beforeRig}=await import(pathToFileURL(path.resolve(`${baselineDir}/odin-rig.ts`)))

function setup(path, create) {
  const bytes=fs.readFileSync(path),asset=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString())
  const objects=asset.nodes.map(n=>{
    const o=new THREE.Object3D();o.name=n.name;o.userData=n.extras||{}
    if(n.matrix)new THREE.Matrix4().fromArray(n.matrix).decompose(o.position,o.quaternion,o.scale)
    if(n.translation)o.position.fromArray(n.translation)
    if(n.rotation)o.quaternion.fromArray(n.rotation)
    if(n.scale)o.scale.fromArray(n.scale)
    return o
  })
  asset.nodes.forEach((n,i)=>n.children?.forEach(j=>objects[i].add(objects[j])))
  const root=new THREE.Group();asset.scenes[asset.scene||0].nodes.forEach(i=>root.add(objects[i]))
  return {root,objects,rig:create(root)}
}
const before=setup(`${baselineDir}/odin.glb`,beforeRig),after=setup('public/models/odin.glb',createOdinRig)
const family=name=>name.startsWith('PDC_')?'quad':/^(Defense_0[5-8]_|DefenseRail_Aft_)/.test(name)?'aftTwin':undefined
const joints=after.objects.filter(o=>o.userData.staticJoint),affected=joints.filter(o=>family(o.name))
let maxPosePathError=0,maxUnaffectedWorldError=0,samples=0
for(const time of [0,20,100])for(let n=0;n<=400;n++) {
  const d=n/400;after.rig.apply(d,time);after.root.updateMatrixWorld(true)
  for(const kind of ['quad','aftTwin',undefined]) {
    before.rig.apply(kind?turretPoseProgress(d,kind):d,time);before.root.updateMatrixWorld(true)
    for(const o of joints.filter(o=>family(o.name)===kind)) {
      const a=before.root.getObjectByName(o.name).matrixWorld.elements,b=o.matrixWorld.elements
      const error=Math.max(...a.map((x,k)=>Math.abs(x-b[k])))
      assert.ok(error<1e-8,`${o.name} changes its accepted path at ${d}`)
      if(kind)maxPosePathError=Math.max(maxPosePathError,error)
      else maxUnaffectedWorldError=Math.max(maxUnaffectedWorldError,error)
    }
  }
  samples++
}
const rows=[]
for(const progress of [...Array.from({length:401},(_,i)=>i/400),...Array.from({length:41},(_,i)=>1-i/40)]) {
  after.rig.apply(progress,20);after.root.updateMatrixWorld(true)
  rows.push({progress,quadProgress:turretPoseProgress(progress,'quad'),aftProgress:turretPoseProgress(progress,'aftTwin'),
    joints:affected.map(o=>({name:o.name,position:o.position.toArray(),quaternion:o.quaternion.toArray()}))})
}
fs.writeFileSync('work/v01143-review/runtime-poses.json',JSON.stringify(rows))

function speedEvidence(scene,name) {
  const o=scene.root.getObjectByName(name)
  scene.rig.apply(0,0);const start=o.position.clone()
  scene.rig.apply(1,0);const end=o.position.clone(),distance=end.distanceTo(start)
  let previous=start,peakSpeed=0,tenth, ninetieth
  for(let n=0;n<=2000;n++) {
    const d=n/2000;scene.rig.apply(d,0)
    const fraction=o.position.distanceTo(start)/distance
    if(tenth===undefined&&fraction>=.1)tenth=d*6.5
    if(ninetieth===undefined&&fraction>=.9)ninetieth=d*6.5
    if(n)peakSpeed=Math.max(peakSpeed,o.position.distanceTo(previous)*2000/6.5)
    previous=o.position.clone()
  }
  return {stroke:distance,peakSpeedModelUnitsPerSecond:peakSpeed,tenToNinetySeconds:ninetieth-tenth}
}
const speedChecks=['PDC_Starboard_Arm_0','PDC_Starboard_Carriage','Defense_05_NotchGate','Defense_05_Carriage'].map(name=>({
  name,before:speedEvidence(before,name),after:speedEvidence(after,name)
}))
const profile=JSON.parse(fs.readFileSync('app/lib/turret-tempo-profile.json'))
const report={version:'0.11.43',baseline:'0.11.42',affectedJoints:affected.length,unaffectedJoints:joints.length-affected.length,
  samples,maxPosePathError,maxUnaffectedWorldError,allAcceptedPosePathsPreserved:true,allOtherMotionUnchanged:true,
  runtimeMeshSweepPoses:rows.length,profile,speedChecks}
fs.writeFileSync('docs/review/v0.11.43/tempo-verification.json',JSON.stringify(report,null,2)+'\n')
console.log(report)
