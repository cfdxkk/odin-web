<script setup lang="ts">
import type { OdinInteriorImage } from '../lib/odin-interiors'
const props = defineProps<{ images: readonly OdinInteriorImage[]; locale: 'zh' | 'en' }>()
const index = ref(0)
const gallery = ref<HTMLElement>()
const lightbox = ref<HTMLDialogElement>()
const thumbnailVideo = ref<HTMLVideoElement>()
const lightboxVideo = ref<HTMLVideoElement>()
const playing = ref<'thumbnail' | 'lightbox' | null>(null)
let playRequest = 0
let desiredVideo: HTMLVideoElement | undefined
let visible = false
let observer: IntersectionObserver | undefined
const current = computed(() => props.images[index.value % Math.max(1, props.images.length)])
const imageStyle = computed(() => {
  const image = current.value
  if (!image?.crop) return {}
  const { x, y, width, height } = image.crop
  return { width: `${image.width / width * 100}%`, height: `${image.height / height * 100}%`, left: `${-x / width * 100}%`, top: `${-y / height * 100}%` }
})
const imageRatio = computed(() => current.value?.crop ? current.value.crop.width / current.value.crop.height : (current.value?.width ?? 16) / (current.value?.height ?? 9))
function pause() {
  playRequest++
  desiredVideo = undefined
  thumbnailVideo.value?.pause()
  lightboxVideo.value?.pause()
  playing.value = null
}
async function play(surface: 'thumbnail' | 'lightbox') {
  const target = surface === 'thumbnail' ? thumbnailVideo.value : lightboxVideo.value
  if (current.value?.type !== 'video' || !target || document.hidden || !visible) return
  if (surface === 'thumbnail' && lightbox.value?.open) return
  pause()
  const request = playRequest
  desiredVideo = target
  target.muted = true
  try {
    await target.play()
    if (request !== playRequest || document.hidden || !visible) {
      if (desiredVideo !== target || document.hidden || !visible) target.pause()
      return
    }
    playing.value = surface
  } catch { if (request === playRequest) playing.value = null }
}
function hover(event: PointerEvent, surface: 'thumbnail' | 'lightbox') {
  if (event.pointerType !== 'touch') void play(surface)
}
function visibilityChanged() { if (document.hidden) pause() }
watch(index, pause, { flush: 'sync' })
watch(() => props.images, () => { pause(); index.value = 0; lightbox.value?.close() }, { flush: 'sync' })
function move(direction: number) { index.value = (index.value + direction + props.images.length) % props.images.length }
function openImage() { pause(); lightbox.value?.showModal(); if (current.value?.type === 'video') void play('lightbox') }
function dialogKey(event: KeyboardEvent) {
  if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End'].includes(event.key)) event.preventDefault()
  if (event.code === 'Space' && (event.target as HTMLElement).tagName !== 'BUTTON') event.preventDefault()
}
onMounted(() => {
  observer = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting)
    if (!visible) { pause(); lightbox.value?.close() }
  }, { threshold: .05 })
  if (gallery.value) observer.observe(gallery.value)
  document.addEventListener('visibilitychange', visibilityChanged)
})
onBeforeUnmount(() => {
  pause()
  observer?.disconnect()
  document.removeEventListener('visibilitychange', visibilityChanged)
})
</script>

