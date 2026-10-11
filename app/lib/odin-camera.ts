import * as THREE from 'three'

// A steady orbit avoids combining rotation with repeated zooms, climbs and
// moving targets. Its clock remains independent of the weapon film.
export const ODIN_CAMERA_ORBIT_SECONDS = 45
const startAngle = -5 * Math.PI / 6
const orbitRadius = 11.2
const orbitSlope = .24
const aimHeight = .20
export type OdinCameraPose = { position: THREE.Vector3; target: THREE.Vector3 }

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
