import * as THREE from 'three'
import { WEAPON_GROUPS, type WeaponGroup } from './odin-weapon-groups.ts'

export const WEAPON_SOURCE = 'https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin'
// Source coordinates: +Y points toward the bow, +Z is above the hull.
// The entry side follows the visible homepage pose. A continuous flank-to-dorsal
// arc overlaps a later climb around the stern, without crossing the far flank.
export const WEAPON_TOUR = [
  // Frame the emitter bank and its aft radiator together; the leader still
  // identifies the emitters rather than following the framing center.
  { id: 'beam', group: null, point: [0, 300, 6.8], calloutPoint: [0, 369.5, 6.8], distance: 4.5, anchor: null, video: 'bow-laser',
    zh: { title: '舰艏光束武器', body: '舰艏的 12 个发射器构成一套 S12 光束武器，由驾驶员控制。', spec: '1 × S12 / 驾驶员控制' },
    en: { title: 'Bow beam weapon', body: 'Twelve bow emitters form one pilot-controlled S12 beam weapon.', spec: '1 × S12 / Pilot controlled' } },
  { id: 'main', group: 'main', point: [0, 70, 0], distance: 5.3, anchor: 'Main_Dorsal_Shroud_Center', anchors: ['Main_Dorsal_Shroud_Center', 'Main_Ventral_Shroud_Center'], video: 'main-battery',
    zh: { title: '三联装主炮', body: '舰体上层与舰腹各布置一座有人炮塔，每座搭载三门 S12 主炮。', spec: '2 座炮塔 / 每座 3 × S12' },
    en: { title: 'Triple main batteries', body: 'One crewed turret sits above the hull and another below it. Each carries three S12 guns.', spec: '2 turrets / 3 × S12 each' } },
  { id: 'torpedoes', group: null, point: [0, 30, 43], distance: 6.0, anchor: null, video: null,
    zh: { title: '垂直发射鱼雷', body: '主炮后方布置 S12 垂直发射系统。', spec: '20 套 S12 垂直发射系统' },
    en: { title: 'Vertical-launch torpedoes', body: 'S12 vertical-launch systems sit behind the main battery.', spec: '20 × S12 vertical-launch systems' } },
  { id: 'single', group: 'single', point: [0, 8, 29], distance: 6.3, anchor: 'SideBattery_2_Starboard', video: null,
    zh: { title: '单联装副炮', body: 'S10 单联炮塔分为有人与遥控两种配置，分布在舰体不同位置。', spec: '3 座有人 + 8 座遥控 / S10' },
    en: { title: 'Single-gun batteries', body: 'S10 single-gun turrets are distributed around the hull in crewed and remote configurations.', spec: '3 crewed + 8 remote / S10' } },
  { id: 'bridge-batteries', group: 'defense', groups: ['defense', 'quad'], point: [0, -55, 73], distance: 6.6,
    anchor: 'Defense_03_Elevation', anchors: ['Defense_03_Elevation', 'PDC_Starboard_Gimbal'], video: 'quad-turret',
    zh: { title: '双联与四联炮塔', body: '八座有人双联炮塔各配备两门 S8 武器。舰桥两侧另设两座有人四联炮塔，每座配备四门 S8 武器。', spec: '8 × 双联 S8 / 2 × 四联 S8' },
    en: { title: 'Twin and quad turrets', body: 'Eight crewed twin turrets carry two S8 guns each. Two crewed quad turrets flank the bridge, with four S8 guns per mount.', spec: '8 × twin S8 / 2 × quad S8' } },
] as const satisfies readonly { id: string; group: WeaponGroup | null; groups?: readonly WeaponGroup[]; point: readonly [number, number, number]; calloutPoint?: readonly [number, number, number]; distance: number; anchor: string | null; anchors?: readonly string[]; video: string | null; zh: { title: string; body: string; spec: string }; en: { title: string; body: string; spec: string } }[]

