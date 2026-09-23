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

test('all five main armor pieces clear before the barrels or armored cradle move', () => {
  const { root, rig } = loadRig()
  rig.apply(0, 0)
  const door = root.getObjectByName('Hatch_Dorsal_Port')
  const barrel = root.getObjectByName('Main_Dorsal_Barrels')
  const mount = root.getObjectByName('Main_Dorsal_Mount')
  const first = { door: door.position.clone(), barrel: barrel.position.clone(), rotation: barrel.quaternion.clone(), mount: mount.position.clone() }
  rig.apply(.20, 0)
  assert.ok(door.position.distanceTo(first.door) > 3, 'Foredeck armor slides clear before the cradle rises')
  assert.ok(barrel.position.distanceTo(first.barrel) < 1e-6, 'Guns wait while the side plates descend')
  assert.ok(mount.position.distanceTo(first.mount) < 1e-6, 'Housing waits until the barrels emerge')
  for (const d of [.10, .20, .30, .34]) {
    rig.apply(d, 0)
    assert.ok(barrel.position.distanceTo(first.barrel) < 1e-6, `Barrels move before armor clearance at ${d}`)
    assert.ok(barrel.quaternion.angleTo(first.rotation) < 1e-6, `Barrels pitch into armor at ${d}`)
  }
  rig.apply(.34, 0)
  const doorOpen = door.position.clone()
  rig.apply(.55, 0)
  assert.ok(door.position.distanceTo(doorOpen) < 1e-6, 'Armor remains parked during the cradle lift')
  assert.ok(barrel.position.distanceTo(first.barrel) > 1, 'Gun bodies emerge after the armor is parked')
  rig.apply(.70, 0)
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
  rig.apply(.50, 3)
  const level = root.getObjectByName('Main_Dorsal_Barrels').quaternion.clone()
  for (const d of [.55, .75, 1]) {
    rig.apply(d, 3)
    assert.ok(root.getObjectByName('Main_Dorsal_Barrels').quaternion.angleTo(level) < 1e-6, `Bores pitch during visible travel at ${d}`)
  }
})

test('polygonal side armor clears outboard before descending into the hull without rotation', () => {
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
      assert.ok(plate.userData.closedOutlineXY.length >= 6, 'The skin has shroud and foredeck chamfers')
      assert.ok(Math.abs(plate.userData.guideExit[0]) > 13, 'The first travel leg clears the bore corridor')
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

test('the aft armor skirts retract independently before their shrouds rise', () => {
  const { root, rig } = loadRig()
  for (const bank of ['Dorsal', 'Ventral']) for (const side of ['Port', 'Starboard']) {
    rig.apply(0, 0)
    const apron = root.getObjectByName(`Hatch_${bank}_Aft_${side}`)
    const start = apron.position.clone(), turn = apron.quaternion.clone()
    assert.equal(apron.userData.sourceObject, bank === 'Dorsal' ? 'holo.001' : 'holo.013')
    assert.equal(apron.parent.name, 'Odin_Asset', 'Aft armor belongs to the hull, not the rising cradle')
    rig.apply(.32, 0)
    const clear = apron.position.clone()
    assert.ok(clear.distanceTo(start) > 9, 'Skirt descends before gun rise')
    for (const d of [.36, .5, .75, 1]) {
      rig.apply(d, 0)
      assert.ok(apron.position.distanceTo(clear) < 1e-6, 'Skirt stays parked while its shroud rises')
      assert.ok(apron.quaternion.angleTo(turn) < 1e-6, 'Skirt translates without hinging')
    }
    rig.apply(0, 0)
    assert.ok(apron.position.distanceTo(start) < 1e-6)
  }
})

test('the short fore-end wedge lifts before sliding forward and closes exactly', () => {
  const { root, rig } = loadRig()
  for (const bank of ['Dorsal', 'Ventral']) {
    rig.apply(0, 0)
    const plate = root.getObjectByName(`Hatch_${bank}_Nose`)
    const start = plate.position.clone(), turn = plate.quaternion.clone()
    rig.apply(.10, 0)
    assert.ok(Math.abs(plate.position.y - start.y) > .8, 'Nose first lifts away from its seal')
    assert.ok(Math.abs(plate.position.z - start.z) < 1e-6, 'Forward travel waits for the seal clearance')
    rig.apply(.31, 0)
    assert.ok(start.z - plate.position.z > 12, 'The short cap slides toward the bow')
    const open = plate.position.clone()
    rig.apply(1, 0)
    assert.ok(plate.position.distanceTo(open) < 1e-6, 'Nose stays clear throughout the turret rise')
    assert.ok(plate.quaternion.angleTo(turn) < 1e-6)
    rig.apply(0, 0)
    assert.ok(plate.position.distanceTo(start) < 1e-6)
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
