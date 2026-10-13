import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import * as THREE from 'three'
import { WEAPON_TOUR, clampWeaponStep, sampleWeaponCamera, uniformWeaponLevels, focusedWeaponLevels, interpolateWeaponLevels } from '../app/lib/odin-weapon-tour.ts'
import { classifyWeaponJoint, WEAPON_GROUPS } from '../app/lib/odin-weapon-groups.ts'
import { interpolateOdinCamera } from '../app/lib/odin-camera.ts'

const aspects = [390 / 844, 4 / 3, 16 / 9, 21 / 9, 32 / 9]
const close = (actual, expected, label) => assert.ok(Math.abs(actual - expected) < 1e-9, `${label}: ${actual} != ${expected}`)
function project(point, pose, up, aspect) {
  const camera = new THREE.PerspectiveCamera(33, aspect, .035, 500)
  camera.position.copy(pose.position)
  camera.up.copy(up)
  camera.lookAt(pose.target)
  camera.updateMatrixWorld(true)
  return point.clone().project(camera)
}

test('weapon cameras travel from bow to aft with one heading and source-axis targets', () => {
  for (const aspect of aspects) {
    const first = sampleWeaponCamera(0, aspect)
    const direction = first.position.clone().sub(first.target).normalize()
    let previousY = Infinity
    for (let step = 0; step < WEAPON_TOUR.length; step++) {
      const shot = WEAPON_TOUR[step], pose = sampleWeaponCamera(step, aspect)
      assert.ok(shot.point[1] < previousY, `${shot.id} must follow the previous station toward the stern`)
      previousY = shot.point[1]
      assert.deepEqual(pose.target.toArray(), [shot.point[0] * .01, shot.point[2] * .01, -shot.point[1] * .01])
      assert.ok(pose.position.toArray().every(Number.isFinite))
      assert.ok(pose.position.distanceTo(pose.target) > .5, 'Camera stays outside the selected mechanism')
      assert.ok(pose.position.clone().sub(pose.target).normalize().distanceTo(direction) < 1e-9, 'Changing weapons pans rather than orbiting around the ship')
      assert.ok(pose.up.distanceTo(first.up) < 1e-9, 'No roll is introduced between weapon steps')
    }
  }
  assert.equal(clampWeaponStep(-10), 0)
  assert.equal(clampWeaponStep(100), WEAPON_TOUR.length - 1)
  assert.equal(clampWeaponStep(NaN), 0)
})

test('weapon inspection keeps the bow horizontal with a modest upward angle', () => {
  for (const aspect of aspects) for (let step = 0; step < WEAPON_TOUR.length; step++) {
    const pose = sampleWeaponCamera(step, aspect)
    const center = project(pose.target, pose, pose.up, aspect)
    const bow = project(pose.target.clone().add(new THREE.Vector3(0, 0, -.25)), pose, pose.up, aspect)
    const horizontal = (bow.x - center.x) * aspect, vertical = bow.y - center.y
    assert.ok(horizontal > 0, 'Bow points right in the inspection view')
    const angle = Math.atan2(vertical, horizontal) * 180 / Math.PI
    assert.ok(angle > 0 && angle < 25, `Bow tilt ${angle} must remain subtle, never vertical`)
    assert.deepEqual(pose.up.toArray(), [0, 1, 0])
  }
})

test('a focused step activates only its physical weapon family, with the static bow beam activating none', () => {
  const bytes = readFileSync(new URL('../public/models/odin.glb', import.meta.url))
  const model = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const joints = new Map(model.nodes.filter(node => node.extras?.staticJoint).map(node => [node.name, node]))
  const expectedGroups = [null, 'main', null, 'single', 'defense', 'quad']
  assert.equal(WEAPON_TOUR.length, expectedGroups.length)
  WEAPON_TOUR.forEach((shot, step) => {
    assert.equal(shot.group, expectedGroups[step])
    const levels = focusedWeaponLevels(step)
    for (const group of WEAPON_GROUPS) assert.equal(levels[group], group === shot.group ? 1 : 0, `${shot.id} incorrectly activates ${group}`)
    if (shot.anchor) {
      assert.ok(joints.has(shot.anchor), `${shot.id} anchor must exist in the actual model`)
      assert.equal(classifyWeaponJoint(shot.anchor), shot.group, `${shot.id} anchor belongs to another mechanism`)
    } else assert.equal(shot.group, null, 'Only a static hull feature can omit a moving anchor')
  })
})

test('rapid weapon reversals retain the visible group pose without mutating transition snapshots', () => {
  let visible = uniformWeaponLevels(0)
  for (const next of [1, 4, 2, 0, 3, 1, 0, 4]) {
    const from = { ...visible }, savedFrom = { ...from }, target = focusedWeaponLevels(next), savedTarget = { ...target }
    assert.deepEqual(interpolateWeaponLevels(from, target, 0), visible, 'A new transition must start at the interrupted pose')
    let previous = from
    for (let frame = 0; frame <= 100; frame++) {
      const sampled = interpolateWeaponLevels(from, target, frame / 100)
      for (const group of WEAPON_GROUPS) {
        assert.ok(sampled[group] >= Math.min(from[group], target[group]) - 1e-9)
        assert.ok(sampled[group] <= Math.max(from[group], target[group]) + 1e-9)
        assert.ok(Math.abs(sampled[group] - previous[group]) < .016, 'No one-frame endpoint snap')
      }
      previous = sampled
    }
    assert.deepEqual(previous, target)
    assert.deepEqual(from, savedFrom)
    assert.deepEqual(target, savedTarget)
    // Interrupt before arrival; the next iteration starts from this exact
    // mixed pose, including the previous weapon still closing.
    visible = interpolateWeaponLevels(from, target, .37)
  }
})

test('reversing a weapon camera mid-pan preserves both the pose and projected callout endpoint', () => {
  for (const aspect of aspects) for (let step = 0; step < WEAPON_TOUR.length - 1; step++) {
    const from = sampleWeaponCamera(step, aspect), to = sampleWeaponCamera(step + 1, aspect)
    for (const fraction of [.12, .43, .81]) {
      const visible = interpolateOdinCamera(from, to, fraction)
      const reverseStart = interpolateOdinCamera(visible, from, 0)
      assert.ok(reverseStart.position.distanceTo(visible.position) < 1e-9)
      assert.ok(reverseStart.target.distanceTo(visible.target) < 1e-9)
      const before = project(to.target, visible, from.up, aspect)
      const after = project(to.target, reverseStart, from.up, aspect)
      close(before.x, after.x, 'callout X at reversal')
      close(before.y, after.y, 'callout Y at reversal')
      const end = interpolateOdinCamera(visible, from, 1)
      assert.ok(end.position.distanceTo(from.position) < 1e-9)
      assert.ok(end.target.distanceTo(from.target) < 1e-9)
    }
  }
})

test('every weapon step has both languages and its optional official clip is available locally', () => {
  const videos = []
  for (const shot of WEAPON_TOUR) {
    assert.deepEqual(Object.keys(shot.zh), Object.keys(shot.en))
    for (const text of Object.values(shot.en)) assert.ok(text && !/[\u3400-\u9fff]/.test(text))
    for (const text of Object.values(shot.zh)) assert.ok(text)
    if (!shot.video) continue
    videos.push(shot.video)
    for (const extension of ['mp4', 'webp']) assert.ok(existsSync(new URL(`../public/videos/odin/${shot.video}.${extension}`, import.meta.url)))
  }
  assert.equal(new Set(videos).size, 3)
})
