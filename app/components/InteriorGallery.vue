<script setup lang="ts">
import type { OdinInteriorImage } from '../lib/odin-interiors'
const props = defineProps<{ images: readonly OdinInteriorImage[]; locale: 'zh' | 'en' }>()
const index = ref(0)
const lightbox = ref<HTMLDialogElement>()
const current = computed(() => props.images[index.value % Math.max(1, props.images.length)])
const imageStyle = computed(() => {
  const image = current.value
  if (!image?.crop) return {}
  const { x, y, width, height } = image.crop
  return { width: `${image.width / width * 100}%`, height: `${image.height / height * 100}%`, left: `${-x / width * 100}%`, top: `${-y / height * 100}%` }
})
const imageRatio = computed(() => current.value?.crop ? current.value.crop.width / current.value.crop.height : (current.value?.width ?? 16) / (current.value?.height ?? 9))
watch(() => props.images, () => { index.value = 0; lightbox.value?.close() })
function move(direction: number) { index.value = (index.value + direction + props.images.length) % props.images.length }
function openImage() { lightbox.value?.showModal() }
function dialogKey(event: KeyboardEvent) {
  if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End'].includes(event.key)) event.preventDefault()
  if (event.code === 'Space' && (event.target as HTMLElement).tagName !== 'BUTTON') event.preventDefault()
}
</script>

<template>
  <figure v-if="current" class="interior-gallery">
    <button class="interior-image-trigger" :aria-label="locale === 'zh' ? '放大图片' : 'Enlarge image'" @click="openImage"><span class="interior-image-frame" :class="{ cropped: current.crop }"><img :src="current.src" :style="imageStyle" :width="current.width" :height="current.height" :alt="current[locale]" loading="lazy" /></span></button>
    <figcaption><a :href="current.source" :title="current[locale]" target="_blank" rel="noopener noreferrer">{{ current[locale] }}<span v-if="current.timestamp"> · {{ current.timestamp }}</span> ↗</a><nav v-if="images.length > 1" :aria-label="locale === 'zh' ? '内部资料图' : 'Interior images'"><button :aria-label="locale === 'zh' ? '上一张内部图' : 'Previous interior image'" @click="move(-1)">←</button><span>{{ index + 1 }} / {{ images.length }}</span><button :aria-label="locale === 'zh' ? '下一张内部图' : 'Next interior image'" @click="move(1)">→</button></nav></figcaption>
    <Teleport to="body"><dialog ref="lightbox" class="interior-lightbox" :style="{ '--image-ratio': imageRatio }" :aria-label="current[locale]" @click.self="lightbox?.close()" @keydown.stop="dialogKey" @wheel.prevent.stop @touchmove.prevent.stop><div class="interior-lightbox-toolbar"><a :href="current.source" target="_blank" rel="noopener noreferrer">{{ locale === 'zh' ? '查看官方来源' : 'View official source' }}<span v-if="current.timestamp"> · {{ current.timestamp }}</span> ↗</a><button :aria-label="locale === 'zh' ? '关闭图片' : 'Close image'" @click="lightbox?.close()">×</button></div><div class="interior-image-frame interior-lightbox-image" :class="{ cropped: current.crop }"><img :src="current.src" :style="imageStyle" :width="current.width" :height="current.height" :alt="current[locale]" /></div></dialog></Teleport>
  </figure>
</template>

<style scoped>
.interior-gallery { width: 100%; pointer-events: auto; }
.interior-image-trigger { display: block; padding: 0; border: 0; width: 100%; cursor: zoom-in; }
.interior-image-frame { display: block; position: relative; aspect-ratio: 16 / 9; overflow: hidden; background: #0b1017; }
.interior-image-frame img { display: block; width: 100%; height: 100%; object-fit: contain; }
.interior-image-frame.cropped img { position: absolute; max-width: none; object-fit: fill; }
.interior-image-trigger:focus-visible { outline: 1px solid var(--accent); outline-offset: 4px; }
figcaption { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 8px; font-size: 9px; color: #9ba5ad; line-height: 1.6; }
figcaption > a { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
nav { display: flex; gap: 10px; align-items: center; white-space: nowrap; }
nav button { min-height: 28px; min-width: 24px; font-size: 18px; }
nav button:hover { color: var(--accent); }
.interior-lightbox { position: fixed; inset: 0; margin: auto; padding: 0; border: 1px solid #39434a; width: min(92vw, 1600px, calc((92vh - 48px) * var(--image-ratio))); max-width: 92vw; max-height: 92vh; color: #e8ecee; background: #080d12; }
.interior-lightbox::backdrop { background: rgb(0 0 0 / 86%); }
.interior-lightbox-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 46px; padding: 0 14px; font-size: 12px; }
.interior-lightbox-toolbar button { font-size: 28px; line-height: 1; width: 32px; height: 36px; }
.interior-lightbox-toolbar a:hover, .interior-lightbox-toolbar button:hover { color: var(--accent); }
.interior-lightbox-image { aspect-ratio: var(--image-ratio); }
@media (max-height: 850px) and (min-width: 701px) { .interior-gallery { max-width: 250px; } }
@media (max-width: 700px) { .interior-gallery { max-width: 245px; } }
</style>
