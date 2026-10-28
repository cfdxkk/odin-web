<script setup lang="ts">
import { isPlaying, nextPlayback } from '~/lib/odin-motion'
import {
  ATLAS_MODES as modes,
  ATLAS_GALLERY as gallery,
  type AtlasModeId,
} from '~/lib/atlas-content'
import { INTERIOR_SECTIONS } from '~/lib/odin-interiors'
const mode = ref<AtlasModeId>('overview'),
  deployment = ref(0)
const currentMode = computed(
  () => modes.find((item) => item.id === mode.value)!,
)
const playback = ref({ userPaused: false, scrubbing: false }),
  playing = computed(() => isPlaying(playback.value))
const technical = ref(false),
  reducedMotion = ref(false),
  ready = ref(false),
  progress = ref(0),
  error = ref('')
const viewer = ref<{
  resetView: () => void
  capturePhoto: () => Promise<Blob>
}>()
const lab = ref<HTMLElement>(),
  labActive = ref(false),
  labLoaded = ref(false),
  visible = ref(true)
const menuOpen = ref(false),
  currentSection = ref('intro'),
  photoStatus = ref(''),
  capturing = ref(false)
const heroShift = ref({ x: 0, y: 0 })
const heroStyle = computed(() => ({
  '--shift-x': `${heroShift.value.x}px`,
  '--shift-y': `${heroShift.value.y}px`,
}))
const links = [
  { id: 'intro', label: '初见', no: '01' },
  { id: 'observatory', label: '机械之美', no: '02' },
  { id: 'interior', label: '舰内世界', no: '03' },
  { id: 'archive', label: '影像档案', no: '04' },
]
const interiorIndex = ref(0)
const interiors = [
  {
    no: '01',
    title: '指挥中枢',
    en: 'THE BRIDGE',
    text: '透过舰桥，读懂一艘战舰。前方中央的舰长席位连接观察、决策与舰队协同。',
    image: INTERIOR_SECTIONS.bridge.images[0]!,
  },
  {
    no: '02',
    title: '舰队的另一端',
    en: 'THE HANGAR',
    text: '中央机库与六座侧机库相连。从回收到补给，每一次再次出动，都从这片空间开始。',
    image: INTERIOR_SECTIONS.aft.images[0]!,
  },
  {
    no: '03',
    title: '行动之前',
    en: 'THE BRIEFING ROOM',
    text: '一场行动，从共同的坐标开始。简报空间为船员集合、讨论与战术协作而设。',
    image: INTERIOR_SECTIONS.bridge.images[2]!,
  },
]
const interior = computed(() => interiors[interiorIndex.value]!)
const lightbox = ref<HTMLDialogElement>(),
  galleryIndex = ref(0)
const galleryImage = computed(() => gallery[galleryIndex.value]!)
const formatIndex = (n: number) => String(n + 1).padStart(2, '0')
function chooseMode(id: AtlasModeId) {
  mode.value = id
  deployment.value = ['main', 'secondary', 'defense', 'bridge'].includes(id)
    ? 1
    : 0
}
function togglePlayback() {
  playback.value = nextPlayback(playback.value, 'toggle')
}
function onSceneFail(message: string) {
  error.value = message
  ready.value = false
}
async function retryScene() {
  error.value = ''
  ready.value = false
  progress.value = 0
  labLoaded.value = false
  await nextTick()
  labLoaded.value = true
}
function beginScrub(event?: PointerEvent) {
  if (event)
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  playback.value = nextPlayback(playback.value, 'scrub-start')
}
function endScrub() {
  playback.value = nextPlayback(playback.value, 'scrub-end')
}
function sliderKey(event: KeyboardEvent) {
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
    beginScrub()
}
function onHeroMove(event: PointerEvent) {
  if (reducedMotion.value || event.pointerType === 'touch') return
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  heroShift.value = {
    x: ((event.clientX - rect.left) / rect.width - 0.5) * 14,
    y: ((event.clientY - rect.top) / rect.height - 0.5) * 10,
  }
}
function openImage(index: number) {
  galleryIndex.value = index
  lightbox.value?.showModal()
}
function stepImage(step: number) {
  galleryIndex.value =
    (galleryIndex.value + step + gallery.length) % gallery.length
}
function onDialogKey(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft') stepImage(-1)
  if (event.key === 'ArrowRight') stepImage(1)
}
async function capture() {
  if (!viewer.value || capturing.value) return
  capturing.value = true
  try {
    const blob = await viewer.value.capturePhoto(),
      url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'ODIN-ATLAS.png'
    anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
    photoStatus.value = '影像已保存'
  } catch {
    photoStatus.value = '保存失败，请重试'
  } finally {
    capturing.value = false
  }
}
function onVisibility() {
  visible.value = !document.hidden
  endScrub()
}
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') menuOpen.value = false
  if (
    event.code === 'Space' &&
    labActive.value &&
    !(
      event.target instanceof Element &&
      event.target.closest('button, input, a, dialog')
    )
  ) {
    event.preventDefault()
    togglePlayback()
  }
}
let observer: IntersectionObserver | undefined,
  navObserver: IntersectionObserver | undefined,
  motionQuery: MediaQueryList | undefined
