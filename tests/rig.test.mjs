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

test('polygonal side armor releases the serrated lip before translating to its exposed endpoint', () => {
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
      const direction = bank === 'Dorsal' ? 1 : -1
      const clearance = new THREE.Vector3(...plate.userData.clearanceLift)
      const seamRelease = new THREE.Vector3(...plate.userData.seamReleaseVector)
      assert.ok(seamRelease.y > 0 && seamRelease.y <= 1, 'Close-fitting aft seams need only a short forward release')
      const maxDescent = bank === 'Dorsal' ? 6.4 : 3
      assert.equal(clearance.x, 0)
      assert.equal(clearance.y, 0)
      assert.ok(Math.abs(clearance.z * direction - (bank === 'Dorsal' ? .8 : 2.2)) < 1e-6, 'The initial lift is only the authored serration clearance')
      assert.ok(Math.abs(x) <= 9.6 + 1e-6 && Math.abs(z) <= maxDescent + 1e-6, `${bank} armor must stop on the short exterior guide instead of sinking into the hull`)
      rig.apply(.05, 0)
      assert.ok((plate.position.y - closedPosition.y) * direction > .01, 'The skin lifts away from the teeth before lateral movement')
      assert.ok(Math.abs(plate.position.x - closedPosition.x) < 1e-6, 'Outboard movement waits for serration release')
      for (const d of [.03, .07, .14, .21, .28, .34, .5, 1]) {
        rig.apply(d, 0)
        assert.ok(plate.quaternion.angleTo(closedRotation) < 1e-6, `${bank} ${side} rotated at ${d}`)
        assert.ok(Math.abs(plate.position.x - closedPosition.x) <= Math.abs(x) + 1e-6, `${bank} ${side} overshoots the outboard endpoint`)
        const outward = (plate.position.y - closedPosition.y) * direction
        assert.ok(outward <= Math.abs(clearance.z) + 1e-6, `${bank} ${side} exceeds the tooth-clearance lift`)
        assert.ok(outward >= -Math.abs(z) - 1e-6, `${bank} ${side} descends past the exterior endpoint`)
        assert.ok(closedPosition.z - plate.position.z >= -1e-6 && closedPosition.z - plate.position.z <= seamRelease.y + 1e-6, 'Forward release stays within the short mating-seam allowance')
      }
      rig.apply(1, 0)
      const expected = closedPosition.clone().add(new THREE.Vector3(x, z, -y-seamRelease.y))
      assert.ok(plate.position.distanceTo(expected) < 1e-6, 'Armor parks on the shortened guide endpoint')
      rig.apply(0, 0)
      assert.ok(plate.position.distanceTo(closedPosition) < 1e-6, `${bank} ${side} did not return exactly`)
    }
  }
})

