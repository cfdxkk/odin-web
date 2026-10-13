<script setup lang="ts">
import { FILM_DURATION, MODES, isPlaying, nextPlayback, sampleOdinMotion } from '~/lib/odin-motion'
import { ODIN_TOUR, clampTourIndex, selectTourChapter, tourWheelTarget } from '~/lib/odin-tour'
import { CHAPTER_COPY } from '~/lib/odin-copy'
import { ODIN_WALLPAPERS } from '~/lib/odin-artwork'
import { WEAPON_TOUR, clampWeaponStep } from '~/lib/odin-weapon-tour'
import { INTERIOR_SECTIONS } from '~/lib/odin-interiors'

const { locale, copy: c, setLocale } = useOdinLocale()
const viewer = ref<{ seek: (t: number) => void; capturePhoto: () => Promise<Blob> }>()
const reviewMode = ref(false), activeChapter = ref(0), modelPanel = ref<HTMLElement>()
const ready = ref(false), progress = ref(0), explore = ref(false), deployed = ref(true), lowPower = ref(false)
const viewportActive = ref(true), reducedMotion = ref(false)
const changingView = ref(false)
const weaponStep = ref(0)
const calloutOrigin = ref({ x: 0, y: 0, visible: false })
const capturing = ref(false), photoStatus = ref('')
const timelineTime = ref(0)
let rewindFrame = 0, rewindStarted = 0
function cancelRewind() { cancelAnimationFrame(rewindFrame); rewindFrame = 0; timelineTime.value = filmTime.value }
function onFilmTick(time: number) { filmTime.value = time; if (!rewindFrame) timelineTime.value = time }
function rewindTimeline() {
  cancelAnimationFrame(rewindFrame)
  if (reducedMotion.value) { timelineTime.value = filmTime.value; return }
  rewindStarted = performance.now()
  const update = (now: number) => {
    const t = Math.min(1, (now - rewindStarted) / 650), eased = t * t * (3 - 2 * t)
    timelineTime.value = FILM_DURATION + (filmTime.value - FILM_DURATION) * eased
    rewindFrame = t < 1 ? requestAnimationFrame(update) : 0
  }
  rewindFrame = requestAnimationFrame(update)
}
async function capturePhoto() {
  if (!viewer.value || capturing.value) return
  capturing.value = true; photoStatus.value = ''
  try {
    const blob = await viewer.value.capturePhoto(), url = URL.createObjectURL(blob)
    const link = document.createElement('a'); link.href = url; link.download = 'odin-free-view.png'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 30000)
    photoStatus.value = locale.value === 'zh' ? '已导出透明 PNG' : 'Transparent PNG exported'
  } catch { photoStatus.value = locale.value === 'zh' ? '导出失败，请重试' : 'Export failed. Please retry.' }
  finally { capturing.value = false }
}
const chromeVisible = computed(() => activeChapter.value === 0 && viewportActive.value)
const archiveActive = ref(false)
const headerVisible = computed(() => chromeVisible.value || archiveActive.value)
// The homepage autoplays; an explicit pause remains in force across chapters.
const playback = ref({ userPaused: false, scrubbing: false })
const sequenceOverride = ref(false)
const playing = computed(() => isPlaying(playback.value))
const filmPlaying = computed(() => !explore.value && playing.value && (activeChapter.value === 0 || sequenceOverride.value))
function togglePlayback() {
  if (activeChapter.value === 1) {
    playback.value = nextPlayback(playback.value, 'toggle')
    sequenceOverride.value = false
    return
  }
  if (filmPlaying.value) playback.value = nextPlayback(playback.value, 'toggle')
  else { playback.value = { ...playback.value, userPaused: false }; sequenceOverride.value = true }
}
const beginScrub = () => { cancelRewind(); playback.value = nextPlayback(playback.value, 'scrub-start') }
const endScrub = () => { playback.value = nextPlayback(playback.value, 'scrub-end') }
const filmTime = ref(0), error = ref(''), showAbout = ref(false)
const aboutDialog = ref<HTMLDialogElement>()
watch(showAbout, value => { if (value) aboutDialog.value?.showModal(); else aboutDialog.value?.close() })
const chapters = computed(() => ODIN_TOUR.map(shot => {
  const copy = CHAPTER_COPY[locale.value][shot.id]
  const interior = shot.id === 'bridge' ? INTERIOR_SECTIONS.bridge : shot.id === 'engines' ? INTERIOR_SECTIONS.aft : undefined
  return { ...shot, ...copy, body: interior?.[locale.value].body ?? copy.body, specs: interior ? [] : copy.specs, interior }
}))
const currentChapter = computed(() => chapters.value[activeChapter.value]!)
const phaseIndex = computed(() => filmTime.value < 12 ? 0 : filmTime.value < 32 ? 1 : 2)
const phases = computed(() => [c.value.exterior, c.value.combat, c.value.navigation])
const formatTime = (t: number) => `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}`
const clock = computed(() => formatTime(filmTime.value))
const artworkIndex = ref(0)
const artwork = computed(() => ODIN_WALLPAPERS[artworkIndex.value]!)
function changeArtwork(index: number) { artworkIndex.value = (index + ODIN_WALLPAPERS.length) % ODIN_WALLPAPERS.length }
function goToChapter(index: number) {
  const next = clampTourIndex(index), element = document.getElementById(ODIN_TOUR[next]!.id)
  if (next === 1 && activeChapter.value !== 1) selectWeaponStep(activeChapter.value < 1 ? 0 : WEAPON_TOUR.length - 1)
  element?.scrollIntoView({ block: 'start', behavior: reducedMotion.value || Math.abs(next - activeChapter.value) > 1 ? 'instant' : 'smooth' })
}
function selectWeaponStep(index: number) {
  const next = clampWeaponStep(index)
  if (next === weaponStep.value) { scheduleWeaponConnector(); return }
  weaponStep.value = next
  nextTick(scheduleWeaponConnector)
}
function advanceChapter(index: number) {
  if (index === 1 && weaponStep.value < WEAPON_TOUR.length - 1) selectWeaponStep(weaponStep.value + 1)
  else goToChapter(index + 1)
}
function nextStepLabel(index: number) {
  return index === 1 && weaponStep.value < WEAPON_TOUR.length - 1 ? locale.value === 'zh' ? '下一项武备' : 'Next weapon' : c.value.nextChapter
}
function goToArchive() { document.getElementById('archive')?.scrollIntoView({ block: 'start', behavior: reducedMotion.value ? 'instant' : 'smooth' }) }
async function choosePhase(index: number) {
  cancelRewind()
  explore.value = false
  await nextTick()
  viewer.value?.seek(filmPlaying.value ? MODES[index]!.time : [0, 24, 46][index]!)
}
watch(locale, () => {
  if (!viewportActive.value || reviewMode.value) return
  const chapter = activeChapter.value
  nextTick(() => document.getElementById(ODIN_TOUR[chapter]!.id)?.scrollIntoView({ block: 'start', behavior: 'instant' }))
})
function toggleExplore() {
  cancelRewind(); photoStatus.value = ''
  if (!explore.value) deployed.value = sampleOdinMotion(filmTime.value).deployment > .5
  explore.value = !explore.value
}
function scrub(event: Event) { cancelRewind(); viewer.value?.seek(Number((event.target as HTMLInputElement).value)) }
function scrubKey(event: KeyboardEvent) { if (/^(Arrow|Home|End|Page)/.test(event.key)) beginScrub() }
function keyboard(event: KeyboardEvent) {
  const element = event.target as HTMLElement
  if (/INPUT|BUTTON|A|TEXTAREA|SELECT/.test(element.tagName) || showAbout.value) return
  if (event.code === 'Space' && viewportActive.value) { event.preventDefault(); if (ready.value && !explore.value) togglePlayback() }
  if (event.key.toLowerCase() === 'r' && !explore.value && viewportActive.value) { cancelRewind(); viewer.value?.seek(ODIN_TOUR[activeChapter.value]!.time) }
}
watch(activeChapter, (chapter, previous) => {
  explore.value = false
  sequenceOverride.value = false
  if (chapter === 1 && previous !== 1) selectWeaponStep(previous < 1 ? 0 : WEAPON_TOUR.length - 1)
  else scheduleWeaponConnector()
})
let scrollFrame = 0
let connectorFrame = 0
function scheduleWeaponConnector() {
  if (!import.meta.client || connectorFrame) return
  connectorFrame = requestAnimationFrame(updateWeaponConnector)
}
function updateWeaponConnector() {
  connectorFrame = 0
  const origin = document.querySelector<HTMLElement>('#batteries .weapon-callout-origin')
  const canvas = modelPanel.value?.querySelector<HTMLCanvasElement>('.odin-canvas')
  if (activeChapter.value !== 1 || !viewportActive.value || !ready.value || !origin || !canvas) {
    calloutOrigin.value = { ...calloutOrigin.value, visible: false }
    return
  }
  const bounds = canvas.getBoundingClientRect(), label = origin.getBoundingClientRect()
  const startX = label.left + label.width / 2 - bounds.left
  const startY = label.top + label.height / 2 - bounds.top
  calloutOrigin.value = { x: startX, y: startY, visible: bounds.width > 0 && bounds.height > 0 && label.width > 0 && label.height > 0 }
}
watch([locale, ready, viewportActive], () => nextTick(scheduleWeaponConnector))
let wheelAmount = 0, wheelLastAt = 0, wheelCommitted = false
function tourAnchor() {
  // Each chapter occupies a whole viewport; the canvas fills that viewport too.
  return 0
}
function onTourWheel(event: WheelEvent) {
  const element = event.target as Element
  if (reviewMode.value || showAbout.value || event.ctrlKey || event.metaKey || Math.abs(event.deltaX) >= Math.abs(event.deltaY)) return
  const archiveTop = document.getElementById('archive')?.getBoundingClientRect().top ?? Infinity
  const fromArchive = !!element.closest?.('#archive') && event.deltaY < 0 && Math.abs(archiveTop) < 48
  if (!element.closest?.('#tour') && !fromArchive) return
  if (explore.value && element.closest('.scene-wrap')) return
  const top = document.getElementById(ODIN_TOUR[activeChapter.value]!.id)?.getBoundingClientRect().top
  if (top === undefined) return
  const next = fromArchive ? 3 : tourWheelTarget(activeChapter.value, event.deltaY > 0 ? 1 : -1, top, tourAnchor(), true)
  if (next === undefined) return
  const direction = event.deltaY > 0 ? 1 : -1
  const nextWeapon = weaponStep.value + direction
  const advanceWeapon = !fromArchive && activeChapter.value === 1 && next !== activeChapter.value && Math.abs(top - tourAnchor()) <= 48 && nextWeapon >= 0 && nextWeapon < WEAPON_TOUR.length
  event.preventDefault()
  const now = performance.now()
  if (now - wheelLastAt > 180) { wheelAmount = 0; wheelCommitted = false }
  wheelLastAt = now
  if (wheelCommitted) return
  wheelAmount += event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1)
  if (Math.abs(wheelAmount) < 40) return
  wheelCommitted = true
  if (advanceWeapon) selectWeaponStep(nextWeapon)
  else if (next === ODIN_TOUR.length) goToArchive()
  else goToChapter(next)
}
function updateChapter() {
  scrollFrame = 0
  if (reviewMode.value) return
  const tour = document.getElementById('tour')?.getBoundingClientRect()
  archiveActive.value = (document.getElementById('archive')?.getBoundingClientRect().top ?? Infinity) < window.innerHeight * .5
  const header = headerVisible.value ? document.querySelector('.site-header')?.getBoundingClientRect().height || 92 : 0
  // Once the canvas has scrolled behind the fixed header, it is no longer
  // visible. Observing its full box alone would keep rendering that hidden strip.
  viewportActive.value = !!tour && tour.bottom > header + 1 && tour.top < window.innerHeight
  const anchor = tourAnchor()
  const tops = ODIN_TOUR.map(shot => document.getElementById(shot.id)?.getBoundingClientRect().top ?? Infinity)
  activeChapter.value = selectTourChapter(tops, anchor)
  scheduleWeaponConnector()
}
function onScroll() { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateChapter) }
onMounted(() => {
  reviewMode.value = new URLSearchParams(window.location.search).get('review') === 'secondary'
  reducedMotion.value = matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reducedMotion.value) playback.value = { ...playback.value, userPaused: true }
  lowPower.value = window.innerWidth < 700
  window.addEventListener('keydown', keyboard)
  window.addEventListener('pointerup', endScrub)
  window.addEventListener('pointercancel', endScrub)
  window.addEventListener('blur', endScrub)
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('wheel', onTourWheel, { passive: false })
  window.addEventListener('resize', onScroll, { passive: true })
  nextTick(() => {
    if (!modelPanel.value) return
    updateChapter()
  })
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', keyboard)
  window.removeEventListener('pointerup', endScrub)
  window.removeEventListener('pointercancel', endScrub)
  window.removeEventListener('blur', endScrub)
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('wheel', onTourWheel)
  window.removeEventListener('resize', onScroll)
  cancelAnimationFrame(scrollFrame)
  cancelAnimationFrame(connectorFrame)
  cancelAnimationFrame(rewindFrame)
})
</script>

