<script setup lang="ts">
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { createOdinRig } from '~/lib/odin-rig'

type Shot = { name: string; point: [number, number, number]; view: [number, number, number]; width: number }
const shots: Shot[] = [
  { name: '单联装 · 舰艏', point: [0,258,40], view: [1,1,.7], width: .72 },
  { name: '单联装 · 舰艏接缝', point: [0,247,39], view: [2,-.35,.3], width: .3 },
  { name: '单联装 · 舰艉', point: [0,-248,52], view: [1,-1,.7], width: .72 },
  { name: '单联装 · 舰腹', point: [0,-58,-64], view: [1,-1,-.7], width: .95 },
  ...(['右舷','左舷'] as const).flatMap((side, i) => {
    const sign = i ? -1 : 1
    return [[74,86,4],[55,16,30],[61,0,-28],[68,-170,29]].map((p, n) => ({ name: `单联装 · ${side} ${n+1}`, point: [sign*p[0]!,p[1]!,p[2]!] as [number,number,number], view: [sign*2,1,n===2?-.7:.7] as [number,number,number], width: .72 }))
  }),
  { name: '四联装 · 右舷', point: [43,-62,106], view: [1,1,.6], width: .6 },
  { name: '四联装 · 左舷', point: [-43,-62,106], view: [-1,1,.6], width: .6 },
  ...([[ -22,-36,53],[-28,-64,53],[22,-36,53],[28,-64,53],[21,-179,43],[14,-221,43],[-21,-179,43],[-14,-221,43]]).map((p,i) => ({ name: `双联装 · ${i+1}${i>=4?' / 船壳盖板':''}`, point: p as [number,number,number], view: [Math.sign(p[0]!)*1.5,1,.6] as [number,number,number], width: .5 })),
  { name: '舰桥 · 前部', point: [0,-27,128], view: [1,2,.5], width: .66 },
  { name: '舰桥 · 后部', point: [0,-43,128], view: [1,-2,.5], width: .7 },
  { name: '舰桥 · 底部涂装', point: [0,-82,68], view: [2,1,.35], width: 1.65 },
  { name: '主炮 · 船体接缝', point: [11.5,117,40], view: [2,0,.2], width: .25 },
  { name: '舰桥 · 雷达与桁架', point: [0,-50,119], view: [1,-1,.55], width: 1.05 },
  { name: '舰桥 · 下层玻璃', point: [0,-24,91], view: [1,3,.4], width: .4 },
  { name: '主炮 · 上方五块护甲', point: [0,124,45], view: [1,1,.8], width: 1.2 },
  { name: '主炮 · 下方五块护甲', point: [0,76,-56], view: [1,1,-.8], width: 1.2 },
]
const canvas = ref<HTMLCanvasElement>(), selected = ref(0), angle = ref('斜视')
const deployment = ref(0), playing = ref(false), loading = ref(0), ready = ref(false), error = ref('')
let focus: (() => void) | undefined, cleanup: (() => void) | undefined, disposed = false, cycle = 0
watch([selected,angle], () => focus?.())
function seek(value: number) { deployment.value=value; playing.value=false; cycle=value*3 }
function scrub(event: Event) { seek(Number((event.target as HTMLInputElement).value)) }
onMounted(async () => {
  const el = canvas.value!
  const renderer = new THREE.WebGLRenderer({ canvas: el, antialias: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.outputColorSpace=THREE.SRGBColorSpace
  renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1
  const scene = new THREE.Scene(); scene.background=new THREE.Color('#1b222a')
  const camera=new THREE.OrthographicCamera(-1,1,1,-1,.001,50)
  const controls=new OrbitControls(camera,el); controls.enableDamping=true; controls.dampingFactor=.08; controls.minZoom=.15; controls.maxZoom=12
  controls.mouseButtons={LEFT:THREE.MOUSE.ROTATE,MIDDLE:THREE.MOUSE.DOLLY,RIGHT:THREE.MOUSE.PAN}
  const pmrem=new THREE.PMREMGenerator(renderer), room=new RoomEnvironment(), env=pmrem.fromScene(room,.15)
  scene.environment=env.texture; scene.environmentIntensity=.38; room.dispose();pmrem.dispose()
  scene.add(new THREE.HemisphereLight(0xc9d1da,0x45434a,.8))
  const key=new THREE.DirectionalLight(0xfff3e6,2.4); key.position.set(4,7,-4);scene.add(key)
  const fill=new THREE.DirectionalLight(0xb7c7df,.9);fill.position.set(-5,2,1);scene.add(fill)
  const rear=new THREE.DirectionalLight(0xd7cbb9,.55);rear.position.set(3,-1.3,4);scene.add(rear)
  const draco=new DRACOLoader().setDecoderPath('/draco/').setWorkerLimit(2)
  const loader=new GLTFLoader().setDRACOLoader(draco)
  let frame=0, observer: ResizeObserver | undefined, previous=performance.now(), elapsed=20
  const map=([x,y,z]: number[])=>new THREE.Vector3(x,z,-y)
  function resize() {
    const box=el.getBoundingClientRect(), w=box.width, h=box.height
    renderer.setSize(w,h,false)
    const width=shots[selected.value]!.width
    camera.left=-width/2;camera.right=width/2;camera.top=width*h/w/2;camera.bottom=-camera.top;camera.updateProjectionMatrix()
  }
  focus=()=>{
    const shot=shots[selected.value]!, p=map(shot.point).multiplyScalar(.01)
    const offset=angle.value==='侧视'?[Math.sign(shot.view[0])||1,0,0]:angle.value==='俯视'?[0,0,shot.point[2]<0?-1:1]:shot.view
    camera.up.set(0,1,0)
    if(angle.value==='俯视')camera.up.set(0,0,-1)
    camera.position.copy(p).add(map(offset).normalize().multiplyScalar(2))
    controls.target.copy(p);camera.zoom=1;camera.lookAt(p);controls.update();resize()
  }
  cleanup=()=>{
    cancelAnimationFrame(frame);observer?.disconnect();controls.dispose();draco.dispose();env.dispose()
    const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>(),textures=new Set<THREE.Texture>()
    scene.traverse(o=>{if(o instanceof THREE.Mesh){geometries.add(o.geometry);(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m))}})
    geometries.forEach(g=>g.dispose());materials.forEach(m=>{Object.values(m).forEach(v=>{if(v instanceof THREE.Texture)textures.add(v)});m.dispose()});textures.forEach(t=>t.dispose());renderer.dispose()
  }
  try {
    const gltf=await loader.loadAsync('/models/odin.glb?v=0.11.15-rc.1',e=>{loading.value=e.total?Math.round(e.loaded/e.total*100):30})
    scene.add(gltf.scene)
    if(disposed){cleanup();return}
    const rig=createOdinRig(gltf.scene)
    gltf.scene.traverse(o=>{if(o instanceof THREE.Mesh)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>{if(m instanceof THREE.MeshStandardMaterial&&m.map)m.map.anisotropy=renderer.capabilities.getMaxAnisotropy()})})
    observer=new ResizeObserver(resize);observer.observe(el);focus();ready.value=true
    function render(now: number) {
      frame=requestAnimationFrame(render);const dt=Math.min((now-previous)/1000,.05);previous=now
      if(document.hidden)return
      if(playing.value){elapsed+=dt;cycle=(cycle+dt)%8;deployment.value=cycle<3?cycle/3:cycle<4?1:cycle<7?1-(cycle-4)/3:0}
      rig.apply(deployment.value,elapsed);controls.update();renderer.render(scene,camera)
      el.dataset.ready='true';el.dataset.deployment=deployment.value.toFixed(3);el.dataset.station=shots[selected.value]!.name;el.dataset.joints=String(rig.jointCount)
    }
    frame=requestAnimationFrame(render)
  }catch(e){error.value=e instanceof Error?e.message:String(e);cleanup()}
})
onBeforeUnmount(()=>{disposed=true;cleanup?.()})
</script>

