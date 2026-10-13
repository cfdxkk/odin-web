<script setup lang="ts">
type Image = { src: string; width: number; height: number; zh: string; en: string; source: string; timestamp?: string }
const props = defineProps<{ images: readonly Image[]; locale: 'zh' | 'en' }>()
const index = ref(0)
const current = computed(() => props.images[index.value % Math.max(1, props.images.length)])
watch(() => props.images, () => { index.value = 0 })
function move(direction: number) { index.value = (index.value + direction + props.images.length) % props.images.length }
</script>

<template>
  <figure v-if="current" class="interior-gallery">
    <a :href="current.src" target="_blank" rel="noopener" :aria-label="locale === 'zh' ? '查看完整图片' : 'View full image'"><img :src="current.src" :width="current.width" :height="current.height" :alt="current[locale]" loading="lazy" /></a>
    <figcaption><a :href="current.source" :title="current[locale]" target="_blank" rel="noopener noreferrer">{{ current[locale] }}<span v-if="current.timestamp"> · {{ current.timestamp }}</span> ↗</a><nav v-if="images.length > 1" :aria-label="locale === 'zh' ? '内部资料图' : 'Interior images'"><button :aria-label="locale === 'zh' ? '上一张内部图' : 'Previous interior image'" @click="move(-1)">←</button><span>{{ index + 1 }} / {{ images.length }}</span><button :aria-label="locale === 'zh' ? '下一张内部图' : 'Next interior image'" @click="move(1)">→</button></nav></figcaption>
  </figure>
</template>

<style scoped>
.interior-gallery { width: 100%; pointer-events: auto; }
.interior-gallery > a { display: block; aspect-ratio: 16 / 9; overflow: hidden; background: #0b1017; }
img { width: 100%; height: 100%; object-fit: contain; }
figcaption { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 8px; font-size: 9px; color: #9ba5ad; line-height: 1.6; }
figcaption > a { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
nav { display: flex; gap: 10px; align-items: center; white-space: nowrap; }
nav button { min-height: 28px; min-width: 24px; font-size: 18px; }
nav button:hover { color: var(--accent); }
@media (max-height: 850px) and (min-width: 701px) { .interior-gallery { max-width: 250px; } }
@media (max-width: 700px) { .interior-gallery { max-width: 245px; } }
</style>
