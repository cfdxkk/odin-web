import * as THREE from 'three'
// One evenly paced orbit. Inspection framing still varies in radius, height
// and aim, with periodic tangents keeping the 60-second wrap smooth.
const shots = [
  [0, 11.6, 3.7, .24, 0],
  [7, 10.7, 2.9, .28, -.20],
  [12, 8.9, 4.4, .38, -.70],
  [18, 7.7, 3.7, .45, -.50],
  [24, 7.0, 2.8, .76, .40],
  [30, 8.6, 2.1, .56, .45],
  [36, 10.1, 3.5, .32, .20],
  [43, 11.0, 2.5, .20, 0],
  [50, 11.6, 4.2, .25, -.20],
  [56, 12.0, 4.5, .24, 0],
  [60, 11.6, 3.7, .24, 0],
] as const
const intervals = shots.slice(1).map((shot, i) => shot[0] - shots[i]![0])
const framingTangents = Array.from({ length: 4 }, (_, axis) => {
  const speeds = shots.slice(1).map((shot, i) => (shot[axis + 1]! - shots[i]![axis + 1]!) / intervals[i]!)
  return shots.map((_, i) => {
    const previous = (i - 1 + speeds.length) % speeds.length, next = i % speeds.length
    const before = speeds[previous]!, after = speeds[next]!
    if (before * after <= 0) return 0
    const w1 = 2 * intervals[next]! + intervals[previous]!, w2 = intervals[next]! + 2 * intervals[previous]!
    return (w1 + w2) / (w1 / before + w2 / after)
  })
})
const orbitSpeed = Math.PI * 2 / 60
// Pass the stern during NAV ignition instead of spending the opening eighteen
// seconds on one quarter and rushing through the remainder of the orbit.
const startAngle = Math.PI / 2 - 40 * orbitSpeed
export function sampleOdinCamera(time: number, aspect = 1.6, mobile = false) {
  const t = THREE.MathUtils.clamp(time, 0, 60)
  let index = shots.findIndex(s => s[0] > t) - 1
  if (index < 0) index = t >= 60 ? shots.length - 2 : 0
  const u = (t - shots[index]![0]) / (shots[index + 1]![0] - shots[index]![0])
  const start = shots[index]!, end = shots[index + 1]!, span = intervals[index]!
  const u2 = u * u, u3 = u2 * u
  const angle = startAngle + t * orbitSpeed
  const [radius, height, aimY, aimZ] = framingTangents.map((tangents, axis) =>
    (2 * u3 - 3 * u2 + 1) * start[axis + 1]! + (u3 - 2 * u2 + u) * span * tangents[index]!
    + (-2 * u3 + 3 * u2) * end[axis + 1]! + (u3 - u2) * span * tangents[index + 1]!)
  const distance = radius! * (mobile ? 1.60 : Math.max(1, 1.25 / aspect))
  return {
    position: new THREE.Vector3(Math.cos(angle) * distance, height!, Math.sin(angle) * distance),
    target: new THREE.Vector3(0, aimY!, aimZ!),
  }
}
