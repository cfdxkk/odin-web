const unit = (value: number) => Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0))

// The weapon chapter has a real document scroll range. The sticky content
// remains at the viewport while this range drives the inspection camera.
export function weaponScrollProgress(top: number, height: number, viewport: number) {
  return unit(-top / Math.max(1, height - viewport))
}
export function weaponScrollOffset(step: number, count: number, height: number, viewport: number) {
  return unit(step / Math.max(1, count - 1)) * Math.max(0, height - viewport)
}
export function weaponStepAt(progress: number, count: number) {
  return Math.round(unit(progress) * Math.max(0, count - 1))
}
export function weaponStageTop(top: number, height: number, viewport: number) {
  return top > 0 ? top : Math.min(0, top + Math.max(0, height - viewport))
}
export function isWithinWeaponScroll(top: number, height: number, viewport: number, direction: -1 | 1) {
  const end = top + height - viewport
  return direction > 0 ? top <= 1 && end > 1 : top < -1 && end >= -1
}
