<script setup lang="ts">
import type { AtlasExperience } from '~/lib/atlas-scene'
import type { AtlasMode } from '~/lib/atlas-viewer-state'

const props = withDefaults(defineProps<{
  playing: boolean
  mode: AtlasMode
  deployment: number
  active: boolean
  reducedMotion: boolean
  technical: boolean
  scrubbing?: boolean
  canvasLabel?: string
}>(), { canvasLabel: '奥丁三维交互模型。拖动旋转，滚轮缩放，右键拖动平移。' })
const emit = defineEmits<{ ready: []; progress: [value: number]; fail: [message: string] }>()
const canvas = ref<HTMLCanvasElement>()
let experience: AtlasExperience | undefined
let disposed = false

onMounted(async () => {
  try {
    const { createAtlasExperience } = await import('~/lib/atlas-scene')
    if (disposed || !canvas.value) return
    experience = await createAtlasExperience(canvas.value, {
      state: () => ({ ...props }),
      progress: value => { if (!disposed) emit('progress', value) },
      fail: message => { if (!disposed) emit('fail', message) },
    })
    if (disposed) { experience.dispose(); return }
    emit('ready')
  } catch (error) {
    if (!disposed) emit('fail', error instanceof Error ? error.message : '无法载入三维模型')
  }
})

watch(() => [props.playing, props.mode, props.deployment, props.active, props.reducedMotion, props.technical, props.scrubbing], () => experience?.invalidate())
onBeforeUnmount(() => { disposed = true; experience?.dispose() })
defineExpose({
  resetView: () => experience?.resetView(),
  capturePhoto: (options?: { tight?: boolean }) => experience ? experience.capturePhoto(options) : Promise.reject(new Error('三维模型尚未就绪。')),
})
</script>

<template>
  <canvas ref="canvas" class="atlas-canvas" :aria-label="canvasLabel" role="img" />
</template>

<style scoped>
.atlas-canvas { display: block; width: 100%; height: 100%; outline: none; touch-action: pan-y; cursor: grab; }
.atlas-canvas:active { cursor: grabbing; }
</style>
