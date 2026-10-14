// Build a traditional amplitude-modulated screen from the existing smooth
// source plate. Ink dots join in light areas and leave small negative holes;
// restricting every dot to an isolated circle would produce an LED matrix.
const fs = require('node:fs')
const { createCanvas, loadImage } = require(process.env.ODIN_CANVAS_PACKAGE || '@napi-rs/canvas')
const clamp = value => Math.max(0, Math.min(1, value))
const smooth = value => { const t = clamp(value); return t * t * (3 - 2 * t) }
function coverage(radius, pitch) {
  const half = pitch / 2
  if (radius <= half) return Math.PI * radius * radius / (pitch * pitch)
  const cap = radius * radius * Math.acos(half / radius) - half * Math.sqrt(radius * radius - half * half)
  return (Math.PI * radius * radius - 4 * cap) / (pitch * pitch)
}
function printRadius(tone, pitch) {
  let low = 0, high = pitch / Math.SQRT2
  for (let i = 0; i < 20; i++) {
    const middle = (low + high) / 2
    if (coverage(middle, pitch) < tone) low = middle
    else high = middle
  }
  return (low + high) / 2
}
async function main() {
  const width = 3600, height = 1200, pitch = 6
  const source = 'assets/illustrations/v0.16.1/odin-mountain-source.png'
  const background = '#070b10', ink = '#939b95'
  const folder = 'assets/illustrations/v0.16.1'
  fs.mkdirSync(folder, { recursive: true }); fs.mkdirSync('docs/review/v0.16.1', { recursive: true })
  const image = await loadImage(source)
  const canvas = createCanvas(width, height), context = canvas.getContext('2d')
  context.fillStyle = background; context.fillRect(0, 0, width, height)
  const imageHeight = width * image.height / image.width
  // Remove any preliminary screen in the generated artwork before rebuilding
  // a single exact lattice. Both the real-model silhouette and mountain tones
  // then receive the same deterministic print treatment.
  context.filter = 'blur(3px)'
  context.drawImage(image, 0, height - imageHeight, width, imageHeight)
  context.filter = 'none'
  const pixels = context.getImageData(0, 0, width, height).data
  const print = createCanvas(width, height), printContext = print.getContext('2d')
  printContext.fillStyle = background; printContext.fillRect(0, 0, width, height)
  printContext.fillStyle = ink
  const circles = [], radii = Array.from({ length: 1025 }, (_, i) => printRadius(i / 1024, pitch))
  let joinedDots = 0
  for (let y = pitch / 2; y < height; y += pitch) for (let x = pitch / 2; x < width; x += pitch) {
    let sum = 0
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const sx = Math.max(0, Math.min(width - 1, x + dx)), sy = Math.max(0, Math.min(height - 1, y + dy))
      const offset = (sy * width + sx) * 4
      sum += .2126 * pixels[offset] + .7152 * pixels[offset + 1] + .0722 * pixels[offset + 2]
    }
    const luminance = sum / 25
    const skyFade = smooth((y - 180) / 360)
    const tone = Math.pow(clamp((luminance - 16) / 144), .9) * skyFade
    const radius = radii[Math.round(tone * 1024)]
    if (!Number.isFinite(radius)) throw new Error(`Invalid radius at ${x},${y}`)
    if (radius < .14) continue
    if (radius > pitch / 2) joinedDots++
    circles.push(`<circle cx="${x}" cy="${y}" r="${radius.toFixed(3)}"/>`)
    printContext.beginPath(); printContext.arc(x, y, radius, 0, Math.PI * 2); printContext.fill()
  }
  const master = `${folder}/odin-mountain-print.svg`
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>Odin in the mountains — fine newspaper screen</title><rect width="100%" height="100%" fill="${background}"/><g fill="${ink}">${circles.join('')}</g></svg>\n`
  fs.writeFileSync(master, svg)
  const target = 'public/images/odin-mountain-footer-v0.16.1.png'
  fs.writeFileSync(target, print.toBuffer('image/png'))
  const record = { source, master, target, width, height, pitch, gridOrigin: [pitch / 2, pitch / 2], dots: circles.length, joinedDots, inks: [background, ink], sourceDescreenPixels: 3, sampling: '5x5 mean luminance', toneMapping: 'circular ink coverage including joined dots and negative holes', amplitudeModulated: true, randomJitter: false, randomDensity: false }
  fs.writeFileSync('docs/review/v0.16.1/halftone-grid.json', JSON.stringify(record, null, 2) + '\n')
  console.log(JSON.stringify(record))
}
main().catch(error => { console.error(error); process.exitCode = 1 })
