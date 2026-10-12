// Build a static amplitude-modulated print screen: no noise or jitter.
// npm runtime supplies @napi-rs/canvas through ODIN_CANVAS_PACKAGE when needed.
const fs = require('node:fs')
const { createCanvas, loadImage } = require(process.env.ODIN_CANVAS_PACKAGE || '@napi-rs/canvas')
async function main() {
  const width = 2400, height = 900, pitch = 4
  const source = 'assets/illustrations/v0.16.0/odin-mountain-grayscale-source.png'
  const image = await loadImage(source)
  const canvas = createCanvas(width, height), context = canvas.getContext('2d')
  context.fillStyle = '#070b10'; context.fillRect(0, 0, width, height)
  const imageHeight = width * image.height / image.width
  context.drawImage(image, 0, height - imageHeight, width, imageHeight)
  const pixels = context.getImageData(0, 0, width, height).data
  const circles = []
  for (let y = pitch / 2; y < height; y += pitch) for (let x = pitch / 2; x < width; x += pitch) {
    let sum = 0
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const sx = Math.max(0, Math.min(width - 1, x + dx)), sy = Math.max(0, Math.min(height - 1, y + dy))
      const offset = (sy * width + sx) * 4
      sum += .2126 * pixels[offset] + .7152 * pixels[offset + 1] + .0722 * pixels[offset + 2]
    }
    const luminance = sum / 25
    const skyFade = Math.max(0, Math.min(1, (y - 220) / 170))
    // Leave the upper corners quiet for the thanks and official links.
    const cornerFade = y < 410 && (x < 750 || x > 1750) ? .25 + .75 * Math.max(0, (y - 310) / 100) : 1
    const tone = Math.max(0, Math.min(1, (luminance - 20) / 200)) * skyFade * cornerFade
    const radius = (pitch / 2) * Math.sqrt(tone * .85)
    if (!Number.isFinite(radius)) throw new Error(`Invalid radius at ${x},${y}`)
    if (radius < .28) continue
    circles.push(`<circle cx="${x}" cy="${y}" r="${radius.toFixed(3)}"/>`)
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>Odin in the mountains — aligned halftone print</title><rect width="100%" height="100%" fill="#070b10"/><g fill="#dce2e7">${circles.join('')}</g></svg>\n`
  const target = 'public/images/odin-mountain-footer-v0.16.0.svg'
  fs.writeFileSync(target, svg)
  const record = { source, target, width, height, pitch, gridOrigin: [pitch / 2, pitch / 2], dots: circles.length, inks: ['#070b10', '#dce2e7'], sampling: '5x5 mean luminance', amplitudeModulated: true, randomJitter: false, randomDensity: false }
  fs.writeFileSync('docs/review/v0.16.0/halftone-grid.json', JSON.stringify(record, null, 2) + '\n')
  console.log(JSON.stringify(record))
}
main().catch(error => { console.error(error); process.exitCode = 1 })
