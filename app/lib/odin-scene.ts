import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { OdinGTAOPass } from './odin-ao'
import { createOdinRig } from './odin-rig'
import { createExplorationControls } from './odin-controls'
import { FILM_DURATION, sampleOdinMotion, advanceManualMotion } from './odin-motion'
import { ODIN_CAMERA_ORBIT_SECONDS, sampleOdinCamera, odinCameraFraming, interpolateOdinCamera, odinCameraPhase } from './odin-camera'
import { clampTourIndex, sampleTourDisplayCamera, ODIN_TOUR, ODIN_TOUR_CAMERA_SECONDS, createTourTransition, sampleTourTransition } from './odin-tour'
import type { TourTransition } from './odin-tour'
import { ODIN_DISPLAY_BACKGROUND, ODIN_ENVIRONMENT_INTENSITY, addOdinDisplayLighting } from './odin-lighting'

type State = { playing: boolean; film?: boolean; explore: boolean; deployed: boolean; lowPower: boolean; viewIndex?: number; active?: boolean; reducedMotion?: boolean }
type Hooks = { progress: (p: number) => void; tick: (t: number) => void; transition?: (active: boolean) => void; state: () => State }
export type OdinExperience = { seek: (t: number) => void; setView: (index: number) => void; setExplore: (b: boolean) => void; resize: () => void; dispose: () => void }
const clamp = THREE.MathUtils.clamp
const smooth = (a: number, b: number, t: number) => THREE.MathUtils.smoothstep(t, a, b)

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
  // A full-screen dark backdrop preserves the original showcase palette.
  scene.background = new THREE.Color(ODIN_DISPLAY_BACKGROUND)
  const camera = new THREE.PerspectiveCamera(33, 1, .035, 500)
  const cameraAim = new THREE.Vector3(0, .24, 0)
  const controls = createExplorationControls(camera, canvas)
  controls.minDistance = .4
  controls.target.copy(cameraAim)

  const pmrem = new THREE.PMREMGenerator(renderer)
  const environmentScene = new RoomEnvironment()
  const environment = pmrem.fromScene(environmentScene, .15)
  scene.environment = environment.texture
  scene.environmentIntensity = ODIN_ENVIRONMENT_INTENSITY
  environmentScene.dispose(); pmrem.dispose()
  addOdinDisplayLighting(scene, true)

  const renderTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: softwareRenderer ? 0 : 4 })
  const composer = new EffectComposer(renderer, renderTarget)
  composer.addPass(new RenderPass(scene, camera))
  const ao = new OdinGTAOPass(scene, camera, 1, 1)
  ao.updateGtaoMaterial({ radius: .065, distanceExponent: 1, thickness: .10, scale: .8, samples: 12 })
  ao.blendIntensity = .35
  composer.addPass(ao)
  // Keep local engine effects and AO without a screen-wide halo or bloom.
  composer.addPass(new OutputPass())

  const draco = new DRACOLoader().setDecoderPath('/draco/').setWorkerLimit(2)
  const loader = new GLTFLoader().setDRACOLoader(draco)
  let gltf
  const modelPath = softwareRenderer || canvas.clientWidth < 700 ? '/models/odin-lite.glb' : '/models/odin.glb'
  canvas.dataset.asset = modelPath
  try {
    gltf = await loader.loadAsync(modelPath + '?v=0.11.43-rc.1', event => hooks.progress(event.total ? Math.min(96, event.loaded / event.total * 96) : 30))
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
          material.metalness = .12
          material.roughness = 1
          material.normalScale.setScalar(.16)
        }
        if (material.name === 'Odin_Added_Machined_Alloy') material.roughness = .62
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
    const length = radius * (i === 0 ? 15 : 11)
    const shader = new THREE.ShaderMaterial({
      uniforms: { time: { value: 0 }, power: { value: 1 } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      vertexShader: `varying vec2 vUv; varying vec3 vNormal; varying vec3 vView;
        void main(){vUv=uv;vec4 p=modelViewMatrix*vec4(position,1.);vNormal=normalize(normalMatrix*normal);vView=-p.xyz;gl_Position=projectionMatrix*p;}`,
      fragmentShader: `varying vec2 vUv; varying vec3 vNormal; varying vec3 vView; uniform float time; uniform float power;
        void main(){float f=pow(clamp(1.-vUv.y,0.,1.),1.8);float bands=.94+.06*sin(vUv.y*42.-time*8.);
        float edge=pow(smoothstep(.02,.7,abs(dot(normalize(vNormal),normalize(vView)))),1.6);
        float a=f*bands*edge*.68*power;
        gl_FragColor=vec4(mix(vec3(.025,.10,.45),vec3(.15,.75,1.8),f),a);}`,
    })
    const cone = new THREE.Mesh(new THREE.ConeGeometry(radius * .82, length, 24, 1, true), shader)
    cone.rotation.x = Math.PI / 2; cone.position.copy(position); cone.position.z += length / 2
    ship.add(cone)
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0x6ba6ff, transparent: true, opacity: .55, blending: THREE.AdditiveBlending, depthWrite: false }))
    glow.position.copy(position); glow.position.z += .015; glow.scale.setScalar(radius * 3.3); ship.add(glow)
    ao.excludedObjects.add(cone); ao.excludedObjects.add(glow)
    exhausts.push({ cone, glow, radius, length, material: shader })
  }

  let time = ODIN_TOUR[clampTourIndex(hooks.state().viewIndex ?? 0)]!.time as number
  let cameraTime = 0, previous = performance.now(), frame = 0, lastTick = -1, alive = true, transitioning = 0, deployment = 0, explorationTime = 0
  let manualMotion = { deployment: 0, thrust: 0 }
  let viewIndex = hooks.state().viewIndex
  let cameraTransitionSeconds = ODIN_TOUR_CAMERA_SECONDS
  let motionTransition: TourTransition | undefined, motionElapsed = 0, guideFromAnimationTime = time
  let renderedMotion: { deployment: number; thrust: number } = sampleOdinMotion(time)
  let renderedAnimationTime = time, lastPlaying = hooks.state().playing
  let lastFilmPlaying = hooks.state().film ?? lastPlaying
  let lastTransitionActive = false
  let needsRender = true, renderedFrames = 0
  let stateKey = ''
  controls.addEventListener('change', () => { needsRender = true })
  let cameraFrom = new THREE.Vector3(), aimFrom = new THREE.Vector3()
  const desired = new THREE.Vector3(), target = new THREE.Vector3()
  let width = 1, height = 1, frameCount = 0, fpsStart = performance.now()
  function frameCamera() {
    if (hooks.state().explore) camera.clearViewOffset()
    else if (viewIndex === undefined) camera.setViewOffset(width, height, 0, height * odinCameraFraming(camera.aspect, width < 700).viewOffsetY, width, height)
    else if (width > 700) camera.setViewOffset(width, height, -width * .08, 0, width, height)
    else camera.clearViewOffset()
  }
  function resize() {
    needsRender = true
    const bounds = canvas.getBoundingClientRect(); width = Math.max(1, bounds.width); height = Math.max(1, bounds.height)
    const ratio = hooks.state().lowPower || softwareRenderer ? 1 : Math.min(2, Math.max(1.5, window.devicePixelRatio))
    renderer.setPixelRatio(ratio); renderer.setSize(width, height, false)
    composer.setPixelRatio(ratio); composer.setSize(width, height)
    camera.aspect = width / height; camera.updateProjectionMatrix()
    ao.enabled = !hooks.state().lowPower && !softwareRenderer
    frameCamera()
    renderer.shadowMap.enabled = !hooks.state().lowPower && !softwareRenderer
  }
  const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(canvas)

  function sampleCamera(t: number) {
    const shot = viewIndex === undefined ? sampleOdinCamera(t, camera.aspect, width < 700) : sampleTourDisplayCamera(viewIndex, t, camera.aspect, width < 700)
    target.copy(shot.target); desired.copy(shot.position)
    // The full-screen lens leaves room for the overlay and keeps the hull intact.
    camera.fov = viewIndex === undefined ? (width < 700 ? 34 : 28) : 33
    camera.updateProjectionMatrix()
  }

  function animate(now: number) {
    if (!alive) return
    frame = requestAnimationFrame(animate)
    const dt = Math.min((now - previous) / 1000, .05); previous = now
    if (document.hidden) { needsRender = true; return }
    const state = hooks.state()
    const filmPlaying = state.film ?? state.playing
    // Explicit playback and timeline actions take control of a finite guide
    // transition without changing the user's persistent pause preference.
    if (state.playing !== lastPlaying || filmPlaying !== lastFilmPlaying) {
      motionTransition = undefined; lastPlaying = state.playing; lastFilmPlaying = filmPlaying; needsRender = true
    }
    const nextStateKey = `${state.playing}/${filmPlaying}/${state.explore}/${state.deployed}/${state.lowPower}/${state.active}`
    if (nextStateKey !== stateKey) { needsRender = true; stateKey = nextStateKey }
    if (state.active === false) { needsRender = true; return }
    if (state.explore) controls.update()
    const manualMoving = state.explore && (Math.abs(manualMotion.deployment - Number(state.deployed)) > .00001 || Math.abs(manualMotion.thrust - Number(!state.deployed)) > .00001)
    // Paused chapters and a viewport scrolled off screen use no GPU frames.
    if (!needsRender && !filmPlaying && !manualMoving && transitioning <= 0 && !motionTransition) return
    if (filmPlaying && !state.explore && (viewIndex === undefined || viewIndex === 0)) {
      // The 45-second orbit has its own clock, including during pose handoffs.
      cameraTime = (cameraTime + dt) % ODIN_CAMERA_ORBIT_SECONDS
    }
    let guidedMotion: ReturnType<typeof sampleTourTransition> | undefined
    if (motionTransition && !state.explore) {
      motionElapsed += dt
      guidedMotion = sampleTourTransition(motionTransition, motionElapsed)
      time = guidedMotion.time
      renderedAnimationTime = THREE.MathUtils.lerp(guideFromAnimationTime, motionTransition.targetTime, smooth(0, 1, motionElapsed / motionTransition.duration))
      if (motionElapsed >= motionTransition.duration) motionTransition = undefined
    } else if (filmPlaying && !state.explore) {
      time = (time + dt) % FILM_DURATION
    }
    if (state.explore) explorationTime += dt
    if (!state.explore) {
      sampleCamera(cameraTime)
      if (transitioning > 0) {
        transitioning = Math.max(0, transitioning - dt)
        const u = smooth(0, 1, 1 - transitioning / cameraTransitionSeconds)
        const pose = interpolateOdinCamera({ position: cameraFrom, target: aimFrom }, { position: desired, target }, u)
        camera.position.copy(pose.position); cameraAim.copy(pose.target)
      } else { camera.position.copy(desired); cameraAim.copy(target) }
      camera.lookAt(cameraAim)
      controls.target.copy(cameraAim)
    } else { cameraAim.copy(controls.target) }

    const motion = guidedMotion ?? sampleOdinMotion(time)
    if (state.explore) manualMotion = advanceManualMotion(manualMotion, state.deployed, dt)
    deployment = state.explore ? manualMotion.deployment : motion.deployment
    const animationTime = state.explore ? explorationTime : guidedMotion ? renderedAnimationTime : time
    renderedAnimationTime = animationTime
    renderedMotion = { deployment: deployment, thrust: state.explore ? manualMotion.thrust : motion.thrust }
    const mechanism = rig.apply(deployment, animationTime)
    const power = state.explore ? manualMotion.thrust : motion.thrust
    engineMaterials.forEach(material => { material.emissiveIntensity = power * 4 })
    exhausts.forEach(({ cone, glow, length, material }, i) => {
      cone.visible = glow.visible = power > .001
      material.uniforms.time!.value = animationTime + i; material.uniforms.power!.value = power
      const factor = .12 + power * 1.23 + Math.sin(animationTime * 9 + i) * .008 * power
      cone.scale.y = factor
      // Scale around the nozzle, not around the exhaust's midpoint.
      cone.position.z += (factor * length / 2 - Number(cone.userData.offset || length / 2))
      cone.userData.offset = factor * length / 2
      glow.material.opacity = power * .65
    })
    if (Math.abs(time - lastTick) > .08) { hooks.tick(time); lastTick = time }
    const transitionActive = transitioning > 0 || !!motionTransition
    if (transitionActive !== lastTransitionActive) { hooks.transition?.(transitionActive); lastTransitionActive = transitionActive }
    composer.render()
    needsRender = false
    canvas.dataset.renderedFrames = String(++renderedFrames)
    canvas.dataset.view = viewIndex === undefined ? 'film' : ODIN_TOUR[viewIndex]!.id
    canvas.dataset.ready = 'true'; canvas.dataset.time = time.toFixed(2)
    canvas.dataset.cameraTime = cameraTime.toFixed(4)
    canvas.dataset.cameraMode = state.explore ? 'manual' : viewIndex === undefined || viewIndex === 0 ? 'orbit' : 'detail'
    canvas.dataset.filmPlaying = (filmPlaying && !state.explore).toString()
    canvas.dataset.cameraTransition = (transitioning > 0).toString()
    canvas.dataset.motionTransition = (!!motionTransition).toString()
    canvas.dataset.cameraFov = camera.fov.toFixed(2)
    canvas.dataset.deployment = deployment.toFixed(3); canvas.dataset.thrust = power.toFixed(3)
    canvas.dataset.joints = String(mechanism.joints); canvas.dataset.quality = state.lowPower ? 'low' : 'high'
    canvas.dataset.cameraTarget = controls.target.toArray().map(n => n.toFixed(3)).join(',')
    canvas.dataset.cameraPosition = camera.position.toArray().map(n => n.toFixed(6)).join(',')
    frameCount++
    if (now - fpsStart > 1500) { canvas.dataset.fps = (frameCount * 1000 / (now - fpsStart)).toFixed(0); fpsStart = now; frameCount = 0 }
  }
  function seek(t: number) {
    needsRender = true
    motionTransition = undefined
    if (viewIndex === undefined) { cameraFrom.copy(camera.position); aimFrom.copy(cameraAim); cameraTransitionSeconds = 1.25; transitioning = hooks.state().reducedMotion ? 0 : cameraTransitionSeconds }
    time = clamp(t, 0, FILM_DURATION - .01)
    renderedMotion = sampleOdinMotion(time); renderedAnimationTime = time
    if (viewIndex === undefined) cameraTime = time % ODIN_CAMERA_ORBIT_SECONDS
    hooks.tick(time)
  }
  function setExplore(enabled: boolean) {
    needsRender = true
    motionTransition = undefined
    controls.enabled = enabled
    frameCamera()
    if (enabled) { manualMotion = { ...sampleOdinMotion(time) }; explorationTime = time; controls.target.copy(cameraAim); controls.update() }
    else {
      cameraFrom.copy(camera.position); aimFrom.copy(cameraAim)
      if (viewIndex === 0) cameraTime = odinCameraPhase({ position: cameraFrom, target: aimFrom })
      cameraTransitionSeconds = ODIN_TOUR_CAMERA_SECONDS; transitioning = hooks.state().reducedMotion ? 0 : cameraTransitionSeconds
    }
  }
  function setView(index: number) {
    viewIndex = clampTourIndex(index)
    cameraFrom.copy(camera.position); aimFrom.copy(cameraAim)
    if (viewIndex === 0) cameraTime = odinCameraPhase({ position: cameraFrom, target: aimFrom })
    // Chapter selection changes effective film playback without changing the
    // user's pause preference. Keep the new guided handoff alive in that case.
    lastFilmPlaying = hooks.state().film ?? hooks.state().playing
    cameraTransitionSeconds = ODIN_TOUR_CAMERA_SECONDS
    transitioning = hooks.state().reducedMotion ? 0 : cameraTransitionSeconds
    const targetTime = ODIN_TOUR[viewIndex]!.time
    const nextMotion = createTourTransition(renderedMotion, targetTime)
    guideFromAnimationTime = renderedAnimationTime; motionElapsed = 0
    motionTransition = !hooks.state().reducedMotion && nextMotion.duration > 0 ? nextMotion : undefined
    if (!motionTransition) { time = targetTime; renderedMotion = sampleOdinMotion(time); renderedAnimationTime = time; hooks.tick(time) }
    needsRender = true
    frameCamera()
  }
  resize(); sampleCamera(0); camera.position.copy(desired); cameraAim.copy(target)
  controls.target.copy(target); controls.update()
  hooks.progress(100); frame = requestAnimationFrame(animate)
  return {
    seek, setView, setExplore, resize,
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
      environment.dispose(); ao.dispose(); composer.dispose(); renderer.dispose()
    },
  }
}
