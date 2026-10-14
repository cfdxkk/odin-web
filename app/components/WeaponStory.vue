<script setup lang="ts">
import { WEAPON_TOUR, WEAPON_SOURCE, clampWeaponStep } from '~/lib/odin-weapon-tour'
import { INTERIOR_SECTIONS } from '~/lib/odin-interiors'
const props = defineProps<{ step: number; locale: 'zh' | 'en'; active: boolean }>()
const emit = defineEmits<{ select: [step: number] }>()
const shot = computed(() => WEAPON_TOUR[clampWeaponStep(props.step)]!)
const copy = computed(() => shot.value[props.locale])
const interior = computed(() => shot.value.id === 'torpedoes' ? INTERIOR_SECTIONS.torpedoes : undefined)
const root = ref<HTMLElement>()
const video = ref<HTMLVideoElement>()
const playing = ref(false)
let playRequest = 0
let desiredVideo: HTMLVideoElement | undefined
let visible = false
let observer: IntersectionObserver | undefined
function pause() {
  playRequest++
  desiredVideo = undefined
  video.value?.pause()
  playing.value = false
}
async function play() {
  const target = video.value
  if (!props.active || !visible || document.hidden || !target) return
  const request = ++playRequest
  desiredVideo = target
  target.muted = true
  try {
    await target.play()
    // A pending play promise must not resume a clip after a new step, a
    // pointer leave, or a chapter transition has already stopped it.
    if (request !== playRequest || target !== video.value || !props.active || document.hidden) {
      if (desiredVideo !== target || target !== video.value || !props.active || document.hidden) target.pause()
      return
    }
    playing.value = true
  } catch {
    if (request === playRequest) playing.value = false
  }
}
function hover(event: PointerEvent) { if (event.pointerType !== 'touch') void play() }
function visibilityChanged() { if (document.hidden) pause() }
watch(() => props.step, pause, { flush: 'sync' })
watch(() => props.active, active => { if (!active) pause() }, { flush: 'sync' })
onMounted(() => {
  observer = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting)
    if (!visible) pause()
  }, { threshold: .05 })
  if (root.value) observer.observe(root.value)
  document.addEventListener('visibilitychange', visibilityChanged)
})
onBeforeUnmount(() => {
  pause()
  observer?.disconnect()
  document.removeEventListener('visibilitychange', visibilityChanged)
})
</script>

<template>
  <div ref="root" class="weapon-story" :data-weapon="shot.id" :data-active="active">
    <div class="weapon-section-label"><p class="eyebrow">02 / {{ locale === 'zh' ? '武备导览' : 'Armament tour' }}</p></div>
    <nav class="weapon-step-nav" :style="{ '--weapon-count': WEAPON_TOUR.length }" :aria-label="locale === 'zh' ? '选择武器' : 'Choose a weapon'">
      <button v-for="(weapon, index) in WEAPON_TOUR" :key="weapon.id" :aria-label="`${String(index + 1).padStart(2, '0')} / ${weapon[locale].title}`" :aria-current="index === clampWeaponStep(step) ? 'step' : undefined" @click="emit('select', index)"><span>{{ String(index + 1).padStart(2, '0') }}</span></button>
    </nav>
    <div class="weapon-copy" :key="shot.id" aria-live="polite" aria-atomic="true">
      <div class="weapon-title-row"><h2 id="batteries-title">{{ copy.title }}</h2><span class="weapon-callout-origin" aria-hidden="true" /></div>
      <p class="chapter-body">{{ interior?.[locale].body ?? copy.body }}</p>
      <ul v-if="interior" class="interior-specs"><li v-for="spec in interior[locale].specs" :key="spec">{{ spec }}</li></ul>
      <p v-else class="weapon-spec">{{ copy.spec }}</p>
    </div>
    <InteriorGallery v-if="interior" :images="interior.images" :locale="locale" />
    <div v-if="shot.video" class="weapon-video-slot">
      <button class="weapon-film" :class="{ 'is-playing': playing }" :aria-pressed="playing" :aria-label="locale === 'zh' ? '播放或暂停官方演示视频' : 'Play or pause the official demonstration'" @pointerenter="hover" @pointerleave="pause" @focus="play" @blur="pause" @click="playing ? pause() : play()">
        <video ref="video" :key="shot.video" :src="`/videos/odin/${shot.video}.mp4`" :poster="`/videos/odin/${shot.video}.webp`" :class="{ mirrored: shot.video === 'main-battery' || shot.video === 'quad-turret' }" preload="none" muted loop playsinline disablepictureinpicture tabindex="-1" aria-hidden="true" />
        <span class="preview-indicator" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="m6 4 9 6-9 6Z" /></svg></span>
      </button>
      <div class="weapon-film-caption"><span>{{ locale === 'zh' ? '官方演示' : 'Official demonstration' }}</span><span>{{ playing ? (locale === 'zh' ? '正在播放' : 'Playing') : (locale === 'zh' ? '悬停播放' : 'Hover to play') }}</span></div>
    </div>
    <a v-if="!interior" class="weapon-source" :href="WEAPON_SOURCE" target="_blank" rel="noopener noreferrer">{{ locale === 'zh' ? '官方武备资料' : 'Official armament details' }} <span aria-hidden="true">↗</span></a>
  </div>
</template>
