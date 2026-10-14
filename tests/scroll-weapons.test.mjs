import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { WEAPON_GROUPS, classifyWeaponJoint } from '../app/lib/odin-weapon-groups.ts'
import { advanceWeaponCameraProgress, interpolateWeaponLevels, uniformWeaponLevels } from '../app/lib/odin-weapon-tour.ts'
import { SCROLL_WEAPON_AIM_TIME, sampleScrollWeaponLevels, sampleScrollWeaponPose } from '../app/lib/odin-scroll-weapons.ts'

const close = (actual, expected, label) => assert.ok(Math.abs(actual - expected) < 1e-10, `${label}: ${actual} != ${expected}`)

test('scroll deployment is cumulative, with partial poses inside each weapon introduction', () => {
  assert.deepEqual(sampleScrollWeaponLevels(0), uniformWeaponLevels(0))
  assert.deepEqual(sampleScrollWeaponLevels(1), uniformWeaponLevels(1))
  const main = sampleScrollWeaponLevels(.2), single = sampleScrollWeaponLevels(.7), bridge = sampleScrollWeaponLevels(.92)
  close(main.main, .5, 'halfway through main opening')
  assert.deepEqual({ ...main, main: 0 }, uniformWeaponLevels(0))
  close(single.single, .5, 'halfway through single opening')
  assert.equal(single.main, 1)
  assert.equal(single.defense, 0); assert.equal(single.quad, 0)
  close(bridge.defense, .5, 'halfway through twin opening')
  close(bridge.quad, .5, 'twin and quad open together')
  assert.equal(bridge.main, 1); assert.equal(bridge.single, 1)
  let previous = uniformWeaponLevels(0)
  for (let frame = 0; frame <= 1000; frame++) {
    const levels = sampleScrollWeaponLevels(frame / 1000)
    for (const group of WEAPON_GROUPS) assert.ok(levels[group] >= previous[group], `${group} must not close when the next weapon is introduced`)
    previous = levels
  }
})

test('reversing the scroll retraces every pose without a history latch or queued animation', () => {
  const positions = [0, .18, .34, .54, .69, .81, .91, 1]
  const forward = positions.map(progress => sampleScrollWeaponPose(progress))
  for (let index = positions.length - 1; index >= 0; index--) {
    assert.deepEqual(sampleScrollWeaponPose(positions[index]), forward[index])
  }
  assert.deepEqual(sampleScrollWeaponLevels(-1), uniformWeaponLevels(0))
  assert.deepEqual(sampleScrollWeaponLevels(2), uniformWeaponLevels(1))
  assert.deepEqual(sampleScrollWeaponLevels(NaN), uniformWeaponLevels(0))
  // Camera smoothing is the only catch-up clock: the rig receives exactly
  // that same intermediate coordinate, and a reversal takes effect next frame.
  let progress = .18
  const before = sampleScrollWeaponLevels(progress)
  progress = advanceWeaponCameraProgress(progress, .28, 1 / 60)
  const after = sampleScrollWeaponLevels(progress)
  assert.ok(after.main > before.main && after.main < 1)
  progress = advanceWeaponCameraProgress(progress, .1, 1 / 60)
  assert.ok(sampleScrollWeaponLevels(progress).main < after.main)
  for (let frame = 0; frame < 300; frame++) progress = advanceWeaponCameraProgress(progress, .2, 1 / 60)
  close(progress, .2, 'camera and mechanisms settle at the scroll coordinate')
  assert.deepEqual(sampleScrollWeaponPose(progress), sampleScrollWeaponPose(.2))
})

test('entry blends the actual visible mixed pose and retargets immediately during rapid scroll', () => {
  const source = { levels: { main: .8, single: .23, defense: .67, quad: .11 }, animationTime: 41 }
  assert.deepEqual(sampleScrollWeaponPose(0, source, 0), source)
  const held = sampleScrollWeaponPose(.7, source, .4)
  const retargeted = sampleScrollWeaponPose(.2, source, .4)
  assert.ok(retargeted.levels.single < held.levels.single, 'Changing scroll changes the handoff destination immediately')
  assert.deepEqual(sampleScrollWeaponPose(.92, source, 1), sampleScrollWeaponPose(.92))
  assert.deepEqual(sampleScrollWeaponPose(.92, source, 4), sampleScrollWeaponPose(.92), 'Entry does not continue after its finite interval')
  const interrupted = sampleScrollWeaponPose(.34, held, 0)
  assert.deepEqual(interrupted, held, 'A new handoff starts at the rendered pose, not an obsolete endpoint')
  assert.equal(sampleScrollWeaponPose(.34).animationTime, SCROLL_WEAPON_AIM_TIME)
  assert.deepEqual(source, { levels: { main: .8, single: .23, defense: .67, quad: .11 }, animationTime: 41 }, 'Sampling must not mutate the source snapshot')
})

