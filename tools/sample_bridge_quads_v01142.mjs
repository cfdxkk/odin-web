// Capture actual Nuxt joint poses for the native mesh sweep.
import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
const bytes=fs.readFileSync('public/models/odin.glb')
const asset=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString())
const objects=asset.nodes.map(n=>{const o=new THREE.Object3D();o.name=n.name;o.userData=n.extras||{};if(n.matrix)new THREE.Matrix4().fromArray(n.matrix).decompose(o.position,o.quaternion,o.scale);if(n.translation)o.position.fromArray(n.translation);if(n.rotation)o.quaternion.fromArray(n.rotation);if(n.scale)o.scale.fromArray(n.scale);return o})
asset.nodes.forEach((n,i)=>n.children?.forEach(j=>objects[i].add(objects[j])))
const root=new THREE.Group();asset.scenes[asset.scene||0].nodes.forEach(i=>root.add(objects[i]))
const rig=createOdinRig(root),joints=objects.filter(o=>o.userData.staticJoint&&o.name.startsWith('PDC_'))
const samples=[]
for(const progress of [...Array.from({length:401},(_,i)=>i/400),...Array.from({length:41},(_,i)=>1-i/40)]){
 rig.apply(progress,20);root.updateMatrixWorld(true)
 samples.push({progress,joints:joints.map(o=>({name:o.name,position:o.position.toArray(),quaternion:o.quaternion.toArray()}))})
}
fs.writeFileSync('work/v01142-review/runtime-poses.json',JSON.stringify(samples))
console.log('Quad runtime samples',samples.length)
