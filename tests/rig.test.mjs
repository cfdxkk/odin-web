import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { createHash } from 'node:crypto'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { turretPoseProgress, reviewStrokeSeconds, retimeReviewCycle } from '../app/lib/turret-tempo.ts'
const tempoProfile = JSON.parse(fs.readFileSync(new URL('../app/lib/turret-tempo-profile.json', import.meta.url)))

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

// Older mechanical tests address the accepted pose path; the new tempo tests
// below exercise real timeline progress and measured speed.
function timelineForPose(pose, family) {
  const knots = tempoProfile[family].knots
  if (pose <= knots[0][1]) return 0
  for (let i = 1; i < knots.length; i++) {
    const [end, to] = knots[i], [start, from] = knots[i - 1]
    if (pose <= to) return start + (end - start) * (pose - from) / (to - from)
  }
  return 1
}
function loadRigAtPoseClock(family) {
  const result = loadRig(), apply = result.rig.apply
  result.rig.apply = (pose, time) => apply(timelineForPose(pose, family), time)
  return result
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
    if (d <= .30) assert.ok(root.getObjectByName('Axial_Bow_Barrel').quaternion.angleTo(new THREE.Quaternion()) < 1e-6)
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

test('original quad tubes retract independently while complete gray cradles retain the source frame-30 turret stroke', () => {
  const { root, rig } = loadRigAtPoseClock('quad')
  rig.apply(0, 0)
  const pod = root.getObjectByName('PDC_Starboard_Carriage'), start = pod.position.clone()
  const arms = ['Port', 'Starboard'].flatMap(side => Array.from({ length: 4 }, (_, i) => root.getObjectByName(`PDC_${side}_Arm_${i}`)))
  const orientations = arms.map(n => n.getWorldQuaternion(new THREE.Quaternion()))
  const locations = arms.map(n => n.getWorldPosition(new THREE.Vector3()))
  const cradles = ['Port', 'Starboard'].flatMap(side => Array.from({ length: 4 }, (_, i) => root.getObjectByName(`PDC_${side}_Cradle_${i}`)))
  const cradleLocations = cradles.map(n => n.getWorldPosition(new THREE.Vector3()))
  for (let d = 0; d <= .78; d += .01) {
    rig.apply(d, 4)
    arms.forEach((n, i) => assert.ok(n.getWorldQuaternion(new THREE.Quaternion()).angleTo(orientations[i]) < 1e-6))
  }
  rig.apply(.78,4)
  assert.ok(Math.abs(pod.position.distanceTo(start) - 10) < 1e-6)
  arms.forEach((n, i) => {
    const travel = n.getWorldPosition(new THREE.Vector3()).distanceTo(locations[i])
    assert.ok(travel > .243 && travel < .247, 'Tube stroke ends at the requested prior 11-percent reach plus the frame-30 carriage stroke')
  })
  cradles.forEach((n,i)=>assert.ok(n.getWorldPosition(new THREE.Vector3()).distanceTo(cradleLocations[i])>.099&&n.getWorldPosition(new THREE.Vector3()).distanceTo(cradleLocations[i])<.103,'Gray cradle follows the turret and small radial packing, without the tube slide'))
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

test('single batteries and restored source quad aim stay fixed in SCM while actual twin mounts scan', () => {
  const { root, nodes, rig } = loadRig()
  const fixed = nodes.filter(n => n.userData.staticJoint && /^(Main_|Axial_|SideBattery_)/.test(n.name))
  rig.apply(1, 0)
  const original = fixed.map(n => [...n.position.toArray(), ...n.quaternion.toArray()])
  const twin = root.getObjectByName('Defense_01_Yaw').quaternion.clone()
  const quad = root.getObjectByName('PDC_Starboard_Gimbal').quaternion.clone()
  rig.apply(1, 10)
  assert.deepEqual(fixed.map(n => [...n.position.toArray(), ...n.quaternion.toArray()]), original)
  assert.ok(twin.angleTo(root.getObjectByName('Defense_01_Yaw').quaternion) > .02)
  assert.ok(quad.angleTo(root.getObjectByName('PDC_Starboard_Gimbal').quaternion) < 1e-6)
  rig.apply(timelineForPose(.78, 'quad'), 10)
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

test('other single barrels retain their existing rear-breech pitch', () => {
  const { nodes, rig } = loadRig()
  const singles = nodes.filter(n => n.userData.singleBattery)
  assert.equal(singles.length, 11)
  for (const gun of singles) {
    if (['Axial_Bow_Barrel', 'Axial_Stern_Barrel'].includes(gun.name) || gun.userData.sourceEulerMotion) continue // Source curves have their own measured location/Euler actions.
    assert.equal(gun.userData.trunnionAdvance, 0, `${gun.name} must use the marked rear trunnion`)
    const map = ([x,y,z]) => new THREE.Vector3(x,z,-y)
    const original = map(gun.userData.sourceBoreDirectionModel).normalize()
    const normal = map(gun.userData.outwardNormal).normalize()
    const transverse = original.clone().cross(normal).normalize()
    for (let i = 0; i <= 100; i++) {
      rig.apply(i / 100, 0)
      const direction = original.clone().applyQuaternion(gun.quaternion)
      assert.ok(Math.abs(direction.dot(transverse)) < 1e-6, `${gun.name} yaws out of its elevation plane`)
      if (i > ((gun.userData.sideBatteryMechanism || gun.userData.stagedSingleBattery) ? 67 : 40))
        assert.ok(direction.dot(normal) > original.dot(normal), `${gun.name} elevates into the hull`)
    }
    assert.equal(nodes.filter(n => n.userData.barrelJoint === gun.name).length, 6, `${gun.name} retains six folding leaves`)
    if (gun.userData.sideBatteryMechanism) assert.equal(nodes.filter(n => n.userData.battery === gun.name && n.userData.system === 'side-front-slider').length, 2, `${gun.name} requires paired first-group sliders`)
    else assert.equal(nodes.filter(n => n.userData.barrel === gun.name).length, 1, `${gun.name} retains one front cap`)
  }
})

test('bow barrel follows the original odin.blend keyframes without reshaping its mesh', () => {
  const { root, rig } = loadRig()
  const samples = JSON.parse(fs.readFileSync(new URL('./fixtures/bow-source-motion-v01114.json', import.meta.url)))
  const barrel = root.getObjectByName('Axial_Bow_Barrel')
  const receiver = root.getObjectByName('Axial_Bow_SourceReceiver')
  rig.apply(0, 0)
  root.updateMatrixWorld(true)
  const closedJoint = barrel.matrixWorld.clone()
  const closedReceiver = receiver.matrixWorld.clone()
  const fromBlender = ([x, y, z]) => new THREE.Vector3(x, z, -y).multiplyScalar(.01)
  for (const sample of samples) {
    rig.apply(sample.frame / 100, 0)
    root.updateMatrixWorld(true)
    const delta = barrel.matrixWorld.clone().multiply(closedJoint.clone().invert())
    for (const index of ['0', '100']) {
      const start = fromBlender(samples[0].vertices[index])
      const expected = fromBlender(sample.vertices[index])
      const actual = start.applyMatrix4(delta)
      assert.ok(actual.distanceTo(expected) < .00001,
        `Bow source vertex ${index} differs from odin.blend at frame ${sample.frame}: ${actual.distanceTo(expected)}`)
    }
    assertMatrixClose(receiver.matrixWorld, closedReceiver, `Bow receiver moves at source frame ${sample.frame}`)
  }
  rig.apply(.56, 0)
  root.updateMatrixWorld(true)
  const deployedSource = barrel.matrixWorld.clone()
  rig.apply(1, 0)
  root.updateMatrixWorld(true)
  assertMatrixClose(barrel.matrixWorld, deployedSource, 'Bow remains at source frame 56 after deployment')
})

test('stern barrel follows its own original odin.blend keyframes', () => {
  const { root, rig } = loadRig()
  const samples = JSON.parse(fs.readFileSync(new URL('./fixtures/stern-source-motion-v01117.json', import.meta.url)))
  const barrel = root.getObjectByName('Axial_Stern_Barrel')
  const receiver = root.getObjectByName('Axial_Stern_Mount')
  rig.apply(0, 0)
  root.updateMatrixWorld(true)
  const closedJoint = barrel.matrixWorld.clone()
  const closedReceiver = receiver.matrixWorld.clone()
  const fromBlender = ([x, y, z]) => new THREE.Vector3(x, z, -y).multiplyScalar(.01)
  rig.apply(.65, 0)
  root.updateMatrixWorld(true)
  assertMatrixClose(barrel.matrixWorld, closedJoint, 'Stern gun must stay lowered until all armor clears')
  const lastLeaf = root.getObjectByName('Axial_Stern_Shutter_Port_02')
  const lastAxis = fromBlender(lastLeaf.userData.hingeAxisModel).normalize()
  const lastStop = new THREE.Quaternion().setFromAxisAngle(lastAxis,
    THREE.MathUtils.degToRad(lastLeaf.userData.closedAngleDegrees - lastLeaf.userData.openingTravelDegrees))
  assert.ok(lastLeaf.quaternion.angleTo(lastStop) < 1e-6,
    'The last stern leaf must reach its reduced open stop before the original gun action begins')
  for (const sample of samples) {
    rig.apply(.66 + (sample.frame - 11) / 100, 0)
    root.updateMatrixWorld(true)
    const delta = barrel.matrixWorld.clone().multiply(closedJoint.clone().invert())
    for (const index of ['0', '100']) {
      const start = fromBlender(samples[0].vertices[index])
      const expected = fromBlender(sample.vertices[index])
      const actual = start.applyMatrix4(delta)
      assert.ok(actual.distanceTo(expected) < .00001,
        `Stern source vertex ${index} differs from odin.blend at frame ${sample.frame}: ${actual.distanceTo(expected)}`)
    }
    assertMatrixClose(receiver.matrixWorld, closedReceiver, `Stern mount moves at source frame ${sample.frame}`)
  }
  rig.apply(.92, 0)
  root.updateMatrixWorld(true)
  const deployedSource = barrel.matrixWorld.clone()
  rig.apply(1, 0)
  root.updateMatrixWorld(true)
  assertMatrixClose(barrel.matrixWorld, deployedSource, 'Stern remains at source frame 37 after deployment')
})

test('stern bore rests at its original odin.blend position, not only its relative action', () => {
  const { root, rig, meshBounds } = loadRig()
  const bore = root.getObjectByName('odin.026')
  assert.ok(bore && meshBounds.has(bore), 'Source stern bore geometry is present')
  rig.apply(0, 0)
  root.updateMatrixWorld(true)
  const actual = meshBounds.get(bore).clone().applyMatrix4(bore.matrixWorld)
  const sourceMin = new THREE.Vector3(-1.6288986206054688, 45.74752426147461, 231.1075897216797).multiplyScalar(.01)
  const sourceMax = new THREE.Vector3(1.6260801553726196, 63.05480194091797, 274.32647705078125).multiplyScalar(.01)
  assert.ok(actual.min.distanceTo(sourceMin) < .0001, `Stern bore minimum differs from source: ${actual.min.distanceTo(sourceMin)}`)
  assert.ok(actual.max.distanceTo(sourceMax) < .0001, `Stern bore maximum differs from source: ${actual.max.distanceTo(sourceMax)}`)
  const asset = root.getObjectByName('Odin_Asset')
  assert.equal(asset.userData.sternRemovedDuplicateShoulderFaces, 818, 'Duplicate vented stern leaves are removed')
  assert.equal(root.getObjectByName('Axial_Stern_OriginalShoulder'), undefined, 'The duplicate static vented armor is absent')
  assert.equal(asset.userData.sternOriginalFrontPlateFaces, 66, 'Stern foremost plate uses the disconnected original armor shell')
  assert.equal(asset.userData.sternRemovedWrongTriangularCapFaces, 8, 'The mistaken hull triangles no longer act as the plate')
  const cap = root.getObjectByName('Axial_Stern_FrontCap')
  assert.equal(cap.userData.sourceObject, 'holo.001')
  assert.equal(cap.children.filter(child => meshBounds.has(child)).length, 1, 'The original stern plate replaces both generated skins')
  assert.equal(cap.children[0].userData.sourceFaceCount, 66)
  assert.equal(asset.userData.sternOriginalForwardHullFaces, 0,
    'The duplicate recovered stern hull is removed after separating the source armor')
  assert.equal(root.getObjectByName('Axial_Stern_OriginalForwardHull'), undefined)
  assert.equal(asset.userData.sternRestoredFixedNoseRoofFaces, 8,
    'The original fixed roof is restored after the incorrect moving mesh is removed')
  const bowCap = root.getObjectByName('Axial_Bow_FrontCap')
  assert.ok(new THREE.Vector3(...bowCap.userData.additionalOpenTravelModel).length() > 3.9,
    'Bow cap clears the original bore along the deck incline')
})

test('axial front caps lift clear before translating toward the muzzle', () => {
  const { root, rig } = loadRig()
  const map = ([x, y, z]) => new THREE.Vector3(x, z, -y)
  for (const station of ['Bow', 'Stern']) {
    const cap = root.getObjectByName(`Axial_${station}_FrontCap`)
    rig.apply(0, 0)
    const closed = cap.position.clone()
    const rise = map(cap.userData.settleVector).negate()
    const forward = map(cap.userData.slideVector).negate()
    assert.ok(rise.y > 0, `${station} cap must lift upward`)
    rig.apply(cap.userData.settleEnd, 0)
    assert.ok(cap.position.distanceTo(closed.clone().add(rise)) < 1e-6,
      `${station} cap should finish lifting before sliding`)
    rig.apply(cap.userData.slideEnd, 0)
    assert.ok(cap.position.distanceTo(closed.clone().add(rise).add(forward)) < 1e-6,
      `${station} cap should finish its forward translation after lifting`)
  }
})

test('axial armor crowns follow the raised hull line and the breech trapezoids meet the gun roots', () => {
  const { root } = loadRig()
  const frames = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.10.0/source-covers.json', import.meta.url)))
  for (const station of ['Bow', 'Stern']) {
    const prefix = `Axial_${station}`
    const frame = frames[prefix]
    const shift = station === 'Bow' ? root.getObjectByName('Axial_Bow_SourceReceiver').userData.receiverShiftModel : [0, 0, 0]
    const origin = new THREE.Vector3(...frame.frameOrigin).add(new THREE.Vector3(...shift))
    const along = new THREE.Vector3(...frame.frameAxes.map(row => row[1]))
    const normal = new THREE.Vector3(...frame.frameAxes.map(row => row[2]))
    const coordinates = point => {
      const delta = new THREE.Vector3(...point).sub(origin)
      return { y: delta.dot(along), z: delta.dot(normal) }
    }
    const breech = root.getObjectByName(`${prefix}_Shutter_Port_00`).userData.closedEndEdgesModel[0]
    const muzzle = root.getObjectByName(`${prefix}_Shutter_Port_02`).userData.closedEndEdgesModel[1]
    const outer = coordinates(breech[0]), inner = coordinates(breech[1])
    const tip = coordinates(muzzle[1])
    const rearTrim = inner.y - outer.y
    assert.ok(station === 'Bow' ? rearTrim > 1.25 && rearTrim < 1.45 : rearTrim > .02 && rearTrim < .08,
      `${station} rear panel should meet the gun root without the artificial crown retreat`)
    if (station === 'Bow') assert.ok(inner.z > 5.3 && inner.z < 5.45,
      'Bow crown must sit on the marked lower hull silhouette')
    else assert.ok(inner.z > 5.2, `${station} crown still follows the low blue line`)
    assert.ok(tip.z > inner.z + .18, `${station} roof does not carry its raised line toward the cap`)
  }
})

test('bow front cap fits between the last hinged leaf and the raised receiver lip', () => {
  const { root } = loadRig()
  const frames = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.10.0/source-covers.json', import.meta.url)))
  for (const station of ['Bow']) {
    const prefix = `Axial_${station}`
    const frame = frames[prefix]
    const origin = new THREE.Vector3(...frame.frameOrigin)
      .add(new THREE.Vector3(...(station === 'Bow'
        ? root.getObjectByName('Axial_Bow_SourceReceiver').userData.receiverShiftModel
        : [0, 0, 0])))
    const along = new THREE.Vector3(...frame.frameAxes.map(row => row[1]))
    const normal = new THREE.Vector3(...frame.frameAxes.map(row => row[2]))
    const yz = point => {
      const delta = new THREE.Vector3(...point).sub(origin)
      return { y: delta.dot(along), z: delta.dot(normal) }
    }
    const leaf = root.getObjectByName(`${prefix}_Shutter_Port_02`)
    const front = yz(leaf.userData.closedEndEdgesModel[1][1])
    const cap = root.getObjectByName(`${prefix}_FrontCap`)
    const rear = yz(cap.userData.closedCrownLineModel[0])
    assert.ok(Math.abs(rear.y - front.y) < .025 && Math.abs(rear.z - front.z) < .025,
      'Shortening the front plate must preserve the accepted last-leaf seam')
    const receiver = cap.userData.receiverForeSeamLocal[2]
    const tip = yz(cap.userData.closedCrownLineModel.at(-1))
    assert.ok(Math.abs(tip.y - receiver[1] + .02) < .0001 && Math.abs(tip.z - receiver[2]) < .0001,
      'The leading crown must meet the unchanged receiver lip rather than extend beyond it')
    const slope = (tip.z - rear.z) / (tip.y - rear.y)
    for (const [index, point] of cap.userData.closedCrownLineModel.entries()) {
      const crown = yz(point)
      assert.ok(Math.abs(crown.z - rear.z - slope * (crown.y - rear.y)) < .025,
        `${station} front cap crown point ${index} bends between its two fitted seams`)
    }
    assert.ok(cap.userData.closedLengthLocal > 9.3 && cap.userData.closedLengthLocal < 9.7,
      'The bow front plate must fit the receiver opening instead of retaining its old 12-unit length')
  }
})

test('stern and keel source nose shells fit the full shutter and fixed receiver profiles', () => {
  const { root } = loadRig()
  const frames = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.10.0/source-covers.json', import.meta.url)))
  const receivers = {
    Stern: [[.015, 18.7318677, 5.8638629], [.4092712, 18.6959981, 5.8276370], [2.4624300, 15.6811440, 2.8621690]],
    Keel: [[.0140122, 18.8725736, 5.3274785], [.2469125, 18.8259012, 5.2875084], [2.2966890, 15.8218248, 2.3257913]],
  }
  for (const station of ['Stern', 'Keel']) {
    const cap = root.getObjectByName(`Axial_${station}_FrontCap`)
    const frame = frames[`Axial_${station}`]
    const origin = new THREE.Vector3(...frame.frameOrigin)
    if (station === 'Keel') origin.add(new THREE.Vector3(...root.getObjectByName('Axial_Keel_Mount').userData.fixedAssemblyOffsetModel))
    const axes = frame.frameAxes[0].map((_, column) => new THREE.Vector3(...frame.frameAxes.map(row => row[column])))
    const local = point => axes.map(axis => new THREE.Vector3(...point).sub(origin).dot(axis))
    const fore = cap.userData.closedForeProfileModel.map(local)
    for (const [index, point] of fore.entries()) {
      const expected = [...receivers[station][index]]
      expected[1] -= .02
      assert.ok(Math.max(...point.map((value, axis) => Math.abs(value - expected[axis]))) < .0001,
        `${station} receiver diagonal fails at crown, crease or outside edge ${index}`)
    }
    const rear = cap.userData.closedRearProfileModel.map(local)
    const leaf = root.getObjectByName(`Axial_${station}_Shutter_Starboard_02`)
    const [outside, center] = leaf.userData.closedEndEdgesModel[1].map(local)
    const [crownStart,crownHeight,crownRake] = cap.userData.closedCrownLineLocal
    for (const p of [fore[0],rear[0],center]) assert.ok(
      Math.abs(p[2] - crownHeight - crownRake * (p[1] - crownStart)) < .0001,
      'The nose crown and shutter crown must continue the same straight line')
    for (const [actual, expected, rise] of [[rear[0], center, .02*crownRake], [rear[2], outside, 0]]) {
      assert.ok(Math.abs(actual[0] - Math.abs(expected[0])) < .0001)
      assert.ok(Math.abs(actual[1] - expected[1] - .02) < .0001)
      assert.ok(Math.abs(actual[2] - expected[2] - rise) < .0001)
    }
    const [closedLow, closedHigh] = cap.userData.originalClosedBounds
    assert.ok(Math.abs(2 * closedHigh[0] - (station === 'Stern' ? 4.92 : 4.596)) < .01,
      'The source nose cover should match the shutter width')
    assert.ok(Math.abs(closedLow[1] - rear[0][1]) < .03)
    assert.equal(cap.userData.armorTemplate, 'odin.blend/holo.001 disconnected 66-face armor shell')
    assert.equal(cap.userData.sourceOpenPose, true)
  }
  assert.equal(root.getObjectByName('Axial_Stern_OriginalNoseRoof'), undefined,
    'The stationary source roof is merged into the fixed asset during export')
})

test('axial bays close six flank-derived leaves muzzle-first, then seat one cap without moving the turret', () => {
  const { root, nodes, rig } = loadRig()
  for (const station of ['Bow', 'Stern', 'Keel']) {
    const prefix = `Axial_${station}`
    const mount = root.getObjectByName(prefix + '_Mount')
    const leaves = nodes.filter(node => node.userData.barrelJoint === prefix + '_Barrel')
    const cap = root.getObjectByName(prefix + '_FrontCap')
    assert.equal(leaves.length, 6)
    assert.equal(cap.userData.system, 'single-front-cap')
    assert.equal(cap.userData.onePieceNoseAssembly, true)
    rig.apply(0, 0)
    root.updateMatrixWorld(true)
    const originalMount = mount.matrixWorld.clone()
    for (const side of ['Port', 'Starboard']) {
      const ordered = [0, 1, 2].map(index => root.getObjectByName(`${prefix}_Shutter_${side}_${String(index).padStart(2, '0')}`))
      for (const leaf of ordered) {
        assert.equal(leaf.parent.name, station === 'Keel' ? 'Axial_Keel_Mount' : 'Odin_Asset', 'Axial plates keep fixed hull pivots')
        assert.ok(leaf.userData.armorTemplate.startsWith('SideBattery_1_Starboard_Shutter_Port_'))
        assert.equal(leaf.userData.closedAngleDegrees, side === 'Port' ? 150 : -150)
        if (station !== 'Bow') assert.equal(leaf.userData.openingTravelDegrees, 95)
      }
      assert.equal(ordered[0].userData.shorterBreechTrapezoid, true)
      for (let index = 0; index < 2; index++) {
        const end = ordered[index].userData.closedEndEdgesModel[1]
        const start = ordered[index+1].userData.closedEndEdgesModel[0]
        for (let corner = 0; corner < 2; corner++)
          assert.ok(new THREE.Vector3(...end[corner]).distanceTo(new THREE.Vector3(...start[corner])) < .055,
            `${station} ${side} armor has an open longitudinal seam`)
      }
    }
    for (const progress of [0, .1, .2, .3, .4, .55, .7, 1]) {
      rig.apply(progress, 0)
      root.updateMatrixWorld(true)
      assertMatrixClose(mount.matrixWorld, originalMount, `${station} turret translates after its armor closes`)
    }
    const early = station === 'Bow' ? .18 : .40
    rig.apply(early, 0)
    const pair = [0, 2].map(index => root.getObjectByName(`${prefix}_Shutter_Port_${String(index).padStart(2, '0')}`))
    assert.ok(pair[0].quaternion.angleTo(new THREE.Quaternion()) < pair[1].quaternion.angleTo(new THREE.Quaternion()),
      `${station} muzzle-end leaf should be farther through its closing stroke`)
    rig.apply(1, 0)
    for (const leaf of leaves) {
      const axis = new THREE.Vector3(...leaf.userData.hingeAxisModel)
      const webAxis = new THREE.Vector3(axis.x, axis.z, -axis.y).normalize()
      const closed = leaf.userData.closedAngleDegrees
      const travel = leaf.userData.openingTravelDegrees ?? Math.abs(closed)
      const expected = new THREE.Quaternion().setFromAxisAngle(webAxis,
        THREE.MathUtils.degToRad(closed - Math.sign(closed) * travel))
      assert.ok(leaf.quaternion.angleTo(expected) < 1e-6)
    }
  }
})

test('bow armor pivots and nose cap share the relocated original receiver datum', () => {
  const { root } = loadRig()
  const frame = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.10.0/source-covers.json', import.meta.url))).Axial_Bow
  const shift = root.getObjectByName('Axial_Bow_SourceReceiver').userData.receiverShiftModel
  const modelPoint = ([x, y, z]) => frame.frameOrigin.map((value, row) =>
    value + frame.frameAxes[row][0] * x + frame.frameAxes[row][1] * y + frame.frameAxes[row][2] * z + shift[row])
  const browserPoint = ([x, y, z]) => new THREE.Vector3(x, z, -y)
  const segments = [-16.25, -6.525, 1.90]
  for (const side of ['Port', 'Starboard']) for (let index = 0; index < 3; index++) {
    const leaf = root.getObjectByName(`Axial_Bow_Shutter_${side}_${String(index).padStart(2, '0')}`)
    const expected = modelPoint([side === 'Port' ? -2.46 : 2.46, segments[index], 2.49])
    assert.ok(leaf.position.distanceTo(browserPoint(expected)) < .0002, `${leaf.name} pivot missed the receiver lip`)
    assert.ok(browserPoint(leaf.userData.hingeEdgeModel[0]).distanceTo(leaf.position) < .0002,
      `${leaf.name} recorded hinge edge missed its physical pivot`)
    assert.deepEqual(leaf.userData.receiverDatumShiftModel.map(x => +x.toFixed(2)), [0, 3.45, .55])
  }
  const cap = root.getObjectByName('Axial_Bow_FrontCap')
  assert.ok(cap.position.distanceTo(browserPoint(modelPoint([0, 15.57, 6.29]))) < .0002,
    'Bow front plate missed the translated receiver datum')
  assert.deepEqual(cap.userData.receiverDatumShiftModel.map(x => +x.toFixed(2)), [0, 3.45, .55])
})

test('original single covers keep their source open pose and stagger root-first', () => {
  const { nodes, rig } = loadRig()
  const sourceRotations = new Map(nodes.map(n => [n.name, n.quaternion.clone()]))
  rig.apply(1, 0)
  for (const cap of nodes.filter(n => n.userData.system === 'single-front-cap')) {
    if (cap.userData.originalSourceArmor) continue // Source carriage armor has its own full-return and sequencing checks.
    const leaves = nodes.filter(n => n.userData.barrelJoint === cap.userData.barrel)
    for (const leaf of leaves) {
      assert.ok(Math.abs(leaf.userData.armorThickness-cap.userData.armorThickness)<1e-6)
      assert.equal(leaf.userData.sourceGeometry, true, 'Use the existing source cover')
      if (leaf.userData.openingTravelDegrees) {
        assert.equal(leaf.userData.openingTravelDegrees, 95, 'Stern aperture stays clear of the aft hull')
      } else {
        assert.ok(leaf.quaternion.angleTo(sourceRotations.get(leaf.name))<1e-7, 'SCM must stop at the original open position')
      }
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
    assert.ok(Math.abs(leaf.quaternion.angleTo(open)-Math.PI*5/6)<1e-6)
  }
})

test('flank rear cradle seats only after folding and carries gun plus groups 3 and 4 rigidly', () => {
  const { root,nodes,rig }=loadRig(), map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  for (const carriage of nodes.filter(n=>n.userData.system==='side-battery-carriage')) {
    const name=carriage.userData.battery, gun=root.getObjectByName(name)
    const carried=nodes.filter(n=>n.userData.barrelJoint===name && n.userData.armorGroup>=3)
    assert.ok(carriage.userData.originalOuterPedestalVertices>2000,'The source rear pedestal must travel with the cradle')
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

test('four flank bores remain centered and stow parallel to their own slots', () => {
  const {root,nodes,rig}=loadRig(),asset=root.getObjectByName('Odin_Asset')
  const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  for(const gun of nodes.filter(n=>n.userData.sideBatteryMechanism && n.userData.singleBattery)) {
    const axis=map(gun.userData.slotAxisModel).normalize()
    const normal=map(gun.userData.outwardNormal).normalize(),transverse=axis.clone().cross(normal).normalize()
    const origin=map(gun.userData.slotOriginModel)
    for(const d of [0,.14,.24,.67,.8,1,.4,0]) {
      rig.apply(d,0);root.updateMatrixWorld(true)
      const [a,b]=gun.userData.boreAxisPointsLocal.map(p=>asset.worldToLocal(gun.localToWorld(map(p))))
      for(const p of [a,b])assert.ok(Math.abs(p.clone().sub(origin).dot(transverse))<.0001,`${gun.name} leaves the slot center plane at ${d}`)
      if(d<=.67)assert.ok(b.clone().sub(a).normalize().distanceTo(axis)<.00001,`${gun.name} folds inward past parallel`)
    }
    assert.equal(gun.userData.stowSink,1.8, 'The centered bore settles behind the re-fitted inner slot roof in NAV')
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
    // The aft end is fitted to its shallower hull receiver, so the required
    // trapezoid is unequal-ended without imposing the old guessed 26° angle.
    assert.ok(Math.abs(edge(endA).normalize().dot(edge(endB).normalize()))<Math.cos(Math.PI/36),'The first leaf must have visibly unequal end slopes')
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

test('source nose caps follow their seat path and side 2/4 hold their raised parking position', () => {
  const { nodes, rig } = loadRig()
  for (const cap of nodes.filter(n => n.userData.system === 'single-front-cap')) {
    const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
    assert.equal(cap.userData.sourceOpenPose, true)
    const deployed = cap.position.clone()
    if (cap.userData.sourceCapStroke) {
      rig.apply(0,0)
      const closed = cap.position.clone(), orientation = cap.quaternion.clone()
      rig.apply(Number(cap.userData.releaseEnd ?? .08),0)
      assert.ok(cap.position.clone().sub(closed).distanceTo(map(cap.userData.clearanceLiftVector)) < 1e-6)
      const lifted = cap.position.clone()
      rig.apply(Number(cap.userData.slideEnd ?? .23),0)
      assert.ok(cap.position.clone().sub(lifted).distanceTo(map(cap.userData.advanceVector)) < 1e-6)
      const advanced = cap.position.clone()
      rig.apply(Number(cap.userData.settleEnd ?? .26),0)
      if (cap.userData.holdRaisedAfterAdvance) {
        assert.ok(cap.position.distanceTo(advanced)<1e-6, 'No downward settling after the forward slide')
        for (const progress of [.18,.3,.42,.8,1,.8,.3,.18]) {
          rig.apply(progress,0)
          assert.ok(cap.position.distanceTo(advanced)<1e-6, 'Raised parking height survives forward and backward scrubbing')
        }
      } else assert.ok(cap.position.distanceTo(deployed)<1e-5)
      assert.ok(cap.quaternion.angleTo(orientation)<1e-6)
      continue
    }
    rig.apply(0,0);const origin=cap.position.clone(),orientation=cap.quaternion.clone()
    rig.apply(Number(cap.userData.slideEnd ?? .23),0);const slid=cap.position.clone().sub(origin)
    const settleComplete = Number(cap.userData.settleEnd ?? .36) <= Number(cap.userData.slideEnd ?? .23)
    const expectedSlide = map(cap.userData.slideVector).negate()
    if (settleComplete) expectedSlide.sub(map(cap.userData.settleVector))
    assert.ok(slid.distanceTo(expectedSlide)<1e-6)
    rig.apply(1,0);const complete=cap.position.clone().sub(origin)
    assert.ok(complete.distanceTo(map(cap.userData.slideVector).add(map(cap.userData.settleVector)).negate())<1e-6)
    assert.ok(cap.position.distanceTo(deployed)<1e-6, 'The original model cap position is the deployed endpoint')
    assert.ok(cap.quaternion.angleTo(orientation)<1e-6, 'Nose cap translates without a hinge rotation')
  }
})

test('aft twin guides retract just behind the gun and sink with its carriage', () => {
  const { root, rig } = loadRigAtPoseClock('aftTwin')
  for (let i = 5; i <= 8; i++) {
    const prefix = `Defense_${String(i).padStart(2, '0')}`
    const gate = root.getObjectByName(prefix + '_NotchGate'), carriage = root.getObjectByName(prefix + '_Carriage')
    const side = carriage.userData.side < 0 ? 'Port' : 'Starboard'
    const rail = root.getObjectByName(`DefenseRail_Aft_${side}`)
    assert.equal(gate.parent.name, 'Odin_Asset')
    assert.equal(rail.parent.name, 'Odin_Asset')
    assert.equal(carriage.userData.finalStowInward, 2.3)
    assert.equal(carriage.userData.finalStowDrop, 4.0,
      'The requested outward adjustment must not increase the original sink distance')
    assert.equal(rail.userData.finalStowDrop, carriage.userData.finalStowDrop)
    assert.equal(rail.userData.finalStowInward, carriage.userData.finalStowInward)
    assert.ok(rail.userData.retractLag > 0 && rail.userData.retractLag <= .03)
    assert.equal(rail.userData.sinkStart, .40)
    assert.equal(carriage.userData.sinkStart, .40)
    rig.apply(0, 0)
    root.updateMatrixWorld(true)
    const shut = gate.position.clone(), parked = carriage.position.clone(), parkedRail = rail.position.clone()
    rig.apply(.20, 0)
    const onset = carriage.position.clone(), onsetRail = rail.position.clone(), open = gate.position.clone()
    assert.ok(shut.y - open.y > 4, 'Gate must clear before the final combined stroke')
    rig.apply(1, 0)
    const deployed = carriage.position.clone(), deployedRail = rail.position.clone()
    assert.ok(onset.y > parked.y && onset.y < deployed.y,
      'Gun is already descending at 20% without reaching the parked level')
    assert.ok(onsetRail.y > parkedRail.y && onsetRail.y < deployedRail.y,
      'Shared rail descends on the same interval')
    assert.ok(Math.abs(deployed.y - parked.y - Number(carriage.userData.finalStowDrop)) < 1e-6)
    assert.ok(Math.abs(deployedRail.y - parkedRail.y - Number(rail.userData.finalStowDrop)) < 1e-6)
    for (const d of [.40, .47, .55, .68, .8, 1]) {
      rig.apply(d, 0)
      assert.ok(Math.abs(carriage.position.y - deployed.y) < 1e-6,
        'Aft gun cannot have a separate late upward lift')
      assert.ok(Math.abs(rail.position.y - deployedRail.y) < 1e-6,
        'Support rail remains at deployed height after 40%')
    }
    let previousHeight = deployed.y
    for (let step = 39; step >= 5; step--) {
      const d = step / 100
      rig.apply(d, 0)
      const gunHeight = carriage.position.y
      const gunProgress = (gunHeight - parked.y) / (deployed.y - parked.y)
      const railProgress = (rail.position.y - parkedRail.y) / (deployedRail.y - parkedRail.y)
      assert.ok(gunHeight <= previousHeight + 1e-6, 'Aft gun must descend monotonically')
      assert.ok(previousHeight - gunHeight < .33, 'Aft gun must descend gently enough to clear the opening')
      assert.ok(Math.abs(gunProgress - railProgress) < 1e-6,
        'Gun and support rail must share the same descent progress')
      previousHeight = gunHeight
    }
    assert.ok(Math.abs(onset.x - parked.x) > .1 && Math.abs(onset.x - parked.x) < Math.abs(deployed.x - parked.x) * .25,
      'At 20%, the turret still has its final inward travel remaining')
    assert.ok(Math.abs(onsetRail.x - parkedRail.x) > Math.abs(onset.x - parked.x),
      'The rail remains only slightly behind the gun at the beginning of the final fifth')
    for (let step = 1; step < 20; step++) {
      rig.apply(step / 20, 0)
      const railFraction = Math.abs((rail.position.x - parkedRail.x) / (deployedRail.x - parkedRail.x))
      const gunFraction = Math.abs((carriage.position.x - parked.x) / (deployed.x - parked.x))
      assert.ok(railFraction >= gunFraction - 1e-6,
        'The rail must retract slightly more slowly than the gun')
      assert.ok(railFraction - gunFraction <= .026,
        'The rail may only lag by a small amount through the glazing')
    }
    rig.apply(.20, 0)
    rig.apply(.10, 0)
    assert.ok(carriage.position.y < onset.y && carriage.position.y > parked.y,
      'Turret sinks while its inward travel is still underway')
    assert.ok(rail.position.y < onsetRail.y && rail.position.y > parkedRail.y,
      'Shared support rail sinks with the turret')
    assert.ok(Math.abs(carriage.position.x - parked.x) < Math.abs(onset.x - parked.x))
    assert.ok(Math.abs(rail.position.x - parkedRail.x) < Math.abs(onsetRail.x - parkedRail.x),
      'Long guides continue retracting with the gun until both reach the same inboard seat')
    rig.apply(.05, 0)
    assert.ok(carriage.position.distanceTo(parked) < 1e-6 && rail.position.distanceTo(parkedRail) < 1e-6,
      'The full carriage and bracket are parked before the gate shuts')
    assert.ok(gate.position.distanceTo(open) < 1e-6)
    for (const d of [.3, .5, .8, 1, .6, .25]) {
      rig.apply(d, 0)
      assert.ok(gate.position.distanceTo(open) < 1e-6)
    }
    rig.apply(0, 0)
    assert.ok(gate.position.distanceTo(shut) < 1e-6)
  }
})

test('keel bay remains at the old 14% assembly position through both directions of armor travel', () => {
  const { root, nodes, rig } = loadRig()
  const reference = JSON.parse(fs.readFileSync(new URL('./fixtures/keel-locked-mount-v01121.json', import.meta.url)))
  const mount = root.getObjectByName('Axial_Keel_Mount')
  const expected = new THREE.Matrix4().fromArray(reference.mountWorld)
  for (const d of [0, .02, .08, .14, .2, .26, .4, .53, .64, .8, 1, .8, .64, .53, .4, .26, .14, 0]) {
    rig.apply(d, 0)
    root.updateMatrixWorld(true)
    assertMatrixClose(mount.matrixWorld, expected, `Keel assembly departed from its old 14% seat at ${d}`)
  }
  const keelLeaves = nodes.filter(n => n.userData.barrelJoint === 'Axial_Keel_Barrel')
  for (const keel of keelLeaves) {
    const stern = root.getObjectByName(keel.name.replace('Axial_Keel', 'Axial_Stern'))
    for (const d of [0, .14, .26, .4, .53, .64, 1]) {
      rig.apply(d, 0)
      assert.ok(Math.abs(keel.quaternion.angleTo(new THREE.Quaternion()) - stern.quaternion.angleTo(new THREE.Quaternion())) < 1e-6,
        'The keel and stern leaves share the same folding order and 95-degree sweep')
    }
  }
  const cap = root.getObjectByName('Axial_Keel_FrontCap')
  rig.apply(0, 0); const closed = cap.position.clone()
  rig.apply(.08, 0); const lifted = cap.position.clone()
  const settle = cap.userData.settleVector
  assert.ok(lifted.clone().sub(closed).distanceTo(new THREE.Vector3(-settle[0], -settle[2], settle[1])) < 1e-5,
    'The front cap releases vertically before advancing')
  rig.apply(.25, 0)
  assert.ok(cap.position.distanceTo(lifted) > 7.9, 'The front plate then advances along the bore')
})

test('side batteries 2 and 4 keep their corrected pivots fixed within their moving turrets', () => {
  const { root, rig } = loadRig()
  for (const i of [2,4]) for (const side of ['Port','Starboard']) {
    const gun = root.getObjectByName(`SideBattery_${i}_${side}`)
    assert.equal(gun.userData.sourceEulerMotion,true)
    assert.equal(gun.userData.stowSink,0)
    assert.equal(gun.userData.userRequestedRestAdjustment,true)
    assert.equal(gun.parent.name, `SideBattery_${i}_${side}_SourceCarriage`)
    rig.apply(0, 0)
    const origin = gun.position.clone()
    for (const d of [.4,.75,1]) {
      rig.apply(d, 0)
      assert.ok(gun.position.distanceTo(origin) < 1e-6)
    }
  }
})

test('side singles 2 and 4 open their original seven source covers before raising the turret', () => {
  const { root, nodes, rig } = loadRig()
  const map = ([x,y,z]) => new THREE.Vector3(x,z,-y)
  for (const i of [2,4]) for (const side of ['Port','Starboard']) {
    const prefix = `SideBattery_${i}_${side}`
    const gun = root.getObjectByName(prefix), cap = root.getObjectByName(prefix + '_FrontCap')
    const leaves = nodes.filter(n => n.userData.barrelJoint === prefix)
    assert.equal(leaves.length, 6)
    assert.equal(cap.userData.sourceRigidCap, true)
    rig.apply(0,0)
    root.updateMatrixWorld(true)
    const closedCap = cap.position.clone(), closedGun = gun.matrix.clone()
    const closedLeaves = leaves.map(n => n.quaternion.clone())
    rig.apply(cap.userData.releaseEnd,0)
    const lifted = cap.position.clone(), lift = lifted.clone().sub(closedCap)
    assert.ok(Math.abs(lift.length() - .6) < 1e-6)
    assert.ok(lift.dot(map(gun.userData.outwardNormal).normalize()) > .599,
      'Release the cap outward from the slot before advancing it')
    rig.apply(cap.userData.settleEnd,0)
    assert.ok(cap.position.distanceTo(lifted) > 7.8)
    leaves.forEach((leaf,k) => assert.ok(leaf.quaternion.angleTo(closedLeaves[k]) < 1e-6,
      'Nose must clear before any side leaf folds'))
    rig.apply(.42,0)
    root.updateMatrixWorld(true)
    assertMatrixClose(gun.matrix, closedGun, 'The original barrel waits for cover clearance')
    for (let k=0;k<leaves.length;k++) {
      const leaf = leaves[k]
      assert.equal(leaf.userData.originalSourceArmor, true)
      assert.ok(!leaf.userData.sourceFlankTemplate)
      const angle = leaf.userData.closedAngleDegrees - Math.sign(leaf.userData.closedAngleDegrees) * leaf.userData.openingTravelDegrees
      const axis = map(leaf.userData.hingeAxisModel).normalize()
      assert.ok(leaf.quaternion.angleTo(new THREE.Quaternion().setFromAxisAngle(axis, THREE.MathUtils.degToRad(angle))) < 1e-6,
        'The original leaf stops at its limited open orientation')
      assert.ok(Math.abs(leaf.quaternion.angleTo(closedLeaves[k]) - THREE.MathUtils.degToRad(leaf.userData.openingTravelDegrees)) < 1e-6)
      assert.equal(leaf.parent.name, leaf.userData.panelIndex === 0 ? prefix + '_SourceCarriage' : 'Odin_Asset')
    }
  }
})

test('side 2 and 4 follow the original three-channel barrel curves on both mirrored sides', () => {
  const {root,rig}=loadRig()
  const references=JSON.parse(fs.readFileSync(new URL('./fixtures/flank-source-motion-v01125.json',import.meta.url)))
  const map=([x,y,z])=>new THREE.Vector3(x,z,-y).multiplyScalar(.01)
  for(const [name,samples]of Object.entries(references)) {
    const gun=root.getObjectByName(name)
    assert.equal(gun.userData.sourceMotionStart,gun.userData.sourceFrameRange[0]/100)
    assert.equal(gun.userData.sourceMotionEnd,gun.userData.sourceFrameRange[1]/100)
    rig.apply(0,0);root.updateMatrixWorld(true)
    const initial=gun.matrixWorld.clone()
    for(const sample of samples) {
      rig.apply(sample.deployment,0);root.updateMatrixWorld(true)
      const delta=gun.matrixWorld.clone().multiply(initial.clone().invert())
      for(const index of ['0','100']) {
        const actual=map(samples[0].vertices[index]).applyMatrix4(delta)
        assert.ok(actual.distanceTo(map(sample.vertices[index]))<.00001,`${name} source frame ${sample.frame} vertex ${index}`)
      }
      assert.ok(gun.getWorldPosition(new THREE.Vector3()).distanceTo(map(sample.origin))<.00001)
    }
  }
})

test('the fitted source side armor retains its grates and UVs and clears the corrected bores', () => {
  const source=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.26/source-fit.json',import.meta.url)))
  const geometry=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.26/source-geometry.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.26/mesh-clearance.json',import.meta.url)))
  assert.equal(source.sourceSha256,'9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e')
  assert.equal(geometry.sourceSha256,source.sourceSha256)
  assert.equal(geometry.meshes.length,28)
  assert.equal(geometry.restoredRailPolygons,8)
  assert.equal(geometry.unchangedBarrelAndTurretMeshes,12)
  assert.ok(geometry.restoredRailCornerError<.00012)
  assert.ok(geometry.restoredRailUvError<.000001)
  assert.equal(geometry.sourceElevationRailPolygons,48)
  assert.ok(geometry.sourceElevationRailCornerError<.00012)
  assert.ok(geometry.sourceElevationRailUvError<.000001)
  for(const row of geometry.meshes) {
    assert.ok(row.maxUvError<.000001,`${row.mesh} changes its source UVs`)
    assert.equal(row.retainedOriginalPolygons,row.originalPolygons,`${row.mesh} loses original grate detail`)
    if(row.mesh.includes('_OriginalArmor')) {
      assert.ok(row.closedExteriorPlaneError<.00012,`${row.mesh} breaks the common closed side plane`)
      assert.ok(Math.abs(row.closedLowerEdgeHalfWidth-2.88)<.00012,`${row.mesh} leaves a tapered lower seam`)
    }
  }
  for(const [name,station]of Object.entries(source.stations)) {
    assert.equal(station.leaves.length,6)
    assert.equal(clearance[name].poses,101)
    assert.deepEqual(clearance[name].barrelArmorContacts,[],`${name} has a geometric barrel/armor contact`)
    assert.ok(clearance[name].limitedOpenCoordinateError<.0001)
  }
})

test('all source flank leaves stop at the requested v25 front-leaf orientation and retain a flat crown', () => {
  const {root,rig}=loadRig()
  const old=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.25/source-armor.json',import.meta.url)))
  const crownFit=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.28/source-fit.json',import.meta.url)))
  const ease=(a,b,d)=>{const t=THREE.MathUtils.clamp((d-a)/(b-a),0,1);return t*t*(3-2*t)}
  for(const i of [2,4])for(const side of ['Port','Starboard'])for(const physical of ['Port','Starboard']) {
    const prefix=`SideBattery_${i}_${side}`
    const front=old.stations[prefix].leaves.find(l=>l.name===`${prefix}_Shutter_${physical}_02`)
    const expectedTravel=Math.abs(front.closedAngle)*ease(.12,.24,i===2?.20:.18)
    for(let k=0;k<3;k++) {
      const leaf=root.getObjectByName(`${prefix}_Shutter_${physical}_0${k}`)
      assert.ok(Math.abs(leaf.userData.openingTravelDegrees-expectedTravel)<1e-6)
      assert.equal(leaf.userData.centerSeamHalfWidth,.02)
      assert.equal(leaf.userData.crownHalfWidth,crownFit.stations[prefix].flatCrownWidth/2,'Closed covers retain the fitted narrow flat crown')
      rig.apply(1,0);const limit=leaf.quaternion.clone()
      for(const d of [.3,.42,.6,.9,1,.6,.3]) {
        rig.apply(d,0)
        assert.ok(leaf.quaternion.angleTo(limit)<1e-6,'Armor stays at its safe open stop while the gun moves')
      }
    }
  }
})

test('side 2 and 4 stow the bore, then seat the turret and rear pair, then close armor', () => {
  const {root,rig}=loadRig()
  for(const i of [2,4])for(const side of ['Port','Starboard']) {
    const prefix=`SideBattery_${i}_${side}`,gun=root.getObjectByName(prefix)
    const carriage=root.getObjectByName(prefix+'_SourceCarriage')
    const rear=['Port','Starboard'].map(s=>root.getObjectByName(`${prefix}_Shutter_${s}_00`))
    const forward=['Port','Starboard'].map(s=>root.getObjectByName(`${prefix}_Shutter_${s}_01`))
    rig.apply(.43,0);root.updateMatrixWorld(true)
    const openCarriage=carriage.position.clone(),openForward=forward.map(o=>o.matrixWorld.clone())
    const boreSeated=gun.quaternion.clone(),rearInTurret=rear.map(o=>o.matrix.clone())
    assert.ok(gun.quaternion.angleTo(new THREE.Quaternion())<1e-6)
    rig.apply(.37,0);root.updateMatrixWorld(true)
    assert.ok(carriage.position.distanceTo(openCarriage)>.1)
    assert.ok(gun.quaternion.angleTo(boreSeated)<1e-6,'Bore is seated throughout turret descent')
    rear.forEach((o,k)=>assertMatrixClose(o.matrix,rearInTurret[k],'Rear armor moves rigidly with its turret'))
    forward.forEach((o,k)=>assertMatrixClose(o.matrixWorld,openForward[k],'Forward armor stays on the hull'))
    rig.apply(.30,0);root.updateMatrixWorld(true)
    const seatedCarriage=carriage.position.clone()
    rear.forEach((o,k)=>assert.ok(o.quaternion.angleTo(new THREE.Quaternion().setFromRotationMatrix(rearInTurret[k]))<1e-6))
    rig.apply(.20,0);root.updateMatrixWorld(true)
    assert.ok(carriage.position.distanceTo(seatedCarriage)<1e-6,'Turret is seated before armor closes')
    assert.ok(rear.some((o,k)=>o.quaternion.angleTo(new THREE.Quaternion().setFromRotationMatrix(rearInTurret[k]))>.1))
  }
})

test('fitted original flank seams hide the interior and only the obsolete housing shell is removed', () => {
  const fit=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.27/source-fit.json',import.meta.url)))
  const geometry=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.27/source-geometry.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.27/mesh-clearance.json',import.meta.url)))
  const native=fs.readFileSync(new URL('../assets/blender/odin_articulated_v0.11.27.blend',import.meta.url))
  assert.equal(createHash('sha256').update(native).digest('hex'),geometry.nativeSha256,'Seam proof must belong to the committed editable model')
  assert.equal(geometry.sourceArmorPolygonsAndUvs.length,28)
  assert.equal(geometry.unchangedJointTransforms,191)
  assert.equal(geometry.unchangedJointMetadata,191)
  assert.equal(fit.removedLegacyHousing.removedPolygons,359)
  assert.equal(geometry.legacyFixedHousingPolygons,0)
  assert.equal(geometry.fixedBearingPolygons,1590,'The two source bearing islands remain fixed and intact')
  assert.equal(fit.removedLegacyHousing.retainedBearingIslands,2)
  assert.deepEqual(geometry.restoredGrayOuterEndFaces,[131174,163397])
  assert.equal(geometry.fixedHullCoordinatesAndUvsUnchanged,true)
  assert.equal(geometry.grayOuterFloorBands,4)
  assert.deepEqual(geometry.originalFloorFacesStillRed,[194058,163402])
  assert.equal(geometry.closedSeams.length,4)
  for(const row of geometry.sourceArmorPolygonsAndUvs)assert.ok(row.maxUvError<1e-6)
  for(const row of geometry.closedSeams) {
    assert.equal(row.rays,1140)
    assert.deepEqual(row.misses,[],`${row.station} exposes an open seam`)
    assert.deepEqual(row.interiorFirstHits,[],`${row.station} shows the red interior through a closed seam`)
    assert.equal(row.centerCrownRays,480)
    assert.deepEqual(row.centerCrownMisses,[],`${row.station} has an open center crown`)
    assert.deepEqual(row.centerCrownInteriorFirstHits,[],`${row.station} shows its red interior through the flat crown`)
    assert.ok(row.maxSurfaceDistanceError<.04)
    assert.deepEqual(clearance[row.station].barrelArmorContacts,[])
    assert.equal(clearance[row.station].poses,101)
  }
})

test('lower flank crowns form a sealed straight narrow roof and clear the unchanged bore action', () => {
  const geometry=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.28/source-geometry.json',import.meta.url)))
  const fit=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.28/source-fit.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.28/mesh-clearance.json',import.meta.url)))
  const native=fs.readFileSync(new URL('../assets/blender/odin_articulated_v0.11.28.blend',import.meta.url))
  assert.equal(createHash('sha256').update(native).digest('hex'),geometry.nativeSha256)
  assert.equal(geometry.sourceArmorPolygonsAndUvs.length,28)
  assert.equal(geometry.unchangedJointTransforms,191)
  assert.equal(geometry.unchangedMechanicalMetadata,191)
  assert.equal(geometry.removedFloatingTriangles,2)
  assert.equal(geometry.originalSourceUnchanged,true)
  for(const row of geometry.sourceArmorPolygonsAndUvs)assert.ok(row.maxUvError<1e-6)
  assert.equal(geometry.closedRoofs.length,4)
  for(const row of geometry.closedRoofs) {
    assert.ok(row.rays>2200)
    assert.deepEqual(row.misses,[],`${row.station} has a roof or bank opening`)
    assert.deepEqual(row.interiorFirstHits,[],`${row.station} shows primer through a closed seam`)
    assert.ok(row.maxCrownLineError<.015,`${row.station} has a stepped crown`)
    assert.ok(row.maxSideSeamError<.025)
    assert.equal(row.fixedReceiverRays,156)
    assert.deepEqual(row.fixedReceiverMisses,[])
    assert.deepEqual(row.fixedReceiverInteriorFirstHits,[])
    assert.ok(row.maxFixedReceiverCrownError<.015,'Fixed nose continues the same crown line')
    assert.ok(row.heightReduction>.7)
    assert.ok(row.flatCrownWidth>0&&row.flatCrownWidth<=.6)
    assert.equal(fit.stations[row.station].leaves.length,6)
    assert.deepEqual(clearance[row.station].barrelArmorContacts,[])
    assert.equal(clearance[row.station].poses,101)
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

test('side 2/4 hinges share the actual fixed-hull seam and lining respects the matching cover banks', () => {
  const {root,rig}=loadRig()
  const frames=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.10.0/source-covers.json',import.meta.url)))
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.29/source-geometry.json',import.meta.url)))
  assert.equal(proof.retainedSourcePolygons,proof.originalSourcePolygons)
  assert.ok(proof.originalSourcePolygons>6000)
  assert.ok(proof.maxSourceAreaError<.002)
  assert.ok(proof.maxSourceUvError<.0006)
  assert.equal(proof.hingeRails.length,24)
  assert.equal(proof.liningBanks.length,24)
  const roof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.29/roof-geometry.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.29/mesh-clearance.json',import.meta.url)))
  for(const row of roof.closedRoofs) {
    assert.equal(row.rays,2231)
    assert.deepEqual(row.misses,[])
    assert.deepEqual(row.interiorFirstHits,[])
    assert.ok(row.maxCrownLineError<.015)
    assert.equal(clearance[row.station].poses,101)
    assert.deepEqual(clearance[row.station].barrelArmorContacts,[])
  }
  for(const lip of roof.fixedHingeLips) {
    assert.equal(lip.rays,482)
    assert.deepEqual(lip.missing,[])
    assert.deepEqual(lip.redFirstHits,[])
    assert.ok(lip.maxOuterRailError<.015)
  }
  const toModel=(p)=>new THREE.Vector3(p.x,-p.z,p.y).multiplyScalar(100)
  for(const n of [2,4])for(const side of ['Port','Starboard']) {
    const name=`SideBattery_${n}_${side}`,frame=frames[name]
    const origin=new THREE.Vector3(...frame.frameOrigin)
    const local=(p)=>frame.frameAxes[0].map((_,c)=>frame.frameAxes.reduce((v,row,r)=>v+row[c]*p.getComponent(r),0))
    rig.apply(.18,0);root.updateMatrixWorld(true)
    for(const physical of ['Port','Starboard'])for(let i=0;i<3;i++) {
      const leaf=root.getObjectByName(`${name}_Shutter_${physical}_0${i}`)
      const [x,b,z]=local(toModel(leaf.getWorldPosition(new THREE.Vector3())).sub(origin))
      assert.ok(Math.abs(Math.abs(x)-2.88)<.0001)
      assert.ok(Math.abs(z-(1.7756-.007*b))<.0001,`${leaf.name} pivot lies on the hull seam during folding`)
      const axis=new THREE.Vector3(...leaf.userData.hingeAxisModel)
      const a=local(axis)
      assert.ok(new THREE.Vector3(...a).cross(new THREE.Vector3(0,1,-.007)).length()<.00001)
      assert.equal(leaf.userData.alignedSeamHinge,true)
    }
    assert.equal(root.getObjectByName(name+'_FrontCap').userData.holdRaisedAfterAdvance,true)
  }
})

test('rear flank covers follow the source turret-root bevels, seal the closed roof and clear the full sweep', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.30/root-geometry.json',import.meta.url)))
  const fit=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.30/root-fit.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.30/mesh-clearance.json',import.meta.url)))
  const native=fs.readFileSync(new URL('../assets/blender/odin_articulated_v0.11.30.blend',import.meta.url))
  assert.equal(createHash('sha256').update(native).digest('hex'),proof.nativeSha256)
  assert.equal(proof.rearCovers.length,8)
  assert.equal(proof.unchangedOtherMeshes,524)
  assert.equal(proof.unchangedJointTransforms,191)
  assert.equal(proof.unchangedMechanicalMetadata,191)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.animationClips,0)
  const {root}=loadRig()
  for(const [station,bay]of Object.entries(fit.stations)) {
    assert.equal(bay.rearCovers.length,2)
    assert.equal(clearance[station].poses,101)
    assert.deepEqual(clearance[station].rearCoverRootBevelContacts,[],`${station}: rear armor clips its inclined root face`)
    assert.deepEqual(clearance[station].barrelArmorContacts,[])
    for(const cover of bay.rearCovers) {
      const leaf=root.getObjectByName(cover.joint)
      assert.equal(leaf.userData.rearScarfClearance,.055)
      assert.equal(leaf.parent.name,station+'_SourceCarriage')
      assert.equal(leaf.userData.alignedSeamHinge,true)
      for(let i=0;i<2;i++) {
        const {sourcePlaneB,coverPlaneB}=cover.planes[i]
        assert.ok(Math.abs(coverPlaneB[2]-sourcePlaneB[2]-.055)<1e-8)
        assert.deepEqual(coverPlaneB.slice(0,2),sourcePlaneB.slice(0,2))
      }
      const result=proof.rearCovers.find(r=>r.mesh===cover.mesh)
      assert.equal(result.closedScarfRays,36)
      assert.deepEqual(result.missingRoof,[])
      assert.deepEqual(result.redFirstHits,[])
      assert.ok(result.maxRoofError<.015)
      assert.ok(result.retainedSourceUvError<.00001)
      assert.ok(result.maxTrimmedAreaError<.001)
      assert.ok(result.minimumPlaneMargins.every(m=>m>-.0001))
      assert.ok(result.sealedEndFaces>0)
    }
  }
})

test('bridge quads use the original frame-30 carriage seat and all original aiming channels on both mirrors', () => {
  const {root,rig}=loadRigAtPoseClock('quad')
  const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/bridge-quad-source-v01131.json',import.meta.url)))
  const toModel=p=>new THREE.Vector3(p.x,-p.z,p.y).multiplyScalar(100)
  const basis=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.PI/2)
  function inverseEase(value){let lo=0,hi=1;for(let i=0;i<45;i++){const x=(lo+hi)/2;if(x*x*(3-2*x)<value)lo=x;else hi=x;}return(lo+hi)/2;}
  for(const row of fixture.samples) {
    const d=row.frame<=45?.20+.36*inverseEase((row.frame-30)/15):.80+.20*(row.frame-53)/33
    rig.apply(d,0);root.updateMatrixWorld(true)
    for(const side of ['Port','Starboard']) {
      const carriage=root.getObjectByName(`PDC_${side}_Carriage`),expected=new THREE.Vector3(...row.carriages[side].slice(0,3).map(r=>r[3]))
      assert.ok(toModel(carriage.getWorldPosition(new THREE.Vector3())).distanceTo(expected)<.0001,`${side} differs from source carriage frame ${row.frame}`)
      if(row.frame>=53) {
        const source=new THREE.Matrix4().set(...row.guns[side].flat())
        if(side==='Starboard')source.multiply(new THREE.Matrix4().makeScale(-1,1,1))
        const turn=new THREE.Quaternion().setFromRotationMatrix(source).normalize()
        const expectedTurn=basis.clone().multiply(turn).multiply(basis.clone().invert())
        assert.ok(root.getObjectByName(`PDC_${side}_Gimbal`).getWorldQuaternion(new THREE.Quaternion()).angleTo(expectedTurn)<.00001,`${side} differs from all source aim channels at frame ${row.frame}`)
      }
    }
  }
})

test('bridge quads preserve the original axial stroke and shorter transverse packing on their accepted pose path', () => {
  const {root,rig}=loadRigAtPoseClock('quad')
  const ease=(a,b,d)=>{const u=THREE.MathUtils.clamp((d-a)/(b-a),0,1);return u*u*(3-2*u)}
  const map=([x,y,z])=>new THREE.Vector3(x,z,-y)
  for(const side of ['Port','Starboard'])for(let i=0;i<4;i++) {
    const tube=root.getObjectByName(`PDC_${side}_Arm_${i}`),cradle=root.getObjectByName(`PDC_${side}_Cradle_${i}`)
    rig.apply(.78,0)
    const t1=tube.position.clone(),c1=cradle.position.clone()
    assert.equal(tube.userData.slideStart,.03);assert.equal(tube.userData.slideEnd,.18)
    assert.equal(tube.userData.extendsAfterPetal,undefined)
    assert.equal(cradle.userData.synchronizedPetal,undefined)
    const vector=map(cradle.userData.compactVector),old=map([0,(i<2?1:-1)*2,(i%2? -1:1)*.3])
    for(const d of [...Array.from({length:181},(_,n)=>n/1000),...Array.from({length:181},(_,n)=>(180-n)/1000)]) {
      rig.apply(d,0)
      const c=1-ease(.03,.18,d),original=c+2.5*c*(1-c)**2,shorter=original*(1-.60*ease(.12,.15,d))
      assert.ok(cradle.position.clone().sub(c1).distanceTo(vector.clone().multiplyScalar(shorter))<1e-9)
      assert.ok(cradle.position.distanceTo(c1)<=old.length()*original+1e-9,'Center packing is never deeper than the original stroke')
      assert.ok(tube.position.clone().sub(t1).distanceTo(map(tube.userData.slideVector).multiplyScalar(c))<1e-9,'Original axial travel and timing stay unchanged')
      if(d>=.15&&d<.18&&original>0)assert.ok(cradle.position.distanceTo(c1)<.401*old.length()*original,'Exposed tubes retain wider transverse spacing')
    }
  }
})

test('quad tubes keep the previous 11-percent reach; all gray armor stays unrotated and locks ship X in plan view', () => {
  const ease=(a,b,d)=>{const t=THREE.MathUtils.clamp((d-a)/(b-a),0,1);return t*t*(3-2*t)}
  const {root,rig,meshBounds}=loadRigAtPoseClock('quad'),travel=32*(1-ease(.03,.18,.11))
  for(const side of ['Port','Starboard'])for(let i=0;i<4;i++) {
    const arm=root.getObjectByName(`PDC_${side}_Arm_${i}`),petal=root.getObjectByName(`PDC_${side}_HullPetal_${i}`)
    rig.apply(1,0);root.updateMatrixWorld(true)
    const a1=arm.position.clone(),p1=petal.position.clone(),restTurn=petal.quaternion.clone()
    const skin=petal.children.find(o=>meshBounds.has(o)),box=meshBounds.get(skin)
    const corners=[box.min.x,box.max.x].flatMap(x=>[box.min.y,box.max.y].flatMap(y=>[box.min.z,box.max.z].map(z=>new THREE.Vector3(x,y,z))))
    const openX=corners.map(p=>p.clone().applyMatrix4(skin.matrixWorld).x)
    assert.equal(arm.userData.stowReferenceProgress,.11)
    assert.ok(Math.abs(arm.userData.stowTravel-travel)<1e-9)
    assert.equal(petal.userData.translationOnly,true)
    assert.equal(petal.userData.compactRotationWXYZ,undefined)
    // Reject the old rotating-plate behavior even if stale rotation extras recur.
    petal.userData.compactRotationWXYZ=[Math.cos(.1),0,Math.sin(.1),0]
    for(const d of [...Array.from({length:101},(_,n)=>1-n/100),...Array.from({length:101},(_,n)=>n/100)]) {
      rig.apply(d,0);root.updateMatrixWorld(true)
      assert.equal(petal.position.x,p1.x,'No port/starboard petal translation at any progress')
      assert.ok(petal.quaternion.angleTo(restTurn)<1e-7,'The original petal orientation never changes')
      corners.forEach((p,n)=>assert.ok(Math.abs(p.clone().applyMatrix4(skin.matrixWorld).x-openX[n])<1e-12,'Every point in the armor bounds retains ship X through aiming, carriage travel and packing'))
      const compact=1-ease(.03,.18,d),center=(compact+2.5*compact*(1-compact)**2)**2,vector=petal.userData.compactVector
      const expected=new THREE.Vector3(0,vector[2],-vector[1]).multiplyScalar(center)
      assert.ok(petal.position.clone().sub(p1).distanceTo(expected)<1e-6)
      assert.ok(Math.abs(arm.position.distanceTo(a1)-travel*(1-ease(.03,.18,d)))<1e-6)
    }
  }
})

test('quad bearings follow the shorter tube packing while guides retain their original net endpoint', () => {
  const {root,rig}=loadRigAtPoseClock('quad')
  const ease=(a,b,d)=>{const u=THREE.MathUtils.clamp((d-a)/(b-a),0,1);return u*u*(3-2*u)}
  for(const side of ['Port','Starboard'])for(let i=0;i<4;i++) {
    const cradle=root.getObjectByName(`PDC_${side}_Cradle_${i}`),guide=root.getObjectByName(`PDC_${side}_CradleGuide_${i}`)
    rig.apply(.78,0);const open=cradle.position.clone(),g1=guide.position.clone()
    let previous=0
    for(let n=0;n<=400;n++) {
      const d=1-n/400;rig.apply(d,0)
      const c=1-ease(.03,.18,d),clock=(c+2.5*c*(1-c)**2)*(1-.60*ease(.12,.15,d))
      const shift=cradle.position.clone().sub(open),expected=new THREE.Vector3(0,0,-guide.userData.compactVector[1]).multiplyScalar(clock)
      assert.equal(shift.x,0)
      assert.ok(guide.position.clone().sub(g1).distanceTo(expected)<1e-9)
      assert.ok(shift.length()>=previous-1e-9,'The packing stroke never reverses')
      previous=shift.length()
    }
    const net=cradle.position.clone().sub(open).add(guide.position.clone().sub(g1))
    assert.ok(Math.abs(Math.abs(net.z)-.6)<1e-6)
    assert.ok(Math.abs(Math.abs(net.y)-.30)<1e-6)
  }
})

test('original bridge quad parts and UVs remain intact; fitted petals match the complete adjoining roof surface', () => {
  const geometry=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.34/source-geometry.json',import.meta.url)))
  const restored=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.34/source-restoration.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.34/mesh-clearance.json',import.meta.url)))
  const native=fs.readFileSync(new URL('../assets/blender/odin_articulated_v0.11.34.blend',import.meta.url))
  assert.equal(createHash('sha256').update(native).digest('hex'),geometry.nativeSha256)
  assert.equal(geometry.maxPointError,0)
  assert.equal(geometry.maxUvError,0)
  assert.equal(geometry.sourceMeshParts.length,36)
  assert.equal(geometry.unchangedOtherMeshes,493)
  assert.equal(geometry.fixedSeamEditedVertices,32)
  assert.equal(geometry.fixedHullOutsideSeamsUnchanged,true)
  assert.equal(geometry.unchangedOtherJoints,171)
  assert.equal(geometry.beltGeometryUnchanged,true)
  assert.equal(geometry.originalSourceUnchanged,true)
  assert.equal(geometry.animationClips,0)
  assert.equal(restored.beltColors.filter(f=>f.material==='Odin_Paint_Dark.001').length,6)
  for(const side of ['Port','Starboard']) {
    assert.equal(restored.quads[side].completeGunVertices,5001)
    assert.equal(restored.quads[side].supportVertices,1602)
    assert.equal(restored.quads[side].sourcePetals,4)
    for(const quadrant of restored.quads[side].quadrants) {
      assert.equal(quadrant.tubeVertices,204,'Complete long tube and inner sleeves share the extra slide')
      assert.equal(quadrant.rearCradleVertices,771,'Original gray cradle, bearing and foot keep the turret stroke')
    }
    assert.equal(clearance[side].poses,401)
    assert.deepEqual(clearance[side].barrelPetalContacts,[])
    assert.deepEqual(clearance[side].cradlePairContacts,[])
    assert.ok(clearance[side].sourceMeshesRemainRigid)
    assert.equal(clearance[side].maxArmorVertexXChange,0)
    assert.equal(clearance[side].maxArmorRotationRadians,0)
    assert.ok(clearance[side].maxArmorReturnStroke<.00002)
    assert.equal(clearance[side].maxOpenEndpointDrift,0)
    for(const seam of clearance[side].closedForwardSeams) {
      assert.ok(seam.closedEdgeEndpointGap<.00003)
      assert.ok(seam.closedEdgeAngleDegrees<.001)
      assert.ok(seam.maxClosedSurfaceError<.00003,'The whole outer skin seats on the adjoining fixed roof plane')
    }
    for(const tube of clearance[side].hiddenBarrelTips) {
      assert.ok(tube.hiddenBehindArmor>.20)
      assert.ok(tube.referenceTipError<.00002,'NAV tube reach matches the requested prior 11-percent position')
    }
  }
})

test('bridge quad armor completes one monotonic stroke and holds its endpoint through carriage travel and aiming', () => {
  const {root,rig}=loadRigAtPoseClock('quad')
  for(const side of ['Port','Starboard'])for(let i=0;i<4;i++) {
    const petal=root.getObjectByName(`PDC_${side}_HullPetal_${i}`),out=i%2?1:-1
    rig.apply(1,0);const open=petal.position.clone()
    assert.equal(petal.userData.monotonicPetalStroke,true)
    assert.equal(petal.userData.translationClearanceZ,undefined)
    assert.equal(petal.userData.openEndpointHoldStart,.18)
    // A stale v33 clearance pulse must never reintroduce the descending leg.
    Object.assign(petal.userData,{translationClearanceZ:.25*out,translationClearanceReleaseStart:.35,translationClearanceReleaseEnd:.60})
    let previous=-Infinity
    for(let n=0;n<=400;n++) {
      const d=n/400;rig.apply(d,0)
      assert.ok(out*petal.position.y>=previous-1e-9,'Opening never reverses direction')
      previous=out*petal.position.y
      if(d>=.18)assert.ok(petal.position.distanceTo(open)<1e-12,'Armor stays at its opening endpoint without lowering')
    }
    for(let n=400;n>=72;n--) {
      rig.apply(n/400,0)
      assert.ok(petal.position.distanceTo(open)<1e-12,'The held endpoint also survives reverse playback')
    }
  }
})

test('synchronized quad revision preserves source geometry and verifies the actual meshes through both strokes', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.41/source-geometry.json',import.meta.url)))
  const hashes=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.41/asset-hashes.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.41/mesh-clearance.json',import.meta.url)))
  for(const[name,path]of[['native','../assets/blender/odin_articulated_v0.11.41.blend']])
    assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[name].sha256)
  assert.equal(proof.nativeSha256,hashes.native.sha256)
  assert.equal(proof.allMeshesUnchanged,550)
  assert.equal(proof.allStaticRestFramesUnchanged,215)
  assert.equal(proof.unaffectedJointProperties,191)
  assert.equal(proof.modifiedJointProperties.length,24)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.animationClips,0)
  for(const side of ['Port','Starboard']) {
    const sweep=clearance[side]
    assert.equal(sweep.poses,442)
    assert.deepEqual(sweep.barrelPetalContacts,[])
    assert.deepEqual(sweep.cradlePairContacts,[])
    assert.deepEqual(sweep.tubePairContacts,[])
    assert.ok(sweep.maxTransverseDisplacementMismatch<.00003)
    assert.equal(sweep.maxTubeAdvanceBeforePetalsOpen,0)
    assert.equal(sweep.maxArmorVertexXChange,0)
    assert.equal(sweep.maxArmorRotationRadians,0)
    for(const seam of sweep.closedForwardSeams){assert.ok(seam.endpointGap<.00003&&seam.surfaceError<.00003&&seam.edgeAngleDegrees<.001)}
    for(const tip of sweep.hiddenBarrelTips)assert.ok(tip.hiddenBehindArmor>.20)
  }
})

test('v35 aft twin cover evidence remains reproducible', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.35/source-geometry.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.35/mesh-clearance.json',import.meta.url)))
  const native=fs.readFileSync(new URL('../assets/blender/odin_articulated_v0.11.35.blend',import.meta.url))
  assert.equal(createHash('sha256').update(native).digest('hex'),proof.nativeSha256)
  assert.equal(proof.covers.length,4)
  assert.ok(proof.unchangedOtherMeshes>=500)
  assert.equal(proof.unchangedJointTransforms,proof.unchangedJointMotionMetadata)
  assert.ok(proof.unchangedJointTransforms>=200)
  assert.equal(proof.fixedHullUnchanged,true)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.animationClips,0)
  for(const cover of proof.covers) {
    assert.equal(cover.vertices,8)
    assert.equal(cover.faces,6)
    assert.ok(cover.outerPlanarityError<.00003)
    assert.ok(cover.maxThicknessError<.00003,'Cover extrusion matches the actual adjoining source-shell thickness')
    assert.ok(cover.coverThickness>.50&&cover.coverThickness<.56,'The old arbitrary 0.18-thick cover must not return')
    assert.ok(cover.sourceCornerGap.every(gap=>gap<.065),'Cover corners remain on the narrow source-rim seam with exterior ridge clearance')
    const sweep=clearance[String(cover.station)]
    assert.equal(sweep.poses,401)
    assert.deepEqual(sweep.gunCoverContacts,[])
    assert.deepEqual(sweep.railCoverContacts,[])
    assert.deepEqual(sweep.scanEndpointContacts,[])
    assert.equal(sweep.closedExteriorHullContacts,0,'The closed skin clears the fixed serrated source rim')
    assert.ok(sweep.unseatedExteriorControlContacts>0,'Removing the exterior ridge clearance must intersect the fixed source rim')
    assert.ok(sweep.unsunkControlContacts>0,'Omitting the original carriage sink must trigger the real mesh intersection check')
  }
  for(const [a,b]of[[5,7],[6,8]]) {
    const x=proof.covers.find(r=>r.station===a),y=proof.covers.find(r=>r.station===b)
    assert.ok(Math.abs(x.coverThickness-y.coverThickness)<.00003)
    assert.ok(Math.abs(x.normal[0]+y.normal[0])<.00001)
    assert.ok(Math.abs(x.normal[1]-y.normal[1])<.00001)
    assert.ok(Math.abs(x.normal[2]-y.normal[2])<.00001)
  }
})

test('v36 first-layer aft twin cover evidence remains reproducible', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.36/source-geometry.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.36/mesh-clearance.json',import.meta.url)))
  const hashes=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.36/asset-hashes.json',import.meta.url)))
  for(const [name,path]of [['native','../assets/blender/odin_articulated_v0.11.36.blend']]) {
    const file=fs.readFileSync(new URL(path,import.meta.url))
    assert.equal(createHash('sha256').update(file).digest('hex'),hashes[name].sha256)
  }
  assert.equal(hashes.native.sha256,proof.nativeSha256)
  assert.ok(proof.sourceReceiverVerticesVerified>=480)
  assert.equal(proof.unchangedOtherMeshes,528)
  assert.equal(proof.unchangedJointTransforms,207)
  assert.equal(proof.unchangedJointMotionMetadata,207)
  assert.equal(proof.fixedHullUnchanged,true)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.animationClips,0)
  for(const row of proof.covers) {
    assert.equal(row.sourceFloorSections,56)
    assert.equal(row.watertightShell,true)
    assert.ok(Object.values(row.receiverContourMaxErrors).every(error=>error<.00803),
      'Both end profiles and all serrated outer/inner floor sections join the actual immutable source cut')
    assert.ok(row.maxEndContourErrorAfterClearance<.00003)
    assert.ok(row.lowerShellSectionVectorError<.00003,'Lower return thickness and direction reproduce the whole source cross-section')
    assert.ok(row.lowerReturnWidths.every(width=>width>.8))
    assert.ok(row.oldCoverControlErrors.innerBottom>.25,'This check rejects the old constant-thickness normal extrusion')
    assert.ok(row.oldCoverControlErrors.outerBottom>.1,'This check rejects the old four-corner approximation')
    const sweep=clearance[String(row.station)]
    assert.equal(sweep.poses,401)
    assert.deepEqual(sweep.gunCoverContacts,[])
    assert.deepEqual(sweep.railCoverContacts,[])
    assert.deepEqual(sweep.scanEndpointContacts,[])
    assert.ok(sweep.unsunkControlContacts>0)
  }
})

test('aft twin cover thickness reaches the innermost original hull edge across the entire upper rim', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.37/source-geometry.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.37/mesh-clearance.json',import.meta.url)))
  const hashes=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.37/asset-hashes.json',import.meta.url)))
  for(const [name,path]of [['native','../assets/blender/odin_articulated_v0.11.37.blend']]) {
    assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[name].sha256)
  }
  assert.equal(hashes.native.sha256,proof.nativeSha256)
  assert.ok(proof.sourceReceiverVerticesVerified>=920)
  assert.equal(proof.sourceRoofEdgesVerified,22)
  assert.equal(proof.unchangedOtherMeshes,528)
  assert.equal(proof.unchangedJointTransforms,207)
  assert.equal(proof.unchangedJointMotionMetadata,207)
  assert.equal(proof.fixedHullUnchanged,true)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.animationClips,0)
  for(const row of proof.covers) {
    assert.equal(row.sourceShellLayers,4)
    assert.equal(row.sourceFloorSections,56)
    assert.equal(row.watertightShell,true)
    assert.ok(Object.values(row.fullReceiverContourMaxErrors).every(error=>error<.00003))
    assert.ok(row.upperShellSectionVectorError<.00003)
    assert.ok(row.lowerShellSectionVectorError<.00003)
    assert.ok(Object.values(row.fullRoofBoundaryErrors).every(error=>error<.00003),
      'The whole top boundary must follow actual original roof edges without a valley at an internal cut vertex')
    assert.equal(row.upperRimSectionLengths.length,56)
    assert.ok(row.upperRimSectionLengths.every(width=>width>1.0))
    assert.ok(row.oldFirstLayerControlMinThicknessError>.50,
      'This independent source-section check must reject the v36 half-thickness upper rim')
    const sweep=clearance[String(row.station)]
    assert.equal(sweep.poses,401)
    assert.deepEqual(sweep.gunCoverContacts,[])
    assert.deepEqual(sweep.railCoverContacts,[])
    assert.deepEqual(sweep.scanEndpointContacts,[])
    assert.ok(sweep.unsunkControlContacts>0)
  }
})

test('forward twins keep fixed hoods and centered complete guides on one shorter measured ramp stroke', () => {
  const { root, rig } = loadRig()
  const fit = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.40/assembly-fit.json', import.meta.url)))
  const old = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.38/source-geometry.json', import.meta.url)))
  const map = ([x,y,z]) => new THREE.Vector3(x,z,-y)
  rig.apply(0, 0); root.updateMatrixWorld(true)
  const baselines = fit.stations.map(row => {
    const prefix = `Defense_${String(row.station).padStart(2,'0')}`
    const carriage = root.getObjectByName(prefix + '_Carriage')
    const hood = root.getObjectByName(prefix + '_FixedHood')
    const lower = root.getObjectByName(prefix + '_LowerCradle')
    const guides = root.getObjectByName(prefix + '_Guides')
    assert.equal(hood.parent.name, prefix + '_FixedArmor')
    assert.equal(hood.parent.parent.name, 'Odin_Asset')
    assert.equal(lower.parent, carriage)
    assert.equal(guides.parent, carriage)
    assert.ok(row.drop > 2.2 && row.drop < 2.7, 'The closed height remains near the former 60-percent pose')
    assert.ok(row.horizontalTravel > 3 && row.horizontalTravel < 3.8, 'The inward stroke is much shorter than the former ten-unit travel')
    const rest = map(old.stations.find(entry => entry.station === row.station).originalRestOrigin)
    const deployed = rest.add(map(row.deployedOffsetModel))
    return { row, prefix, carriage, hood, lower, guides, deployed, slide: map(row.stowVectorModel), normal: map(row.rampNormalModel), transverse: map(row.receiverCrossAxisModel), center: map(row.receiverCenterModel), hoodWorld: hood.matrixWorld.clone(), lowerRelative: relativeMatrix(lower,carriage), guideRelative: relativeMatrix(guides,lower), guideHeading: guides.getWorldQuaternion(new THREE.Quaternion()) }
  })
  for (const d of [0,.04,.22,.24,.32,.4,.47,.52,.56,.60,.64,.65,.69,.85,1,.85,.64,.5,.4,.24,.22,0]) {
    rig.apply(d, 20); root.updateMatrixWorld(true)
    for (const b of baselines) {
      assertMatrixClose(b.hood.matrixWorld,b.hoodWorld,`Fixed white armor on twin ${b.row.station} moved`)
      assertMatrixClose(relativeMatrix(b.lower,b.carriage),b.lowerRelative,'Lower armor and brackets must rise with the turret')
      assert.ok(b.guides.getWorldQuaternion(new THREE.Quaternion()).angleTo(b.guideHeading)<1e-6,'Source guides preserve the receiver heading while the gun aligns')
      const u = Math.max(0,Math.min(1,(d-.24)/.4)), seated = 1-u*u*(3-2*u)
      const delta = b.carriage.position.clone().sub(b.deployed)
      assert.ok(delta.distanceTo(b.slide.clone().multiplyScalar(seated))<.00003,'Inward and downward movement share the same progress')
      assert.ok(Math.abs(delta.dot(b.normal))<.00003,'The entire stroke must be tangent to the original inclined cradle underside')
      assert.ok(Math.abs(b.carriage.position.clone().sub(b.center).dot(b.transverse))<.00003,'The whole turret remains centered on the fixed receiver')
      if (d<=.64) {
        assertMatrixClose(relativeMatrix(b.guides,b.lower),b.guideRelative,'Each guide stays rigidly registered to the cradle throughout the inclined stroke')
        const bore = map(root.getObjectByName(b.prefix+'_Tubes').userData.horizontalBoreAxisModel).applyQuaternion(b.carriage.quaternion)
        assert.ok(Math.abs(bore.dot(b.transverse))<.00003,'The closed gun must face along the hood centerline instead of sitting crooked')
        assert.ok(root.getObjectByName(b.prefix+'_Yaw').quaternion.angleTo(new THREE.Quaternion())<1e-6,'Aiming neutralizes before retraction')
      }
      assert.ok(b.carriage.position.y<=b.deployed.y+.00003 && b.carriage.position.y>=b.deployed.y-b.row.drop-.00003)
    }
  }
})

test('v38 forward twin source partition and clearance evidence remain reproducible', () => {
  const proof = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.38/source-geometry.json',import.meta.url)))
  const hashes = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.38/asset-hashes.json',import.meta.url)))
  const clearance = JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.38/mesh-clearance.json',import.meta.url)))
  for(const [name,path] of [['native','../assets/blender/odin_articulated_v0.11.38.blend']]) {
    assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[name].sha256)
  }
  assert.equal(hashes.native.sha256,proof.nativeSha256)
  assert.equal(proof.originalRailFacesAndUVsPreservedExactlyOnce,true)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.unchangedOtherMeshes,530)
  assert.equal(proof.unchangedStaticJointTransforms,207)
  assert.equal(proof.unchangedOtherJointProperties,201)
  for(const row of proof.stations) {
    assert.equal(row.hoodVertices,718)
    assert.ok(row.supportVertices>8900)
    assert.ok(row.FixedHoodSourceMaxError<.0001)
    assert.ok(row.LowerCradleSourceMaxError<.16)
    assert.ok(row.inheritedSupportSourceSurfaceDifferences.length<.005*row.supportVertices,
      'Existing evaluated bearing seam differences remain bounded while every prior face and UV is preserved')
    const sweep=clearance[String(row.station)]
    assert.equal(sweep.poses,416)
    assert.deepEqual(sweep.hoodContacts,[])
    assert.deepEqual(sweep.upperRailContacts,[])
    assert.ok(sweep.zeroDropControlContacts.length>0,
      'Keeping the old starting height during inward travel must fail the real hood contact check')
  }
})

