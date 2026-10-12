<script setup lang="ts">
const props = defineProps<{ locale: 'zh' | 'en' }>()
const clips = [
  { id: 'main-battery', zh: '主炮', en: 'Main battery', mirror: true },
  { id: 'bow-laser', zh: '舰艏激光阵列', en: 'Bow laser array', mirror: false },
  { id: 'pdc', zh: 'PDC 防御炮', en: 'PDC mounts', mirror: false },
  { id: 'quad-turret', zh: '四联装炮塔', en: 'Quad turret', mirror: true },
] as const
const root = ref<HTMLElement>()
const videos: HTMLVideoElement[] = []
const active = ref(-1)
let visible = false, observer: IntersectionObserver | undefined
function stop(index = active.value) {
  const video = videos[index]
  video?.pause()
  if (video && video.readyState >= 1) video.currentTime = 0
  if (active.value === index) active.value = -1
}
async function start(index: number) {
  if (!visible || document.hidden) return
  if (active.value !== index) stop()
  active.value = index
  const video = videos[index]
  if (!video) return
  video.muted = true
  try { await video.play() } catch { if (active.value === index) active.value = -1 }
}
function visibility() { if (document.hidden) stop() }
onMounted(() => {
  observer = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting)
    if (!visible) stop()
  }, { threshold: .05 })
  if (root.value) observer.observe(root.value)
  document.addEventListener('visibilitychange', visibility)
})
onBeforeUnmount(() => {
  videos.forEach(video => video?.pause())
  observer?.disconnect()
  document.removeEventListener('visibilitychange', visibility)
})
</script>

<template>
  <div ref="root" class="weapon-videos" :aria-label="locale === 'zh' ? '官方炮塔演示视频' : 'Official turret demonstrations'">
    <button v-for="(clip, index) in clips" :key="clip.id" class="weapon-video" :class="{ 'is-playing': active === index }" :aria-label="`${clip[props.locale]} / ${locale === 'zh' ? '预览视频' : 'Preview video'}`" @pointerenter="start(index)" @pointerleave="stop(index)" @focus="start(index)" @blur="stop(index)" @click="active === index ? stop(index) : start(index)">
      <video :ref="el => { if (el) videos[index] = el as HTMLVideoElement }" :src="`/videos/odin/${clip.id}.mp4`" :poster="`/videos/odin/${clip.id}.webp`" :class="{ mirrored: clip.mirror }" preload="none" muted loop playsinline disablepictureinpicture tabindex="-1" aria-hidden="true" />
      <span class="video-caption"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ clip[locale] }}<svg v-if="active !== index" viewBox="0 0 20 20" aria-hidden="true"><path d="m6 4 9 6-9 6Z" /></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="M7 4v12M13 4v12" /></svg></span>
    </button>
  </div>
</template>
