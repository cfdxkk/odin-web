import * as THREE from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { OdinGTAOPass } from './odin-ao.ts'

// A bounded supersampled image keeps ultrawide displays within GPU limits.
export function photoDimensions(width: number, height: number, maxTextureSize = 8192) {
  const scale = Math.min(2, 5760 / Math.max(width, 1), 4320 / Math.max(height, 1), maxTextureSize / Math.max(width, height, 1), Math.sqrt(20_000_000 / Math.max(width * height, 1)))
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) }
}

export async function captureOdinPhoto(scene: THREE.Scene, camera: THREE.PerspectiveCamera, width: number, height: number, lightSurfaces: Iterable<THREE.Object3D>): Promise<Blob> {
  const output = document.createElement('canvas')
  const renderer = new THREE.WebGLRenderer({ canvas: output, alpha: true, antialias: true, premultipliedAlpha: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' })
  const size = photoDimensions(width, height, renderer.capabilities.maxTextureSize)
  renderer.setPixelRatio(1); renderer.setSize(size.width, size.height, false)
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap
  // Camera, scene transforms and all live render targets remain untouched.
  const photoCamera = camera.clone()
  photoCamera.updateMatrixWorld(true)
  const target = new THREE.WebGLRenderTarget(size.width, size.height, { type: THREE.HalfFloatType, samples: Math.min(4, renderer.capabilities.maxSamples) })
  const composer = new EffectComposer(renderer, target)
  composer.setPixelRatio(1); composer.setSize(size.width, size.height)
  const renderPass = new RenderPass(scene, photoCamera)
  renderPass.clearAlpha = 0
  composer.addPass(renderPass)
  const ao = new OdinGTAOPass(scene, photoCamera, size.width, size.height)
  ao.updateGtaoMaterial({ radius: .065, distanceExponent: 1, thickness: .10, scale: .8, samples: 16 }); ao.blendIntensity = .35
  for (const surface of lightSurfaces) ao.excludedObjects.add(surface)
  composer.addPass(ao)
  const outputPass = new OutputPass(); composer.addPass(outputPass)
  // PMREM textures are GPU render targets and cannot be shared across WebGL
  // contexts. Recreate the same environment for this one-off renderer.
  const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment()
  const photoEnvironment = pmrem.fromScene(room, .15)
  room.dispose(); pmrem.dispose()
  const background = scene.background, environment = scene.environment
  try {
    // Render synchronously before yielding. No animation frame can observe
    // the temporary transparent background; the UI/overlay are another canvas.
    scene.background = null
    scene.environment = photoEnvironment.texture
    try { composer.render(0) } finally { scene.background = background; scene.environment = environment }
    return await new Promise<Blob>((resolve, reject) => output.toBlob(blob => blob ? resolve(blob) : reject(new Error('Unable to encode the PNG image.')), 'image/png'))
  } finally {
    scene.background = background
    scene.environment = environment
    photoEnvironment.dispose(); ao.dispose(); outputPass.dispose(); composer.dispose(); renderer.dispose(); renderer.forceContextLoss()
  }
}