test('forward tubes follow the carriage first then withdraw horizontally while original rear brackets hold still', () => {
  const {root,rig}=loadRig()
  rig.apply(.22,0);root.updateMatrixWorld(true)
  const scale=root.getObjectByName('Odin_Asset').scale.x
  const baselines=Array.from({length:4},(_,i)=>{
    const prefix=`Defense_${String(i+1).padStart(2,'0')}`
    const tube=root.getObjectByName(prefix+'_Tubes'),carriage=root.getObjectByName(prefix+'_Carriage')
    const suffix='turret 1'+(i?`.${String(i).padStart(3,'0')}`:'')
    const rear=root.getObjectByName('odin.072__'+suffix)
    return {tube,carriage,rear,rest:tube.position.clone(),initial:tube.getWorldPosition(new THREE.Vector3()),rearWorld:rear.matrixWorld.clone(),carriageWorld:carriage.matrixWorld.clone()}
  })
  for(const d of [.22,.15,.10,.04,0,.1,.22,.4,.64,1,.64,.4,.22,0]){
    rig.apply(d,0);root.updateMatrixWorld(true)
    for(const b of baselines){
      if(d<=.22){
        assertMatrixClose(b.carriage.matrixWorld,b.carriageWorld,'The carriage holds its seat during the extra barrel withdrawal')
        assertMatrixClose(b.rear.matrixWorld,b.rearWorld,'Original rear elevation brackets must not telescope with the tubes')
        const delta=b.tube.getWorldPosition(new THREE.Vector3()).sub(b.initial)
        assert.ok(Math.abs(delta.y)<1e-7,'Extra barrel withdrawal must never move downward')
        if(d===0)assert.ok(Math.abs(delta.length()/scale-5)<1e-5,'Original tubes receive the additional five-unit horizontal stroke')
      }else assert.ok(b.tube.position.distanceTo(b.rest)<1e-7,'The tubes travel rigidly with the turret throughout the inclined carriage stroke')
    }
  }
})

