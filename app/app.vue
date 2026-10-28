<script setup lang="ts">
import { isPlaying, nextPlayback } from '~/lib/odin-motion'
import { ATLAS_MODES } from '~/lib/atlas-content'
import {
  FOLIO_ARTWORK,
  FOLIO_INTERIORS,
  FOLIO_FACTS,
  FOLIO_NOTICE,
  FOLIO_SOURCE,
  FOLIO_FACT_NOTE,
} from '~/lib/folio-content'
import type { AtlasMode } from '~/lib/atlas-viewer-state'
import type { FolioTreatment } from '~/lib/folio-effects'
const pages = [
  { id: 'cover', title: '序 · 舰影', en: 'THE SILHOUETTE' },
  { id: 'anatomy', title: '构 · 武备', en: 'ANATOMY OF FORCE' },
  { id: 'within', title: '内 · 尺度', en: 'LIFE WITHIN' },
  { id: 'archive', title: '藏 · 图像', en: 'VISUAL ARCHIVE' },
] as const
const page = ref(0),
  direction = ref(1),
  focus = ref<AtlasMode>('overview')
const treatment = ref<FolioTreatment>('print'),
  deployment = ref(0)
const ready = ref(false),
  progress = ref(0),
  failure = ref(''),
  sceneKey = ref(0)
const reducedMotion = ref(false),
  motionOptIn = ref(false),
  visible = ref(true)
const playback = ref({ userPaused: false, scrubbing: false })
const effectiveReducedMotion = computed(
  () => reducedMotion.value && !motionOptIn.value,
)
const playing = computed(
  () => isPlaying(playback.value) && !effectiveReducedMotion.value,
)
const pointer = ref({ x: 0, y: 0 })
const scene = ref<{ resetView(): void; capturePhoto(): Promise<Blob> }>()
const currentMode = computed(
  () => ATLAS_MODES.find((item) => item.id === focus.value)!,
)
const interiorIndex = ref(0),
  interior = computed(() => FOLIO_INTERIORS[interiorIndex.value]!)
const imageIndex = ref(0),
  dialog = ref<HTMLDialogElement>(),
  dialogKind = ref<'image' | 'about' | null>(null)
const currentImage = computed(() => FOLIO_ARTWORK[imageIndex.value]!)
const imageSet = computed(() =>
  FOLIO_ARTWORK.filter((item) => item.category === 'exterior'),
)
const photoStatus = ref(''),
  capturing = ref(false)
