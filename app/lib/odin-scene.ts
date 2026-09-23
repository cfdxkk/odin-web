import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js'
import { createOdinRig } from './odin-rig'
import { sampleOdinMotion } from './odin-motion'

type State = { playing: boolean; explore: boolean; deployed: boolean; lowPower: boolean }
type Hooks = { progress: (p: number) => void; tick: (t: number) => void; state: () => State }
export type OdinExperience = { seek: (t: number) => void; reset: () => void; setExplore: (b: boolean) => void; resize: () => void; dispose: () => void }
const TAU = Math.PI * 2
const clamp = THREE.MathUtils.clamp
const smooth = (a: number, b: number, t: number) => THREE.MathUtils.smoothstep(t, a, b)

// A continuous 40-second camera orbit. Angles never wrap inside the rail.
// These are authored web camera positions, not imported Blender keyframes.
const rail = [
  { t: 0, a: -.79, r: 11.6, h: 3.9, aim: [0, .24, 0], fov: 33 },
  { t: 8, a: -.1, r: 10.5, h: 2.9, aim: [0, .20, 0], fov: 33 },
  { t: 12, a: .34, r: 8.7, h: 3.9, aim: [0, .30, -.5], fov: 33 },
  { t: 18, a: .75, r: 5.8, h: 3.0, aim: [0, .52, -.6], fov: 35 },
  { t: 23, a: 1.35, r: 6.6, h: .6, aim: [0, .2, .3], fov: 35 },
  { t: 26, a: 2.10, r: 8.8, h: -2.5, aim: [0, -.15, .2], fov: 33 },
  { t: 30.8, a: 2.28, r: 10.8, h: 2.5, aim: [0, .15, .5], fov: 35 },
  { t: 33.8, a: 2.65, r: 11.5, h: 3.0, aim: [0, .24, .5], fov: 35 },
  { t: 37, a: 4.03, r: 11.6, h: 3.5, aim: [0, .24, 0], fov: 33 },
  { t: 40, a: TAU - .79, r: 11.6, h: 3.9, aim: [0, .24, 0], fov: 33 },
]