<template>
  <main class="articulation-review">
    <canvas ref="canvas" aria-label="奥丁武备动画预览，左键旋转、右键平移、滚轮缩放" />
    <header><div><span class="review-kicker">ODIN / ARTICULATION REVIEW</span><h1>武备与舰桥 <small>v0.11.15</small></h1></div><a href="/">返回舰船展示 ↗</a></header>
    <p v-if="!ready" class="review-loading" role="status">{{ error || `正在载入高精度模型 ${loading}%` }}</p>
    <aside class="review-controls">
      <div class="review-row"><label>查看部位 <select v-model.number="selected" aria-label="查看部位"><option v-for="(shot,i) in shots" :key="shot.name" :value="i">{{ shot.name }}</option></select></label><div class="review-angles"><button v-for="view in ['斜视','侧视','俯视']" :key="view" :aria-pressed="angle===view" @click="angle=view">{{ view }}</button></div></div>
      <div class="review-play"><button :disabled="!ready" @click="playing=!playing">{{playing?'暂停':'播放展开 / 收回'}}</button><button :disabled="!ready" @click="seek(0)">NAV / 完全收起</button><button :disabled="!ready" @click="seek(1)">SCM / 完全展开</button><output>{{Math.round(deployment*100)}}%</output></div>
      <input type="range" min="0" max="1" step="0.001" :value="deployment" aria-label="武备展开进度" :disabled="!ready" @input="scrub" />
      <p>左键旋转 · 右键平移 · 滚轮缩放</p>
    </aside>
  </main>