<template>
  <ClientOnly v-if="reviewMode"><ArticulationReview /></ClientOnly>
  <div v-else class="site-shell">
    <header class="site-header" :class="{ 'is-hidden': !headerVisible }" :inert="!headerVisible" :aria-hidden="!headerVisible">
      <a href="#overview" class="brand" :aria-label="c.home" @click.prevent="goToChapter(0)"><img src="/images/odin-founders-badge-v0.11.47.png" alt="" width="46" height="46" /><span>ODIN<small>{{ c.brandSub }}</small></span></a>
      <nav :aria-label="c.navLabel"><a href="#overview" @click.prevent="goToChapter(0)"><span>01</span>{{ c.navTour }}</a><a href="#archive"><span>02</span>{{ c.navArt }}</a><button @click="showAbout = true"><span>03</span>{{ c.navAbout }}</button></nav>
      <div class="header-right"><button class="language-switch" :aria-label="c.switchLanguage" @click="setLocale(locale === 'zh' ? 'en' : 'zh')">{{ locale === 'zh' ? 'EN' : 'ZH' }} <span aria-hidden="true">↔</span></button></div>
    </header>

    <main>
      <div id="tour" class="tour-layout">
        <section ref="modelPanel" class="model-panel" :class="{ 'is-exploring': explore, 'has-home-controls': chromeVisible }" :aria-label="c.canvasLabel" :data-chapter="currentChapter.id" :data-weapon-step="activeChapter === 1 ? weaponStep : undefined">
          <div class="panel-toprail"><nav class="chapter-index" :aria-label="c.chapterNav"><button v-for="(chapter, index) in chapters" :key="chapter.id" :aria-label="`${String(index + 1).padStart(2,'0')} / ${chapter.label}`" :aria-current="activeChapter === index ? 'step' : undefined" @click="goToChapter(index)"><span>{{ String(index + 1).padStart(2, '0') }}</span></button></nav></div>
          <div class="scene-wrap">
            <ClientOnly><OdinScene ref="viewer" :playing="playing" :film="filmPlaying" :explore="explore" :deployed="deployed" :low-power="lowPower" :view-index="activeChapter" :weapon-step="activeChapter === 1 ? weaponStep : undefined" :callout-origin="calloutOrigin" :active="viewportActive" :reduced-motion="reducedMotion" :canvas-label="c.canvasLabel" @ready="ready = true" @progress="progress = $event" @tick="onFilmTick" @loop="rewindTimeline" @transition="changingView = $event" @fail="error = $event" /></ClientOnly>
            <div class="scene-shade" aria-hidden="true" />
            <div class="viewport-status" :aria-hidden="!chromeVisible">{{ !ready ? c.loading : explore ? c.manualView : changingView ? c.changingView : filmPlaying ? c.playing : c.paused }}</div>
            <Transition name="fade"><div v-if="!ready && !error" class="loading-state" role="status"><p class="eyebrow">{{ c.loading }}</p><p>{{ c.loadingModel }} <span>{{ Math.round(progress) }}%</span></p><div class="loading-track"><span :style="{ width: `${progress}%` }" /></div></div></Transition>
            <div v-if="error" class="error-state" role="alert"><p class="eyebrow">{{ c.unavailable }}</p><h2>{{ c.errorTitle }}</h2><p>{{ c.errorBody }}</p><button class="outline-button" @click="reloadNuxtApp({ force: true })">{{ c.reload }}</button><details><summary>{{ c.errorDetails }}</summary>{{ error }}</details></div>
          </div>
          <div class="viewer-console" :inert="!chromeVisible" :aria-hidden="!chromeVisible">
            <div class="view-actions">
              <div class="manual-actions" :class="{ visible: explore }" :inert="!explore" :aria-hidden="!explore"><button class="mode-switch" @click="deployed = !deployed">{{ deployed ? c.switchNav : c.switchScm }} <span aria-hidden="true">↔</span></button><button class="photo-button" :disabled="capturing" @click="capturePhoto"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h5l2-3h4l2 3h5v13H3Z"/><circle cx="12" cy="13" r="4"/></svg>{{ capturing ? c.capturing : c.photo }}</button></div>
              <button class="explore-button" :disabled="!ready" :aria-pressed="explore" @click="toggleExplore">{{ explore ? c.returnGuide : c.manual }}<span aria-hidden="true">↔</span></button>
            </div>
            <div class="manual-hint" :class="{ visible: explore }" aria-live="polite">{{ photoStatus || c.controlsHint }}</div>
            <div class="playback-top"><button class="play-button" :disabled="!ready || explore" :aria-label="filmPlaying ? c.pause : c.play" @click="togglePlayback"><svg v-if="filmPlaying" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4v12M14 4v12" /></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m6 3 11 7-11 7Z" /></svg></button><span class="timecode">{{ clock }} <span>/ {{ formatTime(FILM_DURATION) }}</span></span><span class="playback-label">{{ c.sequence }}</span><button class="quality-button" :aria-pressed="!lowPower" :aria-label="lowPower ? c.enableHigh : c.enableLow" @click="lowPower = !lowPower">{{ lowPower ? c.lowQuality : c.highQuality }}</button></div>
            <input class="timeline" type="range" min="0" :max="FILM_DURATION - .01" step="0.1" :value="timelineTime" :disabled="!ready || explore" :aria-label="c.animationTime" :aria-valuetext="clock" :style="{ '--progress': `${timelineTime / FILM_DURATION * 100}%` }" @pointerdown="beginScrub" @pointerup="endScrub" @pointercancel="endScrub" @keydown="scrubKey" @keyup="endScrub" @change="endScrub" @input="scrub" />
            <div class="phase-buttons"><button v-for="(phase, index) in phases" :key="index" :disabled="!ready" :aria-pressed="!explore && phaseIndex === index" @click="choosePhase(index)">{{ phase }}</button></div>
          </div>
        </section>
        <div class="story-rail">
          <article v-for="(chapter, index) in chapters" :id="chapter.id" :key="chapter.id" class="story-chapter" :class="{ 'chapter-intro': index === 0, 'weapon-chapter': index === 1, current: index === activeChapter }" :aria-labelledby="`${chapter.id}-title`" :data-index="index">
            <div class="chapter-content">
            <WeaponStory v-if="index === 1" :step="weaponStep" :locale="locale" :active="activeChapter === 1 && viewportActive" @select="selectWeaponStep" />
            <template v-else>
            <div class="chapter-heading"><p class="eyebrow">{{ String(index + 1).padStart(2, '0') }} / {{ chapter.label }}</p><h1 v-if="index === 0" :id="`${chapter.id}-title`">ODIN</h1><h2 v-else :id="`${chapter.id}-title`">{{ chapter.title }}</h2><p v-if="index === 0" class="vehicle-class">{{ c.vehicleClass }}<span>{{ c.manufacturer }}</span></p></div>
            <p v-if="index > 0" class="chapter-body">{{ chapter.body }}</p>
            <dl v-if="chapter.specs.length" class="chapter-specs"><div v-for="spec in chapter.specs" :key="spec[0]"><dt>{{ spec[0] }}</dt><dd>{{ spec[1] }}</dd></div></dl>
            <ul v-if="chapter.interior" class="interior-specs"><li v-for="spec in chapter.interior[locale].specs" :key="spec">{{ spec }}</li></ul>
            <InteriorGallery v-if="chapter.interior" :images="chapter.interior.images" :locale="locale" />
            </template>
            <div class="chapter-bottom"><button v-if="index < chapters.length - 1" class="scroll-cue next-chapter" :aria-label="nextStepLabel(index)" @click="advanceChapter(index)"><svg viewBox="0 0 40 64" aria-hidden="true"><path d="M20 3v52M5 40l15 15 15-15" /></svg></button><a v-else class="scroll-cue next-chapter" :aria-label="c.viewArchive" href="#archive" @click.prevent="goToArchive"><svg viewBox="0 0 40 64" aria-hidden="true"><path d="M20 3v52M5 40l15 15 15-15" /></svg></a></div>
            </div>
          </article>
        </div>
      </div>

      <section id="archive" class="art-archive" :aria-label="c.gallery">
        <div class="archive-heading"><h2>{{ c.artTitle }}</h2><a class="text-link" href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">{{ c.artSource }} ↗</a></div>
        <div class="gallery-layout"><figure class="artwork-figure"><div class="artwork-well"><img :key="artwork.src" :src="artwork.src" :alt="`${c.artTitle} ${artworkIndex + 1}`" :width="artwork.width" :height="artwork.height" loading="lazy" decoding="async" /></div><figcaption><span>© Cloud Imperium Games</span><div class="gallery-controls"><button :aria-label="c.previousArt" @click="changeArtwork(artworkIndex - 1)">←</button><span>{{ String(artworkIndex + 1).padStart(2, '0') }}<small> / {{ ODIN_WALLPAPERS.length }}</small></span><button class="next-art" :aria-label="c.nextArt" @click="changeArtwork(artworkIndex + 1)">→</button></div></figcaption></figure></div>
      </section>
    </main>

    <OdinFooter :locale="locale" @overview="goToChapter(0)" />

    <Teleport to="body"><dialog ref="aboutDialog" class="about-dialog" :aria-label="c.sourceNotes" @close="showAbout = false" @cancel="showAbout = false"><div class="dialog-backdrop" @click="showAbout = false" /><section role="document"><button class="dialog-close" :aria-label="c.closeAbout" @click="showAbout = false">×</button><p class="eyebrow">{{ c.projectNotes }}</p><h2>{{ c.aboutTitle }}</h2><p>{{ c.aboutIntro }}</p><p>{{ c.aboutDesign }}</p><div class="credits"><a href="https://www.youtube.com/watch?v=EKvbJh87rpY" target="_blank" rel="noopener noreferrer">{{ c.inspiration }} ↗</a><a href="https://www.youtube.com/watch?v=CFoQp6wRjPo" target="_blank" rel="noopener noreferrer">{{ c.developerShow }} ↗</a><a href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">{{ c.shipSource }} ↗</a><a href="https://media.robertsspaceindustries.com/84qwqukbwkgsk/source.png" target="_blank" rel="noopener noreferrer">{{ c.badgeSource }} ↗</a></div><small>{{ c.modelNotice }}</small></section></dialog></Teleport>
  </div>
</template>
