import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import * as THREE from 'three'
import { createOdinRig } from '../app/lib/odin-rig.ts'
import { facingWeaponSide, weaponAnchorNames } from '../app/lib/odin-weapon-anchors.ts'
import { classifyWeaponJoint } from '../app/lib/odin-weapon-groups.ts'
import { WEAPON_TOUR, focusedWeaponLevels, sampleWeaponCamera } from '../app/lib/odin-weapon-tour.ts'

// Use the shipped hierarchy and mesh accessor bounds. A joint's local X is
// insufficient: Defense_03 has negative local X but positive world X.
function load(asset) {
  const bytes = readFileSync(new URL(`../public/models/${asset}`, import.meta.url))
  const model = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const nodes = model.nodes.map(node => {
    const object = new THREE.Object3D()
    object.name = node.name; object.userData = { ...node.extras }
    if (node.matrix) new THREE.Matrix4().fromArray(node.matrix).decompose(object.position, object.quaternion, object.scale)
    if (node.translation) object.position.fromArray(node.translation)
    if (node.rotation) object.quaternion.fromArray(node.rotation)
    if (node.scale) object.scale.fromArray(node.scale)
    if (node.mesh !== undefined) {
      const bounds = model.accessors[model.meshes[node.mesh].primitives[0].attributes.POSITION]
      object.userData.meshCenter = new THREE.Vector3().fromArray(bounds.min)
        .add(new THREE.Vector3().fromArray(bounds.max)).multiplyScalar(.5)
    }
    return object
  })
  model.nodes.forEach((node, index) => node.children?.forEach(child => nodes[index].add(nodes[child])))
  const root = new THREE.Group()
  model.scenes[model.scene || 0].nodes.forEach(index => root.add(nodes[index]))
  return { root, rig: createOdinRig(root) }
}

function anchorCenter(root, name) {
  const joint = root.getObjectByName(name)
  assert.ok(joint?.userData.staticJoint, `${name} must be an actual articulated joint`)
  let mesh
  joint.traverse(child => { if (!mesh && child.userData.meshCenter) mesh = child })
  assert.ok(mesh, `${name} must contain the rendered geometry used by its callout`)
  return mesh.localToWorld(mesh.userData.meshCenter.clone())
}

test('centered dorsal cameras retain the last flank instead of oscillating between mounts', () => {
  for (const previous of [-1, 1]) {
    for (const x of [0, -0, -1e-8, 1e-8, -.009, .009]) assert.equal(facingWeaponSide(x, previous), previous)
    assert.equal(facingWeaponSide(-.01, previous), -1)
    assert.equal(facingWeaponSide(.01, previous), 1)
    assert.equal(facingWeaponSide(-3, previous), -1)
    assert.equal(facingWeaponSide(3, previous), 1)
  }
})

test('centerline weapons keep their existing static or dual dorsal/ventral anchors', () => {
  for (const side of [-1, 1]) {
    assert.deepEqual(weaponAnchorNames(WEAPON_TOUR[0], side), [])
    assert.deepEqual(weaponAnchorNames(WEAPON_TOUR[1], side), ['Main_Dorsal_Shroud_Center', 'Main_Ventral_Shroud_Center'])
    assert.deepEqual(weaponAnchorNames(WEAPON_TOUR[2], side), [])
  }
})

for (const asset of ['odin.glb', 'odin-lite.glb']) {
  test(`${asset}: side callouts select real, visible-side mechanisms through the complete deployment`, () => {
    const { root, rig } = load(asset)
    for (const step of [3, 4]) for (const deployment of [0, .5, 1]) {
      const shot = WEAPON_TOUR[step]
      const levels = Object.fromEntries(Object.entries(focusedWeaponLevels(step)).map(([group, active]) => [group, active * deployment]))
      rig.applySelective(levels, 0)
      root.updateMatrixWorld(true)
      for (const entrySide of [-1, 1]) for (const aspect of [390 / 844, 4 / 3, 16 / 9, 21 / 9, 32 / 9]) {
        const pose = sampleWeaponCamera(step, aspect, entrySide)
        // Include the real centered tour pose and both off-center camera
        // positions. A centered camera retains its approach side; moving to
        // either flank must override that history immediately.
        for (const cameraX of [pose.position.x, -2, 2]) {
          const side = facingWeaponSide(cameraX, entrySide)
          assert.equal(side, Math.abs(cameraX) < .01 ? entrySide : Math.sign(cameraX))
          const names = weaponAnchorNames(shot, side)
          const oppositeNames = weaponAnchorNames(shot, -side)
          const groups = names.map(classifyWeaponJoint)
          assert.deepEqual(groups, step === 3 ? ['single'] : ['defense', 'quad'], 'The merged chapter must identify both a twin and a quad mount')
          const camera = new THREE.PerspectiveCamera(33, aspect, .035, 500)
          camera.position.copy(pose.position); camera.position.x = cameraX
          camera.up.copy(pose.up); camera.lookAt(pose.target)
          if (aspect > 1) camera.setViewOffset(1000 * aspect, 1000, -135 * aspect, 0, 1000 * aspect, 1000)
          camera.updateMatrixWorld(true)
          names.forEach((name, index) => {
            const center = anchorCenter(root, name), other = anchorCenter(root, oppositeNames[index])
            assert.equal(Math.sign(center.x), side, `${name} points to the far side of the hull`)
            if (Math.abs(cameraX) >= .01) assert.ok(center.distanceToSquared(camera.position) < other.distanceToSquared(camera.position), `${name} must be closer than its mirrored counterpart`)
            const projected = center.clone().project(camera)
            assert.ok(Math.abs(projected.x) < 1 && Math.abs(projected.y) < 1 && projected.z > -1 && projected.z < 1,
              `${name} leaves the visible frame at ${aspect}, deployment ${deployment}`)
          })
        }
      }
    }
  })
}
