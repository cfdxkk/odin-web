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

test('main covers clear before barrels lift, and PDC carriage clears before arms unfold', () => {
  const { root, rig } = loadRig()
  rig.apply(0, 0)
  const barrel = root.getObjectByName('Main_Dorsal_Barrels')
  const initial = barrel.position.clone()
  for (let d = 0; d <= 1; d += .01) {
    const state = rig.apply(d, 0)
    // Below 0.28 the plates still travel; first small cradle travel remains inside the bay.
    if (state.covers < .999) assert.ok(barrel.position.distanceTo(initial) < 1, `barrel clearance ${d}`)
    if (state.pdcArms > .05) assert.ok(Math.abs(root.getObjectByName('PDC_Starboard_Carriage').position.x - 12.263671875) > 19)
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
