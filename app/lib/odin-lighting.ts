import * as THREE from 'three'

// A warm-neutral studio rig for the light equipment panel. Broad fills keep
// the underside legible without changing the model's original paint colors.
export const ODIN_DISPLAY_BACKGROUND = '#d9dcd5'
export const ODIN_ENVIRONMENT_INTENSITY = .58
export function addOdinDisplayLighting(scene: THREE.Scene, shadows = false) {
  scene.add(new THREE.HemisphereLight(0xf2f0e7, 0x9a958b, 1.15))
  const key = new THREE.DirectionalLight(0xfff7e8, 1.85)
  key.position.set(4, 7, -4)
  key.castShadow = shadows
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: .5, far: 25 })
  key.shadow.bias = -.00008
  key.shadow.normalBias = .003
  scene.add(key)
  const fill = new THREE.DirectionalLight(0xe9edeb, .9)
  fill.position.set(-5, 2, 1)
  scene.add(fill)
  const lower = new THREE.DirectionalLight(0xe6dfd0, .75)
  lower.position.set(3, -2, 4)
  scene.add(lower)
  const bow = new THREE.DirectionalLight(0xf3eee1, .35)
  bow.position.set(-1, 1, -8)
  scene.add(bow)
}
