<script setup lang="ts">
import { cleanFooterTones, footerInkLevel, FOOTER_SCREEN_INKS, FOOTER_SCREEN_MARK_RATIO, FOOTER_SCREEN_PITCH } from '../lib/odin-footer-screen'

defineProps<{ alt: string }>()

const SOURCE = '/images/odin-mountain-footer-v0.23.0.webp'
const BACKGROUND = '#070b10'
const root = ref<HTMLElement>()
const canvas = ref<HTMLCanvasElement>()
let resizeObserver: ResizeObserver | undefined
let intersectionObserver: IntersectionObserver | undefined
let resolutionQuery: MediaQueryList | undefined
let timer: ReturnType<typeof setTimeout> | undefined
let sourceImage: HTMLImageElement | undefined
let loading: Promise<HTMLImageElement> | undefined
let visible = false, disposed = false, dirty = true, rendering = false
let lastSize = '', renderCount = 0

const clamp = (value: number) => Math.max(0, Math.min(1, value))
const smooth = (value: number) => { const t = clamp(value); return t * t * (3 - 2 * t) }

function loadSource() {
  if (sourceImage?.complete && sourceImage.naturalWidth) return Promise.resolve(sourceImage)
  if (loading) return loading
  const image = new Image()
  image.decoding = 'async'
  sourceImage = image
  loading = new Promise<HTMLImageElement>((resolve, reject) => {
    image.onload = () => { image.onload = image.onerror = null; resolve(image) }
    image.onerror = () => { image.onload = image.onerror = null; reject(new Error('Footer plate could not load')) }
    image.src = SOURCE
  }).finally(() => { loading = undefined })
  return loading
}

function cancelTimer() { if (timer !== undefined) { clearTimeout(timer); timer = undefined } }
function schedule(delay = 120) {
  cancelTimer()
  if (disposed || !visible || document.hidden || !dirty) return
  timer = setTimeout(() => { timer = undefined; void render() }, delay)
}
function invalidate() {
  dirty = true
  if (canvas.value) canvas.value.dataset.ready = 'false'
  schedule()
}

async function render() {
  if (disposed || !visible || document.hidden || !dirty || rendering) return
  rendering = true
  try {
    const image = await loadSource()
    const target = canvas.value, host = root.value
    if (disposed || !visible || document.hidden || !target || !host) return
    const { width, height } = host.getBoundingClientRect()
    if (width < 1 || height < 1) return
    const dpr = window.devicePixelRatio || 1
    const mobile = window.matchMedia('(max-width: 700px)').matches
    const pitch = FOOTER_SCREEN_PITCH
    const size = `${width}:${height}:${dpr}:${mobile}`
    if (size === lastSize) { dirty = false; target.dataset.ready = 'true'; return }

    const started = performance.now()
    const artHeight = mobile ? Math.max(300, height * .55) : Math.min(height * .75, width * .43)
    const artTop = height - artHeight
    const columns = Math.ceil(width / pitch), rows = Math.ceil(artHeight / pitch)
    // Descreen the existing illustration into broad tones before applying a
    // single ordered screen. Mountains and ship share this whole pass;
    // no separate ship mask, stipple layer or stretched pre-screened image.
    const plate = document.createElement('canvas')
    plate.width = Math.ceil(width); plate.height = Math.ceil(artHeight)
    const plateContext = plate.getContext('2d')
    const samples = document.createElement('canvas')
    samples.width = columns; samples.height = rows
    const sampleContext = samples.getContext('2d', { willReadFrequently: true })
    const context = target.getContext('2d', { alpha: false })
    if (!sampleContext || !context || !plateContext) throw new Error('Footer canvas is unavailable')
    sampleContext.fillStyle = BACKGROUND
    sampleContext.fillRect(0, 0, columns, rows)
    sampleContext.imageSmoothingEnabled = true
    sampleContext.imageSmoothingQuality = 'high'
    const scale = Math.max(width / image.naturalWidth, artHeight / image.naturalHeight)
    const sourceWidth = width / scale, sourceHeight = artHeight / scale
    const sourceX = (image.naturalWidth - sourceWidth) * (mobile ? .53 : .5)
    const sourceY = (image.naturalHeight - sourceHeight) * (mobile ? .5 : .55)
    plateContext.filter = 'blur(2.2px) grayscale(1)'
    plateContext.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, width, artHeight)
    sampleContext.drawImage(plate, 0, 0, columns, rows)
    const pixels = sampleContext.getImageData(0, 0, columns, rows).data
    const rawTones = new Float32Array(columns * rows)
    for (let i = 0; i < rawTones.length; i++) {
      const offset = i * 4
      const luminance = .2126 * pixels[offset]! + .7152 * pixels[offset + 1]! + .0722 * pixels[offset + 2]!
      rawTones[i] = Math.pow(clamp((luminance - 15) / 110), 1.1) * .95
    }
    const tones = cleanFooterTones(rawTones, columns, rows)

    target.width = Math.round(width * dpr)
    target.height = Math.round(height * dpr)
    // Draw directly into the final device-pixel backing store. CSS never
    // stretches a pre-screened PNG, even on fractional device pixel ratios.
    const print = context.createImageData(target.width, target.height)
    const ink = print.data
    for (let index = 0; index < ink.length; index += 4) {
      ink[index] = 7; ink[index + 1] = 11; ink[index + 2] = 16; ink[index + 3] = 255
    }
    const scaleX = target.width / width, scaleY = target.height / height
    const markSize = pitch * FOOTER_SCREEN_MARK_RATIO
    let marks = 0
    for (let row = 0; row < rows; row++) {
      const localY = (row + .5) * pitch, fraction = localY / artHeight
      const y = artTop + localY
      // Fade the ink over a longer atmospheric depth without shrinking marks.
      const fade = smooth((fraction + .12) / .6) * (1 - .3 * smooth((fraction - .85) / .15))
      if (fade === 0) continue
      for (let column = 0; column < columns; column++) {
        const tone = tones[row * columns + column]!
        const inkLevel = footerInkLevel(tone, column, row)
        if (!inkLevel) continue
        const gray = FOOTER_SCREEN_INKS[inkLevel]!
        const x = (column + .5) * pitch
        // The footprint is fixed at every tone. Exact rectangular pixel
        // coverage keeps fractional DPR from varying the mark's apparent size.
        const x0 = (x - markSize / 2) * scaleX, x1 = (x + markSize / 2) * scaleX
        const y0 = (y - markSize / 2) * scaleY, y1 = (y + markSize / 2) * scaleY
        const left = Math.max(0, Math.floor(x0)), right = Math.min(target.width - 1, Math.ceil(x1) - 1)
        const top = Math.max(0, Math.floor(y0)), bottom = Math.min(target.height - 1, Math.ceil(y1) - 1)
        for (let py = top; py <= bottom; py++) {
          for (let px = left; px <= right; px++) {
            const coverage = Math.max(0, Math.min(px + 1, x1) - Math.max(px, x0))
              * Math.max(0, Math.min(py + 1, y1) - Math.max(py, y0)) * fade
            const index = (py * target.width + px) * 4
            ink[index] = Math.round(7 + (gray - 7) * coverage)
            ink[index + 1] = Math.round(11 + (gray - 11) * coverage)
            ink[index + 2] = Math.round(16 + (gray - 16) * coverage)
          }
        }
        marks++
      }
    }
    context.putImageData(print, 0, 0)
    samples.width = samples.height = plate.width = plate.height = 1
    dirty = false
    lastSize = size
    renderCount++
    Object.assign(target.dataset, {
      ready: 'true', source: SOURCE, gridPitch: String(pitch), screenCount: '1',
      renderCount: String(renderCount), renderMs: (performance.now() - started).toFixed(1),
      dpr: String(dpr), marks: String(marks), raster: 'native-pixels', descreenBlur: '2.2',
      screen: 'ordered-4x4', markShape: 'square', markSize: String(markSize), inkLevels: '4', atmosphericFade: 'ink-only', speckFilter: 'connected-tones',
    })
    delete target.dataset.error
  } catch {
    if (!disposed && canvas.value) {
      canvas.value.dataset.ready = 'false'
      canvas.value.dataset.error = 'print-unavailable'
    }
    // A subsequent resize or re-entry can retry. Do not create a retry loop.
    dirty = false
  } finally {
    rendering = false
  }
}

