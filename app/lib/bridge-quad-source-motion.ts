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

// Relieve only tube packing once the fitted skins have cleared their corridor.
// Keep the original stroke direction, axial motion and release endpoints.
export function bridgeQuadTubeCompactAmount(data: Record<string, any>, deployment: number) {
  const relief = Number(data.compactReleaseRelief ?? 0)
    * ease(Number(data.compactReliefStart ?? .12), Number(data.compactReliefEnd ?? .15), deployment)
  return bridgeQuadCompactAmount(data, deployment) * (1 - relief)
}

// In a ship-side view, model Y is horizontal and model Z is vertical. Keep
// the barrels beside the casing with only a small horizontal packing stroke.
export function bridgeQuadTubeCompactVector(data: Record<string, any>): [number, number, number] {
  const [x, y, z] = data.compactVector as [number, number, number]
  return [x, y * (.67 / 1.98), z * (4 / 3) + .20]
}

// The lower receiver corners previously escaped the sloped closed hull.
// Recenter the quartet on that envelope, retaining the bearing pair's gap.
// Tubes get a little extra vertical packing inside their roomy receivers.
export function bridgeQuadBearingCompactVector(data: Record<string, any>): [number, number, number] {
  const [x, y, z] = data.compactVector as [number, number, number]
  return [x, y * (.67 / 1.98), z * (16 / 15) + .20]
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
