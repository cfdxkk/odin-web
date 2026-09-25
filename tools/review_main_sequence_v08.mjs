// Capture twelve poses from the actual runtime rig and the exported GLB joints.
// This is review data only: no keyframes or animation clips are written to assets.
import fs from 'node:fs'
import crypto from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const assetPath = path.join(project, 'public/models/odin.glb')
const manifestPath = path.join(project, 'public/models/asset-manifest.json')
const outDir = path.join(project, 'work/v08-review')
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
if (manifest.version !== '0.8.0') {
  throw new Error(`Expected exported v0.8.0 asset, found ${manifest.version}. Export the review asset first.`)
}

const bytes = fs.readFileSync(assetPath)
if (bytes.toString('ascii', 0, 4) !== 'glTF') throw new Error(`${assetPath} is not a binary GLB`)
const jsonLength = bytes.readUInt32LE(12)
const gltf = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString('utf8'))
if (gltf.animations?.length) throw new Error('Review GLB unexpectedly contains animation clips')
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
if (!joints.some(object => object.name === 'Main_Dorsal_Mount')) {
  throw new Error('The exported GLB does not contain the dorsal main-battery joints')
}
if (new Set(joints.map(object => object.name)).size !== joints.length) {
  throw new Error('Static joint names must be unique for Blender pose matching')
}

const stages = [
  [0, '完全收拢'],
  [.05, '护甲脱开接缝'],
  [.10, '前盖前移／后片外翻'],
  [.16, '主护甲向外让位'],
  [.22, '后片沿斜轴下翻'],
  [.30, '护甲接近展开终点'],
  [.34, '护甲让位完成'],
  [.45, '炮管调平'],
  [.60, '炮塔升起'],
  [.75, '三根炮管同步伸出'],
  [.90, '炮管接近伸出终点'],
  [1, 'SCM／战斗模式'],
]
const poses = stages.map(([deployment, label], index) => {
  rig.apply(deployment, 20)
  return {
    index: index + 1,
    deployment,
    label,
    file: `frame-${String(index + 1).padStart(2, '0')}-d${deployment.toFixed(2)}.png`,
    joints: joints.map(object => ({
      name: object.name,
      position: object.position.toArray(),
      quaternion: object.quaternion.toArray(),
    })),
  }
})
fs.mkdirSync(outDir, { recursive: true })
fs.writeFileSync(path.join(outDir, 'poses.json'), JSON.stringify({
  source: 'app/lib/odin-rig.ts + public/models/odin.glb',
  assetVersion: manifest.version,
  glbSha256: crypto.createHash('sha256').update(bytes).digest('hex'),
  jointCount: rig.jointCount,
  poses,
}, null, 2) + '\n')
console.log(`Saved ${poses.length} runtime poses from ${rig.jointCount} joints to ${path.join(outDir, 'poses.json')}`)
