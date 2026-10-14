import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import * as THREE from 'three'
import { WEAPON_TOUR, clampWeaponStep, sampleWeaponCamera, sampleContinuousWeaponCamera, advanceWeaponCameraProgress, weaponStepProgress, uniformWeaponLevels, focusedWeaponLevels, interpolateWeaponLevels, chooseWeaponRouteSide, weaponRouteAngles } from '../app/lib/odin-weapon-tour.ts'
import { classifyWeaponJoint, WEAPON_GROUPS } from '../app/lib/odin-weapon-groups.ts'
import { interpolateOdinCamera, interpolateOrientedOdinCamera, odinCameraOrientation, sampleOdinCamera } from '../app/lib/odin-camera.ts'
import { sampleTourCamera } from '../app/lib/odin-tour.ts'

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

test('continuous weapon inspection crosses the dorsal hull then pitches toward the stern', () => {
  for (const aspect of aspects) {
    const first = sampleWeaponCamera(0, aspect)
    assert.ok(first.position.x < first.target.x, 'Start on the port side')
    const last = sampleWeaponCamera(WEAPON_TOUR.length - 1, aspect)
    assert.ok(last.position.z - last.target.z > last.position.y - last.target.y, 'Finish behind the hull looking toward the bridge')
    const overhead = sampleContinuousWeaponCamera(.5, aspect)
    assert.ok(Math.abs(overhead.position.x - overhead.target.x) < .15, 'Torpedo shot reaches the spine')
    assert.ok(overhead.position.y - overhead.target.y > 3, 'Midpoint passes above the hull, not through it')
    let previousY = Infinity
    for (let step = 0; step < WEAPON_TOUR.length; step++) {
      const shot = WEAPON_TOUR[step], pose = sampleWeaponCamera(step, aspect)
      assert.ok(shot.point[1] < previousY, `${shot.id} must follow the previous station toward the stern`)
      previousY = shot.point[1]
      assert.deepEqual(pose.target.toArray(), [shot.point[0] * .01, shot.point[2] * .01, -shot.point[1] * .01])
      assert.ok(pose.position.toArray().every(Number.isFinite))
      assert.ok(pose.position.distanceTo(pose.target) > .5, 'Camera stays outside the selected mechanism')
      assert.ok(pose.position.y > pose.target.y, 'The entire orbit remains above the dorsal surface')
      assert.ok(pose.up.distanceTo(first.up) < 1e-9, 'The ship keeps the same screen-up direction')
      assert.deepEqual(sampleContinuousWeaponCamera(weaponStepProgress(step), aspect).target.toArray(), pose.target.toArray())
    }
  }
  assert.equal(clampWeaponStep(-10), 0)
  assert.equal(clampWeaponStep(100), WEAPON_TOUR.length - 1)
  assert.equal(clampWeaponStep(NaN), 0)
})

test('the bow remains vertical throughout the over-hull orbit without an upside-down flip', () => {
  for (const aspect of aspects) for (let index = 0; index <= 100; index++) {
    const pose = sampleContinuousWeaponCamera(index / 100, aspect)
    const center = project(pose.target, pose, pose.up, aspect)
    const bow = project(pose.target.clone().add(new THREE.Vector3(0, 0, -.25)), pose, pose.up, aspect)
    const horizontal = (bow.x - center.x) * aspect, vertical = bow.y - center.y
    assert.ok(Math.abs(horizontal) < 1e-9, 'The longitudinal axis stays vertical')
    assert.ok(vertical > 0, 'Bow points up from either side and directly overhead')
    assert.deepEqual(pose.up.toArray(), [0, 0, -1])
  }
})

test('continuous scroll never reverses along the hull or jumps at a weapon boundary', () => {
  let previous = sampleContinuousWeaponCamera(0, 16 / 9)
  for (let i = 1; i <= 10000; i++) {
    const next = sampleContinuousWeaponCamera(i / 10000, 16 / 9)
    assert.ok(next.target.z >= previous.target.z, 'Focus must keep traveling from bow to aft')
    assert.ok(next.position.distanceTo(previous.position) < .008)
    assert.ok(next.target.distanceTo(previous.target) < .003)
    previous = next
  }
  for (let i = 1; i < WEAPON_TOUR.length - 1; i++) {
    const p = weaponStepProgress(i), epsilon = 1e-6
    const before = sampleContinuousWeaponCamera(p - epsilon, 16 / 9)
    const at = sampleContinuousWeaponCamera(p, 16 / 9)
    const after = sampleContinuousWeaponCamera(p + epsilon, 16 / 9)
    const leftVelocity = at.position.clone().sub(before.position).divideScalar(epsilon)
    const rightVelocity = after.position.clone().sub(at.position).divideScalar(epsilon)
    assert.ok(leftVelocity.distanceTo(rightVelocity) < .01, 'Camera velocity must not reset at a step boundary')
  }
})

test('scroll smoothing is frame-rate independent and reverses immediately from the visible camera', () => {
  let sixty = 0, thirty = 0
  for (let i = 0; i < 60; i++) sixty = advanceWeaponCameraProgress(sixty, 1, 1/60)
  for (let i = 0; i < 30; i++) thirty = advanceWeaponCameraProgress(thirty, 1, 1/30)
  close(sixty, thirty, 'same one-second scroll response')
  assert.ok(sixty > .999)
  const reversed = advanceWeaponCameraProgress(sixty, 0, 1/60)
  assert.ok(reversed > .8 && reversed < sixty, 'Reversing starts from the current view rather than restarting an old transition')
  assert.equal(advanceWeaponCameraProgress(.4, 1, 0), .4)
})

