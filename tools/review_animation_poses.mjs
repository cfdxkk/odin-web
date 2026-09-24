// Capture real Nuxt/Three rig poses for a local animation review. No GLB clips.
// Node 24+: node tools/review_animation_poses.mjs --version 0.8.1
import fs from 'node:fs'
import crypto from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'

const { values } = parseArgs({ options: {
  version: { type: 'string' },
  'work-dir': { type: 'string' },
  help: { type: 'boolean', short: 'h' },
} })
if (values.help) {
  console.log('Usage: node tools/review_animation_poses.mjs --version 0.8.1 [--work-dir work/preview-v0.8.1]')
  process.exit(0)
}
if (!/^\d+\.\d+\.\d+(?:-[\w.-]+)?$/.test(values.version || '')) {
  throw new Error('Pass --version with the exported asset version, for example 0.8.1')
}
const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const assetPath = path.join(project, 'public/models/odin.glb')
const rigPath = path.join(project, 'app/lib/odin-rig.ts')
const blendPath = path.join(project, `assets/blender/odin_articulated_v${values.version}.blend`)
const manifest = JSON.parse(fs.readFileSync(path.join(project, 'public/models/asset-manifest.json'), 'utf8'))
if (manifest.version !== values.version) {
  throw new Error(`Requested v${values.version}, exported manifest is v${manifest.version}; export first`)
}
const outDir = path.resolve(project, values['work-dir'] || `work/preview-v${values.version}`)
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')
const bytes = fs.readFileSync(assetPath)
if (bytes.toString('ascii', 0, 4) !== 'glTF') throw new Error('Asset is not a binary GLB')
const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'))
if (gltf.animations?.length) throw new Error('Asset unexpectedly contains animation clips')
const nodes = gltf.nodes.map(node => {
  const object = new THREE.Object3D()
  object.name = node.name || ''
  object.userData = node.extras || {}
  if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(object.position, object.quaternion, object.scale)
  if (node.translation) object.position.fromArray(node.translation)
  if (node.rotation) object.quaternion.fromArray(node.rotation)
  if (node.scale) object.scale.fromArray(node.scale)
  return object
})
gltf.nodes.forEach((node, i) => node.children?.forEach(child => nodes[i].add(nodes[child])))
const root = new THREE.Group()
gltf.scenes[gltf.scene || 0].nodes.forEach(index => root.add(nodes[index]))
const rig = createOdinRig(root)
const joints = nodes.filter(object => object.userData.staticJoint)
if (!joints.some(object => object.name === 'Main_Dorsal_Mount')) throw new Error('Missing dorsal main-battery joints')
if (new Set(joints.map(object => object.name)).size !== joints.length) throw new Error('Duplicate static joint names')
const poses = Array.from({ length: 101 }, (_, index) => {
  const deployment = index / 100
  rig.apply(deployment, 20)
  return {
    index, deployment, file: `frame-${String(index).padStart(4, '0')}.png`,
    joints: joints.map(object => ({ name: object.name, position: object.position.toArray(), quaternion: object.quaternion.toArray() })),
  }
})
fs.mkdirSync(outDir, { recursive: true })
fs.writeFileSync(path.join(outDir, 'poses.json'), JSON.stringify({
  source: 'app/lib/odin-rig.ts + public/models/odin.glb',
  assetVersion: manifest.version,
  glbSha256: sha(assetPath), rigSha256: sha(rigPath), blendSha256: sha(blendPath),
  jointCount: rig.jointCount, poses,
}, null, 2) + '\n')
console.log(`Saved ${poses.length} actual runtime poses (${rig.jointCount} joints) to ${outDir}`)
