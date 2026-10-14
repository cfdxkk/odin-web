<script setup lang="ts">
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { createOdinRig } from '~/lib/odin-rig'
import { reviewStrokeSeconds, retimeReviewCycle } from '~/lib/turret-tempo'
import { ODIN_DISPLAY_BACKGROUND, ODIN_ENVIRONMENT_INTENSITY, addOdinDisplayLighting } from '~/lib/odin-lighting'

const { locale, copy: c, setLocale } = useOdinLocale()

type Shot = { name: string; point: [number, number, number]; view: [number, number, number]; width: number }
const shots = computed<Shot[]>(() => [
  { name: `${c.value.single} · ${c.value.bow}`, point: [0,258,40], view: [1,1,.7], width: .72 },
  { name: `${c.value.single} · ${c.value.bow} ${c.value.seam}`, point: [0,247,39], view: [2,-.35,.3], width: .3 },
  { name: `${c.value.single} · ${c.value.stern}`, point: [0,-248,52], view: [1,-1,.7], width: .72 },
  { name: `${c.value.single} · ${c.value.keel}`, point: [0,-58,-64], view: [1,-1,-.7], width: .95 },
  ...([c.value.starboard,c.value.port]).flatMap((side, i) => {
    const sign = i ? -1 : 1
    return [[74,86,4],[55,16,30],[61,0,-28],[68,-170,29]].map((p, n) => ({ name: `${c.value.single} · ${side} ${n+1}`, point: [sign*p[0]!,p[1]!,p[2]!] as [number,number,number], view: [sign*2,1,n===2?-.7:.7] as [number,number,number], width: .72 }))
  }),
  { name: `${c.value.quad} · ${c.value.starboard}`, point: [43,-58,106], view: [1,1,.6], width: .8 },
  { name: `${c.value.quad} · ${c.value.port}`, point: [-43,-58,106], view: [-1,1,.6], width: .8 },
  ...([[ -22,-36,53],[-28,-64,53],[22,-36,53],[28,-64,53],[21,-179,43],[14,-221,43],[-21,-179,43],[-14,-221,43]]).map((p,i) => ({ name: `${c.value.twin} · ${i+1}${i>=4?' / '+c.value.hullCover:''}`, point: p as [number,number,number], view: [Math.sign(p[0]!)*1.5,1,.6] as [number,number,number], width: .5 })),
  { name: `${c.value.bridge} · ${c.value.front}`, point: [0,-27,128], view: [1,2,.5], width: .66 },
  { name: `${c.value.bridge} · ${c.value.rear}`, point: [0,-43,128], view: [1,-2,.5], width: .7 },
  { name: `${c.value.bridge} · ${c.value.paint}`, point: [0,-82,68], view: [2,1,.35], width: 1.65 },
  { name: `${c.value.mainGun} · ${c.value.hullSeam}`, point: [11.5,117,40], view: [2,0,.2], width: .25 },
  { name: `${c.value.bridge} · ${c.value.radar}`, point: [0,-50,119], view: [1,-1,.55], width: 1.05 },
  { name: `${c.value.bridge} · ${c.value.glass}`, point: [0,-24,91], view: [1,3,.4], width: .4 },
  { name: `${c.value.mainGun} · ${c.value.upperArmor}`, point: [0,124,45], view: [1,1,.8], width: 1.2 },
  { name: `${c.value.mainGun} · ${c.value.lowerArmor}`, point: [0,76,-56], view: [1,1,-.8], width: 1.2 },
])
const canvas = ref<HTMLCanvasElement>(), selected = ref(0), angle = ref('oblique')
const angles = computed(() => [{ id: 'oblique', label: c.value.angleOblique }, { id: 'side', label: c.value.angleSide }, { id: 'top', label: c.value.angleTop }, { id: 'front', label: c.value.angleFront }])
const deployment = ref(0), playing = ref(false), loading = ref(0), ready = ref(false), error = ref('')
let focus: (() => void) | undefined, cleanup: (() => void) | undefined, disposed = false, cycle = 0
watch([selected,angle], () => focus?.())
watch(selected, (next, previous) => { cycle=retimeReviewCycle(cycle,reviewStrokeSeconds(previous),reviewStrokeSeconds(next)) })
function seek(value: number) { deployment.value=value; playing.value=false; cycle=value*reviewStrokeSeconds(selected.value) }
function scrub(event: Event) { seek(Number((event.target as HTMLInputElement).value)) }
onMounted(async () => {
  const el = canvas.value!
  const renderer = new THREE.WebGLRenderer({ canvas: el, antialias: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.outputColorSpace=THREE.SRGBColorSpace
  renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1
  const scene = new THREE.Scene(); scene.background=new THREE.Color(ODIN_DISPLAY_BACKGROUND)
  const camera=new THREE.OrthographicCamera(-1,1,1,-1,.001,50)
  const controls=new OrbitControls(camera,el); controls.enableDamping=true; controls.dampingFactor=.08; controls.minZoom=.15; controls.maxZoom=12
  controls.mouseButtons={LEFT:THREE.MOUSE.ROTATE,MIDDLE:THREE.MOUSE.DOLLY,RIGHT:THREE.MOUSE.PAN}
  let needsRender=true, renderedFrames=0
  const stopRenderWatch=watch([deployment,playing],()=>{needsRender=true})
  controls.addEventListener('change',()=>{needsRender=true})
  const pmrem=new THREE.PMREMGenerator(renderer), room=new RoomEnvironment(), env=pmrem.fromScene(room,.15)
  scene.environment=env.texture; scene.environmentIntensity=ODIN_ENVIRONMENT_INTENSITY; room.dispose();pmrem.dispose()
  addOdinDisplayLighting(scene)
  const draco=new DRACOLoader().setDecoderPath('/draco/').setWorkerLimit(2)
  const loader=new GLTFLoader().setDRACOLoader(draco)
  let frame=0, observer: ResizeObserver | undefined, previous=performance.now(), elapsed=20
  const map=([x,y,z]: number[])=>new THREE.Vector3(x,z,-y)
  function resize() {
    const box=el.getBoundingClientRect(), w=box.width, h=box.height
    renderer.setSize(w,h,false)
    needsRender=true
    const width=shots.value[selected.value]!.width
    camera.left=-width/2;camera.right=width/2;camera.top=width*h/w/2;camera.bottom=-camera.top;camera.updateProjectionMatrix()
  }
  focus=()=>{
    const shot=shots.value[selected.value]!, p=map(shot.point).multiplyScalar(.01)
    const offset=angle.value==='side'?[Math.sign(shot.view[0])||1,0,0]:angle.value==='top'?[0,0,shot.point[2]<0?-1:1]:angle.value==='front'?[0,shot.point[1]<0?-1:1,0]:shot.view
    camera.up.set(0,1,0)
    if(angle.value==='top')camera.up.set(0,0,-1)
    camera.position.copy(p).add(map(offset).normalize().multiplyScalar(2))
    controls.target.copy(p);camera.zoom=1;camera.lookAt(p);controls.update();resize()
  }
  cleanup=()=>{
    cancelAnimationFrame(frame);stopRenderWatch();observer?.disconnect();controls.dispose();draco.dispose();env.dispose()
    const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>(),textures=new Set<THREE.Texture>()
    scene.traverse(o=>{if(o instanceof THREE.Mesh){geometries.add(o.geometry);(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m))}})
    geometries.forEach(g=>g.dispose());materials.forEach(m=>{Object.values(m).forEach(v=>{if(v instanceof THREE.Texture)textures.add(v)});m.dispose()});textures.forEach(t=>t.dispose());renderer.dispose()
  }
  try {
    const gltf=await loader.loadAsync('/models/odin.glb?v=0.11.43-rc.1',e=>{loading.value=e.total?Math.round(e.loaded/e.total*100):30})
    scene.add(gltf.scene)
    if(disposed){cleanup();return}
    const rig=createOdinRig(gltf.scene)
    gltf.scene.traverse(o=>{if(o instanceof THREE.Mesh)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>{if(m instanceof THREE.MeshStandardMaterial&&m.map)m.map.anisotropy=renderer.capabilities.getMaxAnisotropy()})})
    observer=new ResizeObserver(resize);observer.observe(el);focus();ready.value=true
    function render(now: number) {
      frame=requestAnimationFrame(render);const dt=Math.min((now-previous)/1000,.05);previous=now
      if(document.hidden){needsRender=true;return}
      if(playing.value){
        const stroke=reviewStrokeSeconds(selected.value)
        elapsed+=dt;cycle=(cycle+dt)%(2*stroke+2)
        deployment.value=cycle<stroke?cycle/stroke:cycle<stroke+1?1:cycle<2*stroke+1?1-(cycle-stroke-1)/stroke:0
      }
      controls.update()
      if(!needsRender&&!playing.value)return
      rig.apply(deployment.value,elapsed);renderer.render(scene,camera);needsRender=false
      el.dataset.ready='true';el.dataset.deployment=deployment.value.toFixed(3);el.dataset.station=shots.value[selected.value]!.name;el.dataset.joints=String(rig.jointCount)
      el.dataset.renderedFrames=String(++renderedFrames)
    }
    frame=requestAnimationFrame(render)
  }catch(e){error.value=e instanceof Error?e.message:String(e);cleanup()}
})
onBeforeUnmount(()=>{disposed=true;cleanup?.()})
</script>