export const WEAPON_DEPLOY_SECONDS = 4.8
export type WeaponLevels = Record<WeaponGroup, number>
export function uniformWeaponLevels(value: number): WeaponLevels {
  return { main: value, single: value, defense: value, quad: value }
}
export function focusedWeaponLevels(step: number): WeaponLevels {
  const levels = uniformWeaponLevels(0), shot = WEAPON_TOUR[clampWeaponStep(step)]!
  const groups = 'groups' in shot ? shot.groups : shot.group ? [shot.group] : []
  for (const group of groups) levels[group] = 1
  return levels
}
export function interpolateWeaponLevels(from: WeaponLevels, to: WeaponLevels, progress: number): WeaponLevels {
  const u = THREE.MathUtils.smoothstep(progress, 0, 1), levels = uniformWeaponLevels(0)
  for (const group of WEAPON_GROUPS) levels[group] = THREE.MathUtils.lerp(from[group], to[group], u)
  return levels
}
export const clampWeaponStep = (step: number) => Math.max(0, Math.min(WEAPON_TOUR.length - 1, Math.round(Number.isFinite(step) ? step : 0)))
export const clampWeaponProgress = (progress: number) => THREE.MathUtils.clamp(Number.isFinite(progress) ? progress : 0, 0, 1)
export const weaponStepProgress = (step: number) => clampWeaponStep(step) / (WEAPON_TOUR.length - 1)

// Shared nonzero velocities carry the camera through chapter stations. Zero
// endpoint accelerations make this quintic track C2 without stopping at knots.
function sampleTrack(values: readonly number[], progress: number) {
  const t = clampWeaponProgress(progress) * (values.length - 1)
  const index = Math.min(values.length - 2, Math.floor(t)), u = t - index
  const slope = (i: number) => {
    if (i === 0) return values[1]! - values[0]!
    if (i === values.length - 1) return values[i]! - values[i - 1]!
    const a = values[i]! - values[i - 1]!, b = values[i + 1]! - values[i]!
    return a * b <= 0 ? 0 : 2 * a * b / (a + b)
  }
  const start = values[index]!, delta = values[index + 1]! - start
  const from = slope(index), to = slope(index + 1)
  return start + from*u + (10*delta - 6*from - 4*to)*u**3
    + (-15*delta + 8*from + 7*to)*u**4 + (6*delta - 3*from - 3*to)*u**5
}
// A single longitudinal axis is used from the very first frame. Moving its
// cross-section height between weapons makes the ship drift sideways as the
// lens rotates, even when the source X coordinates all happen to be zero.
export const WEAPON_ORBIT_AXIS = { x: 0, y: .068 } as const
const trackZ = WEAPON_TOUR.map(shot => -shot.point[1] * .01)
const trackDistance = WEAPON_TOUR.map(shot => shot.distance)

export type WeaponRouteSide = -1 | 1
export function chooseWeaponRouteSide(position: THREE.Vector3, target: THREE.Vector3, previous: WeaponRouteSide = -1): WeaponRouteSide {
  const offset = position.clone().sub(target)
  // Close to a head-on view, retain the previous route rather than choosing
  // an arbitrary side from subpixel noise. Otherwise use the rendered pose.
  return Math.abs(offset.x) < offset.length() * .015 ? previous : offset.x < 0 ? -1 : 1
}

