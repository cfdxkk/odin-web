import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OdinGTAOPass } from './odin-ao'
import { createOdinRig } from './odin-rig'
import { createExplorationControls } from './odin-controls'
import { createOdinExhaust, updateOdinExhaust, type OdinExhaust } from './odin-exhaust'
import { interpolateOdinCamera } from './odin-camera'
import { ATLAS_VIEWS, atlasDeployment, type AtlasMode } from './atlas-viewer-state'
import { sampleAwakeningFilm } from './awakening-film'
import { createAwakeningEffects } from './awakening-effects'

export type AwakeningState = {
  time: number; playing: boolean; started: boolean; inspect: boolean; focus: AtlasMode; deployment: number
  active: boolean; reducedMotion: boolean; spectral: boolean; pointer: { x: number; y: number }
}
export type AwakeningExperience = { invalidate: () => void; resetView: () => void; capturePhoto: () => Promise<Blob>; dispose: () => void }
type Hooks = { state: () => AwakeningState; progress: (value: number) => void; fail: (message: string) => void }

export async function createAwakeningExperience(canvas: HTMLCanvasElement, hooks: Hooks): Promise<AwakeningExperience> {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' })
  const disposers: (() => void)[] = [() => { renderer.dispose(); renderer.forceContextLoss() }]
  let alive = true, frame = 0
  function dispose() {
    if (!alive) return
    alive = false; cancelAnimationFrame(frame); frame = 0
    for (const release of disposers.reverse()) release()
  }
  try {
    const gl = renderer.getContext(), debug = gl.getExtension('WEBGL_debug_renderer_info')
    const gpu = debug ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)) : ''
    const software = /swiftshader|llvmpipe|software|basic render/i.test(gpu)
    canvas.dataset.renderer = gpu
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    renderer.shadowMap.enabled = !software; renderer.shadowMap.type = THREE.PCFShadowMap
    renderer.shadowMap.autoUpdate = false
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x030507)
    scene.fog = new THREE.FogExp2(0x04070b, .012)
    const camera = new THREE.PerspectiveCamera(33, 1.6, .025, 160)
    const controls = createExplorationControls(camera, canvas)
    controls.enabled = false; controls.enableDamping = false
    controls.minDistance = 1.5; controls.maxDistance = 24
    disposers.push(() => controls.dispose())

    const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment()
    const environment = pmrem.fromScene(room, .2)
    room.dispose(); pmrem.dispose(); scene.environment = environment.texture; scene.environmentIntensity = .2
    disposers.push(() => environment.dispose())
    scene.add(new THREE.HemisphereLight(0x8498b6, 0x060607, .10))
    const key = new THREE.DirectionalLight(0xffbd80, 3.8)
    key.position.set(-3.5, 6.5, -5); key.castShadow = !software
    key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: .5, far: 24 })
    key.shadow.bias = -.00008; key.shadow.normalBias = .002
    scene.add(key)
    const cold = new THREE.DirectionalLight(0x82b6ee, 2.2); cold.position.set(4, 1.5, 3); scene.add(cold)
    const rim = new THREE.DirectionalLight(0xff5b16, 3.4); rim.position.set(1, 2, 7); scene.add(rim)
    const top = new THREE.DirectionalLight(0xc4d7ee, .55); top.position.set(-1, 8, 0); scene.add(top)
    const scanLight = new THREE.SpotLight(0x78c9ff, 80, 20, .28, .8, 1)
    scanLight.position.set(-3, 4, -3); scene.add(scanLight, scanLight.target)
    disposers.push(() => scene.traverse(object => { if (object instanceof THREE.Light) object.dispose() }))

    const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: software ? 0 : Math.min(4, renderer.capabilities.maxSamples) })
    const composer = new EffectComposer(renderer, target); composer.addPass(new RenderPass(scene, camera))
    const ao = new OdinGTAOPass(scene, camera, 1, 1)
    ao.updateGtaoMaterial({ radius: .06, distanceExponent: 1, thickness: .10, scale: .8, samples: 12 }); ao.blendIntensity = .3; ao.enabled = !software
    composer.addPass(ao)
    const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .72, .48, 1.05); bloom.enabled = !software; composer.addPass(bloom)
    const effects = createAwakeningEffects(scene); composer.addPass(effects.grade)
    const output = new OutputPass(); composer.addPass(output)
    disposers.push(() => { effects.dispose(); ao.dispose(); bloom.dispose(); output.dispose(); composer.dispose() })
    // Additive atmosphere must not become an opaque silhouette in the AO pass.
    scene.traverse(object => { if (object.name.startsWith('Awakening_')) ao.excludedObjects.add(object) })

    const draco = new DRACOLoader().setDecoderPath('/draco/').setWorkerLimit(2); disposers.push(() => draco.dispose())
    const asset = software ? '/models/odin-lite.glb' : '/models/odin.glb'; canvas.dataset.asset = asset
    const gltf = await new GLTFLoader().setDRACOLoader(draco).loadAsync(`${asset}?v=0.25.0`, event => hooks.progress(event.total ? Math.min(95, event.loaded / event.total * 95) : 25))
    const ship = gltf.scene; scene.add(ship)
    const materials = new Set<THREE.Material>(), textures = new Set<THREE.Texture>(), geometries = new Set<THREE.BufferGeometry>()
    const engineMaterials: THREE.MeshStandardMaterial[] = []
    const scanUniforms = { awakeningScanZ: { value: -3.5 }, awakeningScanAmount: { value: .5 }, awakeningSpectral: { value: 0 } }
    ship.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return
      object.castShadow = true; object.receiveShadow = true; geometries.add(object.geometry)
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        if (materials.has(material)) continue
        materials.add(material)
        for (const value of Object.values(material)) if (value instanceof THREE.Texture) textures.add(value)
        if (!(material instanceof THREE.MeshStandardMaterial)) continue
        material.envMapIntensity = 1.15
        if (material.name.startsWith('Odin_Paint_')) {
          material.color.multiplyScalar(.32); material.metalness = .55; material.roughness = .68; material.normalScale.setScalar(.25)
          // Source roughness textures were tuned for a flat studio rig. A
          // controlled painted finish avoids mirror-white bands in hard light.
          material.roughnessMap = null; material.envMapIntensity = .8
        } else if (material.name === 'Odin_Added_Machined_Alloy') { material.color.multiplyScalar(.45); material.roughness = .48; material.metalness = .85 }
        else if (/Weapon_Steel|Armor|Equipment|Bridge_Trim|Antenna|材质/.test(material.name)) {
          material.color.multiplyScalar(.42); material.metalness = .65; material.roughness = .6; material.roughnessMap = null
        } else if (/DeepRed|Bay_Primer/.test(material.name)) {
          material.color.multiplyScalar(.3); material.roughness = .8
        }
        if (material.name.startsWith('Odin_Nav_')) material.emissiveIntensity = 2.1
        if (material.name === 'Odin_Bay_Service_Light' || material.name === 'Odin_Hangar_Amber') material.emissiveIntensity = 1.2
        for (const map of [material.map, material.normalMap, material.roughnessMap]) if (map) map.anisotropy = renderer.capabilities.getMaxAnisotropy()
        if (material.name === 'Odin_Engine_Emission') { material.emissive.setRGB(.12, .5, 1); engineMaterials.push(material) }
        material.onBeforeCompile = shader => {
          Object.assign(shader.uniforms, scanUniforms)
          shader.vertexShader = 'varying vec3 vAwakeningWorld;\n' + shader.vertexShader
          shader.vertexShader = shader.vertexShader.replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvAwakeningWorld=(modelMatrix*vec4(transformed,1.0)).xyz;')
          shader.fragmentShader = 'varying vec3 vAwakeningWorld; uniform float awakeningScanZ; uniform float awakeningScanAmount; uniform float awakeningSpectral;\n' + shader.fragmentShader
          shader.fragmentShader = shader.fragmentShader.replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
            float awakeningBand=exp(-pow((vAwakeningWorld.z-awakeningScanZ)*8.,2.));
            float awakeningRim=pow(1.-max(0.,dot(normal,normalize(vViewPosition))),3.);
            float awakeningGrid=max(pow(max(0.,cos(vAwakeningWorld.y*85.)),28.),pow(max(0.,cos(vAwakeningWorld.z*42.)),32.)*.3);
            diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.006,.022,.033),awakeningSpectral*.96);
            totalEmissiveRadiance+=vec3(.04,.42,.85)*awakeningBand*awakeningScanAmount*(1.2+awakeningSpectral*2.);
            totalEmissiveRadiance+=vec3(.035,.38,.8)*(awakeningRim*1.8+awakeningGrid*.45)*awakeningSpectral;
          `)
        }
        material.customProgramCacheKey = () => 'odin-awakening-scan-v1'
      }
    })
    disposers.push(() => { geometries.forEach(item => item.dispose()); materials.forEach(item => item.dispose()); textures.forEach(item => item.dispose()) })
    if (gltf.animations.length) throw new Error('奥丁资源必须只包含静态关节。')
    const rig = createOdinRig(ship)
    const glowCanvas = document.createElement('canvas'); glowCanvas.width = glowCanvas.height = 128
    const gc = glowCanvas.getContext('2d')!, gradient = gc.createRadialGradient(64, 64, 0, 64, 64, 64)
    gradient.addColorStop(0, 'rgba(148,209,255,1)'); gradient.addColorStop(.16, 'rgba(41,117,255,.6)'); gradient.addColorStop(.5, 'rgba(20,63,229,.12)'); gradient.addColorStop(1, 'rgba(0,0,0,0)')
    gc.fillStyle = gradient; gc.fillRect(0, 0, 128, 128)
    const glow = new THREE.CanvasTexture(glowCanvas), exhausts: OdinExhaust[] = []
    scene.updateMatrixWorld(true)
    for (let index = 0; index < 13; index++) {
      const core = ship.getObjectByName(`EngineCore_${String(index).padStart(2, '0')}`)
      if (!core) continue
      const radius = Number(core.userData.radius || 3) * .01
      const exhaust = createOdinExhaust(radius, radius * (index === 0 ? 15 : 11), index, glow)
      exhaust.group.position.copy(core.getWorldPosition(new THREE.Vector3())); scene.add(exhaust.group)
      exhaust.lightSurfaces.forEach(surface => ao.excludedObjects.add(surface)); exhausts.push(exhaust)
    }
    disposers.push(() => {
      glow.dispose()
      exhausts.forEach(exhaust => exhaust.group.traverse(object => {
        if (object instanceof THREE.Mesh) object.geometry.dispose()
        if (object instanceof THREE.Mesh || object instanceof THREE.Sprite) for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose()
      }))
    })

    let width = 1, height = 1, previous = performance.now(), effectsTime = 0, frames = 0, dirty = true
    let wasInspecting = hooks.state().inspect, focus = hooks.state().focus, deployment = -1, lastRigTime = -1
    let transition: { from: { position: THREE.Vector3; target: THREE.Vector3 }; elapsed: number } | undefined
    const aim = new THREE.Vector3(), pointer = new THREE.Vector2(), desiredPointer = new THREE.Vector2(), cameraRight = new THREE.Vector3(), cameraUp = new THREE.Vector3()
    const inspectPose = () => {
      const view = ATLAS_VIEWS[focus] || ATLAS_VIEWS.overview, target = new THREE.Vector3(...view.target)
      const aspectScale = Math.max(.85, Math.pow(1.65 / Math.max(1.65, camera.aspect), .4)) * Math.max(1, 1.1 / Math.max(camera.aspect, .1))
      return { target, position: new THREE.Vector3(...view.direction).normalize().multiplyScalar(view.distance * aspectScale).add(target) }
    }
    const applyPose = (pose: { position: THREE.Vector3; target: THREE.Vector3 }) => { camera.position.copy(pose.position); aim.copy(pose.target); camera.up.set(0, 1, 0); camera.lookAt(aim); controls.target.copy(aim) }
    function schedule() { if (alive && !frame && hooks.state().active && !document.hidden) frame = requestAnimationFrame(animate) }
    function invalidate() { dirty = true; schedule() }
    function frameCamera() { camera.setViewOffset(width, height, -width * (hooks.state().inspect ? .055 : .13), 0, width, height) }
    function resize() {
      const rect = canvas.getBoundingClientRect(); width = Math.max(1, rect.width); height = Math.max(1, rect.height)
      const ratio = software ? 1 : Math.min(1.75, Math.max(1, window.devicePixelRatio))
      renderer.setPixelRatio(ratio); renderer.setSize(width, height, false); composer.setPixelRatio(ratio); composer.setSize(width, height)
      camera.aspect = width / height; camera.updateProjectionMatrix(); frameCamera(); invalidate()
    }
    function resetView() {
      if (hooks.state().inspect) transition = { from: { position: camera.position.clone(), target: controls.target.clone() }, elapsed: 0 }
      pointer.set(0, 0); invalidate()
    }
    const observer = new ResizeObserver(resize); observer.observe(canvas); disposers.push(() => observer.disconnect())
    const visibility = () => { previous = performance.now(); if (!document.hidden) invalidate() }
    document.addEventListener('visibilitychange', visibility); disposers.push(() => document.removeEventListener('visibilitychange', visibility))
    const contextLost = (event: Event) => { event.preventDefault(); dispose(); hooks.fail('实时图形连接中断，请重新开启演出。') }
    canvas.addEventListener('webglcontextlost', contextLost); disposers.push(() => canvas.removeEventListener('webglcontextlost', contextLost))
    controls.addEventListener('start', () => { transition = undefined; invalidate() }); controls.addEventListener('change', invalidate)

    function animate(now: number) {
      frame = 0
      const state = hooks.state()
      if (!alive || !state.active || document.hidden) return
      const dt = Math.min(.05, Math.max(0, (now - previous) / 1000)); previous = now
      const moving = state.playing && !state.reducedMotion
      if (moving) effectsTime += dt
      const film = sampleAwakeningFilm(state.started ? state.time : 5)
      controls.enabled = state.inspect
      if (wasInspecting !== state.inspect) {
        wasInspecting = state.inspect; frameCamera()
        if (state.inspect) resetView()
        else transition = undefined
      }
      if (focus !== state.focus) { focus = state.focus; if (state.inspect) resetView() }
      if (state.inspect) {
        if (transition) {
          transition.elapsed += dt
          const progress = !moving ? 1 : Math.min(1, transition.elapsed / 1.1)
          applyPose(interpolateOdinCamera(transition.from, inspectPose(), THREE.MathUtils.smootherstep(progress, 0, 1)))
          if (progress === 1) transition = undefined
        }
        controls.update()
        aim.copy(controls.target)
      } else {
        const target = new THREE.Vector3(...film.camera.target), position = new THREE.Vector3(...film.camera.position)
        const scale = Math.max(.84, Math.pow(1.65 / Math.max(1.65, camera.aspect), .32)) * Math.max(1, 1.12 / Math.max(camera.aspect, .1)) * (state.started ? 1 : 1.06)
        position.sub(target).multiplyScalar(scale)
        if (!state.started) position.applyAxisAngle(new THREE.Vector3(0, 1, 0), Math.sin(effectsTime * .22) * .085)
        position.add(target)
        if (moving) { desiredPointer.set(state.pointer.x, state.pointer.y); pointer.lerp(desiredPointer, 1 - Math.exp(-dt * 3)) }
        cameraRight.setFromMatrixColumn(camera.matrixWorld, 0); cameraUp.setFromMatrixColumn(camera.matrixWorld, 1)
        position.addScaledVector(cameraRight, pointer.x * .16).addScaledVector(cameraUp, -pointer.y * .10)
        applyPose({ position, target })
      }
      const requestedDeployment = state.inspect ? atlasDeployment(state.deployment) : film.deployment
      const rigTime = state.inspect ? 24 + effectsTime : film.time
      if (requestedDeployment !== deployment || rigTime !== lastRigTime) {
        rig.apply(requestedDeployment, rigTime); deployment = requestedDeployment; lastRigTime = rigTime; renderer.shadowMap.needsUpdate = true
      }
      // The same physical lock applies to inspection and every film sample.
      const thrust = deployment === 0 ? state.inspect ? state.focus === 'engines' ? .86 : 0 : film.thrust : 0
      exhausts.forEach(exhaust => updateOdinExhaust(exhaust, thrust, effectsTime))
      engineMaterials.forEach(material => { material.emissiveIntensity = thrust * 5 })
      const reconstruction = state.started && !state.inspect ? THREE.MathUtils.smootherstep(film.time, 14, 20) * (1 - THREE.MathUtils.smootherstep(film.time, 28, 32)) : 0
      const spectral = state.spectral ? 1 : reconstruction
      const scanZ = state.spectral ? Math.sin(effectsTime * .38) * 4.1 : state.started ? -4.1 + film.scan * 8.2 : Math.sin(effectsTime * .18 - 1.3) * 4.1
      scanUniforms.awakeningScanZ.value = scanZ
      scanUniforms.awakeningScanAmount.value = .38 + spectral * 1.02
      scanUniforms.awakeningSpectral.value = spectral
      scanLight.position.set(-2.8, 3.6, scanZ - 1); scanLight.target.position.set(.1, .05, scanZ)
      scanLight.intensity = 19 + spectral * 46
      key.intensity = 3.8 * (1 - spectral * .78)
      cold.intensity = 2.2 + spectral
      rim.color.setRGB(1, .105, .01).lerp(new THREE.Color(.035, .30, 1), spectral)
      bloom.strength = .64 + film.energy * .2 + thrust * .2 + spectral * .12
      effects.update(effectsTime, film.energy, state.inspect ? 0 : film.warp, camera, aim, state.inspect, spectral)
      if (dirty || moving || transition) {
        composer.render(dt); dirty = false
        Object.assign(canvas.dataset, {
          ready: 'true', renderedFrames: String(++frames), time: film.time.toFixed(4), playing: String(state.playing), started: String(state.started), inspect: String(state.inspect),
          deployment: deployment.toFixed(6), thrust: thrust.toFixed(6), weaponGroups: JSON.stringify(rig.groupCounts),
          weaponLevels: JSON.stringify({ main: deployment, single: deployment, defense: deployment, quad: deployment }), joints: String(rig.jointCount),
          cameraPosition: camera.position.toArray().map(value => value.toFixed(5)).join(','), cameraTarget: aim.toArray().map(value => value.toFixed(5)).join(','),
          effectsTime: effectsTime.toFixed(5), spectral: String(state.spectral), materialPhase: spectral.toFixed(4), focus: state.focus, cameraTransition: String(!!transition),
        })
      }
      if (moving || transition) schedule()
    }
    resize(); applyPose({ position: new THREE.Vector3(...sampleAwakeningFilm(5).camera.position), target: new THREE.Vector3(...sampleAwakeningFilm(5).camera.target) })
    renderer.shadowMap.needsUpdate = true; hooks.progress(100); invalidate()
    return {
      invalidate, resetView, dispose,
      capturePhoto: () => {
        if (!alive) return Promise.reject(new Error('实时演出不可用。'))
        const originalRatio = renderer.getPixelRatio(), ratio = Math.min(2, 3840 / width, 2160 / height)
        try {
          renderer.setPixelRatio(ratio); renderer.setSize(width, height, false); composer.setPixelRatio(ratio); composer.setSize(width, height); composer.render(0)
          return new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('无法生成影像。')), 'image/png'))
        } finally {
          renderer.setPixelRatio(originalRatio); renderer.setSize(width, height, false); composer.setPixelRatio(originalRatio); composer.setSize(width, height); invalidate()
        }
      },
    }
  } catch (error) { dispose(); throw error }
}
