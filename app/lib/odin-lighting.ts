import * as THREE from 'three'

// Restore the original dark showcase rig and the model's native paint colors.
export const ODIN_DISPLAY_BACKGROUND = '#070b10'
export const ODIN_ENVIRONMENT_INTENSITY = .28
export function addOdinDisplayLighting(scene: THREE.Scene, shadows = false) {
  scene.add(new THREE.HemisphereLight(0xc9d1da, 0x34373c, .34))
  const key = new THREE.DirectionalLight(0xfff3e6, 2.7)
  key.position.set(4, 7, -4)
  key.castShadow = shadows
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: .5, far: 25 })
  key.shadow.bias = -.00008
  key.shadow.normalBias = .003
  scene.add(key)
  const fill = new THREE.DirectionalLight(0xb7c7df, .62)
  fill.position.set(-5, 2, 1)
  scene.add(fill)
  const rim = new THREE.DirectionalLight(0xd4dfe8, .65)
  rim.position.set(3, 4, 6)
  scene.add(rim)
  const lower = new THREE.DirectionalLight(0xd7cbb9, .45)
  lower.position.set(3, -1.3, 4)
  scene.add(lower)
  const bow = new THREE.DirectionalLight(0xc6ced4, .25)
  bow.position.set(-1, 1, -8)
  scene.add(bow)
}
