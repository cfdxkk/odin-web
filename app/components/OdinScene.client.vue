<script setup lang="ts">
import type { OdinExperience } from '~/lib/odin-scene'
const emit = defineEmits<{
  ready: []
  progress: [value: number]
  tick: [time: number]
  fail: [message: string]
}>()
const props = defineProps<{ playing: boolean; explore: boolean; deployed: boolean; lowPower: boolean }>()
const canvas = ref<HTMLCanvasElement>()
let experience: OdinExperience | undefined
let disposed = false
onMounted(async () => {
  try {
    const { createOdinExperience } = await import('~/lib/odin-scene')
    if (disposed || !canvas.value) return
    experience = await createOdinExperience(canvas.value, {
      progress: p => emit('progress', p), tick: t => emit('tick', t),
      state: () => ({ ...props }),
    })
    if (disposed) { experience.dispose(); return }
    emit('ready')
  } catch (error) {
    emit('fail', error instanceof Error ? error.message : '无法载入三维模型')
  }
})
watch(() => props.explore, value => experience?.setExplore(value))
watch(() => props.lowPower, () => experience?.resize())
onBeforeUnmount(() => { disposed = true; experience?.dispose() })
defineExpose({ seek: (time: number) => experience?.seek(time) })
</script>

<template>
  <canvas ref="canvas" class="odin-canvas" :class="{ interactive: explore }" aria-label="奥丁战列巡洋舰实时三维展示；自由探索模式下可左键拖动旋转、右键拖动平移、滚轮缩放" />
</template>
