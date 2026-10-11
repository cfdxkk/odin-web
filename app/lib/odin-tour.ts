import * as THREE from 'three'

// Points use the source model's axes: X across ship, +Y bow, +Z up.
// Each chapter has a fixed shot. Scrolling selects a chapter, never a camera
// interpolation fraction or a weapon deployment fraction.
export const ODIN_TOUR = [
  { id: 'overview', point: [0, 32, 26], view: [1.6, 1.1, .9], distance: 10.6, time: 0 },
  { id: 'hull', point: [18, 15, 6], view: [2.3, .6, .65], distance: 10, time: 24 },
  { id: 'upper', point: [0, 124, 45], view: [1, 1, 1.05], distance: 2.1, time: 24 },
  { id: 'lower', point: [0, 76, -56], view: [1, 1, -.95], distance: 2.15, time: 24 },
  { id: 'single', point: [55, 16, 30], view: [2, 1, .65], distance: 1.4, time: 24 },
  { id: 'twinfore', point: [28, -48, 53], view: [2, 1, .9], distance: 1.5, time: 24 },
  { id: 'twinrear', point: [18, -202, 43], view: [2, 1, .9], distance: 1.5, time: 24 },
  { id: 'quad', point: [60, -58, 105], view: [1, 1, .55], distance: .9, time: 24 },
  { id: 'pdc', point: [67, 76, 5], view: [2, .6, .85], distance: 2.05, time: 24 },
  { id: 'launchers', point: [0, 235, 20], view: [1, 2, .8], distance: 2.15, time: 24 },
  { id: 'bridge', point: [0, -46, 120], view: [1.15, 1.4, .55], distance: 1.9, time: 24 },
  { id: 'engines', point: [0, -245, 15], view: [.75, -2, .55], distance: 3.7, time: 46 },
] as const

export type TourId = typeof ODIN_TOUR[number]['id']
export function clampTourIndex(index: number) {
  return Math.max(0, Math.min(ODIN_TOUR.length - 1, Math.round(Number.isFinite(index) ? index : 0)))
}
export function selectTourChapter(tops: number[], viewportAnchor: number) {
  // A hysteresis-free midpoint boundary gives the same result going either way.
  // The result is an integer even during a drag or momentum scroll.
  let selected = 0, distance = Infinity
  tops.forEach((top, index) => {
    const candidate = Math.abs(top - viewportAnchor)
    if (candidate < distance) { selected = index; distance = candidate }
  })
  return selected
}
export function sampleTourCamera(index: number, aspect = 1.6) {
  const shot = ODIN_TOUR[clampTourIndex(index)]!
  const [x, y, z] = shot.point
  const [vx, vy, vz] = shot.view
  const target = new THREE.Vector3(x * .01, z * .01, -y * .01)
  const framing = Math.max(.62, Math.pow(1.6 / Math.max(1.6, aspect), .7)) * Math.max(1, 1.25 / Math.max(aspect, .01))
  const position = new THREE.Vector3(vx, vz, -vy).normalize().multiplyScalar(shot.distance * framing).add(target)
  return { position, target }
}