</template>

<style scoped>
.articulation-review{position:fixed;inset:0;background:#1b222a;color:#e9edf0;z-index:100}.articulation-review canvas{width:100%;height:100%;display:block;touch-action:none}.articulation-review header{position:absolute;inset:28px 36px auto;display:flex;justify-content:space-between;pointer-events:none}.articulation-review header a{pointer-events:auto;color:#d3d9df;font-size:13px}.review-kicker{font-size:10px;letter-spacing:.25em;color:#c39775}.articulation-review h1{font-size:24px;margin:8px 0;font-weight:500}.articulation-review small{font-size:12px;color:#909ca7;margin-left:8px}.review-controls{position:absolute;bottom:22px;left:50%;transform:translateX(-50%);width:min(720px,94vw);padding:18px 24px 10px;background:#10171ee8;border:1px solid #3a4651;backdrop-filter:blur(12px)}.review-row,.review-play{display:flex;align-items:center;gap:12px;justify-content:space-between}.review-row label{font-size:12px;color:#a7b1bb}.review-row select{margin-left:10px;padding:8px;background:#202a33;color:#edf1f4;border:1px solid #4d5964;max-width:260px}.review-angles{display:flex;gap:5px}.review-controls button{border:1px solid #49535b;padding:8px 12px;color:#d9e0e4;background:#18222c;cursor:pointer;font-size:12px}.review-controls button[aria-pressed=true]{border-color:#ce7547;color:#fff}.review-controls button:disabled{opacity:.45}.review-play{margin-top:15px;gap:8px;justify-content:start}.review-play output{margin-left:auto;color:#bdc9d4;font:12px monospace}.review-controls input{width:100%;accent-color:#d27a4b;margin:15px 0 4px}.review-controls p{font-size:11px;color:#80909e;margin:2px 0}.review-loading{position:absolute;left:50%;top:45%;transform:translateX(-50%)}@media(max-width:620px){.articulation-review header{inset:20px}.review-controls{padding:12px}.review-row{align-items:start;flex-direction:column}.review-play{flex-wrap:wrap}.review-row select{max-width:220px}}
</style>