<template>
  <main class="articulation-review">
    <canvas ref="canvas" :aria-label="c.reviewCanvas" />
    <header><div><span class="review-kicker">{{ c.reviewKicker }}</span><h1>{{ c.reviewTitle }} <small>v0.22.0</small></h1></div><div class="review-header-actions"><button :aria-label="c.switchLanguage" @click="setLocale(locale === 'zh' ? 'en' : 'zh')">{{ locale === 'zh' ? 'EN' : 'ZH' }}</button><a :href="`/?lang=${locale}&v=0.22.0-rc.1`">{{ c.returnSite }} ↗</a></div></header>
    <p v-if="!ready" class="review-loading" role="status">{{ error || `${c.reviewLoading} ${loading}%` }}</p>
    <aside class="review-controls">
      <div class="review-row"><label>{{ c.reviewSelect }} <select v-model.number="selected" :aria-label="c.reviewSelect"><option v-for="(shot,i) in shots" :key="i" :value="i">{{ shot.name }}</option></select></label><div class="review-angles"><button v-for="view in angles" :key="view.id" :aria-pressed="angle===view.id" @click="angle=view.id">{{ view.label }}</button></div></div>
      <div class="review-play"><button :disabled="!ready" @click="playing=!playing">{{playing?c.pause:c.reviewPlay}}</button><button :disabled="!ready" @click="seek(0)">{{ c.reviewNav }}</button><button :disabled="!ready" @click="seek(1)">{{ c.reviewScm }}</button><output>{{Math.round(deployment*100)}}%</output></div>
      <input type="range" min="0" max="1" step="0.001" :value="deployment" :aria-label="c.reviewProgress" :disabled="!ready" @input="scrub" />
      <p>{{ c.controlsHint }}</p>
    </aside>
  </main>
