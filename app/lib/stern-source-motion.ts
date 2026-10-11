import * as THREE from 'three'
import { ease } from './odin-motion.ts'

// odin.blend: odin.026 action, frames 11–37. The original stern bore has its
// own local translation and three Euler curves under Empty.004; a single pitch
// around the web joint cannot reproduce its motion.
const localStart = {
  position: new THREE.Vector3(-4.005529881, 238.725509644, 44.090751648),
  euler: new THREE.Vector3(-0.328217357, 0.312268078, 0.992682397),
}
const localEnd = {
  position: new THREE.Vector3(-4.005529881, 239.001022339, 43.585639954),
  euler: new THREE.Vector3(-0.131115004, 0.001195928, 1.023922801),
}
const parentPosition = new THREE.Vector3(-4.005618572, 7.815059662, 16.224782944)
const parentRotation = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -Math.PI)
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

export function sternSourceMotion(deployment: number, jointRestWeb: THREE.Vector3) {
  // Start after the muzzle-end leaves clear the bore; reverse evaluation fully
  // lowers the original gun before the leaves fold over it.
  const current = sourceWorldPose(ease(.66, .92, deployment))
  const modelTurn = current.quaternion.multiply(sourceClosed.quaternion.clone().invert())
  const modelOffset = current.position.sub(sourceClosed.position.clone().applyQuaternion(modelTurn))
  const turn = webBasis.clone().multiply(modelTurn).multiply(webBasis.clone().invert())
  const offset = new THREE.Vector3(modelOffset.x, modelOffset.z, -modelOffset.y)
  const move = jointRestWeb.clone().applyQuaternion(turn).add(offset).sub(jointRestWeb)
  return { move, turn }
}