<template>
  <figure v-if="current" ref="gallery" class="interior-gallery" :style="{ '--image-ratio': imageRatio }">
    <button class="interior-image-trigger" :aria-label="locale === 'zh' ? (current.type === 'video' ? '放大演示视频' : '放大图片') : (current.type === 'video' ? 'Enlarge demonstration video' : 'Enlarge image')" @click="openImage" @pointerenter="hover($event, 'thumbnail')" @pointerleave="pause" @focus="play('thumbnail')" @blur="pause">
      <span class="interior-image-frame" :class="{ cropped: current.crop, 'is-playing': playing === 'thumbnail' }">
        <video v-if="current.type === 'video'" ref="thumbnailVideo" :key="current.src" :src="current.src" :poster="current.poster" :width="current.width" :height="current.height" preload="none" muted loop playsinline disablepictureinpicture tabindex="-1" aria-hidden="true" />
        <img v-else :src="current.src" :style="imageStyle" :width="current.width" :height="current.height" :alt="current[locale]" loading="lazy" />
        <span v-if="current.type === 'video' && playing !== 'thumbnail'" class="interior-play-mark" aria-hidden="true">▷</span>
      </span>
    </button>
    <figcaption><span :title="current[locale]">{{ current[locale] }}<span v-if="current.timestamp"> · {{ current.timestamp }}</span></span><nav v-if="images.length > 1" :aria-label="locale === 'zh' ? '内部资料' : 'Interior media'"><button :aria-label="locale === 'zh' ? '上一张内部图' : 'Previous interior image'" @click="move(-1)">←</button><span>{{ index + 1 }} / {{ images.length }}</span><button :aria-label="locale === 'zh' ? '下一张内部图' : 'Next interior image'" @click="move(1)">→</button></nav></figcaption>
    <Teleport to="body">
      <dialog ref="lightbox" class="interior-lightbox" :style="{ '--image-ratio': imageRatio }" :aria-label="current[locale]" @close="pause" @click.self="lightbox?.close()" @keydown.stop="dialogKey" @wheel.prevent.stop @touchmove.prevent.stop>
        <div class="interior-lightbox-toolbar"><span>{{ locale === 'zh' ? '官方概念演示' : 'Official concept demonstration' }}<span v-if="current.timestamp"> · {{ current.timestamp }}</span></span><button :aria-label="locale === 'zh' ? '关闭图片' : 'Close image'" @click="lightbox?.close()">×</button></div>
        <button v-if="current.type === 'video'" class="interior-lightbox-video interior-image-frame" :class="{ 'is-playing': playing === 'lightbox' }" :aria-label="locale === 'zh' ? '播放或暂停演示视频' : 'Play or pause demonstration video'" :aria-pressed="playing === 'lightbox'" @click="playing === 'lightbox' ? pause() : play('lightbox')" @pointerenter="hover($event, 'lightbox')" @pointerleave="pause" @focus="play('lightbox')" @blur="pause">
          <video ref="lightboxVideo" :key="current.src" :src="current.src" :poster="current.poster" :width="current.width" :height="current.height" preload="none" muted loop playsinline disablepictureinpicture tabindex="-1" aria-hidden="true" />
          <span v-if="playing !== 'lightbox'" class="interior-play-mark" aria-hidden="true">▷</span>
        </button>
        <div v-else class="interior-image-frame interior-lightbox-image" :class="{ cropped: current.crop }"><img :src="current.src" :style="imageStyle" :width="current.width" :height="current.height" :alt="current[locale]" /></div>
      </dialog>
    </Teleport>
  </figure>
</template>

<style scoped>
.interior-gallery { width: 100%; pointer-events: auto; }
.interior-image-trigger { display: block; padding: 0; border: 0; width: 100%; cursor: zoom-in; }
.interior-image-frame { display: block; position: relative; aspect-ratio: var(--image-ratio, 16 / 9); overflow: hidden; background: #0b1017; }
.interior-image-frame img, .interior-image-frame video { display: block; width: 100%; height: 100%; object-fit: contain; }
.interior-image-frame video { filter: grayscale(1) brightness(.7); transition: filter 250ms ease; }
.interior-image-frame.is-playing video { filter: grayscale(0) brightness(1); }
.interior-play-mark { position: absolute; inset: 0; display: grid; place-items: center; font-size: 26px; color: #e8ecee; pointer-events: none; }
.interior-image-frame.cropped img { position: absolute; max-width: none; object-fit: fill; }
.interior-image-trigger:focus-visible { outline: 1px solid var(--accent); outline-offset: 4px; }
figcaption { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 8px; font-size: 9px; color: #9ba5ad; line-height: 1.6; }
figcaption > span { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
nav { display: flex; gap: 10px; align-items: center; white-space: nowrap; }
nav button { min-height: 28px; min-width: 24px; font-size: 18px; }
nav button:hover { color: var(--accent); }
.interior-lightbox { position: fixed; inset: 0; margin: auto; padding: 0; border: 1px solid #39434a; width: min(92vw, 1600px, calc((92vh - 48px) * var(--image-ratio))); max-width: 92vw; max-height: 92vh; color: #e8ecee; background: #080d12; }
.interior-lightbox::backdrop { background: rgb(0 0 0 / 86%); }
.interior-lightbox-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 46px; padding: 0 14px; font-size: 12px; }
.interior-lightbox-toolbar button { font-size: 28px; line-height: 1; width: 32px; height: 36px; }
.interior-lightbox-toolbar button:hover { color: var(--accent); }
.interior-lightbox-video { width: 100%; padding: 0; border: 0; cursor: pointer; }
.interior-lightbox-image { aspect-ratio: var(--image-ratio); }
@media (max-height: 850px) and (min-width: 701px) { .interior-gallery { max-width: 250px; } }
@media (max-width: 700px) { .interior-gallery { max-width: 245px; } }
</style>