function onMotion() {
  reducedMotion.value = motionQuery?.matches ?? false
  if (reducedMotion.value) playback.value.userPaused = true
}
onMounted(() => {
  motionQuery = matchMedia('(prefers-reduced-motion: reduce)')
  onMotion()
  motionQuery.addEventListener('change', onMotion)
  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]!
      labActive.value = entry.isIntersecting
      if (entry.isIntersecting) labLoaded.value = true
    },
    { rootMargin: '250px' },
  )
  if (lab.value) observer.observe(lab.value)
  navObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries)
        if (entry.isIntersecting) currentSection.value = entry.target.id
    },
    { rootMargin: '-12% 0px -60% 0px' },
  )
  links.forEach((link) => {
    const section = document.getElementById(link.id)
    if (section) navObserver?.observe(section)
  })
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('pointerup', endScrub)
  window.addEventListener('pointercancel', endScrub)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  navObserver?.disconnect()
  motionQuery?.removeEventListener('change', onMotion)
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('pointerup', endScrub)
  window.removeEventListener('pointercancel', endScrub)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="atlas">
    <a class="skip-link" href="#main">跳至内容</a>
    <header class="site-header">
      <a
        class="brand"
        href="#intro"
        aria-label="Odin Atlas 首页"
        @click="menuOpen = false"
        ><svg viewBox="0 0 36 36" aria-hidden="true">
          <path d="M3 5h9l6 11 6-11h9L22 26h-8L3 5Z" fill="currentColor" />
          <path d="M14 29h8v4h-8z" fill="currentColor" /></svg
        ><span>ODIN<span class="brand-sub">THE ATLAS PROJECT</span></span></a
      >
      <nav class="desktop-nav" aria-label="主要导航">
        <a
          v-for="link in links.slice(1)"
          :key="link.id"
          :href="`#${link.id}`"
          :class="{ selected: currentSection === link.id }"
          >{{ link.label }}<sup>{{ link.no }}</sup></a
        >
      </nav>
      <button
        class="menu-toggle"
        :aria-expanded="menuOpen"
        aria-controls="site-index"
        @click="menuOpen = !menuOpen"
      >
        <span>{{ menuOpen ? '关闭索引' : '探索索引' }}</span
        ><span class="menu-symbol">{{ menuOpen ? '−' : '+' }}</span>
      </button>
    </header>
    <nav
      v-if="menuOpen"
      id="site-index"
      class="site-index"
      aria-label="章节索引"
    >
      <a
        v-for="link in links"
        :key="link.id"
        :href="`#${link.id}`"
        @click="menuOpen = false"
        ><small>{{ link.no }}</small
        >{{ link.label }}<span>↗</span></a
      >
      <p>AN INDEPENDENT STUDY OF THE ANVIL ODIN.</p>
    </nav>
    <main id="main">
      <section
        id="intro"
        class="hero"
        :style="heroStyle"
        @pointermove="onHeroMove"
        @pointerleave="heroShift = { x: 0, y: 0 }"
      >
        <div class="hero-kicker">
          <span><i class="status-dot" />ANVIL AEROSPACE</span
          ><span>BATTLECRUISER / 概念战列巡洋舰</span
          ><span class="hero-edition">INDEPENDENT ARCHIVE — VOL. 01</span>
        </div>
        <h1 class="hero-title">ODIN<span class="title-star">✳</span></h1>
        <div class="hero-orbit" aria-hidden="true">
          <span class="orbit-cross cross-one">+</span
          ><span class="orbit-cross cross-two">+</span>
        </div>
        <div class="hero-image">
          <img
            :src="'/images/atlas-hero-v0.24.0.png'"
            alt="奥丁战列巡洋舰的完整舰体与层叠的舰艉结构"
            width="2600"
            height="1199"
            fetchpriority="high"
          />
        </div>
        <span class="hero-coordinate mono"
          >FIG. 001<br />ANVIL / ODIN<br />EXTERIOR STUDY</span
        >
        <div class="hero-bottom">
          <div class="hero-intro">
            <span class="eyebrow">ENGINEERED TO OVERWHELM.</span>
            <h2>沉默之中，<br />自有雷霆。</h2>
          </div>
          <a class="round-cta" href="#observatory"
            ><span
              >进入三维检视<span class="cta-sub">ENTER OBSERVATORY</span></span
            ><span class="cta-arrow">↗</span></a
          >
          <p class="hero-note">
            一份关于力量、尺度与机械秩序的<br />交互式舰船档案。
          </p>
        </div>
        <div class="hero-foot mono">
          <span>SCROLL TO DISCOVER ↓</span><span>01 — 04</span
          ><span>FAN-MADE. DETAIL-DRIVEN.</span>
        </div>
      </section>
      <section class="manifesto section-pad">
        <p class="eyebrow">
          <span class="section-number">01 /</span> THE PRESENCE
        </p>
        <div class="manifesto-main">
          <h2>有些舰船抵达战场。<br />有些舰船，<span>改变战场。</span></h2>
          <div class="manifesto-copy">
            <p>
              奥丁的魅力，并不止于火力。<br />是装甲开启的节奏，是复杂结构的精确咬合，<br />也是一艘庞大战舰在太空中，近乎从容的姿态。
            </p>
            <a class="text-link" href="#observatory"
              >走近它的每一处细节 <span>↗</span></a
            >
          </div>
        </div>
        <div class="identity-strip">
          <span>ANVIL<small>制造商</small></span
          ><span>BATTLECRUISER<small>战列巡洋舰</small></span
          ><span>SCM ↔ NAV<small>战斗与航行构型</small></span
          ><span>ODIN<small>星际公民 · 概念舰船</small></span>
        </div>
      </section>
      <section id="observatory" ref="lab" class="observatory">
        <div class="lab-heading">
          <p class="eyebrow">
            <span class="section-number">02 /</span> THE OBSERVATORY
          </p>
          <div>
            <h2>解构，<span>机械之美。</span></h2>
            <p>亲手转动视角，让每一处结构进入视野。</p>
          </div>
          <span class="live-status mono"><i class="status-dot" />LIVE 3D</span>
        </div>
        <div class="lab-layout">
          <div class="viewer-stage" :class="{ technical }">
            <div class="viewer-grid" aria-hidden="true" />
            <span class="stage-corner corner-tl" aria-hidden="true" /><span
              class="stage-corner corner-br"
              aria-hidden="true"
            />
            <div class="stage-label mono">
              ODN—01 <span>/ {{ currentMode.eyebrow }}</span>
            </div>
            <AtlasScene
              v-if="labLoaded"
              ref="viewer"
              :playing="playing"
              :mode="mode"
              :deployment="deployment"
              :active="labActive && visible"
              :reduced-motion="reducedMotion"
              :technical="technical"
              :scrubbing="playback.scrubbing"
              @ready="ready = true"
              @progress="progress = $event"
              @fail="onSceneFail"
            />
            <div v-if="!ready && !error" class="model-loading" role="status">
              <span class="loading-orbit" /><span>正在开启检视舱</span
              ><small class="mono">{{ Math.round(progress) }}%</small>
            </div>
            <div v-if="error" class="model-error" role="alert">
              <p>当前设备无法开启三维视图。</p>
              <p>你仍可浏览下方的舰内空间与影像档案。</p>
              <button
                class="text-link"
                @click="retryScene"
              >
                重新尝试 ↻
              </button>
            </div>
            <div class="stage-tools">
              <button
                :disabled="!ready"
                :aria-pressed="technical"
                @click="technical = !technical"
              >
                {{ technical ? '实体材质' : '结构线框'
                }}<span>{{ technical ? '◧' : '⌗' }}</span></button
              ><button
                :disabled="!ready"
                aria-label="重置观察视角"
                @click="viewer?.resetView()"
              >
                复位<span>↺</span></button
              ><button :disabled="!ready || capturing" @click="capture">
                {{ capturing ? '保存中' : '拍照' }}<span>↗</span>
              </button>
            </div>
            <div class="stage-bottom">
              <span class="mono">DRAG TO ORBIT · SCROLL TO ZOOM</span
              ><span>拖动旋转 · 滚轮缩放</span>
            </div>
          </div>
          <aside class="inspection-panel">
            <div class="inspection-top mono">
              <span>SELECT A SYSTEM</span
              ><span>{{ currentMode.number }} / 06</span>
            </div>
            <div class="mode-list" role="group" aria-label="选择检视系统">
              <button
                v-for="item in modes"
                :key="item.id"
                :class="{ active: mode === item.id }"
                :aria-pressed="mode === item.id"
                @click="chooseMode(item.id)"
              >
                <small>{{ item.number }}</small
                ><span>{{ item.label }}</span
                ><span class="mode-arrow">↗</span>
              </button>
            </div>
            <div class="mode-description" aria-live="polite">
              <span class="eyebrow">{{ currentMode.eyebrow }}</span>
              <h3>{{ currentMode.title }}</h3>
              <p>{{ currentMode.body }}</p>
            </div>
            <div class="deployment-control">
              <div>
                <label for="deployment">武备展开程度</label
                ><output for="deployment" class="mono"
                  >{{ Math.round(deployment * 100) }}<small>%</small></output
                >
              </div>
              <input
                id="deployment"
                v-model.number="deployment"
                type="range"
                min="0"
                max="1"
                step="0.001"
                :disabled="!ready || mode === 'engines'"
                aria-label="武备展开程度"
                @pointerdown="beginScrub"
                @pointerup="endScrub"
                @pointercancel="endScrub"
                @keydown="sliderKey"
                @keyup="endScrub"
                @blur="endScrub"
              />
              <div class="range-labels mono">
                <span>STOWED</span><span>DEPLOYED</span>
              </div>
            </div>
            <button
              class="playback-control"
              :aria-pressed="!playback.userPaused"
              @click="togglePlayback"
            >
              <span class="playback-icon">{{
                playback.userPaused ? '▶' : 'Ⅱ'
              }}</span
              >{{ playback.userPaused ? '继续自动环绕' : '暂停自动环绕'
              }}<small>SPACE</small>
            </button>
          </aside>
        </div>
        <div class="lab-footer mono">
          <span>INTERACTIVE MODEL / FAN INTERPRETATION</span
          ><span role="status">{{
            photoStatus || '自由观察，保留你的视角。'
          }}</span
          ><span>ALL SYSTEMS IN VIEW ↗</span>
        </div>
      </section>
      <section class="cinematic" aria-label="奥丁官方概念艺术">
        <img
          src="/images/official/v0.13.0/13-sc-anvil-odin-exterior-3.webp"
          alt="轨道交战中的奥丁，身后是行星与深空"
          width="2400"
          height="1013"
          loading="lazy"
        />
        <div class="cinematic-shade" />
        <div class="cinematic-top mono">
          <span>BEYOND THE SILHOUETTE</span
          ><span>ANVIL ODIN / CONCEPT ART</span>
        </div>
        <h2>AN UNFAIR<br /><em>ADVANTAGE.</em></h2>
        <div class="cinematic-bottom">
          <p>让存在本身，<br />成为一种威慑。</p>
          <span class="mono"
            >OFFICIAL ARTWORK<br />© CLOUD IMPERIUM GAMES</span
          >
        </div>
      </section>
      <section id="interior" class="interior section-pad">
        <div class="section-heading">
          <p class="eyebrow">
            <span class="section-number">03 /</span> LIFE WITHIN
          </p>
          <h2>钢铁之下，<br /><span>另一个世界。</span></h2>
          <p>
            走过指挥中枢、机库与简报室。<br />这艘战舰，也是一群人的共同航程。
          </p>
        </div>
        <div class="interior-layout">
          <div class="interior-nav">
            <button
              v-for="(item, index) in interiors"
              :key="item.no"
              :class="{ active: interiorIndex === index }"
              :aria-pressed="interiorIndex === index"
              @click="interiorIndex = index"
            >
              <small class="mono">{{ item.no }}</small
              ><span
                >{{ item.title }}<small>{{ item.en }}</small></span
              ><span>↗</span>
            </button>
            <div class="interior-description" aria-live="polite">
              <p>{{ interior.text }}</p>
              <a
                :href="interior.image.source"
                target="_blank"
                rel="noopener noreferrer"
                class="text-link"
                >查看官方资料 <span>↗</span></a
              ><small>内部空间与配置处于概念设计阶段。</small>
            </div>
          </div>
          <figure class="interior-figure">
            <div class="interior-image-frame">
              <img
                :key="interior.image.src"
                :src="interior.image.src"
                :alt="interior.image.zh"
                :width="interior.image.width"
                :height="interior.image.height"
                loading="lazy"
              />
            </div>
            <figcaption>
              <span class="mono">{{ interior.en }} — {{ interior.no }}</span
              ><span>空间概念 / 官方资料</span>
            </figcaption>
          </figure>
        </div>
      </section>
      <section id="archive" class="archive section-pad">
        <div class="archive-heading">
          <p class="eyebrow">
            <span class="section-number">04 /</span> THE VISUAL ARCHIVE
          </p>
          <div>
            <h2>每一帧，<span>皆有引力。</span></h2>
            <p>以另一种尺度，看见奥丁。</p>
          </div>
          <span class="archive-count mono">[ 04 IMAGES ]</span>
        </div>
        <div class="gallery-grid">
          <button
            v-for="(item, index) in gallery"
            :key="item.src"
            class="gallery-item"
            @click="openImage(index)"
            :aria-label="`放大查看：${item.zh.title}`"
          >
            <div class="gallery-image">
              <img
                :src="item.src"
                :alt="item.zh.alt"
                :width="item.width"
                :height="item.height"
                loading="lazy"
              /><span class="gallery-open">↗</span>
            </div>
            <div class="gallery-caption">
              <span
                ><small class="mono">{{ formatIndex(index) }}</small
                >{{ item.title }}</span
              ><span class="mono">{{ item.eyebrow }}</span>
            </div>
          </button>
        </div>
        <p class="archive-note">官方概念艺术 · 点击展开影像</p>
      </section>
      <footer class="site-footer">
        <div class="footer-top">
          <p>为想象力而造。<br /><span>为每一个仰望星空的人。</span></p>
          <a href="#intro" class="back-top">回到起点 <span>↑</span></a>
        </div>
        <div class="footer-wordmark">ODIN<span>✳</span></div>
        <div class="footer-bottom">
          <div class="mono">
            THE ATLAS PROJECT<br />AN INDEPENDENT ODIN EXPERIENCE
          </div>
          <p>
            本项目为非官方粉丝创作，与 Cloud Imperium Games 无隶属关系。<br />Star
            Citizen、Anvil Odin
            与官方影像版权归各自权利人所有。舰船资料以官方后续发布为准。
          </p>
          <a
            href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin"
            target="_blank"
            rel="noopener noreferrer"
            >官方舰船档案 ↗</a
          >
        </div>
      </footer>
    </main>
    <dialog
      ref="lightbox"
      class="lightbox"
      aria-label="奥丁影像档案"
      @keydown="onDialogKey"
      @click="
        (event) => {
          if (event.target === lightbox) lightbox?.close()
        }
      "
    >
      <div class="lightbox-inner">
        <div class="lightbox-top">
          <span class="mono"
            >VISUAL ARCHIVE / {{ formatIndex(galleryIndex) }} — 04</span
          ><button autofocus aria-label="关闭影像" @click="lightbox?.close()">
            关闭 <span>×</span>
          </button>
        </div>
        <img
          :src="galleryImage.src"
          :alt="galleryImage.zh.alt"
          :width="galleryImage.width"
          :height="galleryImage.height"
        />
        <div class="lightbox-bottom">
          <div>
            <h3>{{ galleryImage.zh.title }}</h3>
            <a
              :href="galleryImage.source"
              target="_blank"
              rel="noopener noreferrer"
              >官方原图 ↗</a
            >
          </div>
          <div class="lightbox-controls">
            <button aria-label="上一张影像" @click="stepImage(-1)">←</button
            ><button aria-label="下一张影像" @click="stepImage(1)">→</button>
          </div>
        </div>
      </div>
    </dialog>
  </div>
</template>