test('forward twin foundations stay on the hull and cradle heading never changes through either playback direction', () => {
  const {root,rig}=loadRig()
  rig.apply(0,0);root.updateMatrixWorld(true)
  const bases=Array.from({length:4},(_,i)=>{
    const prefix=`Defense_${String(i+1).padStart(2,'0')}`
    const foundation=root.getObjectByName(prefix+'_FixedFoundation'),skin=root.getObjectByName(prefix+'_FoundationGeometry')
    const carriage=root.getObjectByName(prefix+'_Carriage'),guides=root.getObjectByName(prefix+'_Guides')
    assert.equal(foundation.parent.name,'Odin_Asset')
    assert.equal(foundation.userData.staticJoint,undefined)
    assert.equal(skin.parent,foundation)
    assert.equal(carriage.userData.translationOnly,true)
    // A cached former alignment interval must not bring back the late twist.
    Object.assign(carriage.userData,{closedAlignmentDegrees:25,alignStart:.65,alignEnd:.85})
    return {skin,carriage,guides,world:skin.matrixWorld.clone(),turn:carriage.quaternion.clone(),guideTurn:guides.getWorldQuaternion(new THREE.Quaternion())}
  })
  for(const d of [...Array.from({length:401},(_,i)=>i/400),...Array.from({length:401},(_,i)=>1-i/400)]){
    rig.apply(d,20);root.updateMatrixWorld(true)
    for(const b of bases){
      assertMatrixClose(b.skin.matrixWorld,b.world,'The lower 140-vertex source foundation must remain attached to the hull')
      assert.ok(b.carriage.quaternion.angleTo(b.turn)<1e-7,'The cradle never rotates while translating or holding its endpoint')
      assert.ok(b.guides.getWorldQuaternion(new THREE.Quaternion()).angleTo(b.guideTurn)<1e-6,'Fixed guide heading must survive late aiming')
    }
  }
})

