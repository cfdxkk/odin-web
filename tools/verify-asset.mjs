import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import * as THREE from 'three'
const manifest = JSON.parse(readFileSync(new URL('../public/models/asset-manifest.json', import.meta.url)))
for (const model of ['odin.glb', 'odin-lite.glb']) {
const file = readFileSync(new URL(`../public/models/${model}`, import.meta.url))
assert.equal(file.readUInt32LE(0), 0x46546c67, 'GLB header')
assert.equal(file.readUInt32LE(4), 2, 'glTF 2.0')
assert.equal(file.readUInt32LE(8), file.length, 'complete file length')
const asset = JSON.parse(file.subarray(20, 20 + file.readUInt32LE(12)).toString())
assert.equal(asset.animations?.length || 0, 0, 'All animation must remain in Nuxt JavaScript')
assert.equal(asset.cameras?.length || 0, 0, 'No Blender camera exported')
assert.ok(!asset.nodes.some(n => /perseus/i.test(n.name)), 'Other ships excluded')
const names = new Set(asset.nodes.map(n => n.name))
for (const name of ['Odin_Asset', 'Main_Dorsal_Barrels', 'Main_Ventral_Barrels', 'Hatch_Dorsal_Port', 'Hatch_Ventral_Starboard', 'Main_Dorsal_Tube_Port', 'Main_Dorsal_Tube_Center', 'Main_Ventral_Tube_Center', 'Main_Ventral_Tube_Starboard', 'Axial_Bow_SourceReceiver', 'Axial_Stern_Shutter_Starboard_02', 'Axial_Keel_Shutter_Port_01', 'PDC_Port_Arm_0', 'PDC_Starboard_Arm_3', 'PDC_Port_Gimbal', 'PDC_Starboard_Gimbal', 'Defense_08_Elevation', 'SternHangarDoor']) assert.ok(names.has(name), `Required part ${name}`)
assert.ok(![...names].some(name => name.startsWith('Axial_Bow_Shutter_') || name.startsWith('Axial_Bow_FrontCap')), 'Bow is restored before rebuilding its armor')
assert.deepEqual(asset.nodes.find(n => n.name === 'Axial_Bow_SourceReceiver').extras.receiverShiftModel.map(x => +x.toFixed(2)), [0, 3.45, 0.55], 'Only the source bow receiver moves rigidly to the turret edge')
assert.ok(!('rearShoulderLiftModel' in asset.nodes.find(n => n.name === 'Axial_Bow_SourceReceiver').extras), 'Source bow receiver geometry must remain undeformed')
assert.ok(![...names].some(name => name.startsWith('Axial_Bow_SeamFairing')), 'Reject the unrequested added bow shoulder geometry')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'main-hatch' && n.extras?.staticJoint).length, 10, 'Five articulated main armor plates per battery')
const vector = value => Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)
for (const plate of asset.nodes.filter(n => n.extras?.system === 'main-hatch')) {
  assert.ok(vector(plate.extras.slideVector), `${plate.name} has a static displacement vector`)
  assert.ok(plate.extras.closedOutlineXY.length >= 6, `${plate.name} uses a polygonal hull contour`)
  if (plate.extras.armorRole === 'aft') {
    assert.ok(vector(plate.extras.hingeAxis) && new THREE.Vector3(...plate.extras.hingeAxis).length() > .99, `${plate.name} has a fixed sloped hinge axis`)
    assert.equal(Math.abs(plate.extras.openingAngleDegrees), 130, `${plate.name} opens 130 degrees`)
    assert.deepEqual(plate.extras.slideVector, [0, 0, 0], `${plate.name} must hinge rather than slide`)
    assert.ok(Array.isArray(plate.extras.hingeEdge) && plate.extras.hingeEdge.length === 2 && plate.extras.hingeEdge.every(vector), `${plate.name} identifies both fixed hinge endpoints`)
    assert.equal(plate.extras.hullFacesRemoved, 0, `${plate.name} preserves the fixed hull`)
  } else {
    assert.equal(plate.extras.hingeAxis, undefined, `${plate.name} must translate without hinging`)
    if (plate.extras.armorRole === 'side') {
      assert.ok(vector(plate.extras.guideExit) && vector(plate.extras.guidePocket), `${plate.name} retains its static guide metadata`)
      assert.ok(vector(plate.extras.clearanceLift), `${plate.name} has a finite three-axis serration-clearance lift`)
    } else assert.ok(vector(plate.extras.liftVector) && plate.extras.sourceObject, `${plate.name} has an independent short fore-end cap`)
  }
}
assert.equal(asset.nodes.filter(n => n.extras?.barrelJoint && n.extras?.staticJoint).length, 60, 'All other single-battery shutter joints remain')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'single-front-cap').length, 6)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'side-front-slider').length, 8)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'side-battery-carriage').length, 4)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'side-battery-leaf').length, 24)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'pdc-hull-petal').length, 8)
assert.equal(asset.nodes.filter(n => n.extras?.singleBattery).length, 11)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'defense-gate').length, 4)
for (const side of ['Port', 'Starboard']) assert.equal(asset.nodes.find(n => n.name === `PDC_${side}_Gimbal`).extras.fixedRootArmorPieces, 4)
const tubes = asset.nodes.filter(n => n.extras?.system === 'main-telescope' && n.extras?.staticJoint)
const carriages = asset.nodes.filter(n => n.extras?.system === 'main-bore-carriage' && n.extras?.staticJoint)
assert.equal(carriages.length, 6, 'Three independently positioned complete bore carriages per battery')
for (const bank of ['Dorsal', 'Ventral']) for (const role of ['Port', 'Center', 'Starboard']) {
  const name = `Main_${bank}_Carrier_${role}`
  const carriage = carriages.find(n => n.name === name)
  assert.ok(carriage && vector(carriage.extras.stowOffset), `${name} has a measured stow displacement`)
  const coverRole = bank === 'Ventral' && role !== 'Center' ? (role === 'Port' ? 'Starboard' : 'Port') : role
  assert.equal(carriage.extras.followShroud, `Main_${bank}_Shroud_${coverRole}`, `${name} follows its physically corresponding cover`)
  assert.ok(carriage.children?.some(index => asset.nodes[index].mesh !== undefined), `${name} carries the original breech and collar geometry`)
  assert.ok(carriage.children?.some(index => asset.nodes[index].name === `Main_${bank}_Tube_${role}`), `${name} carries its telescopic bore`)
}
assert.equal(tubes.length, 6, 'All three tubes telescope on both main batteries')
for (const tube of tubes) {
  assert.ok(vector(tube.extras.boreAxis) && new THREE.Vector3(...tube.extras.boreAxis).length() > .99, `${tube.name} has a measured bore axis`)
  assert.ok(vector(tube.extras.deployedOffset), `${tube.name} preserves its deployed endpoint`)
  assert.equal(tube.extras.stowTravel, 20, `${tube.name} has the shared telescope stroke with hull-lip clearance`)
  assert.ok(tube.children?.some(index => asset.nodes[index].mesh !== undefined), `${tube.name} carries actual barrel geometry`)
}
const stern = asset.nodes.find(n => n.name === 'SternHangarDoor')
assert.ok(stern.children.some(index => asset.nodes[index].mesh !== undefined), 'Aft door contains actual visible geometry')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'bridge-armor' || n.name.startsWith('BridgeArmor_')).length, 0, 'Bridge armor removed; fixed windows retained')
assert.equal(asset.nodes.filter(n => /^SideBattery_\d_(Port|Starboard)$/.test(n.name)).length, 8, 'Eight independently mirrored secondary batteries')
assert.ok(asset.materials.some(m => m.normalTexture), 'Source tangent normals preserved')
// Named empties alone are insufficient: they used to exist but all had origin (0,0,0).
const nodes = asset.nodes.map(n => {
  const object = new THREE.Object3D()
  if (n.matrix) new THREE.Matrix4().fromArray(n.matrix).decompose(object.position, object.quaternion, object.scale)
  if (n.translation) object.position.fromArray(n.translation)
  if (n.rotation) object.quaternion.fromArray(n.rotation)
  if (n.scale) object.scale.fromArray(n.scale)
  return object
})
asset.nodes.forEach((n, i) => n.children?.forEach(c => nodes[i].add(nodes[c])))
for (let i = 0; i < 13; i++) {
  const name = `EngineCore_${String(i).padStart(2, '0')}`
  const index = asset.nodes.findIndex(n => n.name === name)
  assert.ok(index >= 0, `Engine ${i}`)
  const expected = new THREE.Vector3().fromArray(manifest.engineAnchors[i].position)
  const actual = nodes[index].getWorldPosition(new THREE.Vector3())
  assert.ok(actual.distanceTo(expected) < .001, `${name} must coincide with its nozzle, got ${actual.toArray()}`)
}
assert.ok(asset.images?.length > 0 && asset.images.every(i => i.bufferView !== undefined), 'Textures embedded for portable loading')
assert.ok(asset.materials?.length > 0, 'PBR materials present')
const paintIndex = asset.materials.findIndex(m => m.name === 'Odin_Antenna_Painted_Wrap')
assert.ok(paintIndex >= 0, 'Antenna paint material is present')
const paintTexture = asset.materials[paintIndex].pbrMetallicRoughness.baseColorTexture
assert.ok(paintTexture, 'The antenna band is an embedded texture')
const paintedPrimitives = asset.meshes.flatMap(m => m.primitives).filter(p => p.material === paintIndex)
assert.ok(paintedPrimitives.length > 0 && paintedPrimitives.every(p => p.attributes[`TEXCOORD_${paintTexture.texCoord || 0}`] !== undefined), 'The batched antennas retain the UV channel used by their wraparound band')
assert.ok(file.length < 25 * 1024 * 1024, 'Desktop asset fits the static host 25 MiB per-file budget')
console.log(JSON.stringify({ model, valid: true, sizeMB: +(file.length / 1024 / 1024).toFixed(2), meshes: asset.meshes.length, materials: asset.materials.length, embeddedTextures: asset.images.length, animationClips: 0 }, null, 2))
}