function visibilityChanged() {
  if (document.hidden) cancelTimer()
  else schedule(0)
}
function watchResolution() {
  resolutionQuery?.removeEventListener('change', resolutionChanged)
  resolutionQuery = window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`)
  resolutionQuery.addEventListener('change', resolutionChanged)
}
function resolutionChanged() { watchResolution(); invalidate() }

// Nuxt's client-only wrapper can mount its placeholder before replacing it
// with this template. Start when both real DOM refs exist, rather than losing
// initialization to an early onMounted callback with undefined template refs.
watch([root, canvas], ([host, target]) => {
  if (!host || !target || disposed || resizeObserver) return
  resizeObserver = new ResizeObserver(invalidate)
  resizeObserver.observe(host)
  intersectionObserver = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting)
    if (visible) { if (!lastSize) dirty = true; schedule(0) }
    else cancelTimer()
  }, { threshold: 0 })
  intersectionObserver.observe(host)
  window.addEventListener('resize', invalidate, { passive: true })
  document.addEventListener('visibilitychange', visibilityChanged)
  watchResolution()
  target.dataset.observing = 'true'
}, { flush: 'post' })

onBeforeUnmount(() => {
  disposed = true
  cancelTimer()
  resizeObserver?.disconnect()
  intersectionObserver?.disconnect()
  resolutionQuery?.removeEventListener('change', resolutionChanged)
  window.removeEventListener('resize', invalidate)
  document.removeEventListener('visibilitychange', visibilityChanged)
  if (sourceImage && !sourceImage.complete) sourceImage.src = ''
  sourceImage = undefined
  if (canvas.value) canvas.value.width = canvas.value.height = 1
})
</script>

<template>
  <div ref="root" class="footer-print" role="img" :aria-label="alt">
    <canvas ref="canvas" aria-hidden="true" data-ready="false" data-render-count="0" :data-source="SOURCE" />
  </div>
</template>

<style scoped>
.footer-print { display: block; overflow: hidden; background: #070b10; pointer-events: none; }
canvas { display: block; width: 100%; height: 100%; }
</style>