test('fixed forward foundations preserve original faces and match the stationary ramp throughout actual mesh travel', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.40/source-geometry.json',import.meta.url)))
  const hashes=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.40/asset-hashes.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.40/mesh-clearance.json',import.meta.url)))
  for(const[name,path]of[['native','../assets/blender/odin_articulated_v0.11.40.blend']])
    assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[name].sha256)
  assert.equal(proof.nativeSha256,hashes.native.sha256)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.allLowerFacesAndUVsPreservedExactlyOnce,true)
  assert.ok(proof.unchangedOtherMeshes>530)
  assert.equal(proof.unchangedExistingJointTransforms,215)
  assert.equal(proof.unchangedOtherJointProperties,211)
  for(const row of proof.stations){
    assert.equal(row.foundationVertices,140)
    assert.equal(row.foundationFaces,145)
    assert.equal(row.allLowerFacesAndUVsPreservedExactlyOnce,true)
    assert.ok(row.stationaryRampTangencyError<.00003)
    const sweep=clearance[String(row.station)]
    assert.equal(sweep.poses,416)
    assert.deepEqual(sweep.upperFoundationContacts,[])
    assert.deepEqual(sweep.hoodContacts,[])
    assert.deepEqual(sweep.upperGuideContacts,[])
    assert.equal(sweep.maxFoundationWorldChange,0)
    assert.ok(sweep.maxCradleRotationRadians<1e-6)
  }
})

