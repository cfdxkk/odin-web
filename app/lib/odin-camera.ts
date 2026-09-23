import * as THREE from 'three'
// A continuous inspection flight: establish the silhouette, move toward the
// forward battery, pass the conning tower, then widen across the stern.
// There is no engine-only shot; exhaust remains visible in the aft wide shot.
const shots = [
  [0, -.79, 11.6, 3.7, .24, 0],
  [7, -1.08, 10.7, 2.9, .28, -.20],
  [12, -.95, 8.9, 4.4, .38, -.70],
  [18, -.62, 7.7, 3.7, .45, -.50],
  [24, -.08, 7.0, 2.8, .76, .40],
  [30, .45, 8.6, 2.1, .56, .45],
  [36, 1.02, 10.1, 3.5, .32, .20],
  [43, 1.84, 11.0, 2.5, .20, 0],
  [50, 3.03, 11.6, 4.2, .25, -.20],
  [56, 4.38, 12.0, 4.5, .24, 0],
  [60, 5.493185307179586, 11.6, 3.7, .24, 0],
] as const
const curves = Array.from({ length: 5 }, (_, axis) => new THREE.SplineCurve(shots.map(s => new THREE.Vector2(s[0], s[axis + 1]!))))
export function sampleOdinCamera(time: number, aspect = 1.6, mobile = false) {
  const t = THREE.MathUtils.clamp(time, 0, 60)
  let index = shots.findIndex(s => s[0] > t) - 1
  if (index < 0) index = t >= 60 ? shots.length - 2 : 0
  const u = (t - shots[index]![0]) / (shots[index + 1]![0] - shots[index]![0])
  const fraction = (index + u) / (shots.length - 1)
  const [angle, radius, height, aimY, aimZ] = curves.map(c => c.getPoint(fraction).y)
  const distance = radius! * (mobile ? 1.60 : Math.max(1, 1.25 / aspect))
  return {
    position: new THREE.Vector3(Math.cos(angle!) * distance, height!, Math.sin(angle!) * distance),
    target: new THREE.Vector3(0, aimY!, aimZ!),
  }
}