const treatmentNames = { print: '蚀刻', contour: '线稿', solid: '素模' }
const number = (value: number) => String(value).padStart(2, '0')
function goTo(index: number) {
  const next = Math.max(0, Math.min(pages.length - 1, index))
  if (next === page.value) return
  direction.value = next > page.value ? 1 : -1
  page.value = next
  if (next === 0) {
    focus.value = 'overview'
    deployment.value = 0
  }
  if (next === 1 && focus.value === 'overview') {
    focus.value = 'main'
    deployment.value = 1
  }
  endScrub()
  window.history.replaceState(null, '', `#${pages[next]!.id}`)
}
function chooseMode(mode: AtlasMode) {
  focus.value = mode
  if (mode === 'engines') deployment.value = 0
}
function togglePlayback() {
  if (effectiveReducedMotion.value) {
    motionOptIn.value = true
    playback.value = { ...playback.value, userPaused: false }
  } else playback.value = nextPlayback(playback.value, 'toggle')
}
function startScrub(event?: PointerEvent) {
  playback.value = nextPlayback(playback.value, 'scrub-start')
  if (event)
    (event.currentTarget as HTMLInputElement).setPointerCapture(event.pointerId)
}
function endScrub() {
  playback.value = nextPlayback(playback.value, 'scrub-end')
}
function scrub(event: Event) {
  deployment.value = Number((event.target as HTMLInputElement).value)
}
const rangeKeys = [
  'ArrowLeft',
  'ArrowRight',
  'ArrowUp',
  'ArrowDown',
  'Home',
  'End',
  'PageUp',
  'PageDown',
]
function rangeKey(event: KeyboardEvent) {
  if (rangeKeys.includes(event.key)) startScrub()
}
function followPointer(event: PointerEvent) {
  pointer.value = {
    x: (event.clientX / window.innerWidth - 0.5) * 2,
    y: (0.5 - event.clientY / window.innerHeight) * 2,
  }
}
function clearPointer() {
  pointer.value = { x: 0, y: 0 }
}
function sceneFailed(message: string) {
  failure.value = message
  ready.value = false
}
function retryScene() {
  failure.value = ''
  ready.value = false
  progress.value = 0
  sceneKey.value++
}
function nextInterior(step: number) {
  interiorIndex.value =
    (interiorIndex.value + step + FOLIO_INTERIORS.length) %
    FOLIO_INTERIORS.length
}
async function openImage(id: string) {
  imageIndex.value = FOLIO_ARTWORK.findIndex((item) => item.id === id)
  dialogKind.value = 'image'
  await nextTick()
  dialog.value?.showModal()
}
async function openAbout() {
  dialogKind.value = 'about'
  await nextTick()
  dialog.value?.showModal()
}
function closeDialog() {
  dialog.value?.close()
  dialogKind.value = null
}
function nextImage(step: number) {
  imageIndex.value =
    (imageIndex.value + step + FOLIO_ARTWORK.length) % FOLIO_ARTWORK.length
}
function dialogClick(event: MouseEvent) {
  if (event.target === dialog.value) closeDialog()
}
async function capture() {
  if (!scene.value || capturing.value) return
  capturing.value = true
  photoStatus.value = ''
  try {
    const blob = await scene.value.capturePhoto(),
      url = URL.createObjectURL(blob),
      link = document.createElement('a')
    link.href = url
    link.download = `ODIN-${treatment.value}-${focus.value}.png`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 10000)
    photoStatus.value = '设定稿已保存'
  } catch {
    photoStatus.value = '保存未完成，请再试一次'
  } finally {
    capturing.value = false
  }
}
function onKey(event: KeyboardEvent) {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey)
    return
  if (dialogKind.value === 'image') {
    if (event.key === 'ArrowRight') nextImage(1)
    if (event.key === 'ArrowLeft') nextImage(-1)
    return
  }
  if (
    dialogKind.value ||
    (event.target as HTMLElement)?.closest('input,textarea,select,button,a')
  )
    return
  if (event.key === 'ArrowRight') goTo(page.value + 1)
  if (event.key === 'ArrowLeft') goTo(page.value - 1)
  if (event.code === 'Space' && page.value < 2) {
    event.preventDefault()
    togglePlayback()
  }
}
function onVisibility() {
  visible.value = !document.hidden
  if (!visible.value) endScrub()
}
let media: MediaQueryList | undefined
function motionChanged() {
  reducedMotion.value = !!media?.matches
}
onMounted(() => {
  media = window.matchMedia('(prefers-reduced-motion: reduce)')
  motionChanged()
  media.addEventListener('change', motionChanged)
  const initial = pages.findIndex((item) => `#${item.id}` === location.hash)
  if (initial > 0) goTo(initial)
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('keydown', onKey)
  window.addEventListener('pointerup', endScrub)
  window.addEventListener('pointercancel', endScrub)
  window.addEventListener('blur', endScrub)
})
onBeforeUnmount(() => {
  media?.removeEventListener('change', motionChanged)
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('pointerup', endScrub)
  window.removeEventListener('pointercancel', endScrub)
  window.removeEventListener('blur', endScrub)
})
</script>
<template>
  <div
    class="folio"
    :class="[
      `page-${pages[page]!.id}`,
      { 'is-ready': ready, 'reduce-motion': effectiveReducedMotion },
    ]"
    :style="{ '--direction': direction }"
    @pointermove="followPointer"
    @pointerleave="clearPointer"
  >
    <a class="skip-link" href="#spread">跳至当前页面</a>
    <aside class="book-spine" aria-label="页面索引">
      <button class="sigil" aria-label="返回封面" @click="goTo(0)">
        <svg viewBox="0 0 40 48" aria-hidden="true">
          <path
            d="M20 1 38 12v24L20 47 2 36V12ZM20 9v30M10 17l20 14M30 17 10 31"
          />
        </svg>
      </button>
      <div class="spine-name">ANVIL AEROSPACE — ODIN</div>
      <nav class="spine-index">
        <button
          v-for="(item, index) in pages"
          :key="item.id"
          :aria-label="item.title"
          :aria-current="page === index ? 'page' : undefined"
          @click="goTo(index)"
        >
          <span>{{ number(index + 1) }}</span
          ><i />
        </button>
      </nav>
      <span class="spine-edition">VOL. 01</span>
    </aside>
    <header class="folio-header">
      <button class="wordmark" aria-label="奥丁设定集封面" @click="goTo(0)">
        ODIN<span>VISUAL MONOGRAPH</span>
      </button>
      <div class="header-mid">奥丁 · 形体与力量的研究</div>
      <button class="about-link" @click="openAbout">
        关于这本设定集 <span>↗</span>
      </button>
    </header>
    <main id="spread" class="spread" tabindex="-1">
      <div
        v-show="page < 2"
        class="model-stage"
        :class="{ 'anatomy-stage': page === 1 }"
      >
        <ClientOnly
          ><FolioScene
            :key="sceneKey"
            ref="scene"
            :mode="focus"
            :deployment="deployment"
            :playing="playing"
            :active="page < 2 && visible && !dialogKind"
            :reduced-motion="effectiveReducedMotion"
            :scrubbing="playback.scrubbing"
            :treatment="treatment"
            :pointer="pointer"
            @ready="ready = true"
            @progress="progress = $event"
            @fail="sceneFailed"
        /></ClientOnly>
      </div>
      <Transition name="spread" mode="out-in">
        <section
          v-if="page === 0"
          key="cover"
          class="cover-sheet sheet"
          aria-labelledby="cover-title"
        >
          <div class="cover-meta">
            <span>A STUDY IN<br />FORM & FORCE</span
            ><span>ANVIL<br />BATTLECRUISER</span>
          </div>
          <div class="cover-word" aria-hidden="true">ODIN</div>
          <div class="cover-rule">
            <span>01 / SILHOUETTE</span><i /><span
              >THE THUNDER TAKES SHAPE</span
            >
          </div>
          <div class="cover-cross cross-a" aria-hidden="true">+</div>
          <div class="cover-cross cross-b" aria-hidden="true">+</div>
          <div class="cover-caption">
            <span class="edition-stamp">O / 01</span>
            <p>装甲、空隙与锋芒。<br />一艘战列巡洋舰的形体笔记。</p>
          </div>
          <div class="cover-title">
            <span class="eyebrow">THE SHAPE OF THUNDER</span>
            <h1 id="cover-title">雷霆，有形。</h1>
            <button class="text-link" @click="goTo(1)">
              翻开武备篇 <span>↗</span>
            </button>
          </div>
          <div class="drag-hint">
            <span class="drag-glyph">↔</span> 拖动，改变观察的角度
          </div>
        </section>
        <section
          v-else-if="page === 1"
          key="anatomy"
          class="anatomy-sheet sheet"
          aria-labelledby="anatomy-title"
        >
          <div class="anatomy-ghost" aria-hidden="true">
            {{
              focus === 'main'
                ? 'S12'
                : focus === 'secondary'
                  ? 'S10'
                  : focus === 'engines'
                    ? 'NAV'
                    : 'S8'
            }}
          </div>
          <div class="anatomy-copy">
            <span class="eyebrow">02 / ANATOMY OF FORCE</span>
            <h1 id="anatomy-title">力量的<br /><em>展开式。</em></h1>
            <p>从轮廓，进入结构。<br />逐层展开藏于装甲之下的机械。</p>
          </div>
          <nav class="anatomy-menu" aria-label="舰体观察部位">
            <button
              v-for="item in ATLAS_MODES.slice(1)"
              :key="item.id"
              :class="{ selected: focus === item.id }"
              :aria-pressed="focus === item.id"
              @click="chooseMode(item.id)"
            >
              <span>{{ item.number }}</span
              ><b>{{ item.label }}</b
              ><i>↗</i>
            </button>
          </nav>
          <Transition name="caption" mode="out-in"
            ><div :key="focus" class="mechanism-caption">
              <span class="eyebrow">{{ currentMode.eyebrow }}</span
              ><strong
                >{{ currentMode.metric
                }}<small>{{ currentMode.metricLabel }}</small></strong
              >
              <p>{{ currentMode.body }}</p>
              <span class="concept-label">{{ currentMode.detail }}</span>
            </div></Transition
          >
          <div class="deployment-control">
            <div>
              <label for="deployment">武备展开</label
              ><span>{{ Math.round(deployment * 100) }}<small>%</small></span>
            </div>
            <input
              id="deployment"
              type="range"
              min="0"
              max="1"
              step="0.001"
              :value="deployment"
              :disabled="!ready"
              @input="scrub"
              @pointerdown="startScrub"
              @pointerup="endScrub"
              @pointercancel="endScrub"
              @lostpointercapture="endScrub"
              @blur="endScrub"
              @keydown="rangeKey"
              @keyup="endScrub"
            />
            <div class="range-ends">
              <span>收纳 / STOWED</span><span>展开 / DEPLOYED</span>
            </div>
          </div>
        </section>
        <section
          v-else-if="page === 2"
          key="within"
          class="within-sheet sheet"
          aria-labelledby="within-title"
        >
          <div class="within-top">
            <span class="eyebrow">03 / LIFE WITHIN</span>
            <h1 id="within-title">钢铁之中，<br /><em>人的尺度。</em></h1>
          </div>
          <div class="within-word" aria-hidden="true">WITHIN</div>
          <Transition name="image-reveal" mode="out-in"
            ><button
              :key="interior.id"
              class="interior-image"
              :aria-label="`放大：${interior.title}`"
              @click="openImage(interior.id)"
            >
              <img
                :src="interior.src"
                :alt="interior.alt"
                :style="{ objectPosition: interior.position }"
              /><span class="image-open">查看全幅 ↗</span>
            </button></Transition
          >
          <div class="interior-aside">
            <span class="vertical-label">THE HUMAN ELEMENT</span
            ><span class="interior-count"
              >{{ number(interiorIndex + 1)
              }}<small>/ {{ number(FOLIO_INTERIORS.length) }}</small></span
            >
          </div>
          <div class="interior-bottom">
            <div class="interior-description">
              <span class="eyebrow">{{ interior.kicker }}</span>
              <h2>{{ interior.title }}</h2>
              <p>{{ interior.caption }}</p>
            </div>
            <div class="interior-arrows">
              <button aria-label="上一处舰内空间" @click="nextInterior(-1)">
                ←</button
              ><button aria-label="下一处舰内空间" @click="nextInterior(1)">
                →
              </button>
            </div>
          </div>
          <div class="within-facts">
            <span><b>6 + 1</b>小型 / 中型机库</span
            ><span
              ><b>8,000 <small>SCU</small></b
              >概念货物容量</span
            >
          </div>
        </section>
        <section
          v-else
          key="archive"
          class="archive-sheet sheet"
          aria-labelledby="archive-title"
        >
          <div class="archive-title">
            <span class="eyebrow">04 / SELECTED IMAGERY</span>
            <h1 id="archive-title">舰影，<em>成册。</em></h1>
            <p>
              从概念画面到舰内空间。<br />收录奥丁的
              {{ FOLIO_ARTWORK.length }} 个切面。
            </p>
          </div>
          <div class="archive-display">
            <button
              v-for="(item, index) in imageSet.slice(0, 3)"
              :key="item.id"
              class="archive-print"
              :class="`print-${index}`"
              :aria-label="`放大：${item.title}`"
              @click="openImage(item.id)"
            >
              <img
                :src="item.src"
                :alt="item.alt"
                :style="{ objectPosition: item.position }"
              /><span
                ><b>{{ number(index + 1) }}</b
                >{{ item.title }}<i>↗</i></span
              >
            </button>
          </div>
          <div class="archive-strip">
            <span
              >CONTACT SHEET<br /><b>{{ FOLIO_ARTWORK.length }} PLATES</b></span
            >
            <div class="contact-images">
              <button
                v-for="(item, index) in FOLIO_ARTWORK"
                :key="item.id"
                :aria-label="`打开图像 ${index + 1}：${item.title}`"
                @click="openImage(item.id)"
              >
                <img
                  :src="item.thumb"
                  :alt="item.title"
                  loading="lazy"
                /><span>{{ number(index + 1) }}</span>
              </button>
            </div>
          </div>
          <small class="archive-credit"
            >CONCEPT ART © CLOUD IMPERIUM GAMES</small
          >
        </section>
      </Transition>
      <div
        v-if="page < 2 && !ready && !failure"
        class="loading-mark"
        role="status"
      >
        <span>绘制舰影</span><b>{{ Math.round(progress) }}<small>%</small></b
        ><i :style="{ '--load': `${progress}%` }" />
      </div>
      <div v-if="page < 2 && failure" class="scene-error" role="alert">
        <h2>设定稿暂未载入</h2>
        <p>{{ failure }}</p>
        <button @click="retryScene">重新载入 ↻</button>
      </div>
      <div v-show="page < 2" class="model-tools">
        <div class="treatment-switch" role="group" aria-label="模型表现方式">
          <span>表 现</span
          ><button
            v-for="(label, value) in treatmentNames"
            :key="value"
            :aria-pressed="treatment === value"
            @click="treatment = value"
          >
            {{ label }}<i />
          </button>
        </div>
        <div class="view-tools">
          <button
            :disabled="!ready"
            :aria-label="playing ? '暂停自动转动' : '开始自动转动'"
            :aria-pressed="playing"
            @click="togglePlayback"
          >
            <span>{{ playing ? 'Ⅱ' : '▷' }}</span
            >{{ playing ? '定格' : '缓转' }}</button
          ><button
            :disabled="!ready"
            aria-label="重置视角"
            @click="scene?.resetView()"
          >
            ↺ <span>复位</span></button
          ><button :disabled="!ready || capturing" @click="capture">
            ↗ <span>{{ capturing ? '保存中' : '保存设定稿' }}</span>
          </button>
        </div>
        <span class="photo-status" role="status">{{ photoStatus }}</span>
      </div>
    </main>
    <footer class="folio-footer">
      <div class="folio-pagination">
        <span>{{ number(page + 1) }}</span
        ><small>/ 04</small>
      </div>
      <nav aria-label="设定集章节">
        <button
          v-for="(item, index) in pages"
          :key="item.id"
          :aria-current="page === index ? 'page' : undefined"
          @click="goTo(index)"
        >
          <small>{{ number(index + 1) }} / {{ item.en }}</small
          ><span>{{ item.title }}</span>
        </button>
      </nav>
      <button
        class="page-turn"
        :aria-label="page === 3 ? '返回封面' : '下一章'"
        @click="goTo(page === 3 ? 0 : page + 1)"
      >
        {{ page === 3 ? '↶' : '↗' }}
      </button>
    </footer>
    <dialog
      ref="dialog"
      class="folio-dialog"
      :class="{ 'about-dialog': dialogKind === 'about' }"
      @cancel="dialogKind = null"
      @close="dialogKind = null"
      @click="dialogClick"
    >
      <template v-if="dialogKind === 'image'"
        ><header>
          <span>ODIN / VISUAL ARCHIVE</span
          ><span
            >{{ number(imageIndex + 1) }} —
            {{ number(FOLIO_ARTWORK.length) }}</span
          ><button autofocus aria-label="关闭图像" @click="closeDialog">
            关闭 ×
          </button>
        </header>
        <div class="lightbox-image">
          <img :src="currentImage.src" :alt="currentImage.alt" />
        </div>
        <footer>
          <button aria-label="上一张图像" @click="nextImage(-1)">←</button>
          <div>
            <h2>{{ currentImage.title }}</h2>
            <p>{{ currentImage.caption }}</p>
            <a :href="currentImage.source" target="_blank" rel="noreferrer"
              >官方原图 ↗</a
            >
          </div>
          <button aria-label="下一张图像" @click="nextImage(1)">→</button>
        </footer></template
      >
      <template v-else-if="dialogKind === 'about'"
        ><header>
          <span>COLOPHON / 设定集信息</span
          ><button autofocus aria-label="关闭介绍" @click="closeDialog">
            关闭 ×
          </button>
        </header>
        <div class="colophon">
          <span class="eyebrow">AN INDEPENDENT VISUAL STUDY</span>
          <h2>形体、机械，<br />以及想象。</h2>
          <p>
            这是一册可以触摸的奥丁设定集。以现有舰船模型为基础，让三维形体进入蚀刻、线稿与素模三种视觉语言；翻页，观察武备的展开，也走入舰船之中的空间。
          </p>
          <p>{{ FOLIO_NOTICE }}</p>
          <a :href="FOLIO_SOURCE" target="_blank" rel="noreferrer"
            >前往奥丁官方资料 ↗</a
          >
          <h3>概念配置索引</h3>
          <p class="fact-note">{{ FOLIO_FACT_NOTE }}</p>
          <dl>
            <div v-for="fact in FOLIO_FACTS" :key="fact.id">
              <dt>{{ fact.label }}</dt>
              <dd>
                <b>{{ fact.value }}</b
                ><a
                  :href="fact.source"
                  target="_blank"
                  rel="noreferrer"
                  :aria-label="`${fact.label}的来源`"
                  >来源 ↗</a
                >
              </dd>
            </div>
          </dl>
          <small>ODIN MONOGRAPH / EDITION 01 / v0.26.0-rc.1</small>
        </div></template
      >
    </dialog>
  </div>
</template>
