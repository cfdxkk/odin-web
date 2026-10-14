import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import * as THREE from 'three'
import { WEAPON_TOUR, WEAPON_ROTATION_START, WEAPON_ROTATION_END, clampWeaponStep, sampleWeaponCamera, sampleContinuousWeaponCamera, advanceWeaponCameraProgress, weaponStepProgress, uniformWeaponLevels, focusedWeaponLevels, interpolateWeaponLevels, chooseWeaponRouteSide, weaponRouteAngles } from '../app/lib/odin-weapon-tour.ts'
import { classifyWeaponJoint, WEAPON_GROUPS } from '../app/lib/odin-weapon-groups.ts'
import { interpolateOdinCamera, interpolateOrientedOdinCamera, odinCameraOrientation, sampleOdinCamera } from '../app/lib/odin-camera.ts'
import { sampleTourCamera } from '../app/lib/odin-tour.ts'
import { createOdinRig } from '../app/lib/odin-rig.ts'

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

test('continuous weapon inspection arrives above the spine and stays centered through the later weapons', () => {
  for (const aspect of aspects) {
    const first = sampleWeaponCamera(0, aspect)
    assert.ok(first.position.x < first.target.x, 'Start on the port side')
    const last = sampleWeaponCamera(WEAPON_TOUR.length - 1, aspect)
    assert.ok(Math.abs(last.position.x - last.target.x) < 1e-9 && Math.abs(last.position.z - last.target.z) < 1e-9, 'Finish directly above the hull without an aft tilt')
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
    assert.ok(next.position.distanceTo(previous.position) < .016)
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

test('mirrored routes stop rotating at the torpedoes without crossing the opposite flank', () => {
  for (let step = 0; step <= 200; step++) {
    const p = step / 200, left = sampleContinuousWeaponCamera(p, 16 / 9, -1), right = sampleContinuousWeaponCamera(p, 16 / 9, 1)
    close(left.position.x - left.target.x, -(right.position.x - right.target.x), 'Mirrored side')
    close(left.position.y, right.position.y, 'Shared altitude')
    close(left.position.z, right.position.z, 'Shared fore-aft framing')
    assert.ok(left.position.x <= left.target.x + 1e-9 && right.position.x >= right.target.x - 1e-9, 'Neither route crosses the opposite flank')
  }
  for (const side of [-1, 1]) {
    const held = odinCameraOrientation(sampleContinuousWeaponCamera(WEAPON_ROTATION_END, 16 / 9, side))
    for (let frame = 0; frame <= 1000; frame++) {
      const p = WEAPON_ROTATION_END + (1 - WEAPON_ROTATION_END) * frame / 1000
      const pose = sampleContinuousWeaponCamera(p, 16 / 9, side)
      assert.ok(held.angleTo(odinCameraOrientation(pose)) < 1e-7, '2-3, 2-4 and 2-5 share exactly the same orientation')
      close(weaponRouteAngles(p).lateral, Math.PI / 2, 'Centered dorsal view')
      close(weaponRouteAngles(p).aft, 0, 'No late aft pitch')
    }
  }
})

test('both centered weapon routes pull back into their established rear quarters through bridge and hangars', () => {
  for (const side of [-1, 1]) for (const aspect of aspects) {
    const shots = [sampleWeaponCamera(4, aspect, side), sampleTourCamera(2, aspect, side), sampleTourCamera(3, aspect, side)]
    let previousDistance = 0
    for (const [index, shot] of shots.entries()) {
      const offset = shot.position.clone().sub(shot.target), distance = offset.length()
      if (index > 0) {
        assert.equal(Math.sign(offset.x), -side, 'Both later aft chapters retain the same flank')
        assert.ok(Math.abs(offset.x) / distance > .3, 'The rear quarter must read clearly, rather than almost straight astern')
        assert.ok(offset.z / distance > .75, 'The later route remains behind the ship')
      }
      assert.ok(distance > previousDistance, 'A fixed-FOV shot must pull back at each chapter, including ultrawide screens')
      previousDistance = distance
      if (index === 2) assert.ok(offset.y < 0, 'The hangar remains visible from below')
    }
    for (let chapter = 1; chapter < shots.length; chapter++) {
      const from = { ...shots[chapter - 1], up: shots[chapter - 1].up ?? new THREE.Vector3(0, 1, 0) }
      const to = { ...shots[chapter], up: new THREE.Vector3(0, 1, 0) }
      let previousDistance = from.position.distanceTo(from.target)
      for (let frame = 0; frame <= 100; frame++) {
        const pose = interpolateOrientedOdinCamera(from, to, frame / 100)
        const offset = pose.position.clone().sub(pose.target), distance = offset.length()
        assert.ok(distance >= previousDistance - 1e-8, 'The transition must never dip inward before pulling back')
        assert.ok(offset.x * -side >= -1e-8, 'No transition crosses to the other flank')
        assert.ok(offset.z >= -1e-8, 'No transition crosses the front of the ship')
        previousDistance = distance
      }
    }
  }
})

function actualMainBatteryCenters(deployment) {
  const bytes = readFileSync(new URL('../public/models/odin.glb', import.meta.url))
  const model = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const objects = model.nodes.map(node => {
    const object = new THREE.Object3D(); object.name = node.name; object.userData = node.extras ?? {}
    if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(object.position, object.quaternion, object.scale)
    if (node.translation) object.position.fromArray(node.translation)
    if (node.rotation) object.quaternion.fromArray(node.rotation)
    if (node.scale) object.scale.fromArray(node.scale)
    return object
  })
  model.nodes.forEach((node, index) => node.children?.forEach(child => objects[index].add(objects[child])))
  const root = new THREE.Group(); model.scenes[model.scene ?? 0].nodes.forEach(index => root.add(objects[index]))
  createOdinRig(root).applySelective({ main: deployment, single: 0, defense: 0, quad: 0 }, 0)
  root.updateMatrixWorld(true)
  return ['Dorsal', 'Ventral'].map(side => {
    const parent = model.nodes.find(node => node.name === `Main_${side}_Shroud_Center`)
    const index = parent.children.find(child => model.nodes[child].mesh !== undefined)
    const bounds = model.accessors[model.meshes[model.nodes[index].mesh].primitives[0].attributes.POSITION]
    return new THREE.Vector3(...bounds.min).add(new THREE.Vector3(...bounds.max)).multiplyScalar(.5).applyMatrix4(objects[index].matrixWorld)
  })
}

test('rotation waits until the actual ventral main turret passes screen center in stowed and deployed poses', () => {
  for (const deployment of [0, .5, 1]) {
    const ventral = actualMainBatteryCenters(deployment)[1]
    for (const aspect of aspects) for (const side of [-1, 1]) {
      const main = sampleWeaponCamera(1, aspect, side)
      assert.ok(project(ventral, main, main.up, aspect).y < 0, 'The lower gun first enters below center')
      const beforeTurn = sampleContinuousWeaponCamera(WEAPON_ROTATION_START, aspect, side)
      assert.ok(project(ventral, beforeTurn, beforeTurn.up, aspect).y > 0, 'The lower gun crosses center before any turn begins')
      const held = odinCameraOrientation(main)
      for (let frame = 0; frame <= 100; frame++) {
        const p = .25 + (WEAPON_ROTATION_START - .25) * frame / 100
        assert.ok(held.angleTo(odinCameraOrientation(sampleContinuousWeaponCamera(p, aspect, side))) < 1e-7, 'The flank stays visible during the main-battery inspection')
      }
    }
  }
})

test('the whole weapon scroll pulls back continuously and the dorsal surface never swells inward during the turn', () => {
  const mainLandmarks = [0, 1].flatMap(actualMainBatteryCenters)
  for (const aspect of aspects) for (const side of [-1, 1]) {
    let previousRadius = -Infinity, previousDorsalDepth = -Infinity
    const depths = mainLandmarks.map(() => -Infinity)
    for (let frame = 0; frame <= 10000; frame++) {
      const p = frame / 10000, pose = sampleContinuousWeaponCamera(p, aspect, side)
      const offset = pose.position.clone().sub(pose.target), radius = offset.length()
      assert.ok(radius > previousRadius, 'The sampled radius must increase everywhere, not just at chapter endpoints')
      previousRadius = radius
      if (p >= .25 && p <= .5) mainLandmarks.forEach((point, index) => {
        const depth = point.clone().sub(pose.position).dot(offset.clone().normalize().negate())
        assert.ok(depth > depths[index], 'A fixed actual turret surface must recede while the camera turns overhead')
        depths[index] = depth
      })
      if (p >= .5) {
        assert.ok(pose.position.y > previousDorsalDepth, 'Lowering the aim at 2-4 must not bring the camera closer to the deck')
        previousDorsalDepth = pose.position.y
      }
    }
  }
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
