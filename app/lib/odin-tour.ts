import * as THREE from 'three'
import { DEPLOY_SECONDS, ease, sampleOdinMotion } from './odin-motion.ts'
import { sampleOdinCamera } from './odin-camera.ts'
import { inspectionCameraFraming, type WeaponRouteSide } from './odin-weapon-tour.ts'

// Points use the source model's axes: X across ship, +Y bow, +Z up.
// Scrolling selects an inspection shot (or the opening orbit), never a camera
// interpolation fraction or a weapon deployment fraction.
export const ODIN_TOUR = [
  { id: 'overview', point: [0, 32, 26], view: [1.6, 1.1, .9], distance: 10.6, time: 0 },
  { id: 'batteries', point: [0, 160, 20], view: [1.35, .7, .8], distance: 8.1, time: 24 },
  { id: 'bridge', point: [0, -75, 83], view: [.7, -1.4, .65], distance: 7.2, time: 0 },
  { id: 'engines', point: [0, -190, 2], view: [1.3, -2.2, -.7], distance: 8.0, time: 46 },
] as const

export const ODIN_TOUR_CAMERA_SECONDS = 2.8
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
export function tourWheelTarget(index: number, direction: -1 | 1, currentTop: number, viewportAnchor: number, includeArchive = false) {
  const current = clampTourIndex(index)
  // Return from ordinary scrolling to the current stage before advancing.
  if (direction < 0 && currentTop < viewportAnchor - 48 || direction > 0 && currentTop > viewportAnchor + 48) return current
  const next = current + direction
  if (includeArchive && next === ODIN_TOUR.length) return next
  // At either end, hand the wheel back to ordinary document scrolling.
  return next < 0 || next >= ODIN_TOUR.length ? undefined : next
}
export function sampleTourCamera(index: number, aspect = 1.6, entrySide: WeaponRouteSide = -1) {
  const chapter = clampTourIndex(index), shot = ODIN_TOUR[chapter]!
  const [x, y, z] = shot.point
  const [vx, vy, vz] = shot.view
  const target = new THREE.Vector3(x * .01, z * .01, -y * .01)
  const framing = chapter >= 2 ? inspectionCameraFraming(aspect) : Math.max(.62, Math.pow(1.6 / Math.max(1.6, aspect), .7)) * Math.max(1, 1.25 / Math.max(aspect, .01))
  // The elevated aft weapon view feeds the established rear-quarter route.
  // Both later chapters choose the same side as they pull back around the stern.
  const side = chapter >= 2 ? -entrySide : 1
  const position = new THREE.Vector3(vx * side, vz, -vy).normalize().multiplyScalar(shot.distance * framing).add(target)
  return { position, target }
}

// The first chapter restores the original film orbit; later chapters hold
// their inspection shots while the mechanical transition finishes.
export function sampleTourDisplayCamera(index: number, cameraTime: number, aspect = 1.6, mobile = false, entrySide: WeaponRouteSide = -1) {
  return clampTourIndex(index) === 0 ? sampleOdinCamera(cameraTime, aspect, mobile) : sampleTourCamera(index, aspect, entrySide)
}

type TourMotion = { deployment: number; thrust: number }
export type TourTransition = {
  from: TourMotion; to: TourMotion; targetTime: number
  fadeSeconds: number; moveSeconds: number; igniteSeconds: number; duration: number
}
// A chapter change is a finite pose transition, independent of film playback.
// Entering propulsion lights the engines while the weapons stow. On the return
// to a weapon view, finish fading the exhaust before starting deployment.
export function createTourTransition(from: TourMotion, targetTime: number): TourTransition {
  const to = sampleOdinMotion(targetTime)
  const fadeSeconds = from.thrust > 0 && (to.deployment > 0 || to.thrust < from.thrust) ? from.thrust * 1.2 : 0
  const moveSeconds = Math.abs(to.deployment - from.deployment) * DEPLOY_SECONDS
  const igniteSeconds = Math.max(0, to.thrust - (fadeSeconds ? 0 : from.thrust)) * 2.5
  return { from: { ...from }, to, targetTime, fadeSeconds, moveSeconds, igniteSeconds, duration: fadeSeconds + Math.max(moveSeconds, igniteSeconds) }
}
function inverseEase(value: number) {
  return .5 - Math.sin(Math.asin(1 - 2 * THREE.MathUtils.clamp(value, 0, 1)) / 3)
}
export function sampleTourTransition(transition: TourTransition, elapsed: number) {
  const { from, to, fadeSeconds, moveSeconds, igniteSeconds, duration, targetTime } = transition
  const t = Math.max(0, elapsed)
  if (t >= duration) return { deployment: to.deployment, thrust: to.thrust, time: targetTime }
  let deployment = from.deployment, thrust = from.thrust
  if (fadeSeconds) thrust = from.thrust * (1 - ease(0, fadeSeconds, t))
  if (t >= fadeSeconds) {
    if (moveSeconds) deployment = THREE.MathUtils.lerp(from.deployment, to.deployment, ease(0, moveSeconds, t - fadeSeconds))
    if (igniteSeconds) thrust = THREE.MathUtils.lerp(fadeSeconds ? 0 : from.thrust, to.thrust, ease(0, igniteSeconds, t - fadeSeconds))
  }
  // During concurrent stow/ignition the rig's film time follows deployment;
  // thrust is an independent presentation channel, supplied above.
  const time = deployment > 0 || to.deployment > from.deployment && thrust === 0 ? to.deployment > from.deployment ? 12 + DEPLOY_SECONDS * inverseEase(deployment) : 32 + DEPLOY_SECONDS * inverseEase(1 - deployment)
    : thrust > 0 ? 32 + DEPLOY_SECONDS + 2.5 * inverseEase(thrust)
    : to.thrust > 0 ? 32 + DEPLOY_SECONDS : targetTime
  return { deployment, thrust, time }
}
