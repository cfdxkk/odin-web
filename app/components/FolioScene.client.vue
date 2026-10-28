<script setup lang="ts">
import type { FolioExperience } from '~/lib/folio-scene'
import type { FolioTreatment } from '~/lib/folio-effects'
import type { AtlasMode } from '~/lib/atlas-viewer-state'

const props = withDefaults(
  defineProps<{
    mode: AtlasMode
    deployment: number
    playing: boolean
    active: boolean
    reducedMotion: boolean
    scrubbing?: boolean
    treatment: FolioTreatment
    pointer?: { x: number; y: number }
    canvasLabel?: string
  }>(),
  {
    pointer: () => ({ x: 0, y: 0 }),
    canvasLabel: '奥丁互动设定稿。拖动旋转、滚轮缩放，右键拖动平移。',
  },
)
const emit = defineEmits<{
  ready: []
  progress: [value: number]
  fail: [message: string]
}>()
const canvas = ref<HTMLCanvasElement>()
const abort = new AbortController()
let experience: FolioExperience | undefined

onMounted(async () => {
  try {
    const { createFolioExperience } = await import('~/lib/folio-scene')
    if (abort.signal.aborted || !canvas.value) return
    experience = await createFolioExperience(canvas.value, {
      state: () => ({ ...props }),
      signal: abort.signal,
      progress: (value) => {
        if (!abort.signal.aborted) emit('progress', value)
      },
      fail: (message) => {
        if (!abort.signal.aborted) emit('fail', message)
      },
    })
    if (abort.signal.aborted) {
      experience.dispose()
      return
    }
    emit('ready')
  } catch (error) {
    if (!abort.signal.aborted)
      emit(
        'fail',
        error instanceof Error ? error.message : '无法载入三维设定稿。',
      )
  }
})
watch(
  () => [
    props.mode,
    props.deployment,
    props.playing,
    props.active,
    props.reducedMotion,
    props.scrubbing,
    props.treatment,
    props.pointer.x,
    props.pointer.y,
  ],
  () => experience?.invalidate(),
)
onBeforeUnmount(() => {
  abort.abort()
  experience?.dispose()
})
defineExpose({
  resetView: () => experience?.resetView(),
  capturePhoto: () =>
    experience
      ? experience.capturePhoto()
      : Promise.reject(new Error('三维设定稿尚未就绪。')),
})
</script>

<template>
  <canvas
    ref="canvas"
    class="folio-canvas"
    :aria-label="canvasLabel"
    role="img"
  />
</template>

<style scoped>
.folio-canvas {
  display: block;
  width: 100%;
  height: 100%;
  outline: none;
  touch-action: pan-y;
  cursor: grab;
}
.folio-canvas:active {
  cursor: grabbing;
}
</style>
