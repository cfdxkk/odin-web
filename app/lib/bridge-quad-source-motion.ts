import * as THREE from 'three'
import { ease } from './odin-motion.ts'

const webBasis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2)

// A smooth center lead clears the long tubes without an armor detour. Both
// derivatives still vanish at the ends of the original packing interval.
export function bridgeQuadCompactAmount(data: Record<string, any>, deployment: number) {
  const amount = 1 - ease(Number(data.compactStart), Number(data.compactEnd), deployment)
  return amount + Number(data.compactLead ?? 0) * amount * (1 - amount) ** 2
}

// The fitted armor retains its original packing clock.
export function bridgeQuadPetalAmount(data: Record<string, any>, deployment: number) {
  return bridgeQuadCompactAmount(data, deployment) ** Number(data.petalPackingExponent ?? 1)
}

// Preserve the accepted early transverse clock for the long fixed forks.
// Moving receivers use the later packing clock below; guide compensation
// keeps those forks on their existing world-space trajectories.
export function bridgeQuadTubeCompactAmount(data: Record<string, any>, deployment: number) {
  const relief = Number(data.compactReleaseRelief ?? 0)
    * ease(Number(data.compactReliefStart ?? .12), Number(data.compactReliefEnd ?? .15), deployment)
  return bridgeQuadCompactAmount(data, deployment) * (1 - relief)
}

// Keep the tubes and receivers gathered until their axial stroke reaches the
// previous 42% pose. Then spread before original aiming begins at 69%.
// The same clock gathers them before the final axial withdrawal on closing.
export function bridgeQuadTubePackingAmount(deployment: number) {
  return 1 - ease(.42, .64, deployment)
}

// In a ship-side view, model Y is horizontal and model Z is vertical. Keep
// the gathered tubes within the straight axial corridor beside the casing.
export function bridgeQuadTubeCompactVector(data: Record<string, any>): [number, number, number] {
  const [x, y, z] = data.compactVector as [number, number, number]
  return [x, y * (.60 / 1.98), z * (16 / 15) + .20]
}

// The lower receiver corners previously escaped the sloped closed hull.
// Recenter the quartet on that envelope, retaining the bearing pair's gap.
// Receivers keep their fitted seat while tubes clear the central casing.
export function bridgeQuadBearingCompactVector(data: Record<string, any>): [number, number, number] {
  const [x, y, z] = data.compactVector as [number, number, number]
  return [x, y * (.67 / 1.98), z * (16 / 15) + .20]
}

// The sloped fixed lip narrows toward the outside. Keep the receiver shelves
// seated while the carriage passes it, gathering only their short inner shoes
// further into the bay. Release them once the carriage is clear. The tubes and
// long forks compensate this local motion to retain their own accepted paths.
export function bridgeQuadBearingPackingOffset(data: Record<string, any>, deployment: number): [number, number, number] {
  const seat = 1 - ease(.60, .69, deployment)
  const [x, y, z] = bridgeQuadBearingCompactVector(data)
  const corridor = Math.sign(y) * 1.20 * ease(.35, .50, deployment) * seat
  return [x * seat, y * seat + corridor, z * seat]
}

// Shallow side-view packing keeps the tubes outside the central casing.
// Seat their receivers behind the closing skins before packing; reversing
// releases the skins before visible extension. One broad, smooth timeline
// stroke avoids racing the longer tubes through the short packing interval.
export function bridgeQuadTubeSlideAmount(deployment: number) {
  return 1 - ease(.08, .69, deployment)
}

export function bridgeQuadTubeSlideVector(data: Record<string, any>): [number, number, number] {
  const vector = data.slideVector as [number, number, number]
  const length = Math.hypot(...vector)
  return vector.map(value => value * (length + 8) / length) as [number, number, number]
}

// These long fixed forks are children of the moving bearings. Compensate for
// their revised packing so each fork keeps its accepted world-space path.
export function bridgeQuadGuideCompactVector(cradle: Record<string, any>, guide: Record<string, any>): [number, number, number] {
  const original = cradle.compactVector as number[]
  const corrected = bridgeQuadBearingCompactVector(cradle)
  return original.map((value, axis) => value + Number(guide.compactVector[axis]) - corrected[axis]!) as [number, number, number]
}

// Original bridge turret action: 15–45, horizontal one-third Bezier handles.
// Retain only frames 30–45: NAV is the source midpoint, not its deep stow.
export function bridgeQuadCarriageAmount(data: Record<string, any>, deployment: number) {
  const frameAmount = .5 + .5 * ease(Number(data.sourceCarriageStart), Number(data.sourceCarriageEnd), deployment)
  return 2 * (ease(0, 1, frameAmount) - .5)
}

// Original Empty.007 action: frames 53–86, all three Blender XYZ channels.
// Port uses the original collection; starboard reflects it across ship X.
export function bridgeQuadSourceAim(data: Record<string, any>, deployment: number) {
  const amount = ease(Number(data.sourceAimStart), Number(data.sourceAimEnd), deployment)
  const start = data.sourceEulerStart as number[], end = data.sourceEulerEnd as number[]
  const euler = start.map((value, i) => value + (end[i]! - value) * amount)
  const turn = new THREE.Quaternion().setFromEuler(new THREE.Euler(...euler as [number, number, number], 'ZYX'))
  const rest = new THREE.Quaternion().setFromEuler(new THREE.Euler(...start as [number, number, number], 'ZYX'))
  turn.multiply(rest.invert())
  if (data.sourceMirror > 0) { turn.y *= -1; turn.z *= -1 }
  return webBasis.clone().multiply(turn).multiply(webBasis.clone().invert())
}
