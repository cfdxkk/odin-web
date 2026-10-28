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
import { addOdinDisplayLighting, ODIN_ENVIRONMENT_INTENSITY } from './odin-lighting'
import { interpolateOdinCamera } from './odin-camera'
import { createOdinExhaust, updateOdinExhaust, type OdinExhaust } from './odin-exhaust'
import { ATLAS_VIEWS, atlasDeployment, atlasMotionActive, createAtlasDeploymentTransition, advanceAtlasDeployment, atlasEngineTarget, type AtlasViewerState, type AtlasDeploymentTransition } from './atlas-viewer-state'

export type AtlasExperience = {
  invalidate: () => void
  resetView: () => void
  capturePhoto: (options?: { tight?: boolean }) => Promise<Blob>
  dispose: () => void
}
type Hooks = {
  state: () => AtlasViewerState
  progress: (value: number) => void
  fail: (message: string) => void
}

export async function createAtlasExperience(canvas: HTMLCanvasElement, hooks: Hooks): Promise<AtlasExperience> {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' })
  const disposers: (() => void)[] = [() => { renderer.dispose(); renderer.forceContextLoss() }]
  let alive = true, frame = 0
  const dispose = () => {
    if (!alive) return
    alive = false
    cancelAnimationFrame(frame)
    for (const release of disposers.reverse()) release()
  }

  try {
    const gl = renderer.getContext(), debug = gl.getExtension('WEBGL_debug_renderer_info')
    const gpu = debug ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)) : ''
    const software = /swiftshader|llvmpipe|software|basic render/i.test(gpu)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.12
    renderer.setClearColor(0x000000, 0)
    renderer.shadowMap.enabled = !software
    renderer.shadowMap.type = THREE.PCFShadowMap
    canvas.dataset.renderer = gpu

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(33, 1, .025, 150)
    const controls = createExplorationControls(camera, canvas)
    controls.enabled = true
    controls.minDistance = 1.25
    controls.maxDistance = 24
    controls.dampingFactor = .085
    controls.autoRotateSpeed = .24
    disposers.push(() => controls.dispose())

    const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment()
    const environment = pmrem.fromScene(room, .15)
    room.dispose(); pmrem.dispose()
    scene.environment = environment.texture
    scene.environmentIntensity = ODIN_ENVIRONMENT_INTENSITY
    disposers.push(() => environment.dispose())
    addOdinDisplayLighting(scene, !software)
    // A restrained cool edge separates the aft silhouette from charcoal.
    const edge = new THREE.DirectionalLight(0x9fbcdd, .34)
    edge.position.set(-5, 3, 5); scene.add(edge)
    disposers.push(() => scene.traverse(object => { if (object instanceof THREE.Light) object.dispose() }))

    const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: software ? 0 : Math.min(4, renderer.capabilities.maxSamples) })
    const composer = new EffectComposer(renderer, target)
    const renderPass = new RenderPass(scene, camera)
    renderPass.clearAlpha = 0
    composer.addPass(renderPass)
    const ao = new OdinGTAOPass(scene, camera, 1, 1)
    ao.updateGtaoMaterial({ radius: .065, distanceExponent: 1, thickness: .10, scale: .8, samples: 12 })
    ao.blendIntensity = .35
    composer.addPass(ao)
    const output = new OutputPass(); composer.addPass(output)
    disposers.push(() => { ao.dispose(); output.dispose(); composer.dispose() })

    const draco = new DRACOLoader().setDecoderPath('/draco/').setWorkerLimit(2)
    disposers.push(() => draco.dispose())
    // Desktop keeps the full mesh. Only a software GPU uses the reduced asset.
    const asset = software ? '/models/odin-lite.glb' : '/models/odin.glb'
    canvas.dataset.asset = asset
    const loader = new GLTFLoader().setDRACOLoader(draco)
    const gltf = await loader.loadAsync(`${asset}?v=0.24.0`, event => hooks.progress(event.total ? Math.min(95, event.loaded / event.total * 95) : 25))
    const ship = gltf.scene
    scene.add(ship)
    const materials = new Set<THREE.Material>(), textures = new Set<THREE.Texture>(), geometries = new Set<THREE.BufferGeometry>()
    const engineMaterials: THREE.MeshStandardMaterial[] = []
    ship.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return
      object.castShadow = true; object.receiveShadow = true
      geometries.add(object.geometry)
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        if (materials.has(material)) continue
        materials.add(material)
        for (const value of Object.values(material)) if (value instanceof THREE.Texture) textures.add(value)
        if (!(material instanceof THREE.MeshStandardMaterial)) continue
        material.envMapIntensity = 1
        if (material.name.startsWith('Odin_Paint_')) {
          material.metalness = .12; material.roughness = 1; material.normalScale.setScalar(.16)
        }
        if (material.name === 'Odin_Added_Machined_Alloy') material.roughness = .62
        if (material.name.startsWith('Odin_Nav_')) material.emissiveIntensity = 1.2
        if (material.name === 'Odin_Bay_Service_Light' || material.name === 'Odin_Hangar_Amber') material.emissiveIntensity = .65
        for (const map of [material.map, material.normalMap, material.roughnessMap]) if (map) map.anisotropy = renderer.capabilities.getMaxAnisotropy()
        if (material.name === 'Odin_Engine_Emission') { material.emissive.setRGB(.12, .44, 1); engineMaterials.push(material) }
      }
    })
    disposers.push(() => {
      geometries.forEach(geometry => geometry.dispose())
      materials.forEach(material => material.dispose())
      textures.forEach(texture => texture.dispose())
    })
    if (gltf.animations.length) throw new Error('奥丁展示资源必须只包含静态关节。')
    const rig = createOdinRig(ship)
    const wireMaterial = new THREE.MeshBasicMaterial({ color: 0xc1d4cf, wireframe: true, transparent: true, opacity: .28 })
    disposers.push(() => wireMaterial.dispose())

    const glowCanvas = document.createElement('canvas'); glowCanvas.width = glowCanvas.height = 128
    const gc = glowCanvas.getContext('2d')!
    const gradient = gc.createRadialGradient(64, 64, 0, 64, 64, 64)
    gradient.addColorStop(0, 'rgba(148,209,255,1)'); gradient.addColorStop(.16, 'rgba(41,117,255,.6)')
    gradient.addColorStop(.5, 'rgba(20,63,229,.12)'); gradient.addColorStop(1, 'rgba(0,0,0,0)')
    gc.fillStyle = gradient; gc.fillRect(0, 0, 128, 128)
    const glow = new THREE.CanvasTexture(glowCanvas)
    const exhausts: OdinExhaust[] = []
    scene.updateMatrixWorld(true)
    for (let index = 0; index < 13; index++) {
      const core = ship.getObjectByName(`EngineCore_${String(index).padStart(2, '0')}`)
      if (!core) continue
      const radius = Number(core.userData.radius || 3) * .01
      const exhaust = createOdinExhaust(radius, radius * (index === 0 ? 15 : 11), index, glow)
      exhaust.group.position.copy(core.getWorldPosition(new THREE.Vector3()))
      scene.add(exhaust.group)
      exhaust.lightSurfaces.forEach(surface => ao.excludedObjects.add(surface))
      exhausts.push(exhaust)
    }
    disposers.push(() => {
      glow.dispose()
      exhausts.forEach(exhaust => exhaust.group.traverse(object => {
        if (object instanceof THREE.Mesh) object.geometry.dispose()
        if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) {
          for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose()
        }
      }))
    })

    let width = 1, height = 1, mode = hooks.state().mode, dirty = true, dragging = false, framed = false
    let previous = performance.now(), animationTime = 24, frames = 0, power = 0
    let lastDeployment = -1, lastTechnical = !hooks.state().technical
    let transition: { from: { position: THREE.Vector3; target: THREE.Vector3 }; elapsed: number } | undefined
    let poseTransition: AtlasDeploymentTransition | undefined
    const shot = () => {
      const view = ATLAS_VIEWS[mode] || ATLAS_VIEWS.overview
      const aim = new THREE.Vector3(...view.target)
      const scale = Math.max(1, 1.12 / Math.max(camera.aspect, .1))
      return { target: aim, position: new THREE.Vector3(...view.direction).normalize().multiplyScalar(view.distance * scale).add(aim) }
    }
    const applyCamera = (pose: ReturnType<typeof shot>) => {
      camera.position.copy(pose.position); controls.target.copy(pose.target)
      camera.lookAt(pose.target)
    }
    const resetView = () => {
      transition = { from: { position: camera.position.clone(), target: controls.target.clone() }, elapsed: 0 }
      dirty = true
      schedule()
    }
    function resize() {
      const bounds = canvas.getBoundingClientRect()
      width = Math.max(1, bounds.width); height = Math.max(1, bounds.height)
      const ratio = software ? 1 : Math.min(2, Math.max(1, window.devicePixelRatio))
      renderer.setPixelRatio(ratio); renderer.setSize(width, height, false)
      composer.setPixelRatio(ratio); composer.setSize(width, height)
      const previousScale = Math.max(1, 1.12 / Math.max(camera.aspect, .1))
      camera.aspect = width / height; camera.updateProjectionMatrix()
      if (framed) {
        const nextScale = Math.max(1, 1.12 / Math.max(camera.aspect, .1))
        camera.position.sub(controls.target).multiplyScalar(nextScale / previousScale).add(controls.target)
        if (transition) transition.from.position.sub(transition.from.target).multiplyScalar(nextScale / previousScale).add(transition.from.target)
      }
      dirty = true
      schedule()
    }
    const observer = new ResizeObserver(resize); observer.observe(canvas)
    disposers.push(() => observer.disconnect())

    function schedule() {
      if (alive && !frame && !document.hidden && hooks.state().active) frame = requestAnimationFrame(animate)
    }
    const invalidate = () => { dirty = true; previous = performance.now(); schedule() }
    const visibility = () => { previous = performance.now(); if (!document.hidden) invalidate() }
    document.addEventListener('visibilitychange', visibility)
    disposers.push(() => document.removeEventListener('visibilitychange', visibility))
    const contextLost = (event: Event) => {
      event.preventDefault()
      dispose()
      hooks.fail('三维图形连接已中断，请重新载入页面。')
    }
    canvas.addEventListener('webglcontextlost', contextLost)
    disposers.push(() => canvas.removeEventListener('webglcontextlost', contextLost))
    controls.addEventListener('start', () => { dragging = true; transition = undefined; invalidate() })
    controls.addEventListener('end', () => { dragging = false; invalidate() })
    controls.addEventListener('change', () => { dirty = true; schedule() })

    function animate(now: number) {
      frame = 0
      if (!alive || document.hidden || !hooks.state().active) return
      const state = hooks.state(), dt = Math.min(Math.max((now - previous) / 1000, 0), .05)
      previous = now
      const requestedDeployment = atlasDeployment(state.deployment)
      if (mode !== state.mode) {
        mode = state.mode; resetView()
        if (lastDeployment >= 0 && lastDeployment !== requestedDeployment) {
          poseTransition = createAtlasDeploymentTransition(lastDeployment, requestedDeployment)
        }
      }
      const moving = atlasMotionActive(state, !document.hidden, dragging)
      controls.autoRotate = moving && !transition
      controls.enableDamping = !state.reducedMotion
      if (transition) {
        transition.elapsed += dt
        const fraction = state.reducedMotion ? 1 : Math.min(1, transition.elapsed / 1.35)
        const eased = THREE.MathUtils.smootherstep(fraction, 0, 1)
        applyCamera(interpolateOdinCamera(transition.from, shot(), eased))
        if (fraction === 1) transition = undefined
        dirty = true
      }
      const cameraMoved = controls.update(dt)
      // Choosing a system opens its mechanical pose as a finite transition.
      // Any slider edit takes over immediately; it never changes play intent.
      const pose = advanceAtlasDeployment(poseTransition, requestedDeployment, dt, state.scrubbing, state.reducedMotion)
      const deployment = pose.deployment
      poseTransition = pose.transition
      if (moving) animationTime += dt
      if (lastDeployment !== deployment || moving) {
        rig.apply(deployment, animationTime)
        lastDeployment = deployment
        dirty = true
      }
      if (lastTechnical !== state.technical) {
        scene.overrideMaterial = state.technical ? wireMaterial : null
        ao.enabled = !software && !state.technical
        lastTechnical = state.technical
        dirty = true
      }
      // Engine ignition is interlocked with fully stowed weapons. A chapter
      // change cannot light thrust while the finite closing stroke still runs.
      const targetPower = atlasEngineTarget(deployment, state.mode)
      const previousPower = power
      power = targetPower > power && !state.reducedMotion ? Math.min(targetPower, power + dt * .5) : targetPower
      const thrustChanging = power !== targetPower
      engineMaterials.forEach(material => { material.emissiveIntensity = power * 4 })
      exhausts.forEach(exhaust => updateOdinExhaust(exhaust, state.technical ? 0 : power, animationTime))
      if (dirty || cameraMoved || moving || previousPower !== power) {
        composer.render(dt)
        dirty = false
        canvas.dataset.ready = 'true'
        canvas.dataset.renderedFrames = String(++frames)
        canvas.dataset.mode = mode
        canvas.dataset.playing = String(state.playing)
        canvas.dataset.motionActive = String(moving)
        canvas.dataset.deployment = deployment.toFixed(4)
        canvas.dataset.thrust = power.toFixed(4)
        canvas.dataset.animationTime = animationTime.toFixed(4)
        canvas.dataset.technical = String(state.technical)
        canvas.dataset.joints = String(rig.jointCount)
        canvas.dataset.weaponGroups = JSON.stringify(rig.groupCounts)
        canvas.dataset.weaponLevels = JSON.stringify({ main: deployment, single: deployment, defense: deployment, quad: deployment })
        canvas.dataset.cameraTransition = String(!!transition)
        canvas.dataset.poseTransition = String(!!poseTransition)
        canvas.dataset.cameraPosition = camera.position.toArray().map(value => value.toFixed(5)).join(',')
        canvas.dataset.cameraTarget = controls.target.toArray().map(value => value.toFixed(5)).join(',')
      }
      if (moving || cameraMoved || transition || poseTransition || thrustChanging || dragging) schedule()
    }

    resize()
    applyCamera(shot())
    framed = true
    controls.update()
    rig.apply(atlasDeployment(hooks.state().deployment), animationTime)
    hooks.progress(100)
    invalidate()
    return {
      invalidate, resetView, dispose,
      capturePhoto: (options = {}) => {
        if (!alive || renderer.getContext().isContextLost()) return Promise.reject(new Error('三维模型不可用。'))
        // Reuse the live context. Temporarily supersample its drawing buffer;
        // camera, pose, logical canvas dimensions and playback stay untouched.
        const previousRatio = renderer.getPixelRatio()
        const ratio = Math.min(2, 3840 / width, 2560 / height, renderer.capabilities.maxTextureSize / Math.max(width, height))
        const originalView = camera.view ? { ...camera.view } : null
        const exhaustVisibility = exhausts.map(exhaust => exhaust.group.visible)
        let photoWidth = width, photoHeight = height, photoRatio = ratio
        try {
          if (options.tight) {
            // Frame the actual mesh in the lens before rendering. The PNG is
            // captured directly from WebGL; no raster crop or retouch is used.
            exhausts.forEach(exhaust => { exhaust.group.visible = false })
            composer.render(0)
            const probe = document.createElement('canvas')
            probe.width = Math.ceil(width); probe.height = Math.ceil(height)
            const context = probe.getContext('2d', { willReadFrequently: true })!
            context.drawImage(canvas, 0, 0, probe.width, probe.height)
            const pixels = context.getImageData(0, 0, probe.width, probe.height).data
            const bounds = new THREE.Box2()
            for (let y = 0; y < probe.height; y++) for (let x = 0; x < probe.width; x++) {
              if (pixels[(y * probe.width + x) * 4 + 3]! > 12) bounds.expandByPoint(new THREE.Vector2(x * width / probe.width, y * height / probe.height))
            }
            if (bounds.isEmpty()) throw new Error('无法读取舰船轮廓。')
            const margin = Math.max(bounds.max.x - bounds.min.x, bounds.max.y - bounds.min.y) * .035
            bounds.expandByScalar(margin)
            photoWidth = bounds.max.x - bounds.min.x; photoHeight = bounds.max.y - bounds.min.y
            camera.setViewOffset(width, height, bounds.min.x, bounds.min.y, photoWidth, photoHeight)
            photoRatio = Math.min(2600 / photoWidth, 1800 / photoHeight, renderer.capabilities.maxTextureSize / Math.max(photoWidth, photoHeight))
          }
          renderer.setPixelRatio(photoRatio); renderer.setSize(photoWidth, photoHeight, false)
          composer.setPixelRatio(photoRatio); composer.setSize(photoWidth, photoHeight)
          composer.render(0)
          return new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('无法生成 PNG 图像。')), 'image/png'))
        } finally {
          exhausts.forEach((exhaust, index) => { exhaust.group.visible = exhaustVisibility[index]! })
          if (originalView?.enabled) camera.setViewOffset(originalView.fullWidth, originalView.fullHeight, originalView.offsetX, originalView.offsetY, originalView.width, originalView.height)
          else camera.clearViewOffset()
          renderer.setPixelRatio(previousRatio); renderer.setSize(width, height, false)
          composer.setPixelRatio(previousRatio); composer.setSize(width, height)
          dirty = true; schedule()
        }
      },
    }
  } catch (error) {
    dispose()
    throw error
  }
}
