import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { createOdinExhaust, updateOdinExhaust } from '../app/lib/odin-exhaust.ts'

test('all exhaust layers are additive open surfaces downstream of a fixed nozzle', () => {
  const effect = createOdinExhaust(.04, .6, 0, new THREE.Texture())
  effect.group.position.set(1, 2, 3)
  for (const power of [0, .002, .1, .5, 1]) for (const time of [0, .7, 2, 7]) {
    updateOdinExhaust(effect, power, time)
    effect.group.updateMatrixWorld(true)
    assert.deepEqual(effect.group.position.toArray(), [1, 2, 3])
    assert.equal(effect.group.visible, power > .001)
    for (const mesh of effect.lightSurfaces.filter(o => o instanceof THREE.Mesh)) {
      assert.equal(mesh.geometry.parameters.openEnded, true)
      assert.equal(mesh.material.depthWrite, false)
      assert.equal(mesh.material.blending, THREE.AdditiveBlending)
      const vertices = mesh.geometry.attributes.position
      for (let i = 0; i < vertices.count; i++) {
        const world = new THREE.Vector3().fromBufferAttribute(vertices, i).applyMatrix4(mesh.matrixWorld)
        assert.ok(world.z >= 3 - 1e-7, 'No plume geometry may extend back through the nozzle')
      }
    }
  }
})

test('power clamps, complete shutdown and a frozen effects clock are deterministic', () => {
  const effect = createOdinExhaust(.03, .4, 8, new THREE.Texture())
  updateOdinExhaust(effect, 2, 10)
  assert.ok(effect.materials.every(m => m.uniforms.power.value === 1))
  const scale = effect.group.scale.y
  updateOdinExhaust(effect, 1, 10)
  assert.equal(effect.group.scale.y, scale)
  updateOdinExhaust(effect, -1, 10)
  assert.equal(effect.group.visible, false)
  assert.equal(effect.glow.material.opacity, 0)
  assert.ok(effect.materials.every(m => m.uniforms.power.value === 0))
})
