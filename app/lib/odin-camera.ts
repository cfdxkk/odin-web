import * as THREE from 'three'

// A steady orbit avoids combining rotation with repeated zooms, climbs and
// moving targets. Its clock remains independent of the weapon film.
export const ODIN_CAMERA_ORBIT_SECONDS = 45
const startAngle = -5 * Math.PI / 6
const orbitRadius = 11.2
const orbitSlope = .24
const aimHeight = .20
export type OdinCameraPose = { position: THREE.Vector3; target: THREE.Vector3 }
export type OrientedOdinCameraPose = OdinCameraPose & { up: THREE.Vector3 }

export function odinCameraOrientation(pose: OrientedOdinCameraPose) {
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(pose.position, pose.target, pose.up))
}

// Blend viewing direction and screen orientation together along the shortest
// quaternion arc. A separate world-up blend can wind the frame around the bow
// when entering a vertical inspection from the opposite homepage heading.
export function interpolateOrientedOdinCamera(from: OrientedOdinCameraPose, to: OrientedOdinCameraPose, progress: number): OrientedOdinCameraPose {
  const u = THREE.MathUtils.clamp(progress, 0, 1)
  const orientation = odinCameraOrientation(from).slerp(odinCameraOrientation(to), u)
  const target = from.target.clone().lerp(to.target, u)
  const radius = THREE.MathUtils.lerp(from.position.distanceTo(from.target), to.position.distanceTo(to.target), u)
  return {
    target,
    position: new THREE.Vector3(0, 0, radius).applyQuaternion(orientation).add(target),
    up: new THREE.Vector3(0, 1, 0).applyQuaternion(orientation),
  }
}

// Rejoin the orbit from the visible heading instead of turning back to phase zero.
export function odinCameraPhase(pose: OdinCameraPose) {
  const offset = pose.position.clone().sub(pose.target)
  const angle = Math.atan2(offset.z, offset.x)
  return THREE.MathUtils.euclideanModulo(angle - startAngle, Math.PI * 2) * ODIN_CAMERA_ORBIT_SECONDS / (Math.PI * 2)
}

export function odinCameraFraming(aspect: number, mobile = false) {
  if (mobile) return { distanceScale: 1.60, viewOffsetY: 0 }
  const wideScale = Math.max(.72, Math.pow((16 / 9) / Math.max(16 / 9, aspect), .65))
  return {
    distanceScale: wideScale * Math.max(1, 1.25 / aspect),
    // Lift the enlarged silhouette clear of playback controls on wide screens.
    viewOffsetY: .06 * THREE.MathUtils.smoothstep(aspect, 16 / 9, 21 / 9),
  }
}

export function sampleOdinCamera(time: number, aspect = 1.6, mobile = false): OdinCameraPose {
  const phase = THREE.MathUtils.euclideanModulo(time, ODIN_CAMERA_ORBIT_SECONDS)
  const angle = startAngle + phase * Math.PI * 2 / ODIN_CAMERA_ORBIT_SECONDS
  const radius = orbitRadius * odinCameraFraming(aspect, mobile).distanceScale
  return {
    position: new THREE.Vector3(Math.cos(angle) * radius, aimHeight + radius * orbitSlope, Math.sin(angle) * radius),
    target: new THREE.Vector3(0, aimHeight, 0),
  }
}

// Seeking follows an arc; a straight blend between opposite-side views can
// cut through the hull. This also handles returning from free exploration.
export function interpolateOdinCamera(from: OdinCameraPose, to: OdinCameraPose, progress: number): OdinCameraPose {
  const u = THREE.MathUtils.clamp(progress, 0, 1)
  const start = new THREE.Spherical().setFromVector3(from.position.clone().sub(from.target))
  const end = new THREE.Spherical().setFromVector3(to.position.clone().sub(to.target))
  const turn = THREE.MathUtils.euclideanModulo(end.theta - start.theta + Math.PI, Math.PI * 2) - Math.PI
  const target = from.target.clone().lerp(to.target, u)
  const offset = new THREE.Vector3().setFromSpherical(new THREE.Spherical(
    THREE.MathUtils.lerp(start.radius, end.radius, u),
    THREE.MathUtils.lerp(start.phi, end.phi, u),
    start.theta + turn * u,
  ))
  return { position: target.clone().add(offset), target }
}