</template>

<style scoped>
.articulation-review { position: fixed; inset: 0; background: var(--viewport); color: var(--text); z-index: 100; }
.articulation-review canvas { width: 100%; height: 100%; display: block; touch-action: none; }
.articulation-review header { position: absolute; inset: 24px 28px auto; display: flex; justify-content: space-between; align-items: center; pointer-events: none; padding: 15px 20px; border: 1px solid var(--ink-line); background: var(--panel); }
.articulation-review header a { pointer-events: auto; font-size: 12px; min-height: 44px; display: flex; align-items: center; }
.review-kicker { font: 9px var(--mono); letter-spacing: .09em; }
.review-header-actions { display: flex; align-items: center; gap: 20px; pointer-events: auto; }
.review-header-actions button { min-height: 44px; min-width: 44px; font: 10px var(--mono); border: 1px solid var(--line); }
.articulation-review h1 { font-size: 21px; margin: 7px 0 0; font-weight: 500; }
.articulation-review small { font: 10px var(--mono); color: var(--muted); margin-left: 8px; }
.review-controls { position: absolute; bottom: 22px; left: 50%; transform: translateX(-50%); width: min(760px, 94vw); padding: 20px 24px 13px; background: var(--panel); border: 1px solid var(--ink-line); }
.review-controls::before { content: ""; position: absolute; top: 5px; left: 5px; width: 5px; height: 5px; border: 1px solid #7b7c70; border-radius: 50%; background: #c9c4b8; }
.review-row, .review-play { display: flex; align-items: center; gap: 12px; justify-content: space-between; }
.review-row label { font-size: 12px; }
.review-row select { margin-left: 10px; padding: 9px; min-height: 40px; background: var(--bg); color: var(--text); border: 1px solid var(--ink-line); max-width: 280px; }
.review-angles { display: flex; gap: 5px; }
.review-controls button { border: 1px solid var(--ink-line); padding: 10px 13px; min-height: 40px; color: var(--text); background: var(--panel); cursor: pointer; font-size: 12px; }
.review-controls button:hover, .review-controls button[aria-pressed=true] { color: var(--panel); background: var(--text); }
.review-controls button:disabled { opacity: .45; }
.review-play { margin-top: 14px; gap: 8px; justify-content: start; }
.review-play button:first-child { background: var(--accent); border-color: #b12c21; color: #fff9f0; }
.review-play output { margin-left: auto; font: 12px var(--mono); }
.review-controls input { width: 100%; accent-color: var(--accent); margin: 14px 0 8px; touch-action: none; }
.review-controls p { font-size: 10px; color: var(--muted); margin: 2px 0; }
.review-loading { position: absolute; left: 50%; top: 45%; transform: translateX(-50%); padding: 18px; background: var(--panel); border: 1px solid var(--ink-line); }
@media (max-width: 620px) {
  .articulation-review header { inset: 15px; padding: 12px; }
  .articulation-review header a { font-size: 10px; }
  .articulation-review h1 { font-size: 18px; }
  .review-controls { padding: 15px; }
  .review-row { align-items: start; flex-direction: column; }
  .review-play { flex-wrap: wrap; }
  .review-row select { max-width: 220px; }
}
</style>
