// Sample the actual Nuxt rig for the forward-twin mesh clearance audit.
// Run from the repository root with: node --experimental-strip-types tools/sample_forward_twins_v01138.mjs
import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'

const bytes = fs.readFileSync('public/models/odin.glb')
const asset = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString())
const objects = asset.nodes.map(node => {
  const object = new THREE.Object3D()
  object.name = node.name
  object.userData = node.extras || {}
  if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(object.position, object.quaternion, object.scale)
  if (node.translation) object.position.fromArray(node.translation)
  if (node.rotation) object.quaternion.fromArray(node.rotation)
  if (node.scale) object.scale.fromArray(node.scale)
  return object
})
asset.nodes.forEach((node, i) => node.children?.forEach(child => objects[i].add(objects[child])))
const root = new THREE.Group()
asset.scenes[asset.scene || 0].nodes.forEach(i => root.add(objects[i]))
const rig = createOdinRig(root)
const joints = objects.filter(object => object.userData.staticJoint && object.name.startsWith('Defense'))
const samples = []
function capture(progress, time) {
  rig.apply(progress, time)
  root.updateMatrixWorld(true)
  samples.push({ progress, time, joints: joints.map(object => ({ name: object.name, position: object.position.toArray(), quaternion: object.quaternion.toArray() })) })
}
for (const progress of [...Array.from({length:401}, (_, i) => i / 400), ...Array.from({length:11}, (_, i) => 1 - i / 10)]) capture(progress, 20)
for (const time of [0, 10, 40, 80]) capture(1, time)
fs.mkdirSync('work/v01138-review', {recursive:true})
fs.writeFileSync('work/v01138-review/runtime-poses.json', JSON.stringify(samples))
console.log('Actual runtime poses:', samples.length)
