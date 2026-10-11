// Compare the actual Nuxt rig against v0.11.51, including compensated guides.
import fs from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { turretPoseProgress } from '../app/lib/turret-tempo.ts'
import { bridgeQuadTubeSlideAmount, bridgeQuadTubeSlideVector, bridgeQuadTubePackingAmount, bridgeQuadTubeCompactVector, bridgeQuadBearingPackingOffset } from '../app/lib/bridge-quad-source-motion.ts'

const folder = 'work/v01152-review', target = 'docs/review/v0.11.52', baseline = 'v0.11.51-rc.1'
fs.mkdirSync(folder, { recursive: true })
let oldRig = execFileSync('git', ['show', `${baseline}:app/lib/odin-rig.ts`], { encoding: 'utf8' })
for (const module of ['odin-motion', 'bow-source-motion', 'stern-source-motion', 'flank-source-motion', 'turret-tempo']) {
  oldRig = oldRig.replaceAll(`'./${module}.ts'`, `'../../app/lib/${module}.ts'`).replaceAll(`'./${module}'`, `'../../app/lib/${module}.ts'`)
}
fs.writeFileSync(`${folder}/baseline-rig.ts`, oldRig)
fs.writeFileSync(`${folder}/bridge-quad-source-motion.ts`, execFileSync('git', ['show', `${baseline}:app/lib/bridge-quad-source-motion.ts`], { encoding: 'utf8' }).replace("'./odin-motion.ts'", "'../../app/lib/odin-motion.ts'"))
const { createOdinRig: baselineRig } = await import('../work/v01152-review/baseline-rig.ts')
const bytes = fs.readFileSync('public/models/odin.glb')
const asset = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
function load(create) {
  const objects = asset.nodes.map(n => {
    const o = new THREE.Object3D(); o.name = n.name; o.userData = n.extras || {}
    if (n.matrix) new THREE.Matrix4().fromArray(n.matrix).decompose(o.position, o.quaternion, o.scale)
    if (n.translation) o.position.fromArray(n.translation)
    if (n.rotation) o.quaternion.fromArray(n.rotation)
    if (n.scale) o.scale.fromArray(n.scale)
    return o
  })
  asset.nodes.forEach((n, i) => n.children?.forEach(j => objects[i].add(objects[j])))
  const root = new THREE.Group(); asset.scenes[asset.scene || 0].nodes.forEach(i => root.add(objects[i]))
  return { root, objects, rig: create(root) }
}
const current = load(createOdinRig), previous = load(baselineRig)
const currentJoints = current.objects.filter(o => o.userData.staticJoint)
const previousJoints = new Map(previous.objects.filter(o => o.userData.staticJoint).map(o => [o.name, o]))
const affected = new Set(['Port', 'Starboard'].flatMap(s => Array.from({ length: 4 }, (_, i) => [`PDC_${s}_Cradle_${i}`, `PDC_${s}_Arm_${i}`]).flat()))
const mountedSupports = ['Port', 'Starboard'].map(s => `PDC_${s}_OriginalSupport`)
const samples = [], baselineSamples = []
let maxUnchangedJointWorldError = 0, maxArmPoseError = 0, maxAxialScheduleError = 0, maxRotationError = 0, maxDeployedWorldError = 0, maxEarlySpread = 0, maxSupportMountingError = 0
current.rig.apply(1, 20)
const armRest = new Map(currentJoints.filter(o => /^PDC_.*_Arm_\d$/.test(o.name)).map(o => [o.name, o.position.clone()]))
current.rig.apply(0, 20)
const closedPacking = new Map(currentJoints.filter(o => affected.has(o.name)).map(o => [o.name, o.position.clone()]))
const progressValues = [...Array.from({ length: 151 }, (_, i) => i / 300), ...Array.from({ length: 51 }, (_, i) => .5 + i / 100), ...Array.from({ length: 31 }, (_, i) => 1 - i / 30)]
const map = ([x, y, z]) => new THREE.Vector3(x, z, -y)
function snapshot(data, progress) {
  return { progress, quadProgress: turretPoseProgress(progress, 'quad'), joints: data.objects.filter(o => o.name.startsWith('PDC_') && (o.userData.staticJoint || o.name.endsWith('_OriginalSupport'))).map(o => ({ name: o.name, position: o.position.toArray(), quaternion: o.quaternion.toArray() })) }
}
for (const progress of progressValues) {
  current.rig.apply(progress, 20); previous.rig.apply(progress, 20)
  current.root.updateMatrixWorld(true); previous.root.updateMatrixWorld(true)
  for (const name of mountedSupports) {
    const fit = current.root.getObjectByName(name).position.clone().sub(previous.root.getObjectByName(name).position)
    maxSupportMountingError = Math.max(maxSupportMountingError, fit.distanceTo(new THREE.Vector3(0, -.35, 0)))
  }
  for (const joint of currentJoints) {
    const old = previousJoints.get(joint.name)
    const worldError = Math.max(...joint.matrixWorld.elements.map((value, i) => Math.abs(value - old.matrixWorld.elements[i])))
    if (!affected.has(joint.name)) maxUnchangedJointWorldError = Math.max(maxUnchangedJointWorldError, worldError)
    if (progress === 1) maxDeployedWorldError = Math.max(maxDeployedWorldError, worldError)
    if (progress <= .42 && /^PDC_.*_Arm_\d$/.test(joint.name)) {
      const delta = joint.position.clone().add(joint.parent.position).sub(closedPacking.get(joint.name)).sub(closedPacking.get(joint.parent.name))
      maxEarlySpread = Math.max(maxEarlySpread, Math.abs(delta.y), Math.abs(delta.z))
    }
    if (/^PDC_.*_Arm_\d$/.test(joint.name)) {
      const cradle = joint.parent.userData, q = turretPoseProgress(progress, 'quad')
      const relativePacking = map(bridgeQuadTubeCompactVector(cradle)).multiplyScalar(bridgeQuadTubePackingAmount(progress)).sub(map(bridgeQuadBearingPackingOffset(cradle, progress)))
      const expected = armRest.get(joint.name).clone().add(map(bridgeQuadTubeSlideVector(joint.userData)).multiplyScalar(bridgeQuadTubeSlideAmount(progress))).add(relativePacking)
      maxArmPoseError = Math.max(maxArmPoseError, joint.position.distanceTo(expected))
      maxAxialScheduleError = Math.max(maxAxialScheduleError, Math.abs(joint.position.x - old.position.x))
    }
    maxRotationError = Math.max(maxRotationError, joint.quaternion.angleTo(old.quaternion))
  }
  samples.push(snapshot(current, progress)); baselineSamples.push(snapshot(previous, progress))
}
const hash = path => createHash('sha256').update(fs.readFileSync(path)).digest('hex')
const codeHash = path => createHash('sha256').update(fs.readFileSync(path, 'utf8').replaceAll('\r\n', '\n')).digest('hex')
const report = {
  version: 'v0.11.52-rc.1', baseline, samples: samples.length, unchangedWorldJoints: currentJoints.length - affected.size, affectedJoints: [...affected],
  maxUnchangedJointWorldError, maxArmPoseError, maxAxialScheduleError, maxRotationError, maxDeployedWorldError, maxEarlySpread, mountedSupports, maxSupportMountingError,
  modelPacking: { horizontalBefore: .60, horizontalAfter: .40, tubeVerticalHalfStrokeBefore: .32, tubeVerticalHalfStrokeAfter: .65, bearingHorizontalStroke: .67, bearingVerticalHalfStroke: .32, tubeStowDatumZ: 0, bearingStowDatumZ: .20, supportSeatingZ: -.35 }, spreadingTimelineInterval: [.42, .64],
  receiverCorridor: { additionalInwardShoeTravel: 0, previousAdditionalInwardShoeTravel: 1.20, releaseTimelineInterval: [.60, .69] },
  axialSeating: { previousTravel: 22.40237037037037, newTravel: 22.40237037037037, extensionTimelineInterval: [.08, .69], unchanged: true },
  codeHashEncoding: 'UTF-8 with LF newlines', codeHashes: { motionHelper: codeHash('app/lib/bridge-quad-source-motion.ts'), rig: codeHash('app/lib/odin-rig.ts'), tempo: codeHash('app/lib/turret-tempo-profile.json') },
  assetHashes: { high: hash('public/models/odin.glb'), lite: hash('public/models/odin-lite.glb') }
}
fs.writeFileSync(`${folder}/runtime-poses.json`, JSON.stringify(samples))
fs.writeFileSync(`${folder}/baseline-poses.json`, JSON.stringify(baselineSamples))
fs.mkdirSync(target, { recursive: true }); fs.writeFileSync(`${target}/motion-verification.json`, JSON.stringify(report, null, 2) + '\n')
console.log(JSON.stringify(report))
if (maxUnchangedJointWorldError > 1e-9 || maxArmPoseError > 1e-9 || maxAxialScheduleError > 1e-9 || maxRotationError > 1e-7 || maxDeployedWorldError > 1e-9 || maxEarlySpread > 1e-9 || maxSupportMountingError > 1e-9) process.exitCode = 1
