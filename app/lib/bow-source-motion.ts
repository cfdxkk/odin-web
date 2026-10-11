import * as THREE from 'three'
import { ease } from './odin-motion.ts'

// odin.blend: odin.002 action, frames 30–56. Blender interpolates each local
// location/Euler channel with horizontal one-third Bezier handles. The asset
// was baked at frame 30, so this returns only the rigid delta from that pose.
// Blender's XYZ Euler is applied as Rz * Ry * Rx (Three's ZYX order).
const localStart = {
  position: new THREE.Vector3(-4.005529881, 238.613494873, 44.028533936),
  euler: new THREE.Vector3(-0.328217447, 0.312268108, 0.992682338),
}
const localEnd = {
  position: new THREE.Vector3(-4.005529881, 239.001022339, 43.585639954),
  euler: new THREE.Vector3(-0.131115004, 0.001195928, 1.023922801),
}
// The source parent and parent-inverse are fixed throughout this action.
const parentPosition = new THREE.Vector3(4.005511761, 6.288059235, -24.433135986)
const parentRotation = new THREE.Quaternion()
  .setFromAxisAngle(new THREE.Vector3(1, 0, 0), 0.106559932)
const webBasis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2)

function sourceWorldPose(amount: number) {
  const position = localStart.position.clone().lerp(localEnd.position, amount)
    .applyQuaternion(parentRotation).add(parentPosition)
  const euler = localStart.euler.clone().lerp(localEnd.euler, amount)
  const quaternion = parentRotation.clone().multiply(new THREE.Quaternion()
    .setFromEuler(new THREE.Euler(euler.x, euler.y, euler.z, 'ZYX')))
  return { position, quaternion }
}

const sourceClosed = sourceWorldPose(0)

export function bowSourceMotion(deployment: number, jointRestWeb: THREE.Vector3) {
  const current = sourceWorldPose(ease(.30, .56, deployment))
  const modelTurn = current.quaternion.multiply(sourceClosed.quaternion.clone().invert())
  const modelOffset = current.position.sub(sourceClosed.position.clone().applyQuaternion(modelTurn))
  const turn = webBasis.clone().multiply(modelTurn).multiply(webBasis.clone().invert())
  const offset = new THREE.Vector3(modelOffset.x, modelOffset.z, -modelOffset.y)
  const move = jointRestWeb.clone().applyQuaternion(turn).add(offset).sub(jointRestWeb)
  return { move, turn }
}
