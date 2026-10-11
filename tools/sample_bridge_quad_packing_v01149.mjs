// Record actual Nuxt poses and compare every unaffected joint to v0.11.48.
import fs from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { turretPoseProgress } from '../app/lib/turret-tempo.ts'
import { bridgeQuadTubeSlideAmount, bridgeQuadTubeSlideVector } from '../app/lib/bridge-quad-source-motion.ts'
const folder = 'work/v01149-review'
fs.mkdirSync(folder, { recursive: true })
let oldRig = execFileSync('git', ['show', 'v0.11.48-rc.1:app/lib/odin-rig.ts'], { encoding: 'utf8' })
for (const module of ['odin-motion', 'bow-source-motion', 'stern-source-motion', 'flank-source-motion', 'turret-tempo']) {
  oldRig = oldRig.replaceAll(`'./${module}.ts'`, `'../../app/lib/${module}.ts'`).replaceAll(`'./${module}'`, `'../../app/lib/${module}.ts'`)
}
fs.writeFileSync(`${folder}/baseline-rig.ts`, oldRig)
fs.writeFileSync(`${folder}/bridge-quad-source-motion.ts`, execFileSync('git', ['show', 'v0.11.48-rc.1:app/lib/bridge-quad-source-motion.ts'], { encoding: 'utf8' }).replace("'./odin-motion.ts'", "'../../app/lib/odin-motion.ts'"))
const { createOdinRig: baselineRig } = await import('../work/v01149-review/baseline-rig.ts')
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
const affected = new Set(['Port', 'Starboard'].flatMap(s => Array.from({length:4}, (_, i) => [`PDC_${s}_Cradle_${i}`, `PDC_${s}_Arm_${i}`]).flat()))
const samples = [], baselineSamples = []
let maxUnchangedJointWorldError = 0, maxAxialScheduleError = 0, maxRotationError = 0
current.rig.apply(1, 20)
const armRest = new Map(currentJoints.filter(o => /^PDC_.*_Arm_\d$/.test(o.name)).map(o => [o.name, o.position.clone()]))
const progressValues = [...Array.from({length:151},(_,i)=>i/300), ...Array.from({length:51},(_,i)=>.5+i/100), ...Array.from({length:31},(_,i)=>1-i/30)]
function snapshot(data, progress) {
  return {progress, quadProgress:turretPoseProgress(progress,'quad'), joints:data.objects.filter(o=>o.userData.staticJoint&&o.name.startsWith('PDC_')).map(o=>({name:o.name,position:o.position.toArray(),quaternion:o.quaternion.toArray()}))}
}
for (const progress of progressValues) {
  current.rig.apply(progress, 20); previous.rig.apply(progress, 20)
  current.root.updateMatrixWorld(true); previous.root.updateMatrixWorld(true)
  for (const joint of currentJoints) {
    const old = previousJoints.get(joint.name)
    if (!affected.has(joint.name)) maxUnchangedJointWorldError = Math.max(maxUnchangedJointWorldError, ...joint.matrixWorld.elements.map((v,i)=>Math.abs(v-old.matrixWorld.elements[i])))
    if (/^PDC_.*_Arm_\d$/.test(joint.name)) {
      const [x,y,z] = bridgeQuadTubeSlideVector(joint.userData)
      const expected = armRest.get(joint.name).clone().add(new THREE.Vector3(x,z,-y).multiplyScalar(bridgeQuadTubeSlideAmount(progress)))
      maxAxialScheduleError = Math.max(maxAxialScheduleError,joint.position.distanceTo(expected))
    }
    maxRotationError = Math.max(maxRotationError, joint.quaternion.angleTo(old.quaternion))
  }
  samples.push(snapshot(current,progress)); baselineSamples.push(snapshot(previous,progress))
}
const hash = path => createHash('sha256').update(fs.readFileSync(path)).digest('hex')
const report = {version:'v0.11.49-rc.1',baseline:'v0.11.48-rc.1',samples:samples.length,unchangedWorldJoints:currentJoints.length-affected.size,affectedJoints:[...affected],maxUnchangedJointWorldError,maxAxialScheduleError,maxRotationError,modelPacking:{horizontalBefore:1.98,horizontalAfter:.495,verticalBefore:.30,verticalAfter:.32},axialSeating:{previousTravel:14.40237037037037,newTravel:22.40237037037037,extensionTimelineInterval:[.08,.69],reason:'Shallow packing leaves receivers outside the casing, requiring clearance behind the fitted closing skins.'},codeHashes:{motionHelper:hash('app/lib/bridge-quad-source-motion.ts'),rig:hash('app/lib/odin-rig.ts'),tempo:hash('app/lib/turret-tempo-profile.json')},assetHashes:{high:hash('public/models/odin.glb'),lite:hash('public/models/odin-lite.glb')}}
fs.writeFileSync(`${folder}/runtime-poses.json`,JSON.stringify(samples))
fs.writeFileSync(`${folder}/baseline-poses.json`,JSON.stringify(baselineSamples))
fs.mkdirSync('docs/review/v0.11.49',{recursive:true});fs.writeFileSync('docs/review/v0.11.49/motion-verification.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report))
if(maxUnchangedJointWorldError>1e-9||maxAxialScheduleError>1e-9||maxRotationError>1e-7)process.exitCode=1
