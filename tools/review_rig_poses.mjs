// Evaluate the actual web rig against the exported node hierarchy; no animation export.
import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
const bytes = fs.readFileSync(new URL('../public/models/odin.glb', import.meta.url))
const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString())
const nodes = gltf.nodes.map(node => {
  const o = new THREE.Object3D(); o.name = node.name; o.userData = node.extras || {}
  if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(o.position, o.quaternion, o.scale)
  if (node.translation) o.position.fromArray(node.translation)
  if (node.rotation) o.quaternion.fromArray(node.rotation)
  if (node.scale) o.scale.fromArray(node.scale)
  return o
})
gltf.nodes.forEach((node, i) => node.children?.forEach(child => nodes[i].add(nodes[child])))
const root = new THREE.Group(); gltf.scenes[gltf.scene || 0].nodes.forEach(i => root.add(nodes[i]))
const rig = createOdinRig(root)
const poses = [0, .25, .5, .75, 1].map(deployment => {
  rig.apply(deployment, 20)
  return { deployment, joints: nodes.filter(n => n.userData.staticJoint).map(n => ({ name: n.name, position: n.position.toArray(), quaternion: n.quaternion.toArray() })) }
})
fs.mkdirSync(new URL('../work/rig-review/', import.meta.url), { recursive: true })
fs.writeFileSync(new URL('../work/rig-review/poses.json', import.meta.url), JSON.stringify(poses))
console.log(`Reviewing ${rig.jointCount} static joints at ${poses.length} deployment stages`)