export const WEAPON_DORSAL_ARRIVAL = .68
export const WEAPON_AFT_ARC_START = .42
const flightSamples = 256
function smootherSlope(p: number, start: number, end: number) {
  const u = THREE.MathUtils.clamp((p - start) / (end - start), 0, 1)
  return 30 * u*u * (1-u)**2 / (end - start)
}
function flightDirection(p: number) {
  const turn = Math.PI / 2 * THREE.MathUtils.smootherstep(p, WEAPON_AFT_ARC_START, WEAPON_DORSAL_ARRIVAL)
  return { cos: Math.cos(turn), sin: Math.sin(turn), turnSpeed: Math.PI / 2 * smootherSlope(p, WEAPON_AFT_ARC_START, WEAPON_DORSAL_ARRIVAL),
    taper: 1 - THREE.MathUtils.smootherstep(p, .85, 1), taperSpeed: -smootherSlope(p, .85, 1) }
}
// Integrate one gradually slowing angular velocity, steering its direction
// from sideways to aft. Two independent easing curves create a speed trough
// followed by a second acceleration; this shared field avoids that pulse.
const flightIntegrals = [0, 0, 0, 0]
for (let i = 0; i < flightSamples; i++) for (const [fraction, weight] of [[0, 1], [.5, 4], [1, 1]]) {
  const p = (i + fraction!) / flightSamples, d = flightDirection(p)
  const value = [d.taper*d.cos, p*d.taper*d.cos, d.taper*d.sin, p*d.taper*d.sin]
  value.forEach((v, index) => { flightIntegrals[index]! += v * weight! / (6 * flightSamples) })
}
const [ia, ib, ic, id] = flightIntegrals as [number, number, number, number]
const lateralTravel = Math.PI / 2 - .12, aftTravel = .94 - .12, determinant = ia*id - ib*ic
const flightInitialSpeed = (lateralTravel*id - ib*aftTravel) / determinant
const flightDeceleration = (ic*lateralTravel - ia*aftTravel) / determinant
function flightRates(p: number) {
  const d = flightDirection(p), base = flightInitialSpeed - flightDeceleration*p
  const speed = base*d.taper, acceleration = -flightDeceleration*d.taper + base*d.taperSpeed
  return { lateralSpeed: speed*d.cos, aftSpeed: speed*d.sin,
    lateralAcceleration: acceleration*d.cos - speed*d.sin*d.turnSpeed,
    aftAcceleration: acceleration*d.sin + speed*d.cos*d.turnSpeed }
}
const flightAngles = [{ lateral: .12, aft: .12, ...flightRates(0) }]
for (let i = 1; i <= flightSamples; i++) {
  const start = flightAngles[i-1]!, middle = flightRates((i-.5)/flightSamples), end = flightRates(i/flightSamples)
  flightAngles.push({
    lateral: start.lateral + (start.lateralSpeed + 4*middle.lateralSpeed + end.lateralSpeed) / (6*flightSamples),
    aft: start.aft + (start.aftSpeed + 4*middle.aftSpeed + end.aftSpeed) / (6*flightSamples), ...end,
  })
}
function sampleFlightAngle(start: number, end: number, speed0: number, speed1: number, acceleration0: number, acceleration1: number, u: number) {
  const v0 = speed0/flightSamples, v1 = speed1/flightSamples, a0 = acceleration0/flightSamples**2, a1 = acceleration1/flightSamples**2
  const delta = end - start - v0 - a0/2, velocity = v1 - v0 - a0, acceleration = a1 - a0
  return start + v0*u + a0/2*u*u + (10*delta - 4*velocity + acceleration/2)*u**3
    + (-15*delta + 7*velocity - acceleration)*u**4 + (6*delta - 3*velocity + acceleration/2)*u**5
}
export function weaponRouteAngles(progress: number) {
  const p = clampWeaponProgress(progress), t = p*flightSamples, i = Math.min(flightSamples-1, Math.floor(t)), u = t-i
  const start = flightAngles[i]!, end = flightAngles[i+1]!
  return {
    lateral: p >= WEAPON_DORSAL_ARRIVAL ? Math.PI / 2 : sampleFlightAngle(start.lateral, end.lateral, start.lateralSpeed, end.lateralSpeed, start.lateralAcceleration, end.lateralAcceleration, u),
    aft: p === 1 ? .94 : sampleFlightAngle(start.aft, end.aft, start.aftSpeed, end.aftSpeed, start.aftAcceleration, end.aftAcceleration, u),
  }
}

// The aft tour must use the same lens framing as its weapon entry; changing
// the ultrawide compensation at the chapter boundary would create a zoom-in.
export const inspectionCameraFraming = (aspect: number) => Math.max(.8, Math.pow(1.6 / Math.max(1.6, aspect), .35)) * Math.max(1, 1 / aspect)

export function sampleContinuousWeaponCamera(progress: number, aspect: number, side: WeaponRouteSide = -1) {
  const p = clampWeaponProgress(progress)
  const target = new THREE.Vector3(WEAPON_ORBIT_AXIS.x, WEAPON_ORBIT_AXIS.y, sampleTrack(trackZ, p))
  const framing = inspectionCameraFraming(aspect)
  const angle = weaponRouteAngles(p)
  const position = new THREE.Vector3(side * Math.cos(angle.lateral) * Math.cos(angle.aft), Math.sin(angle.lateral) * Math.cos(angle.aft), Math.sin(angle.aft))
    .multiplyScalar(sampleTrack(trackDistance, p) * framing).add(target)
  return { position, target, up: new THREE.Vector3(0, 0, -1) }
}

export function sampleWeaponCamera(step: number, aspect: number, side: WeaponRouteSide = -1) {
  return sampleContinuousWeaponCamera(weaponStepProgress(step), aspect, side)
}

export function advanceWeaponCameraProgress(current: number, destination: number, dt: number) {
  const target = clampWeaponProgress(destination)
  const next = THREE.MathUtils.lerp(clampWeaponProgress(current), target, 1 - Math.exp(-Math.max(0, dt) / .14))
  return Math.abs(next - target) < .00001 ? target : next
}
