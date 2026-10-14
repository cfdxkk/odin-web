/** Ordered screen: fixed square marks, with tonal changes carried by ink
 * levels and a repeating 4×4 arrangement rather than growing circles. */
export const FOOTER_SCREEN_MATRIX = [
  0, 8, 2, 10,
  12, 4, 14, 6,
  3, 11, 1, 9,
  15, 7, 13, 5,
] as const

export const FOOTER_SCREEN_PITCH = 3.8
export const FOOTER_SCREEN_MARK_RATIO = .84
export const FOOTER_SCREEN_INKS = [0, 78, 143, 208] as const

export function footerInkLevel(tone: number, column: number, row: number) {
  const scaled = Math.max(0, Math.min(1, tone)) * (FOOTER_SCREEN_INKS.length - 1)
  const base = Math.floor(scaled)
  const threshold = (FOOTER_SCREEN_MATRIX[(row & 3) * 4 + (column & 3)]! + .5) / 16
  return Math.min(FOOTER_SCREEN_INKS.length - 1, base + Number(scaled - base > threshold))
}

/** Remove small disconnected low-contrast flecks in the continuous-tone
 * plate before screening. This never changes a surviving mark's footprint
 * and retains both connected faint ridges and small bright ship details. */
export function cleanFooterTones(tones: Float32Array, width: number, height: number) {
  const clean = tones.slice()
  const visited = new Uint8Array(tones.length)
  const queue = new Int32Array(tones.length)
  for (let start = 0; start < tones.length; start++) {
    if (visited[start] || tones[start]! < .01) continue
    let head = 0, tail = 1, peak = 0
    queue[0] = start; visited[start] = 1
    while (head < tail) {
      const index = queue[head++]!, x = index % width, y = Math.floor(index / width)
      peak = Math.max(peak, tones[index]!)
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if ((!dx && !dy) || x + dx < 0 || x + dx >= width || y + dy < 0 || y + dy >= height) continue
        const neighbor = (y + dy) * width + x + dx
        if (!visited[neighbor] && tones[neighbor]! >= .01) {
          visited[neighbor] = 1; queue[tail++] = neighbor
        }
      }
    }
    if (tail < 24 && peak < .32) for (let i = 0; i < tail; i++) clean[queue[i]!] = 0
  }
  // A faint fleck can still be attached to a ridge through sub-visible tones.
  // The ordered screen would turn its tip into one full first-level square.
  // Require either area support or a line continuing through the faint sample;
  // this removes those tips without eroding narrow, continuous distant ridges.
  const supported = clean.slice()
  const threshold = 1 / 96 // First visible threshold of the 4×4, four-ink screen.
  for (let y = 1; y < height - 1; y++) for (let x = 1; x < width - 1; x++) {
    const index = y * width + x
    if (clean[index]! < threshold || clean[index]! >= .04) continue
    const neighbors = [
      clean[index - width - 1]!, clean[index - width]!, clean[index - width + 1]!,
      clean[index - 1]!, clean[index + 1]!,
      clean[index + width - 1]!, clean[index + width]!, clean[index + width + 1]!,
    ].map(tone => tone >= threshold)
    const areaSupport = neighbors.filter(Boolean).length >= 4
    const ridgeSupport = (neighbors[0] && neighbors[7]) || (neighbors[1] && neighbors[6])
      || (neighbors[2] && neighbors[5]) || (neighbors[3] && neighbors[4])
    if (!areaSupport && !ridgeSupport) supported[index] = 0
  }
  return supported
}
