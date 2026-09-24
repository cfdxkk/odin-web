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
for (const name of ['Odin_Asset', 'Main_Dorsal_Barrels', 'Main_Ventral_Barrels', 'Hatch_Dorsal_Port', 'Hatch_Ventral_Starboard', 'Main_Dorsal_Tube_Port', 'Main_Dorsal_Tube_Center', 'Main_Ventral_Tube_Center', 'Main_Ventral_Tube_Starboard', 'Axial_Bow_Shutter_Port', 'Axial_Stern_Shutter_Starboard', 'Axial_Keel_Shutter_Port', 'PDC_Port_Arm_0', 'PDC_Starboard_Arm_3', 'PDC_Port_Gimbal', 'PDC_Starboard_Gimbal', 'Defense_08_Elevation', 'SternHangarDoor']) assert.ok(names.has(name), `Required part ${name}`)
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
assert.equal(asset.nodes.filter(n => n.extras?.system === 'axial-shutter' && n.extras?.staticJoint).length, 6, 'Original shutters on all three axial batteries')
const tubes = asset.nodes.filter(n => n.extras?.system === 'main-telescope' && n.extras?.staticJoint)
assert.equal(tubes.length, 6, 'All three tubes telescope on both main batteries')
for (const tube of tubes) {
  assert.ok(vector(tube.extras.boreAxis) && new THREE.Vector3(...tube.extras.boreAxis).length() > .99, `${tube.name} has a measured bore axis`)
  assert.ok(vector(tube.extras.deployedOffset), `${tube.name} preserves its deployed endpoint`)
  assert.equal(tube.extras.stowTravel, 16, `${tube.name} has the shared telescope stroke`)
  assert.ok(tube.children?.some(index => asset.nodes[index].mesh !== undefined), `${tube.name} carries actual barrel geometry`)
}
const stern = asset.nodes.find(n => n.name === 'SternHangarDoor')
assert.ok(stern.children.some(index => asset.nodes[index].mesh !== undefined), 'Aft door contains actual visible geometry')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'bridge-armor' && n.extras?.staticJoint).length, 45, '45 articulated bridge armor slats')
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
assert.ok(file.length < 25 * 1024 * 1024, 'Desktop asset fits the static host 25 MiB per-file budget')
console.log(JSON.stringify({ model, valid: true, sizeMB: +(file.length / 1024 / 1024).toFixed(2), meshes: asset.meshes.length, materials: asset.materials.length, embeddedTextures: asset.images.length, animationClips: 0 }, null, 2))
}
