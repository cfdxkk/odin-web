import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import * as THREE from 'three'
const manifest = JSON.parse(readFileSync(new URL('../public/models/asset-manifest.json', import.meta.url)))
for (const model of ['odin.glb', 'odin-lite.glb']) {
const file = readFileSync(new URL(`../public/models/${model}`, import.meta.url))
assert.equal(file.readUInt32LE(0), 0x46546c67, 'GLB header')
assert.equal(file.readUInt32LE(4), 2, 'glTF 2.0')
assert.equal(file.readUInt32LE(8), file.length, 'complete file length')
const asset = JSON.parse(file.subarray(20, 20 + file.readUInt32LE(12)).toString())
assert.equal(asset.animations?.length || 0, 0, 'All animation must remain in Nuxt JavaScript')
assert.equal(asset.cameras?.length || 0, 0, 'No Blender camera exported')
assert.ok(!asset.nodes.some(n => /perseus/i.test(n.name)), 'Other ships excluded')
const names = new Set(asset.nodes.map(n => n.name))
for (const name of ['Odin_Asset', 'Main_Dorsal_Barrels', 'Main_Ventral_Barrels', 'Hatch_Dorsal_Port', 'Hatch_Ventral_Starboard', 'Main_Dorsal_Tube_Port', 'Main_Dorsal_Tube_Center', 'Main_Ventral_Tube_Center', 'Main_Ventral_Tube_Starboard', 'Axial_Bow_SourceReceiver', 'Axial_Bow_Shutter_Port_00', 'Axial_Bow_FrontCap', 'Axial_Stern_Shutter_Starboard_02', 'Axial_Stern_FrontCap', 'Axial_Keel_Shutter_Port_01', 'PDC_Port_Arm_0', 'PDC_Starboard_Arm_3', 'PDC_Port_Gimbal', 'PDC_Starboard_Gimbal', 'Defense_08_Elevation', 'SternHangarDoor']) assert.ok(names.has(name), `Required part ${name}`)
assert.deepEqual(asset.nodes.find(n => n.name === 'Axial_Bow_SourceReceiver').extras.receiverShiftModel.map(x => +x.toFixed(2)), [0, 3.45, 0.55], 'Only the source bow receiver moves rigidly to the turret edge')
assert.ok(!('rearShoulderLiftModel' in asset.nodes.find(n => n.name === 'Axial_Bow_SourceReceiver').extras), 'Source bow receiver geometry must remain undeformed')
assert.ok(![...names].some(name => name.startsWith('Axial_Bow_SeamFairing')), 'Reject the unrequested added bow shoulder geometry')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'main-hatch' && n.extras?.staticJoint).length, 10, 'Five articulated main armor plates per battery')
const vector = value => Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)
for (const plate of asset.nodes.filter(n => n.extras?.system === 'main-hatch')) {
  assert.ok(vector(plate.extras.slideVector), `${plate.name} has a static displacement vector`)
  assert.ok(plate.extras.closedOutlineXY.length >= 6, `${plate.name} uses a polygonal hull contour`)
  if (plate.extras.armorRole === 'aft') {
    assert.ok(vector(plate.extras.hingeAxis) && new THREE.Vector3(...plate.extras.hingeAxis).length() > .99, `${plate.name} has a fixed sloped hinge axis`)
    assert.equal(Math.abs(plate.extras.openingAngleDegrees), 130, `${plate.name} opens 130 degrees`)
    assert.deepEqual(plate.extras.slideVector, [0, 0, 0], `${plate.name} must hinge rather than slide`)
    assert.ok(Array.isArray(plate.extras.hingeEdge) && plate.extras.hingeEdge.length === 2 && plate.extras.hingeEdge.every(vector), `${plate.name} identifies both fixed hinge endpoints`)
    assert.equal(plate.extras.hullFacesRemoved, 0, `${plate.name} preserves the fixed hull`)
  } else {
    assert.equal(plate.extras.hingeAxis, undefined, `${plate.name} must translate without hinging`)
    if (plate.extras.armorRole === 'side') {
      assert.ok(vector(plate.extras.guideExit) && vector(plate.extras.guidePocket), `${plate.name} retains its static guide metadata`)
      assert.ok(vector(plate.extras.clearanceLift), `${plate.name} has a finite three-axis serration-clearance lift`)
    } else assert.ok(vector(plate.extras.liftVector) && plate.extras.sourceObject, `${plate.name} has an independent short fore-end cap`)
  }
}
assert.equal(asset.nodes.filter(n => n.extras?.barrelJoint && n.extras?.staticJoint).length, 66, 'All eleven single-battery shutter pairs remain')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'single-front-cap').length, 7)
for (const station of ['Bow', 'Stern', 'Keel']) {
  const prefix = `Axial_${station}`
  const leaves = asset.nodes.filter(n => n.extras?.barrelJoint === `${prefix}_Barrel`)
  assert.equal(leaves.length, 6, `${station} has six folding plates`)
  assert.equal(asset.nodes.filter(n => n.extras?.barrel === `${prefix}_Barrel` && n.extras?.system === 'single-front-cap').length, 1, `${station} has one front plate`)
  for (const leaf of leaves) {
    assert.equal(leaf.extras.physicalHinge, true, `${leaf.name} hinges on the shell edge`)
    assert.ok(leaf.extras.armorTemplate?.startsWith('SideBattery_1_Starboard_Shutter_Port_'), `${leaf.name} derives from the accepted flank armor`)
    assert.ok(leaf.children?.some(i => asset.nodes[i].mesh !== undefined), `${leaf.name} contains fitted flank geometry`)
  }
}
for (const node of asset.nodes.filter(n => n.name.startsWith('Axial_Keel_') &&
  (n.name.includes('_Shutter_') || n.name.includes('_FrontCap')) && n.mesh !== undefined)) {
  const materials = asset.meshes[node.mesh].primitives.map(p => asset.materials[p.material].name)
  assert.ok(materials.some(name => ['Odin_Bay_Primer', 'Odin_Turret_Interior_DeepRed'].includes(name)),
    `${node.name} has a red inward surface`)
  assert.ok(materials.includes('Odin_Paint_Light'), `${node.name} retains its gray exterior`)
}
assert.equal(asset.nodes.filter(n => n.extras?.system === 'side-front-slider').length, 8)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'side-battery-carriage').length, 4)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'side-battery-leaf').length, 24)
assert.equal(asset.nodes.filter(n => n.extras?.system === 'pdc-hull-petal').length, 8)
assert.equal(asset.nodes.filter(n => n.extras?.singleBattery).length, 11)
if (['0.11.25', '0.11.26', '0.11.27', '0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) for (const i of [2, 4]) for (const side of ['Port', 'Starboard']) {
  const prefix = `SideBattery_${i}_${side}`
  const carriage = asset.nodes.find(n => n.name === prefix + '_SourceCarriage')
  const gun = asset.nodes.find(n => n.name === prefix)
  assert.equal(carriage.extras.system, 'single-source-carriage')
  assert.ok(carriage.children.includes(asset.nodes.indexOf(gun)))
  assert.equal(gun.extras.userRequestedRestAdjustment, true)
  assert.equal(gun.extras.sourceEulerMotion, true)
  if (['0.11.26', '0.11.27', '0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) && i === 4) {
    const mesh = asset.nodes[gun.children.find(index => asset.nodes[index].mesh !== undefined)]
    assert.ok(asset.meshes[mesh.mesh].primitives.some(p => asset.materials[p.material].name === 'Odin_Paint_Light'),
      `${gun.name} includes its original gray elevation linkage in the moving barrel assembly`)
  }
  const leaves = asset.nodes.filter(n => n.extras?.barrelJoint === prefix)
  assert.equal(leaves.length, 6)
  for (const leaf of leaves) {
    assert.equal(leaf.extras.originalSourceArmor, true)
    assert.equal(leaf.extras.sourceObject, 'holo.001')
    assert.ok(leaf.extras.sourceIslandIds.length > 1)
    assert.equal(carriage.children.includes(asset.nodes.indexOf(leaf)), leaf.extras.panelIndex === 0)
    assert.ok(!leaf.extras.sourceFlankTemplate)
    const mesh = asset.nodes[leaf.children.find(index => asset.nodes[index].mesh !== undefined)]
    const materials = asset.meshes[mesh.mesh].primitives.map(p => asset.materials[p.material].name)
    assert.ok(materials.includes('Odin_Turret_Interior_DeepRed'), `${leaf.name} retains red inward details`)
    assert.ok(materials.includes('Odin_Paint_Light'), `${leaf.name} retains its gray original exterior`)
    if (['0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) {
      assert.equal(leaf.extras.alignedSeamHinge, true)
      assert.deepEqual(leaf.extras.hingeSeamLocal, [leaf.name.includes('_Shutter_Port_') ? -2.88 : 2.88, 1.7756, -.007])
      assert.equal(mesh.extras.liningPartitionedAtSeams, true)
    }
    if (['0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) && leaf.extras.panelIndex === 0) {
      assert.equal(mesh.extras.sourceRootScarf, true, `${leaf.name} follows the original turret-root bevels`)
      assert.equal(leaf.extras.rearScarfClearance, .055)
      assert.equal(leaf.extras.rearScarfPlanesLocal.length, 2)
      assert.ok(leaf.extras.rearScarfPlanesLocal.every(vector))
      assert.ok(leaf.extras.rearScarfPlanesLocal[0][1] < -.65)
      assert.ok(leaf.extras.rearScarfPlanesLocal[1][1] > .30)
    }
    if (['0.11.26', '0.11.27', '0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) {
      assert.equal(leaf.extras.limitedSourceOpening, true)
      assert.equal(leaf.extras.openingLimitReferenceProgress, i === 2 ? .20 : .18)
      assert.ok(leaf.extras.openingTravelDegrees < (i === 2 ? 130 : 88))
      assert.equal(leaf.extras.crownHalfWidth, ['0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) ? .30 : .45)
      assert.equal(leaf.extras.centerSeamHalfWidth, .02)
      assert.equal(mesh.extras.fittedFlatCrown, true)
      if (['0.11.27', '0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) && leaf.extras.panelIndex > 0)
        assert.equal(mesh.extras.closedSeamReturn, true, `${leaf.name} carries its gray inner seam return`)
      if (['0.11.27', '0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) && leaf.name.includes('_Shutter_Port_'))
        assert.equal(mesh.extras.closedCenterReturn, true, `${leaf.name} hides the narrow flat-roof center seam`)
    }
  }
  const cap = asset.nodes.find(n => n.name === prefix + '_FrontCap')
  assert.equal(cap.extras.originalSourceArmor, true)
  if (['0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) assert.equal(cap.extras.holdRaisedAfterAdvance, true)
  assert.deepEqual(cap.extras.sourceClearanceOffsetModel, [0, 0, 0])
  assert.ok(!asset.nodes.some(n => n.name.startsWith(prefix) && /OuterSkin|FlankReinforcement|SealingReturns/.test(n.name)))
  if (['0.11.26', '0.11.27', '0.11.28', '0.11.29', '0.11.30', '0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) assert.equal(cap.extras.fittedFlatCrown, true)
}
if (manifest.version === '0.11.24') for (const i of [2, 4]) for (const side of ['Port', 'Starboard']) {
  const prefix = `SideBattery_${i}_${side}`
  const gun = asset.nodes.find(n => n.name === prefix)?.extras
  assert.equal(gun?.sourceEulerMotion, true, `${model}: ${prefix} keeps all original Euler channels`)
  assert.equal(gun.stowSink, 0, `${model}: no handmade barrel offset`)
  const cap = asset.nodes.find(n => n.name === prefix + '_FrontCap')?.extras
  assert.equal(cap?.sourceRigidCap, true)
  assert.equal(cap.sourceCapStroke, true)
  const leaves = asset.nodes.filter(n => n.extras?.barrelJoint === prefix)
  assert.equal(leaves.length, 6)
  for (const leaf of leaves) {
    assert.equal(leaf.extras.fixedHullFacesRemoved, 0, `${model}: fixed hull cannot be taken into ${leaf.name}`)
    assert.equal(leaf.extras.sourceFlankTemplate, true)
    assert.ok(leaf.extras.armorTemplate.startsWith('SideBattery_1_Starboard_Shutter_'))
  }
}
assert.equal(asset.nodes.filter(n => n.extras?.system === 'defense-gate').length, 4)
for (const side of ['Port', 'Starboard']) assert.equal(asset.nodes.find(n => n.name === `PDC_${side}_Gimbal`).extras.fixedRootArmorPieces, 4)
if (['0.11.31', '0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) for (const side of ['Port', 'Starboard']) {
  const carriage = asset.nodes.find(n => n.name === `PDC_${side}_Carriage`)
  assert.equal(carriage.extras.sourceQuadCarriage, true)
  assert.equal(carriage.extras.sourceClosedFrame, 30)
  assert.equal(carriage.extras.sourceDeployedFrame, 45)
  assert.ok(names.has(`PDC_${side}_OriginalSupport`))
  assert.equal(asset.nodes.find(n => n.name === `PDC_${side}_Gimbal`).extras.sourceQuadAim, true)
  for (let i = 0; i < 4; i++) {
    const tube = asset.nodes.find(n => n.name === `PDC_${side}_Arm_${i}`)
    const cradle = asset.nodes.find(n => n.name === `PDC_${side}_Cradle_${i}`)
    const petal = asset.nodes.find(n => n.name === `PDC_${side}_HullPetal_${i}`)
    assert.equal(tube.extras.sourceFullTube, true)
    assert.ok(Math.abs(tube.extras.stowTravel - (['0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) ? 14.40237037037037 : 32)) < 1e-8)
    assert.ok(cradle.children.includes(asset.nodes.indexOf(tube)))
    if (['0.11.32', '0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) {
      assert.equal(petal.extras.sourceCenteredPetal, true)
      assert.equal(petal.extras.compactVector[0], 0, 'No axial petal retreat')
      assert.equal(petal.extras.clearanceVector, undefined, 'No release detour')
      assert.equal(tube.extras.stowReferenceProgress, .11)
      if (['0.11.33', '0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) {
        assert.equal(petal.extras.translationOnly, true)
        assert.equal(petal.extras.lockedHullAxis, 'X')
        assert.equal(petal.extras.petalPackingExponent, 2)
        assert.equal(petal.extras.compactVector[1], 0, 'Petal path is entirely vertical in the ship cross-section')
        if (['0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version)) {
          assert.equal(petal.extras.monotonicPetalStroke, true)
          assert.equal(petal.extras.openEndpointHoldStart, .18)
          for (const key of ['translationClearanceZ', 'translationClearanceReleaseStart', 'translationClearanceReleaseEnd'])
            assert.equal(petal.extras[key], undefined, 'The held open endpoint has no later descent')
        } else assert.equal(Math.abs(petal.extras.translationClearanceZ), .25)
        for (const key of ['compactRotationWXYZ', 'alignStart', 'alignEnd']) assert.equal(petal.extras[key], undefined)
      } else {
        assert.equal(petal.extras.alignStart, .20)
        assert.equal(petal.extras.alignEnd, .40)
      }
      const guide = asset.nodes.find(n => n.name === `PDC_${side}_CradleGuide_${i}`)
      assert.ok(cradle.children.includes(asset.nodes.indexOf(guide)), 'Gray support retains its separate sliding guide')
      assert.equal(guide.extras.compactVector[0], 0)
      assert.equal(guide.extras.compactLead, 2.5)
      assert.equal(petal.extras.compactLead, cradle.extras.compactLead)
    } else assert.deepEqual(petal.extras.compactVector.slice(1), cradle.extras.compactVector.slice(1))
    assert.equal(petal.extras.compactStart, cradle.extras.compactStart)
    assert.equal(petal.extras.compactEnd, cradle.extras.compactEnd)
    const skin = asset.nodes[petal.children.find(index => asset.nodes[index].mesh !== undefined)]
    const skinMaterials = ['0.11.34', '0.11.35', '0.11.36', '0.11.37'].includes(manifest.version) ? ['Odin_Bridge_Armor'] : ['Odin_Paint_Light', 'Odin_Paint_Dark.001']
    assert.ok(asset.meshes[skin.mesh].primitives.every(p => skinMaterials.includes(asset.materials[p.material].name)),
      `${petal.name} uses the adjoining hull material`)
  }
  assert.ok(!asset.nodes.some(n => n.name.startsWith(`PDC_${side}_FixedGuide_`)))
}
const tubes = asset.nodes.filter(n => n.extras?.system === 'main-telescope' && n.extras?.staticJoint)
if (manifest.version === '0.11.35') for (const i of [5, 6, 7, 8]) {
  const gate = asset.nodes.find(n => n.name === `Defense_${String(i).padStart(2, '0')}_NotchGate`)
  const skin = asset.nodes[gate.children.find(index => asset.nodes[index].mesh !== undefined)]
  assert.equal(skin.extras.matchedHullRim, true)
  assert.ok(skin.extras.matchedHullThickness > .50 && skin.extras.matchedHullThickness < .56)
  assert.equal(skin.extras.hullFitSource, 'odin.blend / holo.001')
  assert.equal(skin.extras.hullFitPlaneModel.length, 4)
  assert.equal(skin.extras.hullFitEdgeClearance, .012)
  assert.ok(skin.extras.hullFitNormalClearance > .009 && skin.extras.hullFitNormalClearance < .035)
}
const carriages = asset.nodes.filter(n => n.extras?.system === 'main-bore-carriage' && n.extras?.staticJoint)
if (['0.11.36', '0.11.37'].includes(manifest.version)) for (const i of [5, 6, 7, 8]) {
  const gate = asset.nodes.find(n => n.name === `Defense_${String(i).padStart(2, '0')}_NotchGate`)
  const skin = asset.nodes[gate.children.find(index => asset.nodes[index].mesh !== undefined)]
  assert.equal(skin.extras.matchedHullSection, true)
  assert.equal(skin.extras.hullFitEndClearance, .008)
  assert.equal(skin.extras.receiverGridColumns, 56)
  assert.equal(skin.extras.receiverFloorSourceVertices.length, 56)
  assert.equal(skin.extras.receiverInnerFloorSourceVertices.length, 56)
  assert.ok(skin.extras.receiverForeSourceVertices.length >= 4)
  assert.ok(skin.extras.receiverAftSourceVertices.length >= 3)
  assert.equal(skin.extras.matchedHullThickness, undefined, 'Tapered source returns must not become a uniform normal extrusion')
  if (manifest.version === '0.11.37') {
    assert.equal(skin.extras.matchedFullHullThickness, true)
    assert.equal(skin.extras.receiverShellLayers, 4, 'All original shell layers must be represented')
    assert.ok(skin.extras.receiverInnerForeSourceVertices.length >= 2)
    assert.ok(skin.extras.receiverInnerAftSourceVertices.length >= 2)
    assert.ok(skin.extras.receiverRoofForeSourceVertices.length >= 3)
    assert.ok(skin.extras.receiverRoofAftSourceVertices.length >= 3)
    assert.equal(skin.extras.hullFitSource, 'odin.blend / holo.001 / all four shell boundary layers')
  }
}
assert.equal(carriages.length, 6, 'Three independently positioned complete bore carriages per battery')
for (const bank of ['Dorsal', 'Ventral']) for (const role of ['Port', 'Center', 'Starboard']) {
  const name = `Main_${bank}_Carrier_${role}`
  const carriage = carriages.find(n => n.name === name)
  assert.ok(carriage && vector(carriage.extras.stowOffset), `${name} has a measured stow displacement`)
  const coverRole = bank === 'Ventral' && role !== 'Center' ? (role === 'Port' ? 'Starboard' : 'Port') : role
  assert.equal(carriage.extras.followShroud, `Main_${bank}_Shroud_${coverRole}`, `${name} follows its physically corresponding cover`)
  assert.ok(carriage.children?.some(index => asset.nodes[index].mesh !== undefined), `${name} carries the original breech and collar geometry`)
  assert.ok(carriage.children?.some(index => asset.nodes[index].name === `Main_${bank}_Tube_${role}`), `${name} carries its telescopic bore`)
}
assert.equal(tubes.length, 6, 'All three tubes telescope on both main batteries')
for (const tube of tubes) {
  assert.ok(vector(tube.extras.boreAxis) && new THREE.Vector3(...tube.extras.boreAxis).length() > .99, `${tube.name} has a measured bore axis`)
  assert.ok(vector(tube.extras.deployedOffset), `${tube.name} preserves its deployed endpoint`)
  assert.equal(tube.extras.stowTravel, 20, `${tube.name} has the shared telescope stroke with hull-lip clearance`)
  assert.ok(tube.children?.some(index => asset.nodes[index].mesh !== undefined), `${tube.name} carries actual barrel geometry`)
}
const stern = asset.nodes.find(n => n.name === 'SternHangarDoor')
assert.ok(stern.children.some(index => asset.nodes[index].mesh !== undefined), 'Aft door contains actual visible geometry')
assert.equal(asset.nodes.filter(n => n.extras?.system === 'bridge-armor' || n.name.startsWith('BridgeArmor_')).length, 0, 'Bridge armor removed; fixed windows retained')
assert.equal(asset.nodes.filter(n => /^SideBattery_\d_(Port|Starboard)$/.test(n.name)).length, 8, 'Eight independently mirrored secondary batteries')
assert.ok(asset.materials.some(m => m.normalTexture), 'Source tangent normals preserved')
// Named empties alone are insufficient: they used to exist but all had origin (0,0,0).
const nodes = asset.nodes.map(n => {
  const object = new THREE.Object3D()
  if (n.matrix) new THREE.Matrix4().fromArray(n.matrix).decompose(object.position, object.quaternion, object.scale)
  if (n.translation) object.position.fromArray(n.translation)
  if (n.rotation) object.quaternion.fromArray(n.rotation)
  if (n.scale) object.scale.fromArray(n.scale)
  return object
})
asset.nodes.forEach((n, i) => n.children?.forEach(c => nodes[i].add(nodes[c])))
for (let i = 0; i < 13; i++) {
  const name = `EngineCore_${String(i).padStart(2, '0')}`
  const index = asset.nodes.findIndex(n => n.name === name)
  assert.ok(index >= 0, `Engine ${i}`)
  const expected = new THREE.Vector3().fromArray(manifest.engineAnchors[i].position)
  const actual = nodes[index].getWorldPosition(new THREE.Vector3())
  assert.ok(actual.distanceTo(expected) < .001, `${name} must coincide with its nozzle, got ${actual.toArray()}`)
}
assert.ok(asset.images?.length > 0 && asset.images.every(i => i.bufferView !== undefined), 'Textures embedded for portable loading')
assert.ok(asset.materials?.length > 0, 'PBR materials present')
const paintIndex = asset.materials.findIndex(m => m.name === 'Odin_Antenna_Painted_Wrap')
assert.ok(paintIndex >= 0, 'Antenna paint material is present')
const paintTexture = asset.materials[paintIndex].pbrMetallicRoughness.baseColorTexture
assert.ok(paintTexture, 'The antenna band is an embedded texture')
const paintedPrimitives = asset.meshes.flatMap(m => m.primitives).filter(p => p.material === paintIndex)
assert.ok(paintedPrimitives.length > 0 && paintedPrimitives.every(p => p.attributes[`TEXCOORD_${paintTexture.texCoord || 0}`] !== undefined), 'The batched antennas retain the UV channel used by their wraparound band')
assert.ok(file.length < 25 * 1024 * 1024, 'Desktop asset fits the static host 25 MiB per-file budget')
console.log(JSON.stringify({ model, valid: true, sizeMB: +(file.length / 1024 / 1024).toFixed(2), meshes: asset.meshes.length, materials: asset.materials.length, embeddedTextures: asset.images.length, animationClips: 0 }, null, 2))
}