test('inclined twin native surfaces are preserved and clear the fixed receiver throughout both stages', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.39/source-geometry.json',import.meta.url)))
  const hashes=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.39/asset-hashes.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.39/mesh-clearance.json',import.meta.url)))
  for(const [name,path] of [['native','../assets/blender/odin_articulated_v0.11.39.blend']])assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[name].sha256)
  assert.equal(proof.nativeSha256,hashes.native.sha256)
  assert.equal(proof.originalSourceUnchanged,true)
  assert.equal(proof.allPartitionedFacesAndUVsPreservedExactlyOnce,true)
  assert.equal(proof.unchangedOtherMeshes,530)
  assert.equal(proof.unchangedExistingJointTransforms,207)
  assert.equal(proof.unchangedOtherJointProperties,201)
  assert.equal(proof.newHorizontalTubeJoints,4)
  assert.equal(proof.newReceiverGuideJoints,4)
  for(const row of proof.stations){
    assert.equal(row.tubeVertices,9882)
    assert.equal(row.retainedRearBracketVertices,3698)
    assert.equal(row.receiverMaterialsAndUVLayersPreserved,true)
    assert.equal(row.receiverRoofSurfaceSamples,49)
    assert.ok(row.receiverRoofSurfaceMaxError<.00003,'Local receiver side relief must preserve the original central canopy surface')
    assert.ok(row.receiverRoofHeightMaxError<.00003,'Receiver side relief must preserve the roof height')
    assert.ok(row.rampTangencyError<.00003 && row.receiverCenterlineError<.00003 && row.closedBoreAlignmentError<.00003)
    const sweep=clearance[String(row.station)]
    assert.equal(sweep.poses,416)
    assert.deepEqual(sweep.hoodContacts,[])
    assert.deepEqual(sweep.upperGuideContacts,[])
    assert.ok(sweep.horizontalOnlyControlContacts.length>0,'Keeping the stroke horizontal must fail actual fixed-hood clearance')
  }
})

