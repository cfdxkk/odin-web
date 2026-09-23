import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'

function loadRig() {
  const bytes = fs.readFileSync(new URL('../public/models/odin.glb', import.meta.url))
  const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString())
  const nodes = gltf.nodes.map(n => {
    const o = new THREE.Object3D(); o.name = n.name; o.userData = n.extras || {}
    if (n.matrix) new THREE.Matrix4().fromArray(n.matrix).decompose(o.position, o.quaternion, o.scale)
    if (n.translation) o.position.fromArray(n.translation)
    if (n.rotation) o.quaternion.fromArray(n.rotation)
    if (n.scale) o.scale.fromArray(n.scale)
    return o
  })
  gltf.nodes.forEach((n, i) => n.children?.forEach(c => nodes[i].add(nodes[c])))
  const root = new THREE.Group(); gltf.scenes[gltf.scene || 0].nodes.forEach(n => root.add(nodes[n]))
  return { root, nodes, rig: createOdinRig(root) }
}

test('main batteries follow the reference sequence: doors, barrels, then armored cradle', () => {
  const { root, rig } = loadRig()
  rig.apply(0, 0)
  const door = root.getObjectByName('Hatch_Dorsal_Port')
  const barrel = root.getObjectByName('Main_Dorsal_Barrels')
  const mount = root.getObjectByName('Main_Dorsal_Mount')
  const first = { door: door.position.clone(), barrel: barrel.position.clone(), mount: mount.position.clone() }
  rig.apply(.20, 0)
  assert.ok(door.position.distanceTo(first.door) > 3, 'Foredeck armor slides clear before the cradle rises')
  assert.ok(barrel.position.distanceTo(first.barrel) > 1, 'Gun bodies begin to emerge while doors open')
  assert.ok(mount.position.distanceTo(first.mount) < 1e-6, 'Housing waits until the barrels emerge')
  rig.apply(.28, 0)
  const doorOpen = door.position.clone()
  rig.apply(.55, 0)
  assert.ok(door.position.distanceTo(doorOpen) < 1e-6, 'Armor remains parked during the cradle lift')
  assert.ok(mount.position.distanceTo(first.mount) > .2, 'Armored cradle rises and advances')
  for (let d = 0; d <= 1; d += .01) {
    rig.apply(d, 0)
    if (d < .35) assert.ok(root.getObjectByName('Axial_Bow_Barrel').quaternion.angleTo(new THREE.Quaternion()) < 1e-6)
  }
})

test('all three main bores level together and stay parallel during their visible travel', () => {
  const { root, rig } = loadRig()
  for (const d of [.20, .28, .40, .55, .75, 1]) {
    rig.apply(d, 3)
    for (const side of ['Dorsal', 'Ventral']) {
      const barrel = root.getObjectByName(`Main_${side}_Barrels`)
      for (const role of ['Port', 'Center', 'Starboard']) {
        const guide = root.getObjectByName(`Main_${side}_Shroud_${role}`)
        assert.ok(barrel.quaternion.angleTo(guide.quaternion) < 1e-6, `${side} ${role} diverges at ${d}`)
      }
    }
  }
  rig.apply(.35, 3)
  const level = root.getObjectByName('Main_Dorsal_Barrels').quaternion.clone()
  for (const d of [.40, .55, .75, 1]) {
    rig.apply(d, 3)
    assert.ok(root.getObjectByName('Main_Dorsal_Barrels').quaternion.angleTo(level) < 1e-6, `Bores pitch during visible travel at ${d}`)
  }
})

test('paired main armor translates outboard and down without any rotation', () => {
  const { root, rig } = loadRig()
  rig.apply(0, 0)
  for (const bank of ['Dorsal', 'Ventral']) {
    for (const [side, sign] of [['Port', -1], ['Starboard', 1]]) {
      const plate = root.getObjectByName(`Hatch_${bank}_${side}`)
      const closedPosition = plate.position.clone(), closedRotation = plate.quaternion.clone()
      const [x, y, z] = plate.userData.slideVector
      assert.equal(Math.sign(x), sign)
      assert.equal(y, 0)
      assert.equal(Math.sign(z), bank === 'Dorsal' ? -1 : 1)
      for (const d of [.07, .14, .21, .28, .5, 1]) {
        rig.apply(d, 0)
        assert.ok(plate.quaternion.angleTo(closedRotation) < 1e-6, `${bank} ${side} rotated at ${d}`)
      }
      rig.apply(1, 0)
      assert.ok(plate.position.distanceTo(closedPosition) > 12)
      rig.apply(0, 0)
      assert.ok(plate.position.distanceTo(closedPosition) < 1e-6, `${bank} ${side} did not return exactly`)
    }
  }
})

