import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { OdinGTAOPass } from '../app/lib/odin-ao.ts'

function setup() {
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera()
  const hull = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial())
  const plume = new THREE.Mesh(new THREE.ConeGeometry(), new THREE.ShaderMaterial({ transparent: true }))
  const glow = new THREE.Sprite(), unlitGlow = new THREE.Sprite()
  unlitGlow.visible = false
  scene.add(hull, plume, glow, unlitGlow)
  const pass = new OdinGTAOPass(scene, camera, 8, 8)
  for (const effect of [plume, glow, unlitGlow]) pass.excludedObjects.add(effect)
  const buffer = new THREE.WebGLRenderTarget(8, 8)
  return { pass, buffer, hull, plume, glow, unlitGlow }
}

test('engine light does not enter AO depth/normal rendering; physical hull still does', () => {
  const { pass, buffer, hull, plume, glow, unlitGlow } = setup()
  let normalPasses = 0
  pass._renderOverride = () => {
    normalPasses++
    assert.equal(hull.visible, true)
    assert.equal(plume.visible, false)
    assert.equal(glow.visible, false)
    assert.equal(unlitGlow.visible, false)
  }
  pass._renderPass = () => {}
  try {
    pass.render({}, buffer, buffer, 0, false)
    assert.equal(normalPasses, 1)
    assert.equal(plume.visible, true)
    assert.equal(glow.visible, true)
    assert.equal(unlitGlow.visible, false)
    assert.equal(hull.visible, true)
  } finally { pass.dispose(); buffer.dispose() }
})

test('AO restores the exhaust visibility even when the renderer fails', () => {
  const { pass, buffer, plume, glow, unlitGlow } = setup()
  pass._renderOverride = () => { throw new Error('render failure') }
  try {
    assert.throws(() => pass.render({}, buffer, buffer, 0, false), /render failure/)
    assert.equal(plume.visible, true)
    assert.equal(glow.visible, true)
    assert.equal(unlitGlow.visible, false)
  } finally { pass.dispose(); buffer.dispose() }
})
