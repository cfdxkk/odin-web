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
import { FILM_DURATION, DEPLOY_SECONDS, sampleOdinMotion } from './odin-motion'
import { ODIN_CAMERA_ORBIT_SECONDS, sampleOdinCamera, odinCameraFraming, interpolateOdinCamera, interpolateOrientedOdinCamera, odinCameraPhase } from './odin-camera'
import { clampTourIndex, sampleTourDisplayCamera, ODIN_TOUR, ODIN_TOUR_CAMERA_SECONDS, createTourTransition, sampleTourTransition } from './odin-tour'
import type { TourTransition } from './odin-tour'
import { ODIN_DISPLAY_BACKGROUND, ODIN_ENVIRONMENT_INTENSITY, addOdinDisplayLighting } from './odin-lighting'
import { createOdinExhaust, updateOdinExhaust } from './odin-exhaust'
import type { OdinExhaust } from './odin-exhaust'
import { WEAPON_TOUR, WEAPON_DEPLOY_SECONDS, clampWeaponStep, clampWeaponProgress, weaponStepProgress, sampleContinuousWeaponCamera, advanceWeaponCameraProgress, uniformWeaponLevels, focusedWeaponLevels, interpolateWeaponLevels, chooseWeaponRouteSide } from './odin-weapon-tour'
import type { WeaponLevels, WeaponRouteSide } from './odin-weapon-tour'
import { createManualReturn, sampleManualReturn, advanceManualResume, advanceFilmClock } from './odin-manual-return'
import { createOdinCallouts } from './odin-callouts'
import type { CalloutOrigin, CalloutPoint } from './odin-callouts'
import { captureOdinPhoto } from './odin-photo'
import { createSeekTransition, sampleSeekTransition } from './odin-seek'
import type { SeekOptions } from './odin-seek'