test('limited quad packing preserves all source parts and restores every unrelated original trajectory', () => {
  const proof=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.42/source-geometry.json',import.meta.url)))
  const hashes=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.42/asset-hashes.json',import.meta.url)))
  const clearance=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.42/mesh-clearance.json',import.meta.url)))
  const other=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.42/other-motion.json',import.meta.url)))
  const spacing=JSON.parse(fs.readFileSync(new URL('../docs/review/v0.11.42/tube-spacing.json',import.meta.url)))
  for(const[name,path]of[['native','../assets/blender/odin_articulated_v0.11.42.blend']])
    assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex'),hashes[name].sha256)
  assert.equal(proof.nativeSha256,hashes.native.sha256)
  assert.equal(proof.allMeshesUnchanged,550);assert.equal(proof.allStaticRestFramesUnchanged,215)
  assert.equal(proof.unaffectedJointProperties,199);assert.equal(proof.modifiedJointProperties.length,16)
  assert.equal(proof.allArmorGeometryAndMetadataUnchanged,true);assert.equal(proof.axialMotionMetadataUnchanged,true)
  assert.equal(proof.originalSourceUnchanged,true);assert.equal(proof.animationClips,0)
  assert.equal(other.unaffectedJoints,191);assert.equal(other.samples,303);assert.equal(other.maxWorldMatrixError,0)
  for(const side of ['Port','Starboard']) {
    assert.equal(spacing.sides[side].samples,181);assert.equal(spacing.sides[side].neverNarrower,true)
    const visible=spacing.sides[side].examples.find(row=>row.progress===.14)
    assert.ok(visible.current.foreAft-visible.previous.foreAft>.80,'Actual tube mesh centers have visibly wider spacing in the release stroke')
    assert.ok(visible.current.vertical>visible.previous.vertical)
    const sweep=clearance[side]
    assert.equal(sweep.poses,442)
    assert.deepEqual(sweep.barrelPetalContacts,[]);assert.deepEqual(sweep.cradlePairContacts,[]);assert.deepEqual(sweep.tubePairContacts,[])
    assert.ok(sweep.maxPackingPathError<.00003);assert.ok(sweep.maxAxialMotionError<.00003)
    assert.equal(sweep.maxArmorVertexXChange,0);assert.equal(sweep.maxArmorRotationRadians,0)
    for(const seam of sweep.closedForwardSeams)assert.ok(seam.endpointGap<.00003&&seam.surfaceError<.00003&&seam.edgeAngleDegrees<.001)
  }
})
