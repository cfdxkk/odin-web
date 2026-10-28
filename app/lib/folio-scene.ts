import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { OdinGTAOPass } from './odin-ao'
import { createOdinRig } from './odin-rig'
import { createExplorationControls } from './odin-controls'
import { interpolateOdinCamera } from './odin-camera'
import {
  createOdinExhaust,
  updateOdinExhaust,
  type OdinExhaust,
} from './odin-exhaust'
import type { WeaponGroup } from './odin-weapon-groups'
import { folioWeaponGroup } from './folio-highlights'
import {
  ATLAS_VIEWS,
  atlasDeployment,
  createAtlasDeploymentTransition,
  advanceAtlasDeployment,
  type AtlasMode,
  type AtlasDeploymentTransition,
} from './atlas-viewer-state'
import { createFolioPrint, type FolioTreatment } from './folio-effects'

export type FolioState = {
  mode: AtlasMode
  deployment: number
  playing: boolean
  active: boolean
  reducedMotion: boolean
  scrubbing?: boolean
  treatment: FolioTreatment
  pointer: { x: number; y: number }
}
export type FolioExperience = {
  invalidate: () => void
  resetView: () => void
  capturePhoto: () => Promise<Blob>
  dispose: () => void
}
type Hooks = {
  state: () => FolioState
  signal?: AbortSignal
  progress: (value: number) => void
  fail: (message: string) => void
}