function load(asset) {
  const bytes = readFileSync(new URL(`../public/models/${asset}`, import.meta.url))
  const model = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const nodes = model.nodes.map(node => {
    const object = new THREE.Object3D()
    object.name = node.name; object.userData = node.extras || {}
    if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(object.position, object.quaternion, object.scale)
    if (node.translation) object.position.fromArray(node.translation)
    if (node.rotation) object.quaternion.fromArray(node.rotation)
    if (node.scale) object.scale.fromArray(node.scale)
    return object
  })
  model.nodes.forEach((node, index) => node.children?.forEach(child => nodes[index].add(nodes[child])))
  const root = new THREE.Group()
  model.scenes[model.scene || 0].nodes.forEach(index => root.add(nodes[index]))
  return { root, nodes, rig: createOdinRig(root) }
}
function snapshot(scene) {
  scene.root.updateWorldMatrix(true, true)
  return new Map(scene.nodes.filter(node => node.userData.staticJoint).map(node => [node.name, node.matrixWorld.clone()]))
}
function assertPose(actual, expected, label, group) {
  for (const [name, matrix] of actual) {
    if (group && classifyWeaponJoint(name) !== group) continue
    const error = Math.max(...matrix.elements.map((value, index) => Math.abs(value - expected.get(name).elements[index])))
    assert.ok(error < 1e-9, `${label} ${name}: matrix error ${error}`)
  }
}
function apply(scene, pose) {
  scene.rig.applySelective(pose.levels, pose.animationTime)
  return snapshot(scene)
}

for (const asset of ['odin.glb', 'odin-lite.glb']) {
  test(`${asset}: partial scrolling poses use the existing articulation and remain still when scrolling stops`, () => {
    const scroll = load(asset), reference = load(asset)
    const positions = [.2, .7, .92, 1]
    for (const progress of positions) {
      const pose = sampleScrollWeaponPose(progress), expected = apply(scroll, pose)
      for (const group of WEAPON_GROUPS) {
        reference.rig.apply(pose.levels[group], SCROLL_WEAPON_AIM_TIME)
        assertPose(expected, snapshot(reference), `same mechanical path at ${progress}`, group)
      }
      // Many rendered frames at an unchanged scroll position must not move the
      // defense aim scan, quad arms, covers, barrels, or the deployed main guns.
      for (let frame = 0; frame < 12; frame++) assertPose(apply(scroll, sampleScrollWeaponPose(progress)), expected, `stationary ${progress}`)
      apply(scroll, sampleScrollWeaponPose(1 - progress))
      assertPose(apply(scroll, sampleScrollWeaponPose(progress)), expected, `rapid reversal ${progress}`)
    }
    const fullyOpen = apply(scroll, sampleScrollWeaponPose(1))
    const later = apply(scroll, sampleScrollWeaponPose(.91))
    assertPose(later, fullyOpen, 'prior main battery stays deployed', 'main')
    assertPose(later, fullyOpen, 'prior single batteries stay deployed', 'single')
  })

  test(`${asset}: entry and a rapid bridge handoff preserve the visible start and stow all families together`, () => {
    const scene = load(asset), source = sampleScrollWeaponPose(.94)
    const initial = apply(scene, source)
    assertPose(apply(scene, sampleScrollWeaponPose(.2, source, 0)), initial, 'entry has no pose jump')
    const actual = sampleScrollWeaponPose(.7, source, .37)
    const visible = apply(scene, actual)
    const stowedLevels = uniformWeaponLevels(0)
    assertPose(apply(scene, { ...actual, levels: interpolateWeaponLevels(actual.levels, stowedLevels, 0) }), visible, 'bridge starts from rendered mixed levels')
    const halfway = interpolateWeaponLevels(actual.levels, stowedLevels, .5)
    for (const group of WEAPON_GROUPS) close(halfway[group], actual.levels[group] / 2, `${group} stows in the same interval`)
    const bridgeEnd = apply(scene, { animationTime: 0, levels: interpolateWeaponLevels(actual.levels, stowedLevels, 1) })
    scene.rig.apply(0, 0)
    assertPose(bridgeEnd, snapshot(scene), 'bridge reaches the normal film NAV endpoint')
  })
}
