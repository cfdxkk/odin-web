<script setup lang="ts">
import { FILM_DURATION, MODES, isPlaying, nextPlayback, sampleOdinMotion } from '~/lib/odin-motion'
import { ODIN_TOUR, clampTourIndex, selectTourChapter, tourWheelTarget } from '~/lib/odin-tour'
import { CHAPTER_COPY } from '~/lib/odin-copy'
import { ODIN_ARTWORK } from '~/lib/odin-artwork'

const { locale, copy: c, setLocale } = useOdinLocale()
const viewer = ref<{ seek: (t: number) => void }>()
const reviewMode = ref(false), activeChapter = ref(0), modelPanel = ref<HTMLElement>()
const ready = ref(false), progress = ref(0), explore = ref(false), deployed = ref(true), lowPower = ref(false)
const viewportActive = ref(true), reducedMotion = ref(false)
const changingView = ref(false)
// Guided views start still. Playing the sequence is an explicit, persistent choice.
const playback = ref({ userPaused: true, scrubbing: false })
const playing = computed(() => isPlaying(playback.value))
const togglePlayback = () => { playback.value = nextPlayback(playback.value, 'toggle') }
const beginScrub = () => { playback.value = nextPlayback(playback.value, 'scrub-start') }
const endScrub = () => { playback.value = nextPlayback(playback.value, 'scrub-end') }
const filmTime = ref(0), error = ref(''), showAbout = ref(false)
const aboutDialog = ref<HTMLDialogElement>()
watch(showAbout, value => { if (value) aboutDialog.value?.showModal(); else aboutDialog.value?.close() })
const chapters = computed(() => ODIN_TOUR.map(shot => ({ ...shot, ...CHAPTER_COPY[locale.value][shot.id] })))
const currentChapter = computed(() => chapters.value[activeChapter.value]!)
const phaseIndex = computed(() => filmTime.value < 12 ? 0 : filmTime.value < 32 ? 1 : 2)
const phases = computed(() => [c.value.exterior, c.value.combat, c.value.navigation])
const configuration = computed(() => explore.value ? (deployed.value ? 'SCM' : 'NAV') : sampleOdinMotion(filmTime.value).deployment > .001 ? 'SCM' : 'NAV')
const formatTime = (t: number) => `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}`
const clock = computed(() => formatTime(filmTime.value))
const artworkIndex = ref(0)
const artwork = computed(() => ODIN_ARTWORK[artworkIndex.value]!)
const artworkCaption = computed(() => artwork.value[locale.value])
function changeArtwork(index: number) { artworkIndex.value = (index + ODIN_ARTWORK.length) % ODIN_ARTWORK.length }
function goToChapter(index: number) {
  const next = clampTourIndex(index), element = document.getElementById(ODIN_TOUR[next]!.id)
  element?.scrollIntoView({ block: 'start', behavior: reducedMotion.value || Math.abs(next - activeChapter.value) > 1 ? 'instant' : 'smooth' })
}
function choosePhase(index: number) {
  explore.value = false
  viewer.value?.seek(playing.value ? MODES[index]!.time : [0, 24, 46][index]!)
}
watch(locale, () => {
  if (!viewportActive.value || reviewMode.value) return
  const chapter = activeChapter.value
  nextTick(() => document.getElementById(ODIN_TOUR[chapter]!.id)?.scrollIntoView({ block: 'start', behavior: 'instant' }))
})
function toggleExplore() {
  if (!explore.value) deployed.value = sampleOdinMotion(filmTime.value).deployment > .5
  explore.value = !explore.value
}
function scrub(event: Event) { viewer.value?.seek(Number((event.target as HTMLInputElement).value)) }
function scrubKey(event: KeyboardEvent) { if (/^(Arrow|Home|End|Page)/.test(event.key)) beginScrub() }
function keyboard(event: KeyboardEvent) {
  const element = event.target as HTMLElement
  if (/INPUT|BUTTON|A|TEXTAREA|SELECT/.test(element.tagName) || showAbout.value) return
  if (event.code === 'Space' && viewportActive.value) { event.preventDefault(); if (ready.value && !explore.value) togglePlayback() }
  if (event.key.toLowerCase() === 'r' && !explore.value && viewportActive.value) viewer.value?.seek(ODIN_TOUR[activeChapter.value]!.time)
}
watch(activeChapter, () => {
  explore.value = false
})
let viewportObserver: IntersectionObserver | undefined, scrollFrame = 0
let wheelAmount = 0, wheelLastAt = 0, wheelCommitted = false
function tourAnchor() {
  const header = document.querySelector('.site-header')?.getBoundingClientRect().height || 80
  return window.innerWidth <= 800 ? (modelPanel.value?.getBoundingClientRect().bottom || header) + 16 : header + 32
}
function onTourWheel(event: WheelEvent) {
  const element = event.target as Element
  if (reviewMode.value || showAbout.value || event.ctrlKey || event.metaKey || Math.abs(event.deltaX) >= Math.abs(event.deltaY) || !element.closest?.('#tour')) return
  if (explore.value && element.closest('.scene-wrap')) return
  const top = document.getElementById(ODIN_TOUR[activeChapter.value]!.id)?.getBoundingClientRect().top
  if (top === undefined) return
  const next = tourWheelTarget(activeChapter.value, event.deltaY > 0 ? 1 : -1, top, tourAnchor())
  if (next === undefined) return
  event.preventDefault()
  const now = performance.now()
  if (now - wheelLastAt > 180) { wheelAmount = 0; wheelCommitted = false }
  wheelLastAt = now
  if (wheelCommitted) return
  wheelAmount += event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1)
  if (Math.abs(wheelAmount) < 40) return
  wheelCommitted = true
  goToChapter(next)
}
function updateChapter() {
  scrollFrame = 0
  if (reviewMode.value) return
  const anchor = tourAnchor()
  const tops = ODIN_TOUR.map(shot => document.getElementById(shot.id)?.getBoundingClientRect().top ?? Infinity)
  activeChapter.value = selectTourChapter(tops, anchor)
}
function onScroll() { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateChapter) }
const reviewUrl = computed(() => `/?review=secondary&lang=${locale.value}&v=0.14.0-rc.1`)
onMounted(() => {
  reviewMode.value = new URLSearchParams(window.location.search).get('review') === 'secondary'
  reducedMotion.value = matchMedia('(prefers-reduced-motion: reduce)').matches
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
    viewportObserver = new IntersectionObserver(entries => { viewportActive.value = !!entries[0]?.isIntersecting && entries[0].intersectionRatio > .05 }, { threshold: [0, .05] })
    viewportObserver.observe(modelPanel.value.querySelector('.scene-wrap')!)
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
  viewportObserver?.disconnect()
  cancelAnimationFrame(scrollFrame)
})
</script>