test('quad barrels retain orientation during stow/deploy while pod travel is short', () => {
  const { root, rig } = loadRig()
  rig.apply(0, 0)
  const pod = root.getObjectByName('PDC_Starboard_Carriage'), start = pod.position.clone()
  const arms = ['Port', 'Starboard'].flatMap(side => Array.from({ length: 4 }, (_, i) => root.getObjectByName(`PDC_${side}_Arm_${i}`)))
  const orientations = arms.map(n => n.getWorldQuaternion(new THREE.Quaternion()))
  const locations = arms.map(n => n.getWorldPosition(new THREE.Vector3()))
  for (let d = 0; d <= .95; d += .01) {
    rig.apply(d, 4)
    arms.forEach((n, i) => assert.ok(n.getWorldQuaternion(new THREE.Quaternion()).angleTo(orientations[i]) < 1e-6))
  }
  assert.ok(Math.abs(pod.position.distanceTo(start) - 8) < 1e-6)
  arms.forEach((n, i) => assert.ok(n.getWorldPosition(new THREE.Vector3()).distanceTo(locations[i]) > .2))
})

test('outer main tubes telescope independently and the original front bridge shields actually open', () => {
  const { root, rig } = loadRig()
  const names = ['Main_Dorsal_Tube_Port', 'Main_Dorsal_Tube_Starboard', 'Main_Ventral_Tube_Port', 'Main_Ventral_Tube_Starboard']
  rig.apply(0, 0)
  const tubes = names.map(name => root.getObjectByName(name)), starts = tubes.map(n => n.position.clone())
  const armor = root.getObjectByName('BridgeArmor_Front_00'), original = armor.quaternion.clone()
  rig.apply(1, 0)
  tubes.forEach((n, i) => assert.ok(n.position.distanceTo(starts[i]) > 1.9))
  assert.ok(armor.quaternion.angleTo(original) > .7)
  assert.ok(armor.children.some(n => n.type === 'Object3D'), 'Shield joint must carry exported geometry')
})

test('only twin and quad secondary mounts scan after deployment', () => {
  const { root, nodes, rig } = loadRig()
  const fixed = nodes.filter(n => n.userData.staticJoint && /^(Main_|Axial_|Defense_)/.test(n.name))
  rig.apply(1, 0)
  const original = fixed.map(n => [...n.position.toArray(), ...n.quaternion.toArray()])
  const twin = root.getObjectByName('SideBattery_1_Port').quaternion.clone()
  const quad = root.getObjectByName('PDC_Starboard_Gimbal').quaternion.clone()
  rig.apply(1, 10)
  assert.deepEqual(fixed.map(n => [...n.position.toArray(), ...n.quaternion.toArray()]), original)
  assert.ok(twin.angleTo(root.getObjectByName('SideBattery_1_Port').quaternion) > .02)
  assert.ok(quad.angleTo(root.getObjectByName('PDC_Starboard_Gimbal').quaternion) > .005)
  rig.apply(.9, 10)
  assert.ok(root.getObjectByName('PDC_Starboard_Gimbal').quaternion.angleTo(new THREE.Quaternion()) < 1e-6)
})

test('bridge-side twin barrels aim slightly above the hull with distinct headings', () => {
  const { root, rig } = loadRig()
  rig.apply(1, 20)
  for (const side of ['Port', 'Starboard']) {
    const headings = [2, 4].map(index => {
      const gun = root.getObjectByName(`SideBattery_${index}_${side}`)
      const direction = new THREE.Vector3(...gun.userData.sourceBoreDirection).applyQuaternion(gun.quaternion).normalize()
      const elevation = THREE.MathUtils.radToDeg(Math.asin(direction.y))
      assert.ok(elevation > 4 && elevation < 8, `Actual barrel elevation ${elevation}`)
      return Math.atan2(direction.x, -direction.z)
    })
    assert.ok(Math.abs(headings[1] - headings[0]) > .2, 'Twin headings must be visibly staggered')
  }
})

test('scrubbing backward restores every joint exactly without scaling rigid armor', () => {
  const { nodes, rig } = loadRig()
  const joints = nodes.filter(n => n.userData.staticJoint)
  const scales = joints.map(n => n.scale.toArray())
  rig.apply(0, 10)
  const initial = joints.map(n => [...n.position.toArray(), ...n.quaternion.toArray()])
  for (const d of [.25, .5, .75, 1, .6, .1, 0]) {
    rig.apply(d, 10)
    for (const n of joints) assert.ok(Math.abs(n.quaternion.length() - 1) < 1e-6)
  }
  assert.deepEqual(joints.map(n => [...n.position.toArray(), ...n.quaternion.toArray()]), initial)
  assert.deepEqual(joints.map(n => n.scale.toArray()), scales)
})
