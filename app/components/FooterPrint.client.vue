<script setup lang="ts">
defineProps<{ alt: string }>()

const SOURCE = '/images/odin-valley-continuous-v0.16.2.png'
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

// The radius table preserves ink coverage when bright dots meet. A screen
// limited to isolated dots cannot reproduce the continuous plate's midtones.
function coverage(radius: number) {
  if (radius <= .5) return Math.PI * radius * radius
  const cap = radius * radius * Math.acos(.5 / radius) - .5 * Math.sqrt(radius * radius - .25)
  return Math.PI * radius * radius - 4 * cap
}
const radii = Array.from({ length: 1025 }, (_, index) => {
  let low = 0, high = Math.SQRT1_2
  for (let step = 0; step < 18; step++) {
    const radius = (low + high) / 2
    if (coverage(radius) < index / 1024) low = radius
    else high = radius
  }
  return (low + high) / 2
})

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
    const pitch = 3
    const size = `${width}:${height}:${dpr}:${mobile}`
    if (size === lastSize) { dirty = false; target.dataset.ready = 'true'; return }

    const started = performance.now()
    const columns = Math.ceil(width / pitch), rows = Math.ceil(height / pitch)
    // This temporary canvas contains continuous tones, one sample per print
    // cell. Only this unscreened image is ever resampled or resized.
    const samples = document.createElement('canvas')
    samples.width = columns; samples.height = rows
    const sampleContext = samples.getContext('2d', { willReadFrequently: true })
    const context = target.getContext('2d', { alpha: false })
    if (!sampleContext || !context) throw new Error('Footer canvas is unavailable')
    sampleContext.fillStyle = BACKGROUND
    sampleContext.fillRect(0, 0, columns, rows)
    sampleContext.imageSmoothingEnabled = true
    sampleContext.imageSmoothingQuality = 'high'
    const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight)
    const sourceWidth = width / scale, sourceHeight = height / scale
    const sourceX = (image.naturalWidth - sourceWidth) * (mobile ? .53 : .5)
    const sourceY = (image.naturalHeight - sourceHeight) * (mobile ? .5 : .55)
    sampleContext.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, width / pitch, height / pitch)
    const pixels = sampleContext.getImageData(0, 0, columns, rows).data

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
    let dots = 0
    for (let row = 0; row < rows; row++) {
      const y = (row + .5) * pitch, fraction = y / height
      const fade = smooth((fraction - .18) / .22) * (1 - .75 * smooth((fraction - .86) / .14))
      if (fade === 0) continue
      for (let column = 0; column < columns; column++) {
        const offset = (row * columns + column) * 4
        const luminance = .2126 * pixels[offset]! + .7152 * pixels[offset + 1]! + .0722 * pixels[offset + 2]!
        const tone = Math.pow(clamp((luminance - 40) / 190), 1.35) * .9 * fade
        const radius = radii[Math.round(tone * 1024)]! * pitch
        if (radius * dpr < .015) continue
        const x = (column + .5) * pitch
        const cx = x * scaleX, cy = y * scaleY, r = radius * Math.min(scaleX, scaleY)
        const left = Math.max(0, Math.floor(cx - r - .5)), right = Math.min(target.width - 1, Math.ceil(cx + r + .5))
        const top = Math.max(0, Math.floor(cy - r - .5)), bottom = Math.min(target.height - 1, Math.ceil(cy + r + .5))
        // Rasterize a single aligned screen at native resolution. Bounded
        // pixel work avoids giant GPU paths and keeps ultrawide resizing fast.
        for (let py = top; py <= bottom; py++) {
          for (let px = left; px <= right; px++) {
            // A subpixel circle must fade by area, not retain a half-lit
            // center pixel as its radius approaches zero.
            const coverage = Math.min(Math.PI * r * r, clamp(r + .5 - Math.hypot(px + .5 - cx, py + .5 - cy)))
            const index = (py * target.width + px) * 4
            const red = Math.round(7 + 176 * coverage)
            if (red <= ink[index]!) continue
            ink[index] = red
            ink[index + 1] = Math.round(11 + 175 * coverage)
            ink[index + 2] = Math.round(16 + 160 * coverage)
          }
        }
        dots++
      }
    }
    context.putImageData(print, 0, 0)
    samples.width = samples.height = 1
    dirty = false
    lastSize = size
    renderCount++
    Object.assign(target.dataset, {
      ready: 'true', source: SOURCE, gridPitch: String(pitch), screenCount: '1',
      renderCount: String(renderCount), renderMs: (performance.now() - started).toFixed(1),
      dpr: String(dpr), dots: String(dots), raster: 'native-pixels',
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