<template>
  <ClientOnly v-if="reviewMode"><ArticulationReview /></ClientOnly>
  <div v-else class="site-shell">
    <header class="site-header">
      <a href="#overview" class="brand" :aria-label="c.home" @click.prevent="goToChapter(0)"><img src="/images/odin-founders-badge-v0.11.47.png" alt="" width="46" height="46" /><span>ODIN<small>{{ c.brandSub }}</small></span></a>
      <nav :aria-label="c.navLabel"><a href="#overview" @click.prevent="goToChapter(0)"><span>01</span>{{ c.navTour }}</a><a href="#archive"><span>02</span>{{ c.navArt }}</a><button @click="showAbout = true"><span>03</span>{{ c.navAbout }}</button></nav>
      <div class="header-right"><span class="header-meta">2026 / {{ c.document }}</span><button class="language-switch" :aria-label="c.switchLanguage" @click="setLocale(locale === 'zh' ? 'en' : 'zh')">{{ locale === 'zh' ? 'EN' : 'ZH' }} <span aria-hidden="true">↔</span></button></div>
    </header>

    <main>
      <div id="tour" class="tour-layout">
        <section ref="modelPanel" class="model-panel" :class="{ 'is-exploring': explore }" :aria-label="c.canvasLabel" :data-chapter="currentChapter.id">
          <div class="panel-toprail"><span>{{ c.realTime }}</span><nav class="chapter-index" :aria-label="c.chapterNav"><button v-for="(chapter, index) in chapters" :key="chapter.id" :aria-label="`${String(index + 1).padStart(2,'0')} / ${chapter.label}`" :aria-current="activeChapter === index ? 'step' : undefined" @click="goToChapter(index)"><span>{{ String(index + 1).padStart(2, '0') }}</span></button></nav></div>
          <div class="scene-wrap">
            <ClientOnly><OdinScene ref="viewer" :playing="playing" :explore="explore" :deployed="deployed" :low-power="lowPower" :view-index="activeChapter" :active="viewportActive" :reduced-motion="reducedMotion" :canvas-label="c.canvasLabel" @ready="ready = true" @progress="progress = $event" @tick="filmTime = $event" @transition="changingView = $event" @fail="error = $event" /></ClientOnly>
            <div class="viewport-status">{{ !ready ? c.loading : explore ? c.manualView : changingView ? c.changingView : playing ? c.playing : c.paused }}<span>{{ configuration }} / {{ c.config }}</span></div>
            <Transition name="fade"><div v-if="!ready && !error" class="loading-state" role="status"><p class="eyebrow">OD—77 / {{ c.loading }}</p><p>{{ c.loadingModel }} <span>{{ Math.round(progress) }}%</span></p><div class="loading-track"><span :style="{ width: `${progress}%` }" /></div></div></Transition>
            <div v-if="error" class="error-state" role="alert"><p class="eyebrow">{{ c.unavailable }}</p><h2>{{ c.errorTitle }}</h2><p>{{ c.errorBody }}</p><button class="outline-button" @click="reloadNuxtApp({ force: true })">{{ c.reload }}</button><details><summary>{{ c.errorDetails }}</summary>{{ error }}</details></div>
            <button v-if="ready" class="explore-button" :aria-pressed="explore" @click="toggleExplore"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm0 0v18M4 7.5l8 5 8-5" /></svg>{{ explore ? c.returnGuide : c.manual }}<span aria-hidden="true">↗</span></button>
          </div>
          <div class="viewer-console">
            <div v-if="explore" class="explore-tools"><p>{{ c.controlsHint }}</p><button @click="deployed = !deployed">{{ deployed ? c.switchNav : c.switchScm }} →</button></div>
            <div class="playback-top"><button class="play-button" :disabled="!ready || explore" :aria-label="playing ? c.pause : c.play" @click="togglePlayback"><svg v-if="playing" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4v12M14 4v12" /></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m6 3 11 7-11 7Z" /></svg></button><span class="timecode">{{ clock }} <span>/ {{ formatTime(FILM_DURATION) }}</span></span><span class="playback-label">{{ c.sequence }}</span><button class="quality-button" :aria-pressed="!lowPower" :aria-label="lowPower ? c.enableHigh : c.enableLow" @click="lowPower = !lowPower">{{ lowPower ? c.lowQuality : c.highQuality }}</button></div>
            <input class="timeline" type="range" min="0" :max="FILM_DURATION - .01" step="0.1" :value="filmTime" :disabled="!ready || explore" :aria-label="c.animationTime" :aria-valuetext="clock" :style="{ '--progress': `${filmTime / FILM_DURATION * 100}%` }" @pointerdown="beginScrub" @pointerup="endScrub" @pointercancel="endScrub" @keydown="scrubKey" @keyup="endScrub" @change="endScrub" @input="scrub" />
            <div class="phase-buttons"><button v-for="(phase, index) in phases" :key="index" :disabled="!ready" :aria-pressed="!explore && phaseIndex === index" @click="choosePhase(index)"><span>0{{ index + 1 }}</span>{{ phase }}</button></div>
          </div>
          <div class="panel-footrail"><span>{{ c.shortcuts }}</span><span>{{ explore ? c.manualView : currentChapter.label }}</span></div>
        </section>
        <div class="story-rail">
          <article v-for="(chapter, index) in chapters" :id="chapter.id" :key="chapter.id" class="story-chapter" :class="{ 'chapter-intro': index === 0, current: index === activeChapter }" :aria-labelledby="`${chapter.id}-title`" :data-index="index">
            <div class="chapter-topline"><span class="eyebrow">{{ c.guide }}</span><span class="folio">{{ String(index + 1).padStart(2, '0') }} / {{ String(chapters.length).padStart(2, '0') }}</span></div>
            <div class="chapter-heading"><p class="eyebrow">{{ String(index + 1).padStart(2, '0') }} / {{ chapter.label }}</p><h1 v-if="index === 0" :id="`${chapter.id}-title`">ODIN</h1><h2 v-else :id="`${chapter.id}-title`">{{ chapter.title }}</h2><p v-if="index === 0" class="vehicle-class">{{ c.vehicleClass }}<span>{{ c.manufacturer }}</span></p></div>
            <p class="chapter-body">{{ chapter.body }}</p><p class="chapter-detail">{{ chapter.detail }}</p>
            <dl class="chapter-specs"><div v-for="spec in chapter.specs" :key="spec[0]"><dt>{{ spec[0] }}</dt><dd>{{ spec[1] }}</dd></div></dl>
            <div class="chapter-bottom"><button v-if="index < chapters.length - 1" class="next-chapter" @click="goToChapter(index + 1)">{{ index === 0 ? c.scrollHint : c.nextChapter }} ↓</button><a v-else class="next-chapter" href="#archive">{{ c.viewArchive }} ↓</a></div>
            <p v-if="index === 0" class="concept-notice">{{ c.conceptNotice }}</p>
          </article>
        </div>
      </div>

      <section id="archive" class="art-archive" :aria-label="c.gallery">
        <div class="archive-heading"><div><p class="eyebrow">02 / {{ c.artArchive }}</p><h2>{{ c.artTitle }}</h2></div><p>{{ c.artBody }}</p><a class="text-link" href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">{{ c.artSource }} ↗</a></div>
        <div class="gallery-layout"><figure class="artwork-figure"><div class="artwork-well"><img :key="artwork.src" :src="artwork.src" :alt="artworkCaption.alt" :width="artwork.width" :height="artwork.height" loading="lazy" decoding="async" /></div><figcaption><span>{{ String(artworkIndex + 1).padStart(2, '0') }} / {{ ODIN_ARTWORK.length }}</span><span>© Cloud Imperium Games</span></figcaption></figure><div class="gallery-ledger"><p class="eyebrow">{{ c.artCategory }} / {{ artworkCaption.category }}</p><h3>{{ artworkCaption.title }}</h3><p>{{ artworkCaption.alt }}</p><a class="text-link" :href="artwork.source" target="_blank" rel="noopener noreferrer">{{ c.originalArt }} ↗</a><div class="gallery-controls"><button :aria-label="c.previousArt" @click="changeArtwork(artworkIndex - 1)">←</button><span>{{ String(artworkIndex + 1).padStart(2, '0') }}<small> / {{ ODIN_ARTWORK.length }}</small></span><button class="next-art" :aria-label="c.nextArt" @click="changeArtwork(artworkIndex + 1)">→</button></div></div></div>
        <div class="art-thumbnails" :aria-label="c.artThumbnails"><button v-for="(art, index) in ODIN_ARTWORK" :key="art.src" :aria-label="`${c.selectArt} ${index + 1}: ${art[locale].title}`" :aria-pressed="artworkIndex === index" @click="changeArtwork(index)"><img :src="art.thumb" alt="" width="160" height="90" loading="lazy" /><span>{{ String(index + 1).padStart(2, '0') }}</span></button></div>
      </section>
    </main>

    <footer id="footer" class="site-footer">
      <div class="footer-content"><div class="footer-intro"><a class="footer-wordmark" href="#overview" @click.prevent="goToChapter(0)"><img src="/images/odin-founders-badge-v0.11.47.png" alt="" width="44" height="44" />ODIN</a><p>{{ c.footerBody }}</p><span class="eyebrow">{{ c.footerTag }} / OD—77</span><div class="identity-stripe" aria-hidden="true"><i /><i /><i /><i /></div></div><div class="footer-column"><h2>{{ c.footerTour }}</h2><a href="#overview" @click.prevent="goToChapter(0)">{{ c.footerTop }}</a><a href="#batteries" @click.prevent="goToChapter(1)">{{ c.footerMain }}</a><a href="#bridge" @click.prevent="goToChapter(2)">{{ c.footerSecondary }}</a><a href="#engines" @click.prevent="goToChapter(3)">{{ c.footerPropulsion }}</a><a href="#archive">{{ c.footerGallery }}</a></div><div class="footer-column"><h2>{{ c.footerProject }}</h2><button @click="showAbout = true">{{ c.sourceNotes }}</button><a :href="reviewUrl">{{ c.review }}</a><a href="https://robertsspaceindustries.com" target="_blank" rel="noopener noreferrer">{{ c.community }} ↗</a><button @click="setLocale(locale === 'zh' ? 'en' : 'zh')">{{ c.switchLanguage }} ↔</button></div><div class="footer-column"><h2>{{ c.footerSources }}</h2><a href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">Anvil Odin ↗</a><a href="https://www.youtube.com/watch?v=CFoQp6wRjPo" target="_blank" rel="noopener noreferrer">Star Citizen Live ↗</a><a href="https://media.robertsspaceindustries.com/84qwqukbwkgsk/source.png" target="_blank" rel="noopener noreferrer">{{ c.founder }} ↗</a></div></div>
      <div class="footer-legal"><p>{{ c.legal }}</p><a class="community-mark" href="https://robertsspaceindustries.com" target="_blank" rel="noopener noreferrer"><img src="/images/made-by-the-community.png" :alt="c.communityAlt" width="64" height="64" /></a></div>
      <figure class="footer-landscape"><img src="/images/odin-mountain-footer-v0.13.0.webp" :alt="c.footerImageAlt" width="2048" height="683" loading="lazy" /><figcaption><span>{{ c.document }} / {{ c.edition }}</span><a href="#overview" @click.prevent="goToChapter(0)">{{ c.end }} ↑</a></figcaption></figure>
    </footer>

    <Teleport to="body"><dialog ref="aboutDialog" class="about-dialog" :aria-label="c.sourceNotes" @close="showAbout = false" @cancel="showAbout = false"><div class="dialog-backdrop" @click="showAbout = false" /><section role="document"><button class="dialog-close" :aria-label="c.closeAbout" @click="showAbout = false">×</button><p class="eyebrow">{{ c.projectNotes }}</p><h2>{{ c.aboutTitle }}</h2><p>{{ c.aboutIntro }}</p><p>{{ c.aboutDesign }}</p><div class="credits"><a href="https://www.youtube.com/watch?v=EKvbJh87rpY" target="_blank" rel="noopener noreferrer">{{ c.inspiration }} ↗</a><a href="https://www.youtube.com/watch?v=CFoQp6wRjPo" target="_blank" rel="noopener noreferrer">{{ c.developerShow }} ↗</a><a href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">{{ c.shipSource }} ↗</a><a href="https://media.robertsspaceindustries.com/84qwqukbwkgsk/source.png" target="_blank" rel="noopener noreferrer">{{ c.badgeSource }} ↗</a><a href="https://www.nasa.gov/wp-content/uploads/2015/01/nasa_graphics_manual_nhb_1430-2_jan_1976.pdf" target="_blank" rel="noopener noreferrer">{{ c.nasaSource }} ↗</a><a href="https://bethesda.net/en-US/news/starfield-gameplay-reveal" target="_blank" rel="noopener noreferrer">{{ c.starfieldSource }} ↗</a></div><small>{{ c.modelNotice }}</small></section></dialog></Teleport>
  </div>
</template>
