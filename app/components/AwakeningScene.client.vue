<script setup lang="ts">
import type { AwakeningExperience } from '~/lib/awakening-scene'
import type { AtlasMode } from '~/lib/atlas-viewer-state'
const props = defineProps<{
  time: number; playing: boolean; started: boolean; inspect: boolean; focus: AtlasMode; deployment: number
  active: boolean; reducedMotion: boolean; spectral: boolean; pointer: { x: number; y: number }
}>()
const emit = defineEmits<{ ready: []; progress: [value: number]; fail: [message: string] }>()
const canvas = ref<HTMLCanvasElement>()
let experience: AwakeningExperience | undefined, disposed = false
onMounted(async () => {
  try {
    const { createAwakeningExperience } = await import('~/lib/awakening-scene')
    if (disposed || !canvas.value) return
    experience = await createAwakeningExperience(canvas.value, {
      state: () => ({ ...props }), progress: value => { if (!disposed) emit('progress', value) }, fail: message => { if (!disposed) emit('fail', message) },
    })
    if (disposed) { experience.dispose(); return }
    emit('ready')
  } catch (error) { if (!disposed) emit('fail', error instanceof Error ? error.message : '无法开启奥丁实时演出。') }
})
watch(() => [props.time, props.playing, props.started, props.inspect, props.focus, props.deployment, props.active, props.reducedMotion, props.spectral, props.pointer.x, props.pointer.y], () => experience?.invalidate())
onBeforeUnmount(() => { disposed = true; experience?.dispose() })
defineExpose({ resetView: () => experience?.resetView(), capturePhoto: () => experience ? experience.capturePhoto() : Promise.reject(new Error('实时演出尚未就绪。')) })
</script>

<template><canvas ref="canvas" class="awakening-canvas" :class="{ inspecting: inspect }" role="img" aria-label="奥丁苏醒：实时三维演出。自由检视模式可拖动旋转、滚轮缩放。" /></template>

<style scoped>
.awakening-canvas { display: block; width: 100%; height: 100%; outline: none; }
.awakening-canvas.inspecting { cursor: grab; touch-action: none; }
.awakening-canvas.inspecting:active { cursor: grabbing; }
</style>
