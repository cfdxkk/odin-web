/** Ordered screen: fixed square marks, with tonal changes carried by ink
 * levels and a repeating 4×4 arrangement rather than growing circles. */
export const FOOTER_SCREEN_MATRIX = [
  0, 8, 2, 10,
  12, 4, 14, 6,
  3, 11, 1, 9,
  15, 7, 13, 5,
] as const

export const FOOTER_SCREEN_PITCH = 3.2
export const FOOTER_SCREEN_MARK_RATIO = .84
export const FOOTER_SCREEN_INKS = [0, 78, 143, 208] as const

export function footerInkLevel(tone: number, column: number, row: number) {
  const scaled = Math.max(0, Math.min(1, tone)) * (FOOTER_SCREEN_INKS.length - 1)
  const base = Math.floor(scaled)
  const threshold = (FOOTER_SCREEN_MATRIX[(row & 3) * 4 + (column & 3)]! + .5) / 16
  return Math.min(FOOTER_SCREEN_INKS.length - 1, base + Number(scaled - base > threshold))
}