export async function createFolioExperience(
  canvas: HTMLCanvasElement,
  hooks: Hooks,
): Promise<FolioExperience> {
  if (hooks.signal?.aborted)
    throw new DOMException('Loading cancelled', 'AbortError')
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  const manager = new THREE.LoadingManager()
  const disposers: (() => void)[] = [
    () => {
      const contextAlreadyLost = renderer.getContext().isContextLost()
      renderer.dispose()
      if (!contextAlreadyLost) renderer.forceContextLoss()
    },
  ]
  let alive = true,
    frame = 0
  function dispose() {
    if (!alive) return
    alive = false
    cancelAnimationFrame(frame)
    frame = 0
    canvas.dataset.ready = 'false'
    canvas.dataset.motionActive = 'false'
    manager.abort()
    for (const release of disposers.reverse()) release()
  }
  const abort = () => dispose()
  hooks.signal?.addEventListener('abort', abort, { once: true })
  disposers.push(() => hooks.signal?.removeEventListener('abort', abort))
  const contextLost = (event: Event) => {
    event.preventDefault()
    dispose()
    hooks.fail('三维画布连接已中断，请重新载入设定稿。')
  }
  canvas.addEventListener('webglcontextlost', contextLost)
  disposers.push(() =>
    canvas.removeEventListener('webglcontextlost', contextLost),
  )

  try {
    const gl = renderer.getContext(),
      debug = gl.getExtension('WEBGL_debug_renderer_info')
    const gpu = debug
      ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL))
      : ''
    const software = /swiftshader|llvmpipe|software|basic render/i.test(gpu)
    canvas.dataset.renderer = gpu
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.NoToneMapping
    renderer.setClearColor(0x000000, 0)
    renderer.shadowMap.enabled = !software
    renderer.shadowMap.type = THREE.PCFShadowMap
    renderer.shadowMap.autoUpdate = false
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(28, 1.6, 0.025, 100)
    const controls = createExplorationControls(camera, canvas)
    controls.enabled = true
    controls.minDistance = 1.8
    controls.maxDistance = 25
    controls.dampingFactor = 0.08
    controls.autoRotateSpeed = 0.11
    disposers.push(() => controls.dispose())

    // A neutral paper maquette supplies the print's tonal separation. Source
    // albedo/metallic textures are deliberately not part of the illustrated look.
    scene.add(new THREE.HemisphereLight(0xf5f5ed, 0x616c82, 1.0))
    const key = new THREE.DirectionalLight(0xfff8e8, 2.6)
    key.position.set(-3, 7, -4)
    key.castShadow = !software
    key.shadow.mapSize.set(2048, 2048)
    Object.assign(key.shadow.camera, {
      left: -5,
      right: 5,
      top: 5,
      bottom: -5,
      near: 0.5,
      far: 20,
    })
    key.shadow.bias = -0.00006
    key.shadow.normalBias = 0.003
    scene.add(key)
    const fill = new THREE.DirectionalLight(0xcdd4e5, 0.48)
    fill.position.set(5, 1, 4)
    scene.add(fill)
    disposers.push(() =>
      scene.traverse((object) => {
        if (object instanceof THREE.Light) object.dispose()
      }),
    )

    const renderTarget = new THREE.WebGLRenderTarget(32, 32, {
      type: THREE.HalfFloatType,
      samples: software ? 0 : Math.min(4, renderer.capabilities.maxSamples),
    })
    const composer = new EffectComposer(renderer, renderTarget)
    const render = new RenderPass(scene, camera)
    render.clearAlpha = 0
    composer.addPass(render)
    const ao = new OdinGTAOPass(scene, camera, 32, 32)
    ao.updateGtaoMaterial({
      radius: 0.055,
      distanceExponent: 1,
      thickness: 0.1,
      scale: 0.85,
      samples: software ? 4 : 12,
    })
    ao.blendIntensity = 0.62
    composer.addPass(ao)
    const print = createFolioPrint(ao.normalTexture, ao.depthTexture, camera)
    composer.addPass(print.pass)
    const output = new OutputPass()
    composer.addPass(output)
    disposers.push(() => {
      print.dispose()
      ao.dispose()
      output.dispose()
      composer.dispose()
    })

    const draco = new DRACOLoader(manager)
      .setDecoderPath('/draco/')
      .setWorkerLimit(2)
    disposers.push(() => draco.dispose())
    const asset = software ? '/models/odin-lite.glb' : '/models/odin.glb'
    canvas.dataset.asset = asset
    const gltf = await new GLTFLoader(manager)
      .setDRACOLoader(draco)
      .loadAsync(`${asset}?v=0.26.0`, (event) => {
        if (alive)
          hooks.progress(
            event.total ? Math.min(95, (event.loaded / event.total) * 95) : 25,
          )
      })
    const ship = gltf.scene
    const originalMaterials = new Set<THREE.Material>(),
      materials = new Set<THREE.Material>()
    const textures = new Set<THREE.Texture>(),
      geometries = new Set<THREE.BufferGeometry>()
    const materialMap = new Map<string, THREE.MeshStandardMaterial>()
    const weaponMaterials: {
      material: THREE.MeshStandardMaterial
      group: WeaponGroup
      base: THREE.Color
    }[] = []
    const engineMaterials: THREE.MeshStandardMaterial[] = []
    ship.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return
      object.castShadow = true
      object.receiveShadow = true
      geometries.add(object.geometry)
      const weaponGroup = folioWeaponGroup(object, ship)
      const replace = (source: THREE.Material) => {
        const materialKey = `${source.uuid}:${weaponGroup || 'hull'}`
        if (materialMap.has(materialKey)) return materialMap.get(materialKey)!
        originalMaterials.add(source)
        for (const value of Object.values(source))
          if (value instanceof THREE.Texture) textures.add(value)
        const darker = /Weapon|Steel|Equipment|Bay|Trim|Antenna|Engine/i.test(
          source.name,
        )
        const material = new THREE.MeshStandardMaterial({
          name: `Folio_${source.name}`,
          color: darker ? 0x6a7078 : 0x9ca1a5,
          metalness: 0,
          roughness: 1,
          side: source.side,
        })
        if (weaponGroup)
          weaponMaterials.push({
            material,
            group: weaponGroup,
            base: material.color.clone(),
          })
        if (source.name === 'Odin_Engine_Emission') {
          material.emissive.set(0x2851cf)
          engineMaterials.push(material)
        }
        materialMap.set(materialKey, material)
        materials.add(material)
        return material
      }
      object.material = Array.isArray(object.material)
        ? object.material.map(replace)
        : replace(object.material)
    })
    const releaseShip = () => {
      geometries.forEach((item) => item.dispose())
      originalMaterials.forEach((item) => item.dispose())
      materials.forEach((item) => item.dispose())
      textures.forEach((item) => item.dispose())
    }
    if (!alive) {
      releaseShip()
      throw new DOMException('Loading cancelled', 'AbortError')
    }
    disposers.push(releaseShip)
    scene.add(ship)
    if (gltf.animations.length)
      throw new Error('奥丁设定稿资源必须只包含静态关节。')
    const rig = createOdinRig(ship)

    const glowCanvas = document.createElement('canvas')
    glowCanvas.width = glowCanvas.height = 64
    const gc = glowCanvas.getContext('2d')!,
      gradient = gc.createRadialGradient(32, 32, 0, 32, 32, 32)
    gradient.addColorStop(0, 'rgba(63,103,255,1)')
    gradient.addColorStop(0.3, 'rgba(51,83,219,.3)')
    gradient.addColorStop(1, 'rgba(51,83,219,0)')
    gc.fillStyle = gradient
    gc.fillRect(0, 0, 64, 64)
    const glow = new THREE.CanvasTexture(glowCanvas),
      exhausts: OdinExhaust[] = []
    scene.updateMatrixWorld(true)
    for (let index = 0; index < 13; index++) {
      const core = ship.getObjectByName(
        `EngineCore_${String(index).padStart(2, '0')}`,
      )
      if (!core) continue
      const radius = Number(core.userData.radius || 3) * 0.01
      const exhaust = createOdinExhaust(
        radius,
        radius * (index === 0 ? 15 : 11),
        index,
        glow,
      )
      exhaust.group.position.copy(core.getWorldPosition(new THREE.Vector3()))
      scene.add(exhaust.group)
      exhaust.lightSurfaces.forEach((surface) =>
        ao.excludedObjects.add(surface),
      )
      exhausts.push(exhaust)
    }
    disposers.push(() => {
      glow.dispose()
      exhausts.forEach((exhaust) =>
        exhaust.group.traverse((object) => {
          if (object instanceof THREE.Mesh) object.geometry.dispose()
          if (object instanceof THREE.Mesh || object instanceof THREE.Sprite)
            for (const material of Array.isArray(object.material)
              ? object.material
              : [object.material])
              material.dispose()
        }),
      )
    })

    let width = 1,
      height = 1,
      mode = hooks.state().mode,
      dirty = true,
      dragging = false,
      framed = false
    let previous = performance.now(),
      animationTime = 24,
      orbitTime = 0,
      orbitAngle = 0,
      frames = 0,
      power = 0,
      lastDeployment = -1
    let lastAccent: AtlasMode | undefined,
      treatmentSettling = false
    let transition:
      | {
          from: { position: THREE.Vector3; target: THREE.Vector3 }
          elapsed: number
        }
      | undefined
    let poseTransition: AtlasDeploymentTransition | undefined
    const pointer = new THREE.Vector2(),
      desiredPointer = new THREE.Vector2(),
      cameraRight = new THREE.Vector3(),
      cameraUp = new THREE.Vector3()
    const aspectScale = () =>
      Math.max(
        1,
        (mode === 'overview' ? 1.8 : 2.1) / Math.max(camera.aspect, 0.1),
      )
    const frameCamera = () => {
      const compact = window.innerWidth <= 700
      const offsetX =
        mode === 'overview' ? (compact ? 0 : 0.025) : compact ? -0.05 : -0.13
      const offsetY = mode === 'overview' ? (compact ? 0.02 : 0.125) : 0
      camera.setViewOffset(
        width,
        height,
        width * offsetX,
        height * offsetY,
        width,
        height,
      )
    }
    const shot = () => {
      const view =
        mode === 'overview'
          ? {
              target: [0, 0.1, -0.05] as const,
              direction: [-1.7, 1.25, -1.3] as const,
              distance: 8.7,
            }
          : {
              ...ATLAS_VIEWS[mode],
              distance:
                ATLAS_VIEWS[mode].distance *
                1.18 *
                (mode === 'secondary' ? 1.2 : 1),
            }
      const target = new THREE.Vector3(...view.target),
        scale = aspectScale()
      return {
        target,
        position: new THREE.Vector3(...view.direction)
          .normalize()
          .multiplyScalar(view.distance * scale)
          .add(target),
      }
    }
    const applyCamera = (pose: ReturnType<typeof shot>) => {
      camera.position.copy(pose.position)
      controls.target.copy(pose.target)
      camera.up.set(0, 1, 0)
      camera.lookAt(pose.target)
    }
    function schedule() {
      if (alive && !frame && !document.hidden && hooks.state().active)
        frame = requestAnimationFrame(animate)
    }
    const invalidate = () => {
      dirty = true
      schedule()
    }
    function resetView() {
      transition = {
        from: {
          position: camera.position.clone(),
          target: controls.target.clone(),
        },
        elapsed: 0,
      }
      orbitTime = 0
      orbitAngle = 0
      pointer.set(0, 0)
      dirty = true
      schedule()
    }
    function setSize(ratio: number, w = width, h = height) {
      renderer.setPixelRatio(ratio)
      renderer.setSize(w, h, false)
      composer.setPixelRatio(ratio)
      composer.setSize(w, h)
      print.resize(w, h, ratio)
    }
    function resize() {
      const bounds = canvas.getBoundingClientRect()
      width = Math.max(1, bounds.width)
      height = Math.max(1, bounds.height)
      const previousScale = aspectScale()
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      frameCamera()
      if (framed) {
        const nextScale = aspectScale()
        camera.position
          .sub(controls.target)
          .multiplyScalar(nextScale / previousScale)
          .add(controls.target)
        if (transition)
          transition.from.position
            .sub(transition.from.target)
            .multiplyScalar(nextScale / previousScale)
            .add(transition.from.target)
      }
      setSize(
        software ? 1 : Math.min(2, Math.max(1.5, window.devicePixelRatio)),
      )
      dirty = true
      schedule()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)
    disposers.push(() => observer.disconnect())
    const visibility = () => {
      previous = performance.now()
      if (!document.hidden) invalidate()
    }
    document.addEventListener('visibilitychange', visibility)
    disposers.push(() =>
      document.removeEventListener('visibilitychange', visibility),
    )
    controls.addEventListener('start', () => {
      dragging = true
      transition = undefined
      orbitTime = 0
      orbitAngle = 0
      pointer.set(0, 0)
      invalidate()
    })
    controls.addEventListener('end', () => {
      dragging = false
      invalidate()
    })
    controls.addEventListener('change', () => {
      dirty = true
      schedule()
    })
    function renderFrame() {
      const originalPosition = camera.position.clone(),
        originalQuaternion = camera.quaternion.clone()
      cameraRight.set(1, 0, 0).applyQuaternion(camera.quaternion)
      cameraUp.set(0, 1, 0).applyQuaternion(camera.quaternion)
      camera.position
        .addScaledVector(cameraRight, pointer.x * 0.16)
        .addScaledVector(cameraUp, pointer.y * 0.08)
      camera.lookAt(controls.target)
      composer.render(0)
      camera.position.copy(originalPosition)
      camera.quaternion.copy(originalQuaternion)
      camera.updateMatrixWorld()
    }
    function animate(now: number) {
      frame = 0
      if (!alive || document.hidden || !hooks.state().active) return
      const state = hooks.state(),
        dt = Math.min(Math.max((now - previous) / 1000, 0), 0.05)
      previous = now
      const requested = atlasDeployment(state.deployment)
      if (mode !== state.mode) {
        mode = state.mode
        resetView()
        frameCamera()
        if (lastDeployment >= 0 && lastDeployment !== requested)
          poseTransition = createAtlasDeploymentTransition(
            lastDeployment,
            requested,
          )
      }
      const moving =
        state.playing && !state.reducedMotion && !state.scrubbing && !dragging
      controls.autoRotate = false
      controls.enableDamping = !state.reducedMotion
      if (transition) {
        transition.elapsed += dt
        const fraction = state.reducedMotion
          ? 1
          : Math.min(1, transition.elapsed / 1.25)
        applyCamera(
          interpolateOdinCamera(
            transition.from,
            shot(),
            THREE.MathUtils.smootherstep(fraction, 0, 1),
          ),
        )
        if (fraction === 1) transition = undefined
        dirty = true
      }
      // A bounded arc keeps the cover composition intact indefinitely. Dragging
      // rebases the arc to the user's new angle instead of snapping back.
      if (moving && !transition) {
        orbitTime += dt
        const angle = Math.sin(orbitTime * 0.12) * 0.075
        camera.position
          .sub(controls.target)
          .applyAxisAngle(THREE.Object3D.DEFAULT_UP, angle - orbitAngle)
          .add(controls.target)
        orbitAngle = angle
      }
      const cameraMoved = controls.update(dt)
      if (moving) {
        animationTime += dt
        desiredPointer.set(
          THREE.MathUtils.clamp(state.pointer.x || 0, -1, 1),
          THREE.MathUtils.clamp(state.pointer.y || 0, -1, 1),
        )
        pointer.lerp(desiredPointer, 1 - Math.exp(-dt * 2.8))
      }
      const pose = advanceAtlasDeployment(
        poseTransition,
        requested,
        dt,
        state.scrubbing,
        state.reducedMotion,
      )
      const deployment = pose.deployment
      poseTransition = pose.transition
      if (lastDeployment !== deployment || moving) {
        rig.apply(deployment, animationTime)
        lastDeployment = deployment
        renderer.shadowMap.needsUpdate = true
        dirty = true
      }
      // No idle flame in the folio. The engine study alone may ignite, and only
      // after every mechanical group has returned to exactly zero deployment.
      const targetPower = deployment === 0 && mode === 'engines' ? 0.85 : 0,
        previousPower = power
      power =
        targetPower > power && !state.reducedMotion
          ? Math.min(targetPower, power + dt * 0.5)
          : targetPower
      engineMaterials.forEach((material) => {
        material.emissiveIntensity = power * 1.8
      })
      exhausts.forEach((exhaust) =>
        updateOdinExhaust(exhaust, power, animationTime),
      )
      if (lastAccent !== mode) {
        const selected =
          mode === 'secondary' ? 'single' : mode === 'bridge' ? 'quad' : mode
        weaponMaterials.forEach(({ material, group, base }) => {
          material.color.copy(
            group === selected ? new THREE.Color(0x2851cf) : base,
          )
          material.emissive.set(group === selected ? 0x081343 : 0x000000)
          material.emissiveIntensity = 0.4
        })
        lastAccent = mode
        dirty = true
      }
      const treatmentTransition = print.setTreatment(
        state.treatment,
        dt,
        state.reducedMotion,
      )
      if (treatmentTransition || treatmentSettling) dirty = true
      treatmentSettling = treatmentTransition
      if (dirty || cameraMoved || moving || power !== previousPower) {
        renderFrame()
        dirty = false
        Object.assign(canvas.dataset, {
          ready: 'true',
          renderedFrames: String(++frames),
          mode,
          treatment: state.treatment,
          playing: String(state.playing),
          motionActive: String(moving),
          deployment: deployment.toFixed(5),
          thrust: power.toFixed(5),
          animationTime: animationTime.toFixed(5),
          joints: String(rig.jointCount),
          weaponGroups: JSON.stringify(rig.groupCounts),
          orbitAngle: orbitAngle.toFixed(6),
          orbitTime: orbitTime.toFixed(4),
          weaponLevels: JSON.stringify({
            main: deployment,
            single: deployment,
            defense: deployment,
            quad: deployment,
          }),
          cameraTransition: String(!!transition),
          poseTransition: String(!!poseTransition),
          treatmentTransition: String(treatmentTransition),
          highlightedGroup:
            mode === 'secondary'
              ? 'single'
              : mode === 'bridge'
                ? 'quad'
                : mode === 'overview' || mode === 'engines'
                  ? ''
                  : mode,
          cameraPosition: camera.position
            .toArray()
            .map((value) => value.toFixed(5))
            .join(','),
          cameraTarget: controls.target
            .toArray()
            .map((value) => value.toFixed(5))
            .join(','),
        })
      }
      if (
        moving ||
        cameraMoved ||
        transition ||
        poseTransition ||
        power !== targetPower ||
        dragging ||
        treatmentTransition
      )
        schedule()
    }
    resize()
    applyCamera(shot())
    framed = true
    controls.update()
    rig.apply(atlasDeployment(hooks.state().deployment), animationTime)
    renderer.shadowMap.needsUpdate = true
    hooks.progress(100)
    invalidate()
    return {
      invalidate,
      resetView,
      dispose,
      capturePhoto: () => {
        if (!alive || renderer.getContext().isContextLost())
          return Promise.reject(new Error('三维设定稿不可用。'))
        const previousRatio = renderer.getPixelRatio()
        try {
          setSize(
            Math.min(
              2,
              3840 / width,
              2560 / height,
              renderer.capabilities.maxTextureSize / Math.max(width, height),
            ),
          )
          renderFrame()
          return new Promise<Blob>((resolve, reject) =>
            canvas.toBlob(
              (blob) =>
                blob
                  ? resolve(blob)
                  : reject(new Error('无法生成设定稿图像。')),
              'image/png',
            ),
          )
        } finally {
          setSize(previousRatio)
          dirty = true
          schedule()
        }
      },
    }
  } catch (error) {
    dispose()
    throw error
  }
}
