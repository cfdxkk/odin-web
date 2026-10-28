<script setup lang="ts">
import { isPlaying, nextPlayback } from '~/lib/odin-motion'
import {
  AWAKENING_DURATION,
  AWAKENING_CHAPTERS,
  sampleAwakeningFilm,
  shouldAdvanceFilm,
  clampFilmTime,
} from '~/lib/awakening-film'
import { ATLAS_MODES, ATLAS_SOURCE } from '~/lib/atlas-content'
import type { AtlasMode } from '~/lib/atlas-viewer-state'
const started = ref(false),
  time = ref(0),
  inspect = ref(false),
  focus = ref<AtlasMode>('overview')
const deployment = ref(0),
  spectral = ref(false),
  ready = ref(false),
  progress = ref(0),
  error = ref('')
const reducedMotion = ref(false),
  visible = ref(true),
  sceneKey = ref(0)
const motionOptIn = ref(false)
const effectiveReducedMotion = computed(
  () => reducedMotion.value && !motionOptIn.value,
)
const playback = ref({ userPaused: false, scrubbing: false })
const playing = computed(() => isPlaying(playback.value))
const pointer = ref({ x: 0, y: 0 })
const viewer = ref<{ resetView(): void; capturePhoto(): Promise<Blob> }>()
const chapters = AWAKENING_CHAPTERS
const sample = computed(() => sampleAwakeningFilm(time.value))
const currentChapter = computed(() => chapters[sample.value.chapter]!)
const currentFocus = computed(
  () => ATLAS_MODES.find((item) => item.id === focus.value)!,
)
const filmProgress = computed(() => (time.value / AWAKENING_DURATION) * 100)
const clock = computed(
  () =>
    `${String(Math.floor(time.value / 60)).padStart(2, '0')}:${String(Math.floor(time.value % 60)).padStart(2, '0')}`,
)
const ended = computed(() => time.value >= AWAKENING_DURATION)
const overlay = ref<'interior' | 'archive' | 'about' | null>(null)
const modal = ref<HTMLDialogElement>(),
  slideIndex = ref(0),
  slideDirection = ref(1)
const photoStatus = ref(''),
  capturing = ref(false)
const fullscreen = ref(false)
const memories = [
  {
    src: '/images/odin-interiors/hangar-cargo-deck.webp',
    title: '归航，亦是序章。',
    en: 'THE HANGAR',
    text: '中央机库与六座侧机库相连，容纳每一次归航，也准备下一次出发。',
    source: 'https://media.robertsspaceindustries.com/d8q6m2h9ecdeo/source.jpg',
  },
  {
    src: '/images/odin-interiors/briefing-room.webp',
    title: '共享一个坐标。',
    en: 'THE BRIEFING ROOM',
    text: '共同的意图，在这里成为行动。属于船员的简报与集合空间。',
    source: 'https://media.robertsspaceindustries.com/seyogl9pfjzgz/source.jpg',
  },
  {
    src: '/images/official/v0.13.0/17-sc-anvil-odin-interior-7.webp',
    title: '钢铁之中，人的尺度。',
    en: 'LIFE WITHIN',
    text: '穿过巨舰内部的结构与通道，重新感知这座移动基地的体量。',
    source: ATLAS_SOURCE,
  },
  {
    src: '/images/official/v0.13.0/16-sc-anvil-odin-interior-9.webp',
    title: '一双手，唤醒庞然之躯。',
    en: 'THE HUMAN ELEMENT',
    text: '每一项系统，最终都与操控它的人相连。',
    source: ATLAS_SOURCE,
  },
]
const archives = [
  {
    src: '/images/official/v0.13.0/27-sc-anvil-odin-exterior-5.webp',
    title: '停泊，是另一种威慑。',
    en: 'AT BERTH',
    text: '空间站之间，奥丁的完整侧影。',
    source: ATLAS_SOURCE,
  },
  {
    src: '/images/official/v0.13.0/06-sc-anvil-odin-exterior-7.webp',
    title: '于深空之中，显现全貌。',
    en: 'THE ENTIRETY',
    text: '甲板、机库与武备，共同勾勒出全舰轮廓。',
    source: ATLAS_SOURCE,
  },
  {
    src: '/images/official/v0.13.0/13-sc-anvil-odin-exterior-3.webp',
    title: '天际线，被重新划定。',
    en: 'BEYOND THE HORIZON',
    text: '行星弧光之上，驶向交锋之处。',
    source: ATLAS_SOURCE,
  },
  {
    src: '/images/official/v0.13.0/20-sc-anvil-odin-exterior-4.webp',
    title: '雷霆之后，继续向前。',
    en: 'FORWARD, ALWAYS',
    text: '推进阵列与交错火线，将舰影延伸至深空。',
    source: ATLAS_SOURCE,
  },
]
const slides = computed(() =>
  overlay.value === 'interior' ? memories : archives,
)
const slide = computed(() => slides.value[slideIndex.value]!)
const number = (n: number) => String(n + 1).padStart(2, '0')
let raf = 0,
  last = 0,
  cleanup = () => {}