type State = { playing: boolean; film?: boolean; explore: boolean; deployed: boolean; lowPower: boolean; viewIndex?: number; weaponStep?: number; weaponProgress?: number; calloutOrigin?: CalloutOrigin; active?: boolean; reducedMotion?: boolean }
type Hooks = { progress: (p: number) => void; tick: (t: number) => void; transition?: (active: boolean) => void; loop?: () => void; anchor?: (point: { x: number; y: number; visible: boolean }) => void; state: () => State }
export type OdinExperience = { seek: (t: number, options?: SeekOptions) => void; setView: (index: number) => void; setWeaponStep: (step: number) => void; setExplore: (b: boolean) => void; capturePhoto: () => Promise<Blob>; resize: () => void; dispose: () => void }
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
  const exhausts: OdinExhaust[] = []
  scene.updateMatrixWorld(true)
  for (let i = 0; i < 13; i++) {
    const engineCore = find(`EngineCore_${String(i).padStart(2, '0')}`)
    if (!engineCore) continue
    const position = engineCore.getWorldPosition(new THREE.Vector3())
    const radius = Number(engineCore.userData.radius || 3) * .01
    const length = radius * (i === 0 ? 15 : 11)
    const effect = createOdinExhaust(radius, length, i, glowTex)
    effect.group.position.copy(position); ship.add(effect.group)
    effect.lightSurfaces.forEach(surface => ao.excludedObjects.add(surface))
    exhausts.push(effect)
  }

  let time = ODIN_TOUR[clampTourIndex(hooks.state().viewIndex ?? 0)]!.time as number
  let cameraTime = 0, effectTime = 0, previous = performance.now(), frame = 0, lastTick = -1, alive = true, transitioning = 0, deployment = 0, explorationTime = 0
  let manualMotion = { deployment: 0, thrust: 0 }
  let manualLevels: WeaponLevels | undefined
  let viewIndex = hooks.state().viewIndex
  let weaponStep = clampWeaponStep(hooks.state().weaponStep ?? 0)
  let animateWeaponEntryCallout = viewIndex === 1 && weaponStep === 0
  let weaponCameraProgress = clampWeaponProgress(hooks.state().weaponProgress ?? weaponStepProgress(weaponStep))
  let weaponRouteSide: WeaponRouteSide = -1
  let orientedCameraTransition = viewIndex === 1 || viewIndex === 2
  let weaponLevels = uniformWeaponLevels(sampleOdinMotion(time).deployment)
  let selective = viewIndex === 1
  let weaponTransition: { from: WeaponLevels; to: WeaponLevels; elapsed: number; duration: number } | undefined
  if (selective) weaponLevels = focusedWeaponLevels(weaponStep)
  let cameraTransitionSeconds = ODIN_TOUR_CAMERA_SECONDS
  let motionTransition: TourTransition | undefined, motionElapsed = 0, guideFromAnimationTime = time
  let returningFromManual = false, savedGuideTime = time
  let seeking = false
  let renderedMotion: { deployment: number; thrust: number } = sampleOdinMotion(time)
  let renderedAnimationTime = time, lastPlaying = hooks.state().playing
  let lastFilmPlaying = hooks.state().film ?? lastPlaying
  let lastTransitionActive = false
  let needsRender = true, renderedFrames = 0
  let stateKey = ''
  controls.addEventListener('change', () => { needsRender = true })
  let cameraFrom = new THREE.Vector3(), aimFrom = new THREE.Vector3(), upFrom = new THREE.Vector3(0, 1, 0)
  const desiredUp = new THREE.Vector3(0, 1, 0), projectedAnchor = new THREE.Vector3(), anchorWorld = new THREE.Vector3()
  const callouts = createOdinCallouts(canvas.parentElement!)
  const calloutPoints: CalloutPoint[] = []
  const weaponAnchors = WEAPON_TOUR.map(shot => {
    const names = (shot as { anchors?: readonly string[] }).anchors ?? (shot.anchor ? [shot.anchor] : [])
    return names.map(name => {
      const joint = find(name), mesh = joint?.getObjectByProperty('isMesh', true) as THREE.Mesh | undefined
      if (!mesh) return joint ? { name, object: joint, center: new THREE.Vector3() } : undefined
      mesh.geometry.computeBoundingBox()
      return { name, object: mesh, center: mesh.geometry.boundingBox!.getCenter(new THREE.Vector3()) }
    }).filter((anchor): anchor is NonNullable<typeof anchor> => !!anchor)
  })
  const desired = new THREE.Vector3(), target = new THREE.Vector3()
  let width = 1, height = 1, frameCount = 0, fpsStart = performance.now()
  let manualFraming: { x: number; y: number } | undefined
  function frameCamera() {
    if (hooks.state().explore) {
      if (manualFraming) camera.setViewOffset(width, height, width * manualFraming.x, height * manualFraming.y, width, height)
      else camera.clearViewOffset()
    }
    else if (viewIndex === undefined) camera.setViewOffset(width, height, 0, height * odinCameraFraming(camera.aspect, width < 700).viewOffsetY, width, height)
    else if (width > 700) camera.setViewOffset(width, height, -width * .135, 0, width, height)
    else camera.clearViewOffset()
  }
  function resize() {
    needsRender = true
    const bounds = canvas.getBoundingClientRect(); width = Math.max(1, bounds.width); height = Math.max(1, bounds.height)
    const ratio = hooks.state().lowPower || softwareRenderer ? 1 : Math.min(2, Math.max(1.5, window.devicePixelRatio))
    renderer.setPixelRatio(ratio); renderer.setSize(width, height, false)
    composer.setPixelRatio(ratio); composer.setSize(width, height)
    callouts.resize(width, height, ratio)
    camera.aspect = width / height; camera.updateProjectionMatrix()
    ao.enabled = !hooks.state().lowPower && !softwareRenderer
    frameCamera()
    renderer.shadowMap.enabled = !hooks.state().lowPower && !softwareRenderer
  }
  const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(canvas)

  function sampleCamera(t: number) {
    const shot = viewIndex === 1 ? sampleContinuousWeaponCamera(weaponCameraProgress, camera.aspect, weaponRouteSide) : viewIndex === undefined ? sampleOdinCamera(t, camera.aspect, width < 700) : sampleTourDisplayCamera(viewIndex, t, camera.aspect, width < 700, weaponRouteSide)
    target.copy(shot.target); desired.copy(shot.position)
    if ('up' in shot) desiredUp.copy(shot.up as THREE.Vector3)
    else desiredUp.set(0, 1, 0)
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
      // Finish a finite selective-to-film handoff at its common endpoint.
      // A pause still persists, but must not abandon the global half of that
      // handoff and snap the rig back to an unrelated film pose afterward.
      if (!weaponTransition && !returningFromManual && !seeking) motionTransition = undefined
      lastPlaying = state.playing; lastFilmPlaying = filmPlaying; needsRender = true
    }
    const nextStateKey = `${state.playing}/${filmPlaying}/${state.explore}/${state.deployed}/${state.lowPower}/${state.active}/${state.weaponProgress}/${state.calloutOrigin?.x}/${state.calloutOrigin?.y}/${state.calloutOrigin?.visible}`
    if (nextStateKey !== stateKey) { needsRender = true; stateKey = nextStateKey }
    if (state.active === false) { needsRender = true; return }
    if (state.explore) controls.update()
    const manualMoving = state.explore && (!!manualLevels || Math.abs(manualMotion.deployment - Number(state.deployed)) > .00001 || Math.abs(manualMotion.thrust - Number(!state.deployed)) > .00001)
    const weaponDestination = clampWeaponProgress(state.weaponProgress ?? weaponStepProgress(weaponStep))
    const weaponCameraMoving = viewIndex === 1 && !state.explore && weaponCameraProgress !== weaponDestination
    if (weaponCameraMoving) weaponCameraProgress = state.reducedMotion ? weaponDestination : advanceWeaponCameraProgress(weaponCameraProgress, weaponDestination, dt)
    // Paused chapters and a viewport scrolled off screen use no GPU frames.
    const exhaustMoving = state.playing && renderedMotion.thrust > .001
    if (!needsRender && !filmPlaying && !manualMoving && !weaponCameraMoving && !exhaustMoving && transitioning <= 0 && !motionTransition && !weaponTransition && !callouts.moving(state.calloutOrigin)) return
    if (state.playing) effectTime += dt
    if (filmPlaying && !state.explore && (viewIndex === undefined || viewIndex === 0)) {
      // The 45-second orbit has its own clock, including during pose handoffs.
      cameraTime = (cameraTime + dt) % ODIN_CAMERA_ORBIT_SECONDS
    }
    let guidedMotion: ReturnType<typeof sampleTourTransition> | undefined
    if (motionTransition && !state.explore) {
      motionElapsed += dt
      guidedMotion = seeking ? sampleSeekTransition(motionTransition, motionElapsed) : returningFromManual ? sampleManualReturn(motionTransition, motionElapsed) : sampleTourTransition(motionTransition, motionElapsed)
      time = guidedMotion.time
      renderedAnimationTime = THREE.MathUtils.lerp(guideFromAnimationTime, motionTransition.targetTime, smooth(0, 1, motionElapsed / motionTransition.duration))
      if (motionElapsed >= motionTransition.duration) { motionTransition = undefined; returningFromManual = false; seeking = false }
    } else if (filmPlaying && !state.explore) {
      const next = advanceFilmClock(time, dt, FILM_DURATION)
      time = next.time
      if (next.looped) hooks.loop?.()
    }
    if (state.explore) explorationTime += dt
    if (!state.explore) {
      sampleCamera(cameraTime)
      if (transitioning > 0) {
        transitioning = Math.max(0, transitioning - dt)
        const u = smooth(0, 1, 1 - transitioning / cameraTransitionSeconds)
        if (orientedCameraTransition) {
          const pose = interpolateOrientedOdinCamera({ position: cameraFrom, target: aimFrom, up: upFrom }, { position: desired, target, up: desiredUp }, u)
          camera.position.copy(pose.position); cameraAim.copy(pose.target); camera.up.copy(pose.up)
        } else {
          const pose = interpolateOdinCamera({ position: cameraFrom, target: aimFrom }, { position: desired, target }, u)
          camera.position.copy(pose.position); cameraAim.copy(pose.target)
          camera.up.copy(upFrom).lerp(desiredUp, u).normalize()
        }
      } else { camera.position.copy(desired); cameraAim.copy(target); camera.up.copy(desiredUp) }
      camera.lookAt(cameraAim)
      controls.target.copy(cameraAim)
    } else { cameraAim.copy(controls.target) }

    const motion = guidedMotion ?? sampleOdinMotion(time)
    if (state.explore) {
      manualMotion = advanceManualResume(manualMotion, state.deployed, dt, manualLevels ? Math.max(...Object.values(manualLevels)) : 0)
      // Exploration may interrupt a selective-to-home handoff. Preserve each
      // family instead of expanding the other families to the current maximum.
      if (manualLevels) {
        let matched = true
        for (const group of Object.keys(manualLevels) as (keyof WeaponLevels)[]) {
          const delta = manualMotion.deployment - manualLevels[group]
          manualLevels[group] += clamp(delta, -dt / DEPLOY_SECONDS, dt / DEPLOY_SECONDS)
          if (Math.abs(manualLevels[group] - manualMotion.deployment) > .00001) matched = false
        }
        weaponLevels = manualLevels
        if (matched) manualLevels = undefined
      }
    }
    deployment = state.explore ? manualMotion.deployment : motion.deployment
    const animationTime = state.explore ? explorationTime : guidedMotion ? renderedAnimationTime : time
    renderedAnimationTime = animationTime
    renderedMotion = { deployment: deployment, thrust: state.explore ? manualMotion.thrust : motion.thrust }
    if (weaponTransition && !state.explore) {
      weaponTransition.elapsed += dt
      weaponLevels = interpolateWeaponLevels(weaponTransition.from, weaponTransition.to, weaponTransition.elapsed / weaponTransition.duration)
      if (weaponTransition.elapsed >= weaponTransition.duration) {
        weaponLevels = { ...weaponTransition.to }; weaponTransition = undefined
        if (viewIndex !== 1) selective = false
      }
    }
    const useSelective = selective && !state.explore || !!manualLevels && state.explore
    const mechanism = useSelective ? rig.applySelective(weaponLevels, animationTime) : rig.apply(deployment, animationTime)
    if (!useSelective) weaponLevels = uniformWeaponLevels(deployment)
    else { deployment = Math.max(...Object.values(weaponLevels)); renderedMotion.deployment = deployment }
    const power = state.explore ? manualMotion.thrust : motion.thrust
    engineMaterials.forEach(material => { material.emissiveIntensity = power * 4 })
    exhausts.forEach(effect => updateOdinExhaust(effect, power, effectTime))
    if (Math.abs(time - lastTick) > .08) { hooks.tick(time); lastTick = time }
    const transitionActive = transitioning > 0 || !!motionTransition || !!weaponTransition || weaponCameraMoving
    if (transitionActive !== lastTransitionActive) { hooks.transition?.(transitionActive); lastTransitionActive = transitionActive }
    composer.render()
    calloutPoints.length = 0
    if (viewIndex === 1 && !state.explore) {
      const anchors = weaponAnchors[weaponStep]!
      for (let index = 0; index < Math.max(1, anchors.length); index++) {
        const anchor = anchors[index]
        if (anchor) anchor.object.localToWorld(anchorWorld.copy(anchor.center))
        else {
          const shot = WEAPON_TOUR[weaponStep]!
          const [x, y, z] = 'calloutPoint' in shot ? shot.calloutPoint : shot.point
          anchorWorld.set(x * .01, z * .01, -y * .01)
        }
        projectedAnchor.copy(anchorWorld).project(camera)
        const ghost = !!anchor && (anchor.name.includes('Ventral') ? camera.position.y > anchorWorld.y : anchor.name.includes('Dorsal') && camera.position.y < anchorWorld.y)
        calloutPoints.push({ x: (projectedAnchor.x + 1) * width / 2, y: (1 - projectedAnchor.y) * height / 2, visible: projectedAnchor.z > -1 && projectedAnchor.z < 1 && Math.abs(projectedAnchor.x) < 1 && Math.abs(projectedAnchor.y) < 1, ghost })
      }
      hooks.anchor?.(calloutPoints[0]!)
    } else hooks.anchor?.({ x: 0, y: 0, visible: false })
    callouts.render(viewIndex === 1 && !state.explore ? state.calloutOrigin : undefined, calloutPoints, dt, !!state.reducedMotion, {
      key: weaponStep, animate: animateWeaponEntryCallout, cameraRemaining: transitioning,
      // The first leader begins as the camera settles, even while unrelated
      // turrets finish stowing. Later leaders simply track their moving guns.
      scrolling: Math.abs(weaponCameraProgress - weaponDestination) > .002,
    })
    needsRender = false
    canvas.dataset.renderedFrames = String(++renderedFrames)
    canvas.dataset.view = viewIndex === undefined ? 'film' : ODIN_TOUR[viewIndex]!.id
    canvas.dataset.ready = 'true'; canvas.dataset.time = time.toFixed(2)
    canvas.dataset.cameraTime = cameraTime.toFixed(4)
    canvas.dataset.cameraMode = state.explore ? 'manual' : viewIndex === undefined || viewIndex === 0 ? 'orbit' : 'detail'
    canvas.dataset.filmPlaying = (filmPlaying && !state.explore).toString()
    canvas.dataset.cameraTransition = (transitioning > 0).toString()
    canvas.dataset.motionTransition = (!!motionTransition).toString()
    canvas.dataset.manualReturn = String(returningFromManual)
    canvas.dataset.seeking = String(seeking)
    canvas.dataset.cameraFov = camera.fov.toFixed(2)
    canvas.dataset.cameraOffset = camera.view?.enabled ? `${(camera.view.offsetX / camera.view.fullWidth).toFixed(4)},${(camera.view.offsetY / camera.view.fullHeight).toFixed(4)}` : '0.0000,0.0000'
    canvas.dataset.deployment = deployment.toFixed(3); canvas.dataset.thrust = power.toFixed(3)
    canvas.dataset.exhaustLayers = String(exhausts.length * 3); canvas.dataset.exhaustTime = effectTime.toFixed(3)
    canvas.dataset.joints = String(mechanism.joints); canvas.dataset.quality = state.lowPower ? 'low' : 'high'
    canvas.dataset.cameraTarget = controls.target.toArray().map(n => n.toFixed(3)).join(',')
    canvas.dataset.cameraPosition = camera.position.toArray().map(n => n.toFixed(6)).join(',')
    canvas.dataset.cameraQuaternion = camera.quaternion.toArray().map(n => n.toFixed(6)).join(',')
    canvas.dataset.weapon = viewIndex === 1 ? WEAPON_TOUR[weaponStep]!.id : ''
    canvas.dataset.weaponLevels = JSON.stringify(weaponLevels)
    canvas.dataset.weaponTransition = String(!!weaponTransition)
    canvas.dataset.weaponProgress = weaponCameraProgress.toFixed(6)
    canvas.dataset.weaponRouteSide = weaponRouteSide < 0 ? 'port' : 'starboard'
    canvas.dataset.cameraUp = camera.up.toArray().map(n => n.toFixed(3)).join(',')
    frameCount++
    if (now - fpsStart > 1500) { canvas.dataset.fps = (frameCount * 1000 / (now - fpsStart)).toFixed(0); fpsStart = now; frameCount = 0 }
  }
  function seek(t: number, options: SeekOptions = {}) {
    // R in the weapon chapter reframes the current mount; it never starts
    // the all-weapons film behind the focused presentation.
    if (viewIndex === 1) { setWeaponStep(weaponStep); return }
    needsRender = true
    motionTransition = undefined
    returningFromManual = false
    seeking = false
    const immediate = !!options.immediate || !!hooks.state().reducedMotion
    const destination = clamp(t, 0, FILM_DURATION - .01)
    const transition = createSeekTransition(renderedMotion, destination)
    guideFromAnimationTime = renderedAnimationTime; motionElapsed = 0
    // In particular, a click during the selective-to-home handoff must retain
    // the visible mix of families rather than snapping every group to its max.
    if (selective && !immediate) transitionWeapons(uniformWeaponLevels(transition.to.deployment), transition.duration)
    else { weaponTransition = undefined; selective = false }
    const orbit = viewIndex === undefined || viewIndex === 0
    if (orbit) { cameraFrom.copy(camera.position); aimFrom.copy(cameraAim); upFrom.copy(camera.up); cameraTransitionSeconds = 1.25; transitioning = immediate ? 0 : cameraTransitionSeconds }
    time = destination
    if (immediate) { renderedMotion = sampleOdinMotion(time); renderedAnimationTime = time }
    else { motionTransition = transition; seeking = true }
    if (orbit) cameraTime = time % ODIN_CAMERA_ORBIT_SECONDS
    hooks.tick(time)
  }
  function setExplore(enabled: boolean) {
    needsRender = true
    motionTransition = undefined
    returningFromManual = false
    seeking = false
    lastPlaying = hooks.state().playing; lastFilmPlaying = hooks.state().film ?? lastPlaying
    controls.enabled = enabled
    if (enabled) {
      const framing = camera.view
      manualFraming = framing?.enabled ? { x: framing.offsetX / framing.fullWidth, y: framing.offsetY / framing.fullHeight } : undefined
    }
    frameCamera()
    if (enabled) {
      transitioning = 0
      savedGuideTime = time
      manualMotion = { ...renderedMotion }; explorationTime = renderedAnimationTime
      manualLevels = selective ? { ...weaponLevels } : undefined
      weaponTransition = undefined; selective = false
      callouts.reset()
      // OrbitControls can retain damped rotation/pan from an earlier manual
      // session. Flush it, then restore the exact pose before enabling input.
      const heldPosition = camera.position.clone(), heldAim = cameraAim.clone()
      controls.target.copy(heldAim); controls.enableDamping = false; controls.update()
      camera.position.copy(heldPosition); controls.target.copy(heldAim); controls.update()
      controls.enableDamping = true
    }
    else {
      const transition = createManualReturn(renderedMotion, savedGuideTime)
      if (manualLevels) {
        transition.duration = Math.max(WEAPON_DEPLOY_SECONDS, transition.duration)
        transitionWeapons(uniformWeaponLevels(transition.to.deployment), transition.duration)
        manualLevels = undefined
      }
      guideFromAnimationTime = renderedAnimationTime; motionElapsed = 0
      time = savedGuideTime
      if (hooks.state().reducedMotion) { renderedMotion = sampleOdinMotion(time); renderedAnimationTime = time }
      else { motionTransition = transition; returningFromManual = true }
      cameraFrom.copy(camera.position); aimFrom.copy(cameraAim); upFrom.copy(camera.up)
      if (viewIndex === 0) cameraTime = odinCameraPhase({ position: cameraFrom, target: aimFrom })
      cameraTransitionSeconds = ODIN_TOUR_CAMERA_SECONDS; transitioning = hooks.state().reducedMotion ? 0 : cameraTransitionSeconds
    }
  }
  function setView(index: number) {
    returningFromManual = false
    seeking = false
    callouts.reset()
    const previousViewIndex = viewIndex
    viewIndex = clampTourIndex(index)
    if ((previousViewIndex === undefined || previousViewIndex === 0) && viewIndex !== 0) {
      weaponRouteSide = chooseWeaponRouteSide(camera.position, cameraAim, weaponRouteSide)
    }
    orientedCameraTransition = viewIndex === 1 || viewIndex === 2 || previousViewIndex === 1 || previousViewIndex === 2
    cameraFrom.copy(camera.position); aimFrom.copy(cameraAim); upFrom.copy(camera.up)
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
    if (viewIndex === 1) {
      weaponStep = clampWeaponStep(hooks.state().weaponStep ?? 0)
      animateWeaponEntryCallout = previousViewIndex !== 1 && weaponStep === 0
      weaponCameraProgress = clampWeaponProgress(hooks.state().weaponProgress ?? weaponStepProgress(weaponStep))
      transitionWeapons(focusedWeaponLevels(weaponStep))
    } else if (selective) transitionWeapons(uniformWeaponLevels(sampleOdinMotion(targetTime).deployment), Math.max(WEAPON_DEPLOY_SECONDS, nextMotion.duration))
    needsRender = true
    frameCamera()
  }
  function transitionWeapons(to: WeaponLevels, duration = WEAPON_DEPLOY_SECONDS) {
    selective = true
    const unchanged = (Object.keys(to) as (keyof WeaponLevels)[]).every(group => Math.abs(weaponLevels[group] - to[group]) < .00001)
    if (hooks.state().reducedMotion || unchanged) { weaponLevels = { ...to }; weaponTransition = undefined; selective = viewIndex === 1 }
    else weaponTransition = { from: { ...weaponLevels }, to, elapsed: 0, duration }
    needsRender = true
  }
  function setWeaponStep(step: number) {
    const next = clampWeaponStep(step)
    if (next === weaponStep) return
    weaponStep = next
    animateWeaponEntryCallout = false
    if (viewIndex !== 1) return
    callouts.reset()
    transitionWeapons(focusedWeaponLevels(weaponStep))
  }
  resize(); sampleCamera(0); camera.position.copy(desired); cameraAim.copy(target); camera.up.copy(desiredUp)
  controls.target.copy(target); controls.update()
  hooks.progress(100); frame = requestAnimationFrame(animate)
  let pendingPhoto: Promise<Blob> | undefined
  function capturePhoto() {
    if (!alive) return Promise.reject(new Error('The 3D viewer has been closed.'))
    if (!pendingPhoto) pendingPhoto = captureOdinPhoto(scene, camera, width, height, ao.excludedObjects).finally(() => { pendingPhoto = undefined })
    return pendingPhoto
  }
  return {
    seek, setView, setWeaponStep, setExplore, capturePhoto, resize,
    dispose() {
      alive = false; cancelAnimationFrame(frame); resizeObserver.disconnect(); controls.dispose(); draco.dispose(); callouts.dispose()
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
