// Build-time illustration: the actual Odin GLB and a procedural mountain valley.
// No geometry is edited or guessed. This renderer is never loaded by the site.
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { createOdinRig } from '../app/lib/odin-rig'

const width = 3840, height = 1600
const canvas = document.createElement('canvas')
document.body.append(canvas)
canvas.style.cssText = 'display:block;width:100%;height:auto'
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true })
renderer.setSize(width, height, false)
renderer.outputColorSpace = THREE.SRGBColorSpace
renderer.toneMapping = THREE.ACESFilmicToneMapping
renderer.toneMappingExposure = 1.05
renderer.shadowMap.enabled = true
renderer.shadowMap.type = THREE.PCFSoftShadowMap
const scene = new THREE.Scene()
scene.background = new THREE.Color('#080b0e')
scene.fog = new THREE.Fog('#879189', 25, 82)
const camera = new THREE.OrthographicCamera(-14, 14, 14 / (width / height), -14 / (width / height), .1, 100)
camera.position.set(0, 13, 35)
camera.lookAt(0, 5, -5)
scene.add(new THREE.HemisphereLight(0xdedfd9, 0x161a1c, .8))
const pmrem = new THREE.PMREMGenerator(renderer)
const studio = new RoomEnvironment()
const environment = pmrem.fromScene(studio, .2)
scene.environment = environment.texture
scene.environmentIntensity = .6
studio.dispose(); pmrem.dispose()
const key = new THREE.DirectionalLight(0xfffaf0, 3.1)
key.position.set(-10, 18, 7)
key.castShadow = true
key.shadow.mapSize.set(4096, 4096)
Object.assign(key.shadow.camera, { left: -24, right: 24, top: 24, bottom: -24, near: .5, far: 70 })
key.shadow.normalBias = .015
scene.add(key)
const fill = new THREE.DirectionalLight(0xd1dae3, .55)
fill.position.set(10, 5, -12)
scene.add(fill)

const fract = (n: number) => n - Math.floor(n)
const hash = (x: number, z: number) => fract(Math.sin(x * 127.1 + z * 311.7) * 43758.5453)
function noise(x: number, z: number) {
  const a = Math.floor(x), b = Math.floor(z), u = x - a, v = z - b
  const sx = u * u * (3 - 2 * u), sz = v * v * (3 - 2 * v)
  return THREE.MathUtils.lerp(THREE.MathUtils.lerp(hash(a, b), hash(a + 1, b), sx), THREE.MathUtils.lerp(hash(a, b + 1), hash(a + 1, b + 1), sx), sz)
}
function terrainHeight(x: number, z: number) {
  const valley = Math.abs(x + 2.3 * Math.sin(z * .115) - 1)
  const shoulder = Math.pow(Math.min(1, valley / 12), 1.25)
  let detail = 0, amplitude = 1.2, frequency = .16
  for (let i = 0; i < 5; i++) { detail += noise(x * frequency + i * 5, z * frequency - i * 3) * amplitude; frequency *= 2.08; amplitude *= .42 }
  const ridges = Math.pow(Math.max(0, Math.sin(z * .24 + x * .12)), 2)
  return -.8 + shoulder * (1.6 + detail * 2.4 + ridges * 1.2) + detail * .35
}
const terrain = new THREE.PlaneGeometry(70, 100, 560, 800)
terrain.rotateX(-Math.PI / 2)
const positions = terrain.attributes.position
const colors = new Float32Array(positions.count * 3)
for (let i = 0; i < positions.count; i++) {
  const x = positions.getX(i), z = positions.getZ(i) - 12
  const y = terrainHeight(x, z)
  positions.setXYZ(i, x, y, z)
  const tone = .008 + noise(x * .7, z * .7) * .012
  colors.set([tone, tone * 1.04, tone * 1.02], i * 3)
}
terrain.setAttribute('color', new THREE.BufferAttribute(colors, 3))
terrain.computeVertexNormals()
const mountainMaterial = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, envMapIntensity: 0 })
mountainMaterial.onBeforeCompile = shader => {
  shader.vertexShader = 'varying vec3 valleyPosition;\n' + shader.vertexShader
  shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvalleyPosition = position;')
  shader.fragmentShader = 'varying vec3 valleyPosition;\n' + shader.fragmentShader
  shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>', `
    float valleyMist = (1.0 - smoothstep(0.3, 3.6, valleyPosition.y)) * (1.0 - smoothstep(4.0, 25.0, valleyPosition.z));
    outgoingLight = mix(outgoingLight, vec3(0.19, 0.22, 0.20), valleyMist * 0.92);
    #include <opaque_fragment>
  `)
}
const mountains = new THREE.Mesh(terrain, mountainMaterial)
mountains.receiveShadow = true; mountains.castShadow = true
scene.add(mountains)

const draco = new DRACOLoader().setDecoderPath('/public/draco/')
const model = await new GLTFLoader().setDRACOLoader(draco).loadAsync('/public/models/odin.glb')
const ship = model.scene
createOdinRig(ship).apply(0, 0)
ship.rotation.y = -1.38
ship.scale.multiplyScalar(1.10)
ship.position.set(1, 3.7, -6)
ship.traverse(object => {
  if (!(object instanceof THREE.Mesh)) return
  object.castShadow = false; object.receiveShadow = true
  for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
    if (!(material instanceof THREE.MeshStandardMaterial)) continue
    // Keep the object legible against the atmospheric valley; distant terrain
    // carries the fog, not the subject of this technical illustration.
    material.fog = false
    if (material.name.startsWith('Odin_Paint_')) { material.metalness = .08; material.roughness = .9; material.normalScale.setScalar(.1) }
    material.emissiveIntensity = 0
  }
})
scene.add(ship)
scene.updateMatrixWorld(true)
renderer.render(scene, camera)
const box = new THREE.Box3().setFromObject(ship)
document.documentElement.dataset.ready = 'true'
document.documentElement.dataset.shipBounds = JSON.stringify({ min: box.min.toArray(), max: box.max.toArray() })
document.documentElement.dataset.model = '/models/odin.glb'
document.documentElement.dataset.animationClips = String(model.animations.length)
draco.dispose()