test('bow framing includes the aft radiator while the callout remains on the emitter bank', () => {
  const shot = WEAPON_TOUR[0]
  assert.deepEqual(shot.calloutPoint, [0, 369.5, 6.8])
  assert.ok(shot.point[1] < shot.calloutPoint[1], 'Framing moves aft of the emitter tip')
  for (const side of [-1, 1]) for (const aspect of aspects) {
    const pose = sampleWeaponCamera(0, aspect, side)
    const emitter = new THREE.Vector3(shot.calloutPoint[0] * .01, shot.calloutPoint[2] * .01, -shot.calloutPoint[1] * .01)
    const projected = project(emitter, pose, pose.up, aspect)
    assert.ok(projected.y > 0 && projected.y < .7, 'The emitter remains comfortably visible above the framing center')
    assert.ok(Math.abs(projected.x) < .9)
  }
})

test('focused chapters activate the selected families and combine twin and quad turrets', () => {
  const bytes = readFileSync(new URL('../public/models/odin.glb', import.meta.url))
  const model = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const joints = new Map(model.nodes.filter(node => node.extras?.staticJoint).map(node => [node.name, node]))
  const expectedGroups = [[], ['main'], [], ['single'], ['defense', 'quad']]
  assert.equal(WEAPON_TOUR.length, expectedGroups.length)
  WEAPON_TOUR.forEach((shot, step) => {
    const levels = focusedWeaponLevels(step)
    for (const group of WEAPON_GROUPS) assert.equal(levels[group], expectedGroups[step].includes(group) ? 1 : 0, `${shot.id} incorrectly activates ${group}`)
    if (shot.anchor) {
      for (const anchor of shot.anchors ?? [shot.anchor]) {
        assert.ok(joints.has(anchor), `${shot.id} anchor must exist in the actual model`)
        assert.ok(expectedGroups[step].includes(classifyWeaponJoint(anchor)), `${shot.id} anchor belongs to another mechanism`)
      }
    } else assert.equal(shot.group, null, 'Only a static hull feature can omit a moving anchor')
  })
})

test('entry chooses the currently visible homepage side and takes the shortest orientation arc', () => {
  for (const aspect of aspects) for (let time = 0; time < 45; time += .25) {
    const visible = { ...sampleOdinCamera(time, aspect), up: new THREE.Vector3(0, 1, 0) }
    const offset = visible.position.clone().sub(visible.target)
    const side = chooseWeaponRouteSide(visible.position, visible.target)
    if (Math.abs(offset.x) > offset.length() * .015) assert.equal(side, Math.sign(offset.x))
    const end = sampleWeaponCamera(0, aspect, side)
    assert.equal(Math.sign(end.position.x - end.target.x), side)
    const startOrientation = odinCameraOrientation(visible), endOrientation = odinCameraOrientation(end)
    let previousOrientation = startOrientation, total = 0
    for (let step = 0; step <= 32; step++) {
      const pose = interpolateOrientedOdinCamera(visible, end, step / 32)
      const orientation = odinCameraOrientation(pose)
      total += previousOrientation.angleTo(orientation); previousOrientation = orientation
      assert.ok(pose.position.distanceTo(pose.target) >= Math.min(offset.length(), end.position.distanceTo(end.target)) - 1e-8, 'Never dive through the hull during the handoff')
    }
    assert.ok(total <= Math.PI + 1e-6, 'No extra revolution or roll is introduced')
    assert.ok(Math.abs(total - startOrientation.angleTo(endOrientation)) < 1e-6)
  }
  const headOn = new THREE.Vector3(1e-8, 2, 9), aim = new THREE.Vector3()
  assert.equal(chooseWeaponRouteSide(headOn, aim, 1), 1)
  assert.equal(chooseWeaponRouteSide(headOn, aim, -1), -1)
})

test('mirrored entry routes share a soft overlapping lateral-to-aft rotation and an aft bridge continuation', () => {
  for (let step = 0; step <= 200; step++) {
    const p = step / 200, left = sampleContinuousWeaponCamera(p, 16 / 9, -1), right = sampleContinuousWeaponCamera(p, 16 / 9, 1)
    close(left.position.x - left.target.x, -(right.position.x - right.target.x), 'Mirrored side')
    close(left.position.y, right.position.y, 'Shared altitude')
    close(left.position.z, right.position.z, 'Shared aft pitch')
  }
  const a = weaponRouteAngles(.48), b = weaponRouteAngles(.52)
  assert.ok(b.lateral > a.lateral && b.aft > a.aft, 'Both axes move together around the torpedo handoff')
  close(weaponRouteAngles(.75).lateral, weaponRouteAngles(1).lateral, 'Lateral sweep has stopped for the aft chapters')
  assert.ok(weaponRouteAngles(1).aft > weaponRouteAngles(.75).aft, 'Aft pitch continues through the combined turrets')
  const single = sampleWeaponCamera(3, 16 / 9), combined = sampleWeaponCamera(4, 16 / 9), bridge = sampleTourCamera(2, 16 / 9)
  assert.ok(single.position.y - single.target.y > single.position.z - single.target.z, 'Single batteries are shown from high above the stern')
  assert.ok(combined.position.z > combined.target.z && bridge.position.z > bridge.target.z, 'Combined turrets and bridge keep the same aft hemisphere')
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
