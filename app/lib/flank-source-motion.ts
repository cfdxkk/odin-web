import * as THREE from 'three'
import { ease } from './odin-motion.ts'

const webBasis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2)

// Source odin.023 / odin.071: fixed location and two Euler keys with horizontal
// one-third Bezier handles. Keep all three channels, including their yaw/roll.
// Port geometry is the original model's reflection about the ship centreline.
export function flankSourceMotion(data: Record<string, any>, deployment: number) {
  const amount = ease(Number(data.sourceMotionStart), Number(data.sourceMotionEnd), deployment)
  const start = data.sourceEulerStart as number[], end = data.sourceEulerEnd as number[]
  const [w, x, y, z] = data.sourceParentRotationWXYZ as number[]
  const parent = new THREE.Quaternion(x, y, z, w)
  const rotation = (fraction: number) => parent.clone().multiply(new THREE.Quaternion().setFromEuler(
    new THREE.Euler(...start.map((value, i) => value + (end[i]! - value) * fraction) as [number, number, number], 'ZYX')))
  const delta = rotation(amount).multiply(rotation(0).invert())
  if (data.sourceMirror < 0) {
    // S R S for S=diag(-1,1,1) is a proper rotation; an axial vector's Y/Z
    // components change sign under this reflection.
    delta.y *= -1
    delta.z *= -1
  }
  if (data.sourceRigRotationWXYZ) {
    const [rw, rx, ry, rz] = data.sourceRigRotationWXYZ as number[]
    const rest = new THREE.Quaternion(rx, ry, rz, rw)
    delta.premultiply(rest).multiply(rest.clone().invert())
  }
  return webBasis.clone().multiply(delta).multiply(webBasis.clone().invert())
}
