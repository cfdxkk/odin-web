import * as THREE from 'three'
import { ease } from './odin-motion.ts'

const webBasis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2)

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
