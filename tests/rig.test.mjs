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
  const meshBounds = new Map()
  gltf.nodes.forEach((node, index) => {
    if (node.mesh === undefined) return
    const bounds = new THREE.Box3()
    for (const primitive of gltf.meshes[node.mesh].primitives) {
      const position = gltf.accessors[primitive.attributes.POSITION]
      if (position.min && position.max) bounds.union(new THREE.Box3(new THREE.Vector3(...position.min), new THREE.Vector3(...position.max)))
    }
    if (!bounds.isEmpty()) meshBounds.set(nodes[index], bounds)
  })
  return { root, nodes, meshBounds, rig: createOdinRig(root) }
}

function relativeMatrix(object, reference) {
  return reference.matrixWorld.clone().invert().multiply(object.matrixWorld)
}

function assertMatrixClose(actual, expected, message, tolerance = 1e-6) {
  const error = Math.max(...actual.elements.map((value, i) => Math.abs(value - expected.elements[i])))
  assert.ok(error < tolerance, `${message}; matrix error ${error}`)
}

function mainAssemblies(root) {
  return ['Dorsal', 'Ventral'].flatMap(bank => ['Port', 'Center', 'Starboard'].map(role => {
    const coverRole = bank === 'Ventral' && role !== 'Center' ? (role === 'Port' ? 'Starboard' : 'Port') : role
    return {
      bank, role, outward: bank === 'Dorsal' ? 1 : -1,
      carrier: root.getObjectByName(`Main_${bank}_Carrier_${role}`),
      shroud: root.getObjectByName(`Main_${bank}_Shroud_${coverRole}`),
      tube: root.getObjectByName(`Main_${bank}_Tube_${role}`),
    }
  }))
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
  assert.ok(barrel.position.distanceTo(first.barrel) > .1, 'Gun bodies emerge after the armor is parked')
  rig.apply(.70, 0)
  assert.ok(mount.position.distanceTo(first.mount) > .2, 'Armored cradle rises and advances')
  for (let d = 0; d <= 1; d += .01) {
    rig.apply(d, 0)
    if (d < .35) assert.ok(root.getObjectByName('Axial_Bow_Barrel').quaternion.angleTo(new THREE.Quaternion()) < 1e-6)
  }
})

test('every main bore follows its physical cover as a rigid assembly throughout the common stroke', () => {
  const { root, rig } = loadRig()
  const assemblies = mainAssemblies(root)
  rig.apply(1, 0)
  root.updateMatrixWorld(true)
  const reference = assemblies.map(({ carrier, shroud }) => relativeMatrix(carrier, shroud))
  for (let index = 0; index <= 1000; index++) {
    const d = index / 1000
    rig.apply(d, 3)
    root.updateMatrixWorld(true)
    assemblies.forEach(({ bank, role, carrier, shroud, tube }, i) => {
      assert.equal(tube.parent, carrier, 'The telescopic tube travels with its own collar and breech')
      assert.ok(carrier.children.some(child => child.name.includes('CarrierMesh')), 'The rigid assembly includes the original collar and breech')
      const relative = relativeMatrix(carrier, shroud)
      if (role === 'Center' || d >= .56) assertMatrixClose(relative, reference[i], `${bank} ${role} slips relative to its physical cover at ${d}`)
      assert.ok(new THREE.Quaternion().setFromRotationMatrix(relative).angleTo(new THREE.Quaternion().setFromRotationMatrix(reference[i])) < 1e-6, `${bank} ${role} twists independently of its cover at ${d}`)
    })
  }
  // Reverse evaluation must preserve the same rigid relationship after arbitrary seeks.
  for (const d of [.9, .55, .8, .44, .34, 0]) {
    rig.apply(d, 7)
    root.updateMatrixWorld(true)
    assemblies.forEach(({ bank, role, carrier, shroud }, i) => {
      if (role === 'Center' || d >= .56) assertMatrixClose(relativeMatrix(carrier, shroud), reference[i], `${bank} ${role} loses its cover attachment after scrubbing`)
    })
  }
})

