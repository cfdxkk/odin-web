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
const selected = ref(0)
const active = ref(-1)
let visible = false, observer: IntersectionObserver | undefined
function stop(index = active.value) {
  const video = videos[index]
  video?.pause()
  if (video && video.readyState >= 1) video.currentTime = 0
  if (active.value === index) active.value = -1
}
async function start(index: number) {
  selected.value = index
  if (!visible || document.hidden) return
  if (active.value !== index) stop()
  active.value = index
  const video = videos[index]
  if (!video) return
  video.muted = true
  try { await video.play() } catch { if (active.value === index) active.value = -1 }
}
function leaveFocus(event: FocusEvent) {
  if (!root.value?.contains(event.relatedTarget as Node | null)) stop()
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
  <div ref="root" class="weapon-videos" :class="{ 'is-playing': active !== -1 }" :aria-label="locale === 'zh' ? '官方炮塔演示视频' : 'Official turret demonstrations'" @pointerleave="stop()" @focusout="leaveFocus">
    <div class="weapon-preview" @pointerenter="start(selected)">
      <video v-for="(clip, index) in clips" v-show="selected === index" :key="clip.id" :ref="el => { if (el) videos[index] = el as HTMLVideoElement }" :src="`/videos/odin/${clip.id}.mp4`" :poster="`/videos/odin/${clip.id}.webp`" :class="{ mirrored: clip.mirror }" preload="none" muted loop playsinline disablepictureinpicture tabindex="-1" aria-hidden="true" />
      <span class="preview-indicator" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="m6 4 9 6-9 6Z" /></svg></span>
    </div>
    <div class="weapon-choices">
      <button v-for="(clip, index) in clips" :key="clip.id" class="weapon-choice" :aria-pressed="selected === index" :aria-label="`${clip[props.locale]} / ${locale === 'zh' ? '预览视频' : 'Preview video'}`" @pointerenter="start(index)" @focus="start(index)" @click="start(index)"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ clip[locale] }}<span class="choice-arrow" aria-hidden="true">↗</span></button>
    </div>
  </div>
</template>
