import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { classifyWeaponJoint, WEAPON_GROUPS } from '../app/lib/odin-weapon-groups.ts'

function load(asset = 'odin.glb') {
  const bytes = fs.readFileSync(new URL(`../public/models/${asset}`, import.meta.url))
  const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const nodes = gltf.nodes.map(node => {
    const object = new THREE.Object3D()
    object.name = node.name; object.userData = node.extras || {}
    if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(object.position, object.quaternion, object.scale)
    if (node.translation) object.position.fromArray(node.translation)
    if (node.rotation) object.quaternion.fromArray(node.rotation)
    if (node.scale) object.scale.fromArray(node.scale)
    return object
  })
  gltf.nodes.forEach((node, index) => node.children?.forEach(child => nodes[index].add(nodes[child])))
  const root = new THREE.Group()
  gltf.scenes[gltf.scene || 0].nodes.forEach(index => root.add(nodes[index]))
  const original = nodes.map(node => [node.position.clone(), node.quaternion.clone()])
  return { root, nodes, original, rig: createOdinRig(root) }
}

function snapshot(scene) {
  scene.root.updateWorldMatrix(true, true)
  return new Map(scene.nodes.map(node => [node.name, node.matrixWorld.clone()]))
}
function closeMatrix(actual, expected, label) {
  const error = Math.max(...actual.elements.map((value, index) => Math.abs(value - expected.elements[index])))
  assert.ok(error < 1e-9, `${label}: matrix error ${error}`)
}
const all = value => ({ main: value, single: value, defense: value, quad: value })

test('weapon groups include covers and guides and distinguish legacy PDC quads from defense twins', () => {
  for (const name of ['Main_Dorsal_Tube_Center', 'Hatch_Ventral_Aft_Port']) assert.equal(classifyWeaponJoint(name), 'main')
  for (const name of ['Axial_Bow_SourceReceiver', 'SideBattery_4_Starboard_FrontCap']) assert.equal(classifyWeaponJoint(name), 'single')
  for (const name of ['Defense_06_NotchGate', 'DefenseRail_Aft_Port']) assert.equal(classifyWeaponJoint(name), 'defense')
  for (const name of ['PDC_Starboard_CradleGuide_1', 'PDC_Port_HullPetal_2']) assert.equal(classifyWeaponJoint(name), 'quad')
  assert.equal(classifyWeaponJoint('SternHangarDoor'), undefined)
  assert.equal(classifyWeaponJoint('MainBay_Dorsal'), undefined)
})

for (const asset of ['odin.glb', 'odin-lite.glb']) {
  test(`${asset}: shared clocks preserve the accepted complete mechanical pose`, () => {
    const baseline = load(asset), selective = load(asset)
    // Initialization must still leave the static joints at the source pose.
    selective.nodes.forEach((node, index) => {
      if (!node.userData.staticJoint) return
      assert.ok(node.position.distanceTo(selective.original[index][0]) < 1e-10, node.name)
      assert.ok(1 - Math.abs(node.quaternion.dot(selective.original[index][1])) < 1e-10, node.name)
    })
    for (const value of [0, .07, .28, .52, .88, 1, .35, 0]) {
      baseline.rig.apply(value, 19.4)
      selective.rig.applySelective(all(value), 19.4)
      const expected = snapshot(baseline), actual = snapshot(selective)
      for (const [name, matrix] of actual) closeMatrix(matrix, expected.get(name), `${value} ${name}`)
    }
  })

  test(`${asset}: independent clocks follow original trajectories and inactive groups return to real NAV`, () => {
    const baseline = load(asset), selective = load(asset)
    baseline.rig.apply(0, 0)
    const stowed = snapshot(baseline)
    const levels = { main: .76, single: .43, defense: .89, quad: .27 }
    selective.rig.applySelective(levels, 22.3)
    const combined = snapshot(selective)
    for (const group of WEAPON_GROUPS) {
      baseline.rig.apply(levels[group], 22.3)
      const expected = snapshot(baseline)
      for (const node of baseline.nodes.filter(node => node.userData.staticJoint && classifyWeaponJoint(node.name) === group)) {
        closeMatrix(combined.get(node.name), expected.get(node.name), `${group} ${node.name}`)
      }
    }
    // Switch directly from a mixed pose to one weapon. Closed sources are
    // measured from rig.apply(0), not from the GLB's initially exposed tubes.
    for (const active of WEAPON_GROUPS) {
      selective.rig.applySelective({ ...all(0), [active]: .67 }, 28)
      const actual = snapshot(selective)
      for (const node of selective.nodes.filter(node => node.userData.staticJoint && classifyWeaponJoint(node.name) !== active)) {
        closeMatrix(actual.get(node.name), stowed.get(node.name), `${active} must stow ${node.name}`)
      }
    }
    // Returning to the unchanged global path cannot retain a guided pose.
    baseline.rig.apply(.61, 31); selective.rig.apply(.61, 31)
    const expected = snapshot(baseline), actual = snapshot(selective)
    for (const [name, matrix] of actual) closeMatrix(matrix, expected.get(name), `global restore ${name}`)
  })
}

test('selective diagnostics expose stable group counts and clamped independent progress', () => {
  const { rig, nodes } = load()
  const result = rig.applySelective({ main: 2, single: -.2, defense: NaN, quad: .42 }, 0)
  assert.deepEqual(result.progress, { main: 1, single: 0, defense: 0, quad: .42 })
  assert.equal(result.deployment, 1)
  assert.equal(result.groupCounts, rig.groupCounts)
  assert.equal(Object.values(rig.groupCounts).reduce((sum, count) => sum + count, 0), nodes.filter(node => node.userData.staticJoint && node.name !== 'SternHangarDoor').length)
  for (const group of WEAPON_GROUPS) assert.ok(rig.groupCounts[group] > 0)
  assert.equal(rig.applySelective(all(0), 0), result, 'diagnostics reuse their frame buffer')
})