let soundContext: AudioContext | undefined, soundGain: GainNode | undefined
const sound = ref(false)
const soundNodes: AudioNode[] = []
function startFilm() {
  started.value = true
  inspect.value = false
  time.value = 0
  motionOptIn.value = true
  playback.value = { userPaused: false, scrubbing: false }
}
function togglePlay() {
  if (ended.value && !inspect.value) return startFilm()
  if (playback.value.userPaused) motionOptIn.value = true
  playback.value = nextPlayback(playback.value, 'toggle')
}
function seek(value: number) {
  started.value = true
  time.value = clampFilmTime(value)
}
function chooseChapter(index: number) {
  inspect.value = false
  seek(chapters[index]!.start)
}
function beginScrub(event: PointerEvent) {
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  playback.value = nextPlayback(playback.value, 'scrub-start')
}
function endScrub() {
  playback.value = nextPlayback(playback.value, 'scrub-end')
}
function keyScrub(event: KeyboardEvent) {
  if (
    [
      'ArrowLeft',
      'ArrowRight',
      'ArrowUp',
      'ArrowDown',
      'Home',
      'End',
      'PageUp',
      'PageDown',
    ].includes(event.key)
  )
    playback.value = nextPlayback(playback.value, 'scrub-start')
}
function onTimeline(event: Event) {
  seek(Number((event.target as HTMLInputElement).value))
}
function onDeployment(event: Event) {
  deployment.value = Number((event.target as HTMLInputElement).value)
}
function toggleInspect() {
  inspect.value = !inspect.value
  if (inspect.value) deployment.value = sample.value.deployment
}
function returnPrelude() {
  started.value = false
  inspect.value = false
  time.value = 0
}
function chooseFocus(value: AtlasMode) {
  focus.value = value
  deployment.value = ['main', 'secondary', 'defense', 'bridge'].includes(value)
    ? 1
    : 0
}
function onPointer(event: PointerEvent) {
  if (event.pointerType !== 'touch')
    pointer.value = {
      x: (event.clientX / window.innerWidth) * 2 - 1,
      y: (event.clientY / window.innerHeight) * 2 - 1,
    }
}
function failScene(message: string) {
  error.value = message
  ready.value = false
}
function retryScene() {
  error.value = ''
  ready.value = false
  progress.value = 0
  sceneKey.value++
}
async function openOverlay(value: 'interior' | 'archive' | 'about') {
  overlay.value = value
  slideIndex.value = 0
  await nextTick()
  modal.value?.showModal()
}
function closeOverlay() {
  modal.value?.close()
  overlay.value = null
}
function turnSlide(direction: number) {
  slideDirection.value = direction
  slideIndex.value =
    (slideIndex.value + direction + slides.value.length) % slides.value.length
}
function dialogKey(event: KeyboardEvent) {
  if (overlay.value === 'about') return
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    turnSlide(1)
  }
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    turnSlide(-1)
  }
}
async function takePhoto() {
  if (!viewer.value || capturing.value) return
  capturing.value = true
  try {
    const blob = await viewer.value.capturePhoto(),
      url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ODIN-AWAKENING-${Math.floor(time.value)}.png`
    a.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 3000)
    photoStatus.value = '画面已保存'
  } catch {
    photoStatus.value = '暂时无法保存，请重试'
  } finally {
    capturing.value = false
    window.setTimeout(() => {
      photoStatus.value = ''
    }, 3000)
  }
}
async function toggleSound() {
  if (!soundContext) {
    try {
      soundContext = new AudioContext()
      soundGain = soundContext.createGain()
      soundGain.gain.value = 0
      soundGain.connect(soundContext.destination)
      // Original quiet procedural drone; only enabled by this explicit gesture.
      for (const [hz, amplitude] of [
        [43.65, 0.16],
        [65.41, 0.07],
        [130.81, 0.025],
      ]) {
        const oscillator = soundContext.createOscillator(),
          gain = soundContext.createGain()
        oscillator.type = 'sine'
        oscillator.frequency.value = hz!
        gain.gain.value = amplitude!
        oscillator.connect(gain)
        gain.connect(soundGain)
        oscillator.start()
        soundNodes.push(oscillator, gain)
      }
    } catch {
      photoStatus.value = '当前浏览器不支持声音'
      return
    }
  }
  await soundContext.resume()
  sound.value = !sound.value
  syncSound()
}
function syncSound() {
  if (!soundContext || !soundGain) return
  const audible =
    sound.value && playing.value && visible.value && !overlay.value
  soundGain.gain.setTargetAtTime(
    audible ? 0.55 + sample.value.energy * 0.3 : 0,
    soundContext.currentTime,
    0.35,
  )
}
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await document.documentElement.requestFullscreen()
  } catch {
    photoStatus.value = '当前浏览器暂不支持全屏'
  }
}
watch([playing, visible, overlay, sound], syncSound)
onMounted(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion.value = motion.matches
  if (motion.matches) playback.value.userPaused = true
  const visibility = () => {
    visible.value = !document.hidden
    last = 0
    if (!visible.value) endScrub()
  }
  const syncFullscreen = () => {
    fullscreen.value = !!document.fullscreenElement
  }
  const changeMotion = () => {
    reducedMotion.value = motion.matches
    motionOptIn.value = false
  }
  const key = (event: KeyboardEvent) => {
    if (
      overlay.value ||
      /INPUT|TEXTAREA|BUTTON|A/.test((event.target as HTMLElement)?.tagName)
    )
      return
    if (event.code === 'Space' && ready.value) {
      event.preventDefault()
      togglePlay()
    }
    if (event.key.toLowerCase() === 'i' && ready.value) toggleInspect()
    if (started.value && !inspect.value && event.key === 'ArrowRight')
      seek(time.value + 5)
    if (started.value && !inspect.value && event.key === 'ArrowLeft')
      seek(time.value - 5)
  }
  const frame = (now: number) => {
    const dt = last ? Math.min((now - last) / 1000, 0.08) : 0
    last = now
    if (
      ready.value &&
      shouldAdvanceFilm({
        ...playback.value,
        visible: visible.value,
        overlayOpen: !!overlay.value,
        inspect: inspect.value,
        reducedMotion: effectiveReducedMotion.value,
        started: started.value,
      })
    )
      time.value = clampFilmTime(time.value + dt)
    raf = requestAnimationFrame(frame)
  }
  raf = requestAnimationFrame(frame)
  document.addEventListener('visibilitychange', visibility)
  document.addEventListener('fullscreenchange', syncFullscreen)
  window.addEventListener('keydown', key)
  motion.addEventListener('change', changeMotion)
  window.addEventListener('pointerup', endScrub)
  window.addEventListener('pointercancel', endScrub)
  window.addEventListener('blur', endScrub)
  cleanup = () => {
    document.removeEventListener('visibilitychange', visibility)
    document.removeEventListener('fullscreenchange', syncFullscreen)
    window.removeEventListener('keydown', key)
    motion.removeEventListener('change', changeMotion)
    window.removeEventListener('pointerup', endScrub)
    window.removeEventListener('pointercancel', endScrub)
    window.removeEventListener('blur', endScrub)
  }
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  cleanup()
  soundNodes.forEach((node) => node.disconnect())
  void soundContext?.close()
})
</script>

<template>
  <main
    class="awakening"
    :class="{
      'is-started': started,
      'is-inspecting': inspect,
      'is-paused': !playing || !visible || !!overlay,
      'is-ready': ready,
      'is-reduced': effectiveReducedMotion,
      'is-spectral': spectral,
    }"
    :style="{
      '--film-progress': `${filmProgress}%`,
      '--pointer-x': pointer.x,
      '--pointer-y': pointer.y,
    }"
    @pointermove="onPointer"
  >
    <div class="stage-ground" aria-hidden="true" />
    <div class="monument" aria-hidden="true">ODIN</div>
    <div class="scene-host">
      <ClientOnly
        ><AwakeningScene
          v-if="!error"
          :key="sceneKey"
          ref="viewer"
          :time="time"
          :playing="playing"
          :started="started"
          :inspect="inspect"
          :focus="focus"
          :deployment="deployment"
          :active="visible && !overlay"
          :reduced-motion="effectiveReducedMotion"
          :spectral="spectral"
          :pointer="pointer"
          @ready="ready = true"
          @progress="progress = $event"
          @fail="failScene"
      /></ClientOnly>
    </div>
    <div class="stage-shade" aria-hidden="true" />
    <div class="film-grain" aria-hidden="true" />
    <div class="edge-caption edge-caption-left" aria-hidden="true">
      ANVIL AEROSPACE — ODIN CLASS
    </div>
    <div class="edge-caption edge-caption-right" aria-hidden="true">
      A STUDY OF POWER / 2026
    </div>
    <header class="site-header">
      <button class="brand" aria-label="返回序幕" @click="returnPrelude">
        <svg
          class="brand-mark"
          viewBox="0 0 40 40"
          fill="none"
          aria-hidden="true"
        >
          <path d="M20 2 37 12v16L20 38 3 28V12Z" stroke="currentColor" />
          <path
            d="m12 10 8 9 8-9M20 19v14M10 27l10-8 10 8"
            stroke="currentColor"
            stroke-width="2"
          /></svg
        ><span>ODIN<small>AWAKENING</small></span>
      </button>
      <p class="header-center">AN UNOFFICIAL STAR CITIZEN EXPERIENCE</p>
      <nav aria-label="影像与资料">
        <button @click="openOverlay('interior')">
          舰内记忆 <span>↗</span></button
        ><button @click="openOverlay('archive')">
          概念影像 <span>↗</span></button
        ><button
          class="about-button"
          aria-label="关于这个作品"
          @click="openOverlay('about')"
        >
          i
        </button>
      </nav>
    </header>
    <Transition name="veil" mode="out-in">
      <section v-if="!started && !inspect" key="prologue" class="prologue">
        <p class="eyebrow">
          <span class="signal-dot" /> TRANSMISSION 001 / THE AWAKENING
        </p>
        <h1>WAKE<br /><span>THE GOD.</span></h1>
        <p class="prologue-line">沉默，是雷霆的前奏。</p>
        <p class="prologue-description">
          一场关于力量与尺度的深空仪式。<br />唤醒奥丁，穿越它的钢铁之躯。
        </p>
        <button class="awaken-button" :disabled="!ready" @click="startFilm">
          <span class="awaken-orbit" aria-hidden="true"
            ><svg viewBox="0 0 48 48">
              <path d="m20 16 12 8-12 8Z" fill="currentColor" /></svg></span
          ><span
            >{{ ready ? '开始唤醒' : '信号接入中'
            }}<small>{{
              ready
                ? 'ENTER THE EXPERIENCE · 72 SEC'
                : `${Math.round(progress)}% / ESTABLISHING UPLINK`
            }}</small></span
          ><span class="button-arrow" aria-hidden="true">↗</span>
        </button>
      </section>
      <section v-else-if="inspect" key="inspection" class="inspection-panel">
        <p class="eyebrow">FREE EXPLORATION / 自由观察</p>
        <h1>触碰<br />钢铁之躯<span>.</span></h1>
        <div class="focus-list" role="group" aria-label="观察部位">
          <button
            v-for="(item, index) in ATLAS_MODES"
            :key="item.id"
            :aria-pressed="focus === item.id"
            @click="chooseFocus(item.id)"
          >
            <span>{{ number(index) }}</span
            >{{ item.label }}<b aria-hidden="true">↗</b>
          </button>
        </div>
        <p class="focus-detail">{{ currentFocus.detail }}</p>
        <label class="deployment-control"
          ><span
            >武备展开 <b>{{ Math.round(deployment * 100) }}%</b></span
          ><input
            aria-label="武备展开程度"
            type="range"
            min="0"
            max="1"
            step="0.001"
            :value="deployment"
            @input="onDeployment"
            @pointerdown="beginScrub"
            @pointerup="endScrub"
            @pointercancel="endScrub"
            @lostpointercapture="endScrub"
            @blur="endScrub"
            @keydown="keyScrub"
            @keyup="endScrub"
        /></label>
        <p class="gesture-note">拖动旋转 · 滚轮靠近 · 右键平移</p>
      </section>
      <section
        v-else-if="!ended"
        :key="`chapter-${sample.chapter}`"
        class="chapter-caption"
        aria-live="polite"
      >
        <p class="eyebrow">
          ACT {{ number(sample.chapter) }} / {{ currentChapter.en }}
        </p>
        <h1>{{ currentChapter.title }}<span>.</span></h1>
        <p>{{ currentChapter.line }}</p>
        <span class="chapter-large-number" aria-hidden="true">{{
          number(sample.chapter)
        }}</span>
      </section>
    </Transition>
    <div v-if="error" class="scene-error" role="alert">
      <p>信号暂时中断</p>
      <span>{{ error }}</span
      ><button @click="retryScene">重新接入 ↗</button>
    </div>
    <div v-if="started && ended && !inspect" class="film-ending">
      <p>THE GOD IS AWAKE.</p>
      <h2>雷霆，已被唤醒。</h2>
      <button @click="startFilm">再次演出 ↺</button
      ><button @click="toggleInspect">亲手探索 ↗</button>
    </div>
    <div class="scene-tools" aria-label="场景工具">
      <button
        :disabled="!ready"
        :aria-pressed="spectral"
        @click="spectral = !spectral"
      >
        <span class="tool-icon" aria-hidden="true">⌖</span
        >{{ spectral ? '实体视界' : '光谱视界' }}
      </button>
      <button :disabled="!ready" :aria-pressed="inspect" @click="toggleInspect">
        <span class="tool-icon" aria-hidden="true">{{
          inspect ? '▷' : '◎'
        }}</span
        >{{ inspect ? '返回演出' : '自由观察' }}
      </button>
      <button v-if="inspect" :disabled="!ready" @click="viewer?.resetView()">
        <span class="tool-icon" aria-hidden="true">↺</span>复位镜头
      </button>
      <button :disabled="!ready || capturing" @click="takePhoto">
        <span class="tool-icon" aria-hidden="true">⊞</span
        >{{ capturing ? '保存中' : '保存此刻' }}
      </button>
      <button :aria-pressed="fullscreen" @click="toggleFullscreen">
        <span class="tool-icon" aria-hidden="true">⛶</span
        >{{ fullscreen ? '退出全屏' : '进入全屏' }}
      </button>
    </div>
    <footer class="stage-footer">
      <div class="transport-row">
        <div class="transport-controls">
          <button
            class="play-toggle"
            :disabled="!ready"
            :aria-label="playing ? '暂停演出' : '继续演出'"
            @click="togglePlay"
          >
            <span aria-hidden="true">{{ playing ? 'Ⅱ' : '▷' }}</span></button
          ><button
            class="sound-toggle"
            :aria-pressed="sound"
            :aria-label="sound ? '关闭氛围音' : '开启氛围音'"
            @click="toggleSound"
          >
            <span
              class="sound-bars"
              :class="{ enabled: sound }"
              aria-hidden="true"
              ><i /><i /><i /><i /><i /></span
            ><span>SOUND {{ sound ? 'ON' : 'OFF' }}</span>
          </button>
        </div>
        <span class="transport-hint">{{
          inspect
            ? 'DRAG TO EXPLORE'
            : started
              ? playing
                ? '让视线，跟随雷霆。'
                : '时间，停在此刻。'
              : '建议全屏 · 开启声音 · 进入深空'
        }}</span
        ><span class="timecode">{{ clock }} <span>/ 01:12</span></span>
      </div>
      <div class="film-timeline">
        <div class="timeline-track" aria-hidden="true"><i /></div>
        <input
          aria-label="演出时间"
          type="range"
          min="0"
          :max="AWAKENING_DURATION"
          step="0.05"
          :value="time"
          :disabled="!ready || inspect"
          @input="onTimeline"
          @pointerdown="beginScrub"
          @pointerup="endScrub"
          @pointercancel="endScrub"
          @lostpointercapture="endScrub"
          @blur="endScrub"
          @keydown="keyScrub"
          @keyup="endScrub"
        />
        <div class="chapter-navigation" role="group" aria-label="演出章节">
          <button
            v-for="(chapter, index) in chapters"
            :key="chapter.id"
            :disabled="!ready"
            :class="{
              current: started && !inspect && sample.chapter === index,
            }"
            :aria-current="
              started && !inspect && sample.chapter === index
                ? 'step'
                : undefined
            "
            @click="chooseChapter(index)"
          >
            <span>{{ number(index) }}</span
            ><b>{{ chapter.title }}</b
            ><small>{{ chapter.en }}</small
            ><i aria-hidden="true">↗</i>
          </button>
        </div>
      </div>
      <div class="colophon">
        <span>ODIN — A DIGITAL RITUAL</span
        ><span>FAN ART / CONCEPT VESSEL</span>
      </div>
    </footer>
    <p class="status-toast" role="status">{{ photoStatus }}</p>
    <dialog
      ref="modal"
      class="memory-dialog"
      :class="{ 'is-about': overlay === 'about' }"
      @cancel.prevent="closeOverlay"
      @close="overlay = null"
      @keydown="dialogKey"
    >
      <header class="memory-header">
        <span>{{
          overlay === 'interior'
            ? 'INNER WORLDS / 舰内记忆'
            : overlay === 'archive'
              ? 'VISUAL ARCHIVE / 概念影像'
              : 'ABOUT THE EXPERIENCE'
        }}</span
        ><button autofocus aria-label="关闭影像空间" @click="closeOverlay">
          <span>返回深空</span> ×
        </button>
      </header>
      <div v-if="overlay === 'about'" class="about-content">
        <p class="eyebrow">A DIGITAL TRIBUTE</p>
        <h2>以雷霆之名。<br />向想象力致意。</h2>
        <p>
          ODIN AWAKENING
          是以奥丁战列巡洋舰为主题的非官方互动艺术作品。舰船模型以实时光影、程序动画与原创氛围音重新演绎；日蚀、扫描与跃迁效果为艺术化表达。
        </p>
        <p>
          官方概念影像与 Star Citizen、Anvil Aerospace 相关内容归 Cloud Imperium
          Games / Roberts Space Industries
          所有。舰船配置仍处概念阶段，以官方最终发布为准。
        </p>
        <a :href="ATLAS_SOURCE" target="_blank" rel="noopener noreferrer"
          >查看官方奥丁概念资料 ↗</a
        ><span>DESIGNED FOR CURIOSITY. BUILT FOR AWE.</span>
      </div>
      <template v-else-if="overlay"
        ><div
          class="memory-stage"
          :class="{ 'is-interior': overlay === 'interior' }"
          :style="{ '--slide-direction': slideDirection }"
        >
          <Transition name="memory" mode="out-in"
            ><figure :key="`${overlay}-${slideIndex}`">
              <img :src="slide.src" :alt="slide.title" draggable="false" />
              <figcaption>
                <span class="eyebrow">{{ slide.en }}</span>
                <h2>{{ slide.title }}</h2>
                <p>{{ slide.text }}</p>
              </figcaption>
            </figure></Transition
          ><span class="memory-watermark" aria-hidden="true">{{
            number(slideIndex)
          }}</span>
        </div>
        <footer class="memory-footer">
          <div class="memory-pagination">
            <button aria-label="上一张影像" @click="turnSlide(-1)">←</button
            ><span
              >{{ number(slideIndex) }}
              <i>/ {{ number(slides.length - 1) }}</i></span
            ><button aria-label="下一张影像" @click="turnSlide(1)">→</button>
          </div>
          <div class="memory-ticks">
            <button
              v-for="(item, index) in slides"
              :key="item.src"
              :aria-label="`查看：${item.title}`"
              :aria-pressed="slideIndex === index"
              @click="slideIndex = index"
            >
              <span>{{ number(index) }}</span>
            </button>
          </div>
          <a :href="slide.source" target="_blank" rel="noopener noreferrer"
            >官方概念资料 ↗</a
          >
        </footer></template
      >
    </dialog>
  </main>
</template>
