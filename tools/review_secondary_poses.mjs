import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
const version = process.argv[2] || '0.10.0'
const path = new URL(`../work/v${version.replaceAll('.', '')}-review/`, import.meta.url)
fs.mkdirSync(path, { recursive: true })
let graph
if (process.argv.includes('--exported')) {
  const file = fs.readFileSync(new URL('../public/models/odin.glb', import.meta.url))
  const asset = JSON.parse(file.subarray(20,20+file.readUInt32LE(12)).toString())
  const parents = new Map()
  asset.nodes.forEach((n,i)=>n.children?.forEach(c=>parents.set(c,i)))
  graph = asset.nodes.map((n,i)=>({name:n.name,parent:asset.nodes[parents.get(i)]?.name,extras:n.extras||{},matrix:n.matrix||new THREE.Matrix4().compose(new THREE.Vector3(...(n.translation||[0,0,0])),new THREE.Quaternion(...(n.rotation||[0,0,0,1])),new THREE.Vector3(...(n.scale||[1,1,1]))).toArray()}))
} else {
  graph = JSON.parse(fs.readFileSync(new URL('rig-nodes.json', path), 'utf8'))
}
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
