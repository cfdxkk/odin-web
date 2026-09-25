import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
const path = new URL('../work/v090-review/', import.meta.url)
const graph = JSON.parse(fs.readFileSync(new URL('rig-nodes.json', path), 'utf8'))
const nodes = new Map(graph.map(n => {
  const o = new THREE.Object3D(); o.name = n.name; o.userData = n.extras
  new THREE.Matrix4().fromArray(n.matrix).decompose(o.position, o.quaternion, o.scale)
  return [n.name, o]
}))
const root = new THREE.Group()
for (const n of graph) (nodes.get(n.parent) || root).add(nodes.get(n.name))
const rig = createOdinRig(root)
const poses = Array.from({ length: 101 }, (_, i) => {
  rig.apply(i / 100, 20)
  return { deployment: i / 100, joints: [...nodes.values()].filter(n => n.userData.staticJoint).map(n => ({ name: n.name, position: n.position.toArray(), quaternion: n.quaternion.toArray() })) }
})
fs.writeFileSync(new URL('candidate-poses.json', path), JSON.stringify(poses))
console.log(`Sampled 101 actual JS poses across ${rig.jointCount} joints`)