test('the centre bore and its cover travel without a downward or backward rebound', () => {
  const { root, rig, meshBounds } = loadRig()
  const probes = []
  for (const bank of ['Dorsal', 'Ventral']) {
    const tube = root.getObjectByName(`Main_${bank}_Tube_Center`)
    tube.traverse(mesh => {
      const bounds = meshBounds.get(mesh)
      if (!bounds) return
      const centre = bounds.getCenter(new THREE.Vector3())
      probes.push({ bank, object: mesh, point: centre, label: 'tube midpoint' })
      // Follow the measured bore axis through the exported mesh bounds, with
      // Blender-to-glTF coordinates and the mesh's own transform accounted for.
      const axis = tube.userData.boreAxis
      const direction = new THREE.Vector3(axis[0], axis[2], -axis[1])
        .transformDirection(tube.matrixWorld).transformDirection(mesh.matrixWorld.clone().invert())
      const distance = Math.min(...['x', 'y', 'z'].filter(key => Math.abs(direction[key]) > 1e-8)
        .map(key => ((direction[key] > 0 ? bounds.max[key] : bounds.min[key]) - centre[key]) / direction[key]))
      probes.push({ bank, object: mesh, point: centre.clone().addScaledVector(direction, distance), label: 'tube forward section' })
    })
    probes.push({ bank, object: root.getObjectByName(`Main_${bank}_Shroud_Center`), point: new THREE.Vector3(), label: 'cover pivot' })
  }
  assert.ok(probes.length >= 6, 'Both centre bores require actual exported mesh bounds')
  let previous
  const initial = []
  for (let index = 0; index <= 1000; index++) {
    const d = index / 1000
    rig.apply(d, 0)
    root.updateMatrixWorld(true)
    const current = probes.map(({ object, point }) => point.clone().applyMatrix4(object.matrixWorld))
    if (!index) initial.push(...current.map(point => point.clone()))
    current.forEach((point, i) => {
      if (!previous) return
      const { bank, label } = probes[i], outward = bank === 'Dorsal' ? 1 : -1
      assert.ok((point.y - previous[i].y) * outward >= -1e-8, `${bank} ${label} dips back into the hull at ${d}`)
      assert.ok(point.z - previous[i].z <= 1e-8, `${bank} ${label} reverses toward the stern at ${d}`)
      if (d <= .40) assert.ok(point.distanceTo(initial[i]) < 1e-7, 'The centre and its cover wait for armor clearance and the start of outer-bore seating')
    })
    previous = current
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
      assert.ok(seamRelease.y > 0 && seamRelease.y <= 1.1, 'Close-fitting aft seams need only a short forward release')
      const maxDescent = bank === 'Dorsal' ? 6.4 : 3
      assert.equal(clearance.x, 0)
      assert.equal(clearance.y, 0)
      assert.ok(Math.abs(clearance.z * direction - (bank === 'Dorsal' ? .75 : 2.2)) < 1e-6, 'The reinforced dorsal plate releases its fitted lip before travel')
      assert.ok(Math.abs(x) <= 9.6 + 1e-6 && Math.abs(z) <= maxDescent + 1e-6, `${bank} armor must stop on the short exterior guide instead of sinking into the hull`)
      rig.apply(.05, 0)
      assert.ok((plate.position.y - closedPosition.y) * direction > 1e-5, 'The skin lifts away from the teeth before lateral movement')
      assert.ok(Math.abs(plate.position.x - closedPosition.x) < 1e-6, 'Outboard movement waits for serration release')
      if (bank === 'Dorsal') assert.ok(closedPosition.z - plate.position.z > .1, 'The fitted rear edge releases forward before it can scrape the closed shroud')
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
    rig.apply(bank === 'Dorsal' ? .07 : .10, 0)
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
  assert.ok(Math.abs(pod.position.distanceTo(start) - 2) < 1e-6)
  arms.forEach((n, i) => {
    const travel = n.getWorldPosition(new THREE.Vector3()).distanceTo(locations[i])
    assert.ok(travel > .14 && travel < .17, 'The bore retracts on its rail while its rear support stays outside the hull')
  })
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
    assert.ok(tube.userData.stowTravel >= 16, `${name} must retain at least the approved recessed stroke`)
    assert.ok(Math.abs(tube.position.distanceTo(stowed.get(name)) - tube.userData.stowTravel) < 1e-6, `${name} does not follow its authored telescopic stroke`)
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

test('outer bores finish a short sink after their covers stop on the return stroke', () => {
  const { root, rig } = loadRig()
  const outer = mainAssemblies(root).filter(({ role }) => role !== 'Center')
  rig.apply(.40, 0)
  root.updateMatrixWorld(true)
  const seated = outer.map(({ carrier, shroud }) => ({
    cover: shroud.matrixWorld.clone(),
    bore: carrier.getWorldPosition(new THREE.Vector3()),
    turn: carrier.getWorldQuaternion(new THREE.Quaternion()),
  }))
  rig.apply(.34, 0)
  root.updateMatrixWorld(true)
  const closed = outer.map(({ carrier }) => carrier.getWorldPosition(new THREE.Vector3()))
  outer.forEach(({ bank, outward }, i) => {
    const finalSink = (seated[i].bore.y - closed[i].y) * outward
    assert.ok(finalSink > .003 && finalSink < .008, `${bank} final descent should be short, not a second full stroke: ${finalSink}`)
  })
  let previous = seated.map(({ bore }) => bore.clone())
  for (let index = 0; index <= 60; index++) {
    const d = .40 - index / 1000
    rig.apply(d, 0)
    root.updateMatrixWorld(true)
    outer.forEach(({ bank, role, outward, carrier, shroud }, i) => {
      assertMatrixClose(shroud.matrixWorld, seated[i].cover, `${bank} ${role} cover moves during the separate final sink`, 1e-8)
      assert.ok(carrier.getWorldQuaternion(new THREE.Quaternion()).angleTo(seated[i].turn) < 1e-6, 'The final sink translates the complete bore without pitching it')
      const point = carrier.getWorldPosition(new THREE.Vector3())
      const stroke = closed[i].clone().sub(seated[i].bore), travelled = point.clone().sub(seated[i].bore)
      assert.ok(travelled.clone().cross(stroke).length() < 1e-8, 'The bore follows one straight seating guide')
      assert.ok((point.y - previous[i].y) * outward <= 1e-8, `${bank} ${role} rises again during final seating at ${d}`)
      assert.ok(point.distanceTo(closed[i]) <= previous[i].distanceTo(closed[i]) + 1e-8, 'The sink approaches its endpoint without reversing')
      previous[i] = point
    })
  }
  for (const d of [.3, .15, 0]) {
    rig.apply(d, 0)
    root.updateMatrixWorld(true)
    outer.forEach(({ carrier, shroud }, i) => {
      assert.ok(carrier.getWorldPosition(new THREE.Vector3()).distanceTo(closed[i]) < 1e-7, 'The bores remain seated while the bay armor closes')
      assertMatrixClose(shroud.matrixWorld, seated[i].cover, 'The individual cover stays seated while the bay armor closes', 1e-8)
    })
  }
})

test('outer bores keep moving through the handoff to the shared lift in both directions', () => {
  const { root, rig } = loadRig()
  const outer = mainAssemblies(root).filter(({ role }) => role !== 'Center')
  const samples = []
  for (let index = 0; index <= 1000; index++) {
    rig.apply(index / 1000, 0)
    root.updateMatrixWorld(true)
    samples.push(outer.map(({ carrier }) => carrier.getWorldPosition(new THREE.Vector3())))
  }
  for (let index = 341; index <= 930; index++) outer.forEach(({ bank, role, outward }, i) => {
    const speed = (samples[index][i].y - samples[index - 1][i].y) * outward * 1000
    assert.ok(speed > 0, `${bank} ${role} stops or reverses during its lift at ${index / 1000}`)
    // Inspect actual world travel, not a copy of the two animation curves.
    // The old curve fell to zero around 44–46% and visibly started a second time.
    if (index >= 400 && index <= 600) assert.ok(speed > .06, `${bank} ${role} visibly stalls during the handoff: ${speed}`)
  })
  for (let index = 650; index >= 340; index--) {
    rig.apply(index / 1000, 0)
    root.updateMatrixWorld(true)
    outer.forEach(({ carrier }, i) => assert.ok(carrier.getWorldPosition(new THREE.Vector3()).distanceTo(samples[index][i]) < 1e-8, 'Reversing follows the same continuous path'))
  }
})

test('stowed outer bores nest just below their covers without the former deep drop', () => {
  const { root, rig } = loadRig()
  const outer = mainAssemblies(root).filter(({ role }) => role !== 'Center')
  rig.apply(1, 0); root.updateMatrixWorld(true)
  const attachments = outer.map(({ carrier, shroud }) => relativeMatrix(carrier, shroud))
  rig.apply(0, 0); root.updateMatrixWorld(true)
  outer.forEach(({ bank, role, outward, carrier, shroud }, i) => {
    const seated = new THREE.Vector3().setFromMatrixPosition(shroud.matrixWorld.clone().multiply(attachments[i]))
    const stowed = carrier.getWorldPosition(new THREE.Vector3())
    const depth = (seated.y - stowed.y) * outward
    assert.ok(depth > .02 && depth < .03, `${bank} ${role} stow depth should be 2–3 model cm, not the former 5.2 cm: ${depth}`)
  })
})

test('the main mechanism preserves its approved deployed world transforms and hull armor behavior', () => {
  const baseline = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.8.3/baseline/v0.8.2-clearance-poses.json', import.meta.url), 'utf8'))
  assert.equal(baseline.length, 101)
  const { root, nodes, rig } = loadRig()
  const staticNodes = new Map(nodes.filter(node => node.userData.staticJoint).map(node => [node.name, node]))
  rig.apply(0, 20)
  const fixedAftPivots = new Map([...staticNodes].filter(([name]) => /^Hatch_(Dorsal|Ventral)_Aft_/.test(name)).map(([name, object]) => [name, object.position.clone()]))
  for (const pose of baseline) {
    rig.apply(pose.deployment, 20)
    for (const expected of pose.joints) {
      if (/^(Main_|SideBattery_|Axial_|Defense|PDC_|BridgeArmor_)/.test(expected.name)) continue
      const actual = staticNodes.get(expected.name)
      assert.ok(actual, `Missing unchanged system joint ${expected.name}`)
      // v0.8.10 fits the aft axes to the real material attachment edges.
      // The dedicated hinge test verifies those intentional axes and the
      // unchanged 130-degree turn; their origins stay fixed throughout.
      // Those origins must stay fixed throughout the motion. v0.8.8 also
      // shortens the dorsal main-skin lift and releases its fitted rear seam
      // earlier; the guide/return test above checks that intentional change.
      // v0.8.11 releases the thicker dorsal nose earlier; its dedicated test
      // checks lift-before-slide and identical endpoints. Other systems stay.
      const expectedPosition = fixedAftPivots.get(expected.name) || new THREE.Vector3(...expected.position)
      if (!/^Hatch_Dorsal_(Port|Starboard|Nose)$/.test(expected.name)) {
        assert.ok(actual.position.distanceTo(expectedPosition) < 1e-7, `${expected.name} moved from its fixed reference at ${pose.deployment}`)
      }
      // Some source quaternions carry float32 length error. Comparing their
      // components avoids angleTo reporting a false turn for identical values.
      const quaternion = actual.quaternion.toArray()
      const turnError = Math.min(...[1, -1].map(sign => Math.max(...quaternion.map((value, i) => Math.abs(value - sign * expected.quaternion[i])))))
      if (!fixedAftPivots.has(expected.name)) assert.ok(turnError < 1e-8, `${expected.name} turned from v0.8.2 at ${pose.deployment}`)
    }
  }
  rig.apply(1, 20)
  root.updateMatrixWorld(true)
  const deployed = new Map([...staticNodes].filter(([name]) => name.startsWith('Main_')).map(([name, object]) => [name, object.matrixWorld.clone()]))
  const reference = loadRig()
  const referenceNodes = new Map(reference.nodes.map(node => [node.name, node]))
  for (const joint of baseline.at(-1).joints) {
    const object = referenceNodes.get(joint.name)
    if (!object) continue
    object.position.fromArray(joint.position)
    object.quaternion.fromArray(joint.quaternion)
  }
  reference.root.updateMatrixWorld(true)
  for (const [name, matrix] of deployed) assertMatrixClose(matrix, referenceNodes.get(name).matrixWorld, `${name} changed the approved fully deployed position`, 1e-7)
})

test('the fixed bridge has no remaining armor mechanism', () => {
  const { nodes } = loadRig()
  assert.equal(nodes.filter(n => n.name.startsWith('BridgeArmor_') || n.userData.system === 'bridge-armor').length, 0)
})

test('all eleven single batteries stay fixed in SCM; only real twin and quad mounts scan', () => {
  const { root, nodes, rig } = loadRig()
  const fixed = nodes.filter(n => n.userData.staticJoint && /^(Main_|Axial_|SideBattery_)/.test(n.name))
  rig.apply(1, 0)
  const original = fixed.map(n => [...n.position.toArray(), ...n.quaternion.toArray()])
  const twin = root.getObjectByName('Defense_01_Yaw').quaternion.clone()
  const quad = root.getObjectByName('PDC_Starboard_Gimbal').quaternion.clone()
  rig.apply(1, 10)
  assert.deepEqual(fixed.map(n => [...n.position.toArray(), ...n.quaternion.toArray()]), original)
  assert.ok(twin.angleTo(root.getObjectByName('Defense_01_Yaw').quaternion) > .02)
  assert.ok(quad.angleTo(root.getObjectByName('PDC_Starboard_Gimbal').quaternion) > .005)
  rig.apply(.9, 10)
  assert.ok(root.getObjectByName('PDC_Starboard_Gimbal').quaternion.angleTo(new THREE.Quaternion()) < 1e-6)
})

test('all eight actual twin batteries, including the lower starboard bridge pair, point above the horizon', () => {
  const { root, rig } = loadRig()
  rig.apply(1, 20)
  for (const indices of [[1, 2], [3, 4], [5, 6], [7, 8]]) {
    const headings = indices.map(index => {
      const gun = root.getObjectByName(`Defense_${String(index).padStart(2, '0')}_Elevation`)
      const [x,y,z] = gun.userData.sourceBoreDirectionModel
      const direction = new THREE.Vector3(x,z,-y).applyQuaternion(gun.getWorldQuaternion(new THREE.Quaternion())).normalize()
      const elevation = THREE.MathUtils.radToDeg(Math.asin(direction.y))
      assert.ok(elevation > 4 && elevation < 8, `Actual barrel elevation ${elevation}`)
      return Math.atan2(direction.x, -direction.z)
    })
    assert.ok(Math.abs(headings[1] - headings[0]) > .2, 'Twin headings must be visibly staggered')
  }
})

test('every single barrel pitches in its own vertical plane about the rear breech', () => {
  const { nodes, rig } = loadRig()
  const singles = nodes.filter(n => n.userData.singleBattery)
  assert.equal(singles.length, 11)
  for (const gun of singles) {
    assert.equal(gun.userData.trunnionAdvance, 0, `${gun.name} must use the marked rear trunnion`)
    const map = ([x,y,z]) => new THREE.Vector3(x,z,-y)
    const original = map(gun.userData.sourceBoreDirectionModel).normalize()
    const normal = map(gun.userData.outwardNormal).normalize()
    const transverse = original.clone().cross(normal).normalize()
    for (let i = 0; i <= 100; i++) {
      rig.apply(i / 100, 0)
      const direction = original.clone().applyQuaternion(gun.quaternion)
      assert.ok(Math.abs(direction.dot(transverse)) < 1e-6, `${gun.name} yaws out of its elevation plane`)
      if (i > (gun.userData.sideBatteryMechanism ? 67 : 40)) assert.ok(direction.dot(normal) > original.dot(normal), `${gun.name} elevates into the hull`)
    }
    assert.equal(nodes.filter(n => n.userData.barrelJoint === gun.name).length, 6, `${gun.name} requires three leaves per side`)
    if (gun.userData.sideBatteryMechanism) assert.equal(nodes.filter(n => n.userData.battery === gun.name && n.userData.system === 'side-front-slider').length, 2, `${gun.name} requires paired first-group sliders`)
    else assert.equal(nodes.filter(n => n.userData.barrel === gun.name).length, 1, `${gun.name} requires an independent front cap`)
  }
})

test('original single covers keep their source open pose and stagger root-first', () => {
  const { nodes, rig } = loadRig()
  const sourceRotations = new Map(nodes.map(n => [n.name, n.quaternion.clone()]))
  rig.apply(1, 0)
  for (const cap of nodes.filter(n => n.userData.system === 'single-front-cap')) {
    const leaves = nodes.filter(n => n.userData.barrelJoint === cap.userData.barrel)
    for (const leaf of leaves) {
      assert.ok(Math.abs(leaf.userData.armorThickness-cap.userData.armorThickness)<1e-6)
      assert.equal(leaf.userData.sourceGeometry, true, 'Use the existing source cover')
      assert.ok(leaf.quaternion.angleTo(sourceRotations.get(leaf.name))<1e-7, 'SCM must stop at the original open position')
    }
    const panels = leaves.filter(n => n.name.includes('_Shutter_Port_')).sort((a,b)=>a.userData.panelIndex-b.userData.panelIndex)
    assert.ok(panels[0].userData.openEnd < panels[1].userData.openEnd && panels[1].userData.openEnd < panels[2].userData.openEnd)
    assert.ok(panels[0].userData.openEnd-panels[0].userData.openStart < panels[2].userData.openEnd-panels[2].userData.openStart)
  }
})

test('four flank first pairs lift before sliding and retain finite flat crowns', () => {
  const { nodes, rig } = loadRig()
  const sliders = nodes.filter(n => n.userData.system === 'side-front-slider')
  assert.equal(sliders.length, 8)
  const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  for (const slider of sliders) {
    rig.apply(0,0); const closed=slider.position.clone(), rotation=slider.quaternion.clone()
    rig.apply(.07,0)
    assert.ok(slider.position.clone().sub(closed).distanceTo(map(slider.userData.liftVector))<1e-6)
    rig.apply(.24,0)
    assert.ok(slider.position.clone().sub(closed).distanceTo(map(slider.userData.liftVector).add(map(slider.userData.slideVector)))<1e-6)
    assert.ok(slider.quaternion.angleTo(rotation)<1e-7)
    assert.equal(slider.userData.allowHullParkingIntersection, slider.name.includes('Battery_3_'))
  }
  for (const leaf of nodes.filter(n=>n.userData.system==='side-battery-leaf')) {
    assert.equal(leaf.userData.physicalHinge,true)
    assert.ok(leaf.userData.ridgeHalfWidth>.1)
    rig.apply(1,0);const position=leaf.position.clone(),open=leaf.quaternion.clone()
    rig.apply(0,0)
    assert.ok(leaf.position.distanceTo(position)<1e-6,'The hinge stays on its attachment rail')
    assert.ok(Math.abs(leaf.quaternion.angleTo(open)-Math.PI)<1e-6)
  }
})

test('flank rear cradle seats only after folding and carries gun plus groups 3 and 4 rigidly', () => {
  const { root,nodes,rig }=loadRig(), map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  for (const carriage of nodes.filter(n=>n.userData.system==='side-battery-carriage')) {
    const name=carriage.userData.battery, gun=root.getObjectByName(name)
    const carried=nodes.filter(n=>n.userData.barrelJoint===name && n.userData.armorGroup>=3)
    assert.ok(carriage.userData.originalOuterPedestalVertices>2000,'The complete source outer pedestal must travel with the rear cradle')
    assert.equal(carried.length,4);assert.equal(gun.parent,carriage)
    for(const leaf of carried)assert.equal(leaf.parent,carriage)
    for(const fixed of nodes.filter(n=>n.userData.barrelJoint===name && n.userData.armorGroup===2))assert.equal(fixed.parent.name,'Odin_Asset')
    rig.apply(.24,0);root.updateMatrixWorld(true)
    const origin=carriage.position.clone(), relatives=[gun,...carried].map(n=>relativeMatrix(n,carriage))
    rig.apply(.14,0);root.updateMatrixWorld(true)
    assert.ok(carriage.position.clone().sub(origin).distanceTo(map(carriage.userData.liftVector))<1e-6,'Finish lift before forward seating')
    rig.apply(0,0);root.updateMatrixWorld(true)
    assert.ok(carriage.position.clone().sub(origin).distanceTo(map(carriage.userData.liftVector).add(map(carriage.userData.slideVector)))<1e-6)
    for(let i=0;i<=24;i++) {
      rig.apply(i/100,0);root.updateMatrixWorld(true)
      ;[gun,...carried].forEach((n,k)=>assertMatrixClose(relativeMatrix(n,carriage),relatives[k],`${n.name} slips on the closing cradle`))
    }
  }
})

test('flank inclined edges meet after the complete carriage seats', () => {
  const {root,nodes,rig}=loadRig(), asset=root.getObjectByName('Odin_Asset')
  const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  rig.apply(0,0);root.updateMatrixWorld(true)
  for(const second of nodes.filter(n=>n.userData.system==='side-battery-leaf' && n.userData.armorGroup===2)) {
    const third=root.getObjectByName(second.name.replace('_02','_01'))
    const points=n=>n.userData.seamEdgeLocal.map(p=>asset.worldToLocal(n.localToWorld(map(p))))
    const a=points(second),b=points(third),axis=map(second.userData.hingeAxisModel).normalize()
    for(let i=0;i<2;i++)assert.ok(Math.abs(a[i].distanceTo(b[i])-.026)<.0001,`${second.name} leaves an open carriage seam`)
    assert.ok(Math.abs(a[1].clone().sub(a[0]).dot(axis))>.8,'The butt seam must be inclined rather than square-cut')
    assert.ok(a[1].clone().sub(a[0]).normalize().dot(b[1].clone().sub(b[0]).normalize())>.99999,'Mating edges stay parallel')
  }
  for(const slider of nodes.filter(n=>n.userData.system==='side-front-slider')) {
    const p=slider.userData.closedOutlineModel.map(v=>new THREE.Vector3(...v))
    // Both flat-ridge returns and both sloping corners are in this outline.
    // Pick the long edges of the sloping section on each end geometrically.
    const endA=p.slice(0,3),endB=p.slice(3).reverse()
    const edge=q=>q[1].distanceTo(q[0])>q[2].distanceTo(q[1])?q[1].clone().sub(q[0]):q[2].clone().sub(q[1])
    assert.ok(Math.abs(edge(endA).normalize().dot(edge(endB).normalize()))<.9,'The first leaf must have unequal end slopes')
  }
})

test('closed flank leaves have equal lengths and straight seams across the flat crown', () => {
  const {root,nodes,rig}=loadRig(),asset=root.getObjectByName('Odin_Asset')
  const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  rig.apply(0,0);root.updateMatrixWorld(true)
  for(const leaf of nodes.filter(n=>n.userData.system==='side-battery-leaf' && n.name.includes('_Shutter_Port_'))) {
    const paired=root.getObjectByName(leaf.name.replace('_Shutter_Port_','_Shutter_Starboard_'))
    const [lo,hi]=leaf.userData.closedLongitudinalRange
    assert.ok(Math.abs(hi-lo-8.70)<1e-6,'Groups 2, 3 and 4 must expose the same length')
    for(let end=0;end<2;end++) {
      const points=[leaf,paired].flatMap(n=>n.userData.crownSeamsLocal[end].map(p=>asset.worldToLocal(n.localToWorld(map(p)))))
      const direction=points[3].clone().sub(points[0]).normalize()
      for(const p of points)assert.ok(p.clone().sub(points[0]).cross(direction).length()<.0001,'The crown seam must be one straight line across both halves')
    }
  }
})

test('each source nose cap returns to its original deployed seat after sliding and settling', () => {
  const { nodes, rig } = loadRig()
  for (const cap of nodes.filter(n => n.userData.system === 'single-front-cap')) {
    const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
    assert.equal(cap.userData.sourceOpenPose, true)
    const deployed = cap.position.clone()
    rig.apply(0,0);const origin=cap.position.clone(),orientation=cap.quaternion.clone()
    rig.apply(.23,0);const slid=cap.position.clone().sub(origin)
    assert.ok(slid.distanceTo(map(cap.userData.slideVector).negate())<1e-6)
    rig.apply(1,0);const complete=cap.position.clone().sub(origin)
    assert.ok(complete.distanceTo(map(cap.userData.slideVector).add(map(cap.userData.settleVector)).negate())<1e-6)
    assert.ok(cap.position.distanceTo(deployed)<1e-6, 'The original model cap position is the deployed endpoint')
    assert.ok(cap.quaternion.angleTo(orientation)<1e-6, 'Nose cap translates without a hinge rotation')
  }
})

test('the four aft hull gates descend before twin carriages move and close after their return', () => {
  const { root, rig } = loadRig()
  for (let i = 5; i <= 8; i++) {
    const prefix = `Defense_${String(i).padStart(2, '0')}`
    const gate = root.getObjectByName(prefix + '_NotchGate'), carriage = root.getObjectByName(prefix + '_Carriage')
    assert.equal(gate.parent.name, 'Odin_Asset')
    rig.apply(0, 0)
    const closed = gate.position.clone(), parked = carriage.position.clone()
    rig.apply(.22, 0)
    assert.ok(closed.y - gate.position.y > 4, 'Gate must clear the notch before the carriage leaves')
    assert.ok(carriage.position.distanceTo(parked) < 1e-6)
    const open = gate.position.clone()
    for (const d of [.3, .5, .8, 1, .6, .25]) {
      rig.apply(d, 0)
      assert.ok(gate.position.distanceTo(open) < 1e-6)
    }
    rig.apply(0, 0)
    assert.ok(gate.position.distanceTo(closed) < 1e-6)
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