test('the aft armor fillers fold 130 degrees around fixed hull-lip hinges before their shrouds rise', () => {
  const { root, rig } = loadRig()
  for (const bank of ['Dorsal', 'Ventral']) for (const side of ['Port', 'Starboard']) {
    rig.apply(0, 0)
    const apron = root.getObjectByName(`Hatch_${bank}_Aft_${side}`)
    const start = apron.position.clone(), turn = apron.quaternion.clone()
    assert.equal(apron.userData.hullFacesRemoved, 0, 'Filling the gap must preserve the original fixed hull faces')
    assert.equal(apron.parent.name, 'Odin_Asset', 'Aft armor belongs to the hull, not the rising cradle')
    assert.deepEqual(apron.userData.slideVector, [0, 0, 0], 'Aft fillers rotate without a slide offset')
    assert.equal(Math.abs(apron.userData.openingAngleDegrees), 130)
    const axis = new THREE.Vector3(apron.userData.hingeAxis[0], apron.userData.hingeAxis[2], -apron.userData.hingeAxis[1]).normalize()
    const edgeWorld = apron.userData.hingeEdge.map(([x, y, z]) => apron.parent.localToWorld(new THREE.Vector3(x, z, -y)))
    const edgeLocal = edgeWorld.map(p => apron.worldToLocal(p.clone()))
    for (const d of [.08, .16, .24, .32, .5, 1]) {
      rig.apply(d, 0)
      assert.ok(apron.position.distanceTo(start) < 1e-6, 'The fixed hull hinge must not translate')
      edgeLocal.forEach((p, index) => assert.ok(apron.localToWorld(p.clone()).distanceTo(edgeWorld[index]) < 1e-5, 'The entire sloped hinge edge remains fixed'))
    }
    rig.apply(.32, 0)
    const open = apron.quaternion.clone()
    const expected = new THREE.Quaternion().setFromAxisAngle(axis, THREE.MathUtils.degToRad(apron.userData.openingAngleDegrees)).multiply(turn)
    assert.ok(open.angleTo(expected) < 1e-6, 'Gap filler opens around its authored axis in the correct direction')
    assert.ok(Math.abs(THREE.MathUtils.radToDeg(open.angleTo(turn)) - 130) < 1e-5)
    for (const d of [.36, .5, .75, 1]) {
      rig.apply(d, 0)
      assert.ok(apron.position.distanceTo(start) < 1e-6, 'The hinge stays fixed while its shroud rises')
      assert.ok(apron.quaternion.angleTo(open) < 1e-6, 'Filler stays folded clear while its shroud rises')
    }
    rig.apply(0, 0)
    assert.ok(apron.position.distanceTo(start) < 1e-6)
    assert.ok(apron.quaternion.angleTo(turn) < 1e-6)
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

test('all three main tubes telescope in sync while retaining their full SCM reach', () => {
  const { root, rig } = loadRig()
  const sourcePositions = new Map()
  for (const bank of ['Dorsal', 'Ventral']) for (const leaf of ['Port', 'Center', 'Starboard']) {
    const name = `Main_${bank}_Tube_${leaf}`, tube = root.getObjectByName(name)
    sourcePositions.set(name, tube.position.clone())
  }
  rig.apply(0, 0)
  const stowed = new Map()
  for (const bank of ['Dorsal', 'Ventral']) for (const leaf of ['Port', 'Center', 'Starboard']) {
    const name = `Main_${bank}_Tube_${leaf}`, tube = root.getObjectByName(name)
    stowed.set(name, tube.position.clone())
    // The original visible inner bore is about 34 units long. The red-line
    // target removes about 40% of that exposed length (at least 13.5 units).
    assert.ok(tube.position.z - sourcePositions.get(name).z >= 13.5, `${name} still protrudes past the marked stow line`)
  }
  for (const d of [.1, .2, .34, .5, .65]) {
    rig.apply(d, 0)
    for (const [name, position] of stowed) {
      assert.ok(root.getObjectByName(name).position.distanceTo(position) < 1e-6, `${name} extends before the armor and cradle clear`)
    }
  }
  rig.apply(1, 0)
  for (const bank of ['Dorsal', 'Ventral']) for (const leaf of ['Port', 'Center', 'Starboard']) {
    const name = `Main_${bank}_Tube_${leaf}`, tube = root.getObjectByName(name)
    const endOffset = leaf === 'Center' ? new THREE.Vector3() : new THREE.Vector3(0, bank === 'Dorsal' ? -.389 : .389, -2)
    const expected = sourcePositions.get(name).clone().add(endOffset)
    assert.ok(tube.position.distanceTo(expected) < 1e-6, `${name} changed the existing fully deployed reach`)
    assert.ok(tube.position.distanceTo(stowed.get(name)) >= 15.5, `${name} lacks the deeper telescopic stroke`)
    const axis = new THREE.Vector3(tube.userData.boreAxis[0], tube.userData.boreAxis[2], -tube.userData.boreAxis[1]).normalize()
    assert.ok(tube.position.clone().sub(stowed.get(name)).normalize().angleTo(axis) < 1e-6, `${name} slips across its bore axis`)
  }
  for (const d of [.67, .72, .8, .9, .93, .8, .72]) {
    rig.apply(d, 0)
    const fractions = [...stowed].map(([name, start]) => {
      const tube = root.getObjectByName(name)
      return tube.position.distanceTo(start) / tube.userData.stowTravel
    })
    assert.ok(fractions.every(f => Math.abs(f - fractions[0]) < 1e-6), 'Center and both outer tubes must share the same extension progress')
  }
  // The same reverse timeline must finish tube retraction while the armor
  // remains parked, with no direction-dependent state after scrubbing.
  rig.apply(.65, 0)
  for (const [name, position] of stowed) assert.ok(root.getObjectByName(name).position.distanceTo(position) < 1e-6)
  rig.apply(0, 0)
  for (const [name, position] of stowed) assert.ok(root.getObjectByName(name).position.distanceTo(position) < 1e-6)
})

test('the original front bridge shields actually open', () => {
  const { root, rig } = loadRig()
  rig.apply(0, 0)
  const armor = root.getObjectByName('BridgeArmor_Front_00'), original = armor.quaternion.clone()
  rig.apply(1, 0)
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