export async function createOdinExperience(canvas: HTMLCanvasElement, hooks: Hooks): Promise<OdinExperience> {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' })
  const gl = renderer.getContext()
  const debugRenderer = gl.getExtension('WEBGL_debug_renderer_info')
  const gpuName = debugRenderer ? String(gl.getParameter(debugRenderer.UNMASKED_RENDERER_WEBGL)) : ''
  canvas.dataset.renderer = gpuName
  const softwareRenderer = /swiftshader|llvmpipe|software|basic render/i.test(gpuName)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFShadowMap
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#070b12')
  const camera = new THREE.PerspectiveCamera(33, 1, .035, 500)
  const cameraAim = new THREE.Vector3(0, .24, 0)
  const controls = new OrbitControls(camera, canvas)
  controls.enabled = false; controls.enableDamping = true; controls.dampingFactor = .06
  controls.minDistance = 3; controls.maxDistance = 22; controls.enablePan = false
  controls.rotateSpeed = .5; controls.zoomSpeed = .6
  controls.target.copy(cameraAim)

  const pmrem = new THREE.PMREMGenerator(renderer)
  const environmentScene = new RoomEnvironment()
  const environment = pmrem.fromScene(environmentScene, .15)
  scene.environment = environment.texture
  scene.environmentIntensity = .38
  environmentScene.dispose(); pmrem.dispose()
  scene.add(new THREE.HemisphereLight(0xc9d1da, 0x34373c, .45))
  const key = new THREE.DirectionalLight(0xfff3e6, 2.4); key.position.set(4, 7, -4); scene.add(key)
  key.castShadow = true
  key.shadow.mapSize.set(4096, 4096)
  Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: .5, far: 25 })
  key.shadow.bias = -.00008; key.shadow.normalBias = .003
  const rim = new THREE.DirectionalLight(0xb7c7df, .9); rim.position.set(-5, 2, 1); scene.add(rim)
  const fill = new THREE.DirectionalLight(0xd7cbb9, .45); fill.position.set(3, -1.3, 4); scene.add(fill)
  const bow = new THREE.DirectionalLight(0xc6ced4, .25); bow.position.set(-1, 1, -8); scene.add(bow)

  // A deterministic, sparse star field. No network images or video backgrounds.
  let seed = 7729
  const random = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646 }
  const starGeo = new THREE.BufferGeometry()
  const positions: number[] = [], colors: number[] = []
  for (let i = 0; i < 1250; i++) {
    const az = random() * TAU, y = random() * 2 - 1, r = 65 + random() * 100
    const cross = Math.sqrt(1 - y * y)
    positions.push(Math.cos(az) * cross * r, y * r, Math.sin(az) * cross * r)
    const value = .16 + random() * .34
    colors.push(value * .75, value * .87, value)
  }
  starGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  starGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ size: .10, vertexColors: true, transparent: true, opacity: .7, depthWrite: false }))
  scene.add(stars)

  const renderTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: softwareRenderer ? 0 : 4 })
  const composer = new EffectComposer(renderer, renderTarget)
  composer.addPass(new RenderPass(scene, camera))
  const ao = new GTAOPass(scene, camera, 1, 1)
  ao.updateGtaoMaterial({ radius: .065, distanceExponent: 1, thickness: .10, scale: .8, samples: 12 })
  ao.blendIntensity = .48
  composer.addPass(ao)
  // Subtle glow above the hull's working range, rather than blooming its reflections.
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .16, .22, 2.8)
  composer.addPass(bloom)
  const grade = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, time: { value: 0 } },
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader: `uniform sampler2D tDiffuse; uniform float time; varying vec2 vUv;
      void main(){vec3 c=texture2D(tDiffuse,vUv).rgb;
      float halo=exp(-length((vUv-vec2(.61,.54))*vec2(1.1,1.7))*6.);
      c+=vec3(.013,.025,.039)*halo;
      float vig=1.-.28*smoothstep(.25,.78,length(vUv-.5));
      float grain=fract(sin(dot(vUv*900.,vec2(12.9898,78.233))+floor(time*12.))*43758.5453)-.5;
      gl_FragColor=vec4(max(c*vig+grain*.0015,0.),1.);}`,
  })
  composer.addPass(grade); composer.addPass(new OutputPass())

  const draco = new DRACOLoader().setDecoderPath('/draco/').setWorkerLimit(2)
  const loader = new GLTFLoader().setDRACOLoader(draco)
  let gltf
  const modelPath = softwareRenderer || canvas.clientWidth < 700 ? '/models/odin-lite.glb' : '/models/odin.glb'
  canvas.dataset.asset = modelPath
  try {
    gltf = await loader.loadAsync(modelPath, event => hooks.progress(event.total ? Math.min(96, event.loaded / event.total * 96) : 30))
  } catch (error) {
    controls.dispose(); composer.dispose(); environment.dispose(); renderer.dispose(); draco.dispose()
    throw error
  }
  const ship = new THREE.Group(); ship.name = 'Odin_runtime_motion'; ship.add(gltf.scene); scene.add(ship)
  const materials = new Set<THREE.Material>()
  const engineMaterials: THREE.MeshStandardMaterial[] = []
  gltf.scene.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    object.frustumCulled = true
    object.castShadow = true; object.receiveShadow = true
    const list = Array.isArray(object.material) ? object.material : [object.material]
    list.forEach(material => {
      if (materials.has(material)) return
      materials.add(material)
      if (material instanceof THREE.MeshStandardMaterial) {
        material.envMapIntensity = 1
        // The exterior is painted armor; exposed gun/engine alloys remain metallic.
        if (material.name.startsWith('Odin_Paint_')) {
          material.metalness = .18
          material.roughness = 1.4
        }
        if (material.name === 'Odin_Added_Machined_Alloy') material.roughness = .43
        if (material.name.startsWith('Odin_Nav_')) material.emissiveIntensity = 1.2
        if (material.name === 'Odin_Bay_Service_Light' || material.name === 'Odin_Hangar_Amber') material.emissiveIntensity = .65
        for (const map of [material.map, material.normalMap, material.roughnessMap]) if (map) map.anisotropy = renderer.capabilities.getMaxAnisotropy()
        if (material.name === 'Odin_Engine_Emission') {
          material.emissive.setRGB(.12, .44, 1)
          engineMaterials.push(material)
        }
      }
    })
  })
  const find = (name: string) => gltf.scene.getObjectByName(name)
  const rig = createOdinRig(gltf.scene)

  const glowCanvas = document.createElement('canvas'); glowCanvas.width = glowCanvas.height = 128
  const gc = glowCanvas.getContext('2d')!
  const gradient = gc.createRadialGradient(64, 64, 0, 64, 64, 64)
  gradient.addColorStop(0, 'rgba(148,209,255,1)'); gradient.addColorStop(.16, 'rgba(41,117,255,.6)'); gradient.addColorStop(.5, 'rgba(20,63,229,.12)'); gradient.addColorStop(1, 'rgba(0,0,0,0)')
  gc.fillStyle = gradient; gc.fillRect(0, 0, 128, 128)
  const glowTex = new THREE.CanvasTexture(glowCanvas)
  const exhausts: { cone: THREE.Mesh; glow: THREE.Sprite; radius: number; length: number; material: THREE.ShaderMaterial }[] = []
  scene.updateMatrixWorld(true)
  for (let i = 0; i < 13; i++) {
    const engineCore = find(`EngineCore_${String(i).padStart(2, '0')}`)
    if (!engineCore) continue
    const position = engineCore.getWorldPosition(new THREE.Vector3())
    const radius = Number(engineCore.userData.radius || 3) * .01
    const length = radius * (i === 0 ? 20 : 12)
    const shader = new THREE.ShaderMaterial({
      uniforms: { time: { value: 0 }, power: { value: 1 } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      vertexShader: `varying vec2 vUv; varying vec3 vNormal; varying vec3 vView;
        void main(){vUv=uv;vec4 p=modelViewMatrix*vec4(position,1.);vNormal=normalize(normalMatrix*normal);vView=-p.xyz;gl_Position=projectionMatrix*p;}`,
      fragmentShader: `varying vec2 vUv; varying vec3 vNormal; varying vec3 vView; uniform float time; uniform float power;
        void main(){float f=pow(clamp(1.-vUv.y,0.,1.),1.35);float bands=.87+.13*sin(vUv.y*42.-time*12.);
        float edge=pow(clamp(abs(dot(normalize(vNormal),normalize(vView))),0.,1.),1.3);
        float a=f*bands*edge*.55*power;
        gl_FragColor=vec4(mix(vec3(.08,.38,1.4),vec3(.65,1.6,2.7),f),a);}`,
    })
    const cone = new THREE.Mesh(new THREE.ConeGeometry(radius * .82, length, 24, 1, true), shader)
    cone.rotation.x = Math.PI / 2; cone.position.copy(position); cone.position.z += length / 2
    ship.add(cone)
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0x6ba6ff, transparent: true, opacity: .55, blending: THREE.AdditiveBlending, depthWrite: false }))
    glow.position.copy(position); glow.position.z += .015; glow.scale.setScalar(radius * 3.3); ship.add(glow)
    exhausts.push({ cone, glow, radius, length, material: shader })
  }

  let time = 0, previous = performance.now(), frame = 0, lastTick = -1, alive = true, transitioning = 0, deployment = 0
  let cameraFrom = new THREE.Vector3(), aimFrom = new THREE.Vector3()
  const desired = new THREE.Vector3(), target = new THREE.Vector3()
  let width = 1, height = 1, frameCount = 0, fpsStart = performance.now()
  function resize() {
    const bounds = canvas.getBoundingClientRect(); width = Math.max(1, bounds.width); height = Math.max(1, bounds.height)
    const ratio = hooks.state().lowPower || softwareRenderer ? 1 : Math.min(2, Math.max(1.5, window.devicePixelRatio))
    renderer.setPixelRatio(ratio); renderer.setSize(width, height, false)
    composer.setPixelRatio(ratio); composer.setSize(width, height)
    camera.aspect = width / height; camera.updateProjectionMatrix()
    ao.enabled = !hooks.state().lowPower && !softwareRenderer
    camera.setViewOffset(width, height, 0, -height * (width < 700 ? 0 : .035), width, height)
    bloom.enabled = !hooks.state().lowPower
    renderer.shadowMap.enabled = !hooks.state().lowPower && !softwareRenderer
  }
  const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(canvas)

  function sampleCamera(t: number) {
    const index = Math.min(rail.length - 2, rail.findIndex((p, i) => i < rail.length - 1 && t >= p.t && t < rail[i + 1]!.t))
    const a = rail[Math.max(0, index)]!, b = rail[Math.max(0, index) + 1]!
    const u = smooth(0, 1, (t - a.t) / (b.t - a.t))
    const angle = THREE.MathUtils.lerp(a.a, b.a, u)
    const radius = THREE.MathUtils.lerp(a.r, b.r, u) * (width < 700 ? 1.60 : 1)
    target.set(...a.aim as [number, number, number]).lerp(new THREE.Vector3(...b.aim as [number, number, number]), u)
    desired.set(Math.cos(angle) * radius, THREE.MathUtils.lerp(a.h, b.h, u), Math.sin(angle) * radius)
    camera.fov = THREE.MathUtils.lerp(a.fov, b.fov, u) + (width < 700 ? 16 : 0)
    camera.updateProjectionMatrix()
  }

  function animate(now: number) {
    if (!alive) return
    frame = requestAnimationFrame(animate)
    const dt = Math.min((now - previous) / 1000, .05); previous = now
    if (document.hidden) return
    const state = hooks.state()
    if (state.playing && !state.explore) time = (time + dt) % 40
    if (!state.explore) {
      sampleCamera(time)
      if (transitioning > 0) {
        transitioning = Math.max(0, transitioning - dt)
        const u = smooth(0, 1, 1 - transitioning / 1.25)
        camera.position.copy(cameraFrom).lerp(desired, u); cameraAim.copy(aimFrom).lerp(target, u)
      } else { camera.position.copy(desired); cameraAim.copy(target) }
      camera.lookAt(cameraAim)
      controls.target.copy(cameraAim)
    } else { controls.update(); cameraAim.copy(controls.target) }

    const motion = sampleOdinMotion(time)
    const targetDeployment = state.explore ? Number(state.deployed) : motion.deployment
    // In manual mode deployment eases independently; a paused film remains frozen.
    deployment = state.explore ? THREE.MathUtils.damp(deployment, targetDeployment, 3, dt) : targetDeployment
    const mechanism = rig.apply(deployment, time)
    const power = state.explore ? 0 : motion.thrust
    engineMaterials.forEach(material => { material.emissiveIntensity = power * 4 })
    exhausts.forEach(({ cone, glow, length, material }, i) => {
      cone.visible = glow.visible = power > .001
      material.uniforms.time!.value = time + i; material.uniforms.power!.value = power
      const factor = .12 + power * 1.23 + Math.sin(time * 17 + i) * .02 * power
      cone.scale.y = factor
      // Scale around the nozzle, not around the exhaust's midpoint.
      cone.position.z += (factor * length / 2 - Number(cone.userData.offset || length / 2))
      cone.userData.offset = factor * length / 2
      glow.material.opacity = power * .42
    })
    ship.rotation.z = Math.sin(time * TAU / 40) * .014
    stars.rotation.y = time * .0007
    grade.uniforms.time!.value = time
    if (Math.abs(time - lastTick) > .08) { hooks.tick(time); lastTick = time }
    composer.render()
    canvas.dataset.ready = 'true'; canvas.dataset.time = time.toFixed(2)
    canvas.dataset.deployment = deployment.toFixed(3); canvas.dataset.thrust = power.toFixed(3)
    canvas.dataset.joints = String(mechanism.joints); canvas.dataset.quality = state.lowPower ? 'low' : 'high'
    frameCount++
    if (now - fpsStart > 1500) { canvas.dataset.fps = (frameCount * 1000 / (now - fpsStart)).toFixed(0); fpsStart = now; frameCount = 0 }
  }
  function seek(t: number) {
    cameraFrom.copy(camera.position); aimFrom.copy(cameraAim); transitioning = 1.25
    time = clamp(t, 0, 39.99); hooks.tick(time)
  }
  function setExplore(enabled: boolean) {
    controls.enabled = enabled
    if (enabled) { controls.target.copy(cameraAim); controls.update() }
    else { cameraFrom.copy(camera.position); aimFrom.copy(cameraAim); transitioning = 1.25 }
  }
  function reset() {
    time = 0; sampleCamera(time); camera.position.copy(desired); cameraAim.copy(target)
    controls.target.copy(target); controls.update()
  }
  resize(); reset(); hooks.progress(100); frame = requestAnimationFrame(animate)
  return {
    seek, reset, setExplore, resize,
    dispose() {
      alive = false; cancelAnimationFrame(frame); resizeObserver.disconnect(); controls.dispose(); draco.dispose()
      const geometries = new Set<THREE.BufferGeometry>(), textures = new Set<THREE.Texture>(), allMaterials = new Set<THREE.Material>()
      scene.traverse(o => {
        const mesh = o as THREE.Mesh
        if (mesh.geometry) geometries.add(mesh.geometry)
        if (mesh.material) (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach(m => allMaterials.add(m))
      })
      allMaterials.forEach(m => { Object.values(m).forEach(v => { if (v instanceof THREE.Texture) textures.add(v) }); m.dispose() })
      geometries.forEach(g => g.dispose()); textures.forEach(t => t.dispose()); glowTex.dispose()
      environment.dispose(); ao.dispose(); bloom.dispose(); grade.dispose(); composer.dispose(); renderer.dispose()
    },
  }
}
