import * as THREE from 'three'
import { WEAPON_GROUPS, type WeaponGroup } from './odin-weapon-groups.ts'

export const WEAPON_SOURCE = 'https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin'
// Source coordinates: +Y points toward the bow, +Z is above the hull.
// The inspection follows the hull from bow to aft while crossing over the
// dorsal surface, from port to starboard. Bow remains at the top of the view.
export const WEAPON_TOUR = [
  { id: 'beam', group: null, point: [0, 369.5, 6.8], distance: 4.1, anchor: null, video: 'bow-laser',
    zh: { title: '舰艏光束武器', body: '舰艏的 12 个发射器构成一套 S12 光束武器，由驾驶员控制。', spec: '1 × S12 / 驾驶员控制' },
    en: { title: 'Bow beam weapon', body: 'Twelve bow emitters form one pilot-controlled S12 beam weapon.', spec: '1 × S12 / Pilot controlled' } },
  { id: 'main', group: 'main', point: [0, 100, 0], distance: 5.9, anchor: 'Main_Dorsal_Shroud_Center', anchors: ['Main_Dorsal_Shroud_Center', 'Main_Ventral_Shroud_Center'], video: 'main-battery',
    zh: { title: '三联装主炮', body: '舰体上层与舰腹各布置一座有人炮塔，每座搭载三门 S12 主炮。', spec: '2 座炮塔 / 每座 3 × S12' },
    en: { title: 'Triple main batteries', body: 'One crewed turret sits above the hull and another below it. Each carries three S12 guns.', spec: '2 turrets / 3 × S12 each' } },
  { id: 'torpedoes', group: null, point: [12, 30, 43], distance: 4.5, anchor: null, video: null,
    zh: { title: '垂直发射鱼雷', body: '主炮后方布置 S12 垂直发射系统。', spec: '20 套 S12 垂直发射系统' },
    en: { title: 'Vertical-launch torpedoes', body: 'S12 vertical-launch systems sit behind the main battery.', spec: '20 × S12 vertical-launch systems' } },
  { id: 'single', group: 'single', point: [45, 16, 10], distance: 7, anchor: 'SideBattery_2_Starboard', video: null,
    zh: { title: '单联装副炮', body: 'S10 单联炮塔分为有人与遥控两种配置，分布在舰体不同位置。', spec: '3 座有人 + 8 座遥控 / S10' },
    en: { title: 'Single-gun batteries', body: 'S10 single-gun turrets are distributed around the hull in crewed and remote configurations.', spec: '3 crewed + 8 remote / S10' } },
  { id: 'twin', group: 'defense', point: [22, -36, 53], distance: 3.6, anchor: 'Defense_03_Elevation', video: null,
    zh: { title: '双联装炮塔', body: '八座有人双联炮塔，每座配备两门 S8 武器。', spec: '8 座炮塔 / 每座 2 × S8' },
    en: { title: 'Twin-gun turrets', body: 'Eight crewed twin turrets each carry two S8 weapons.', spec: '8 turrets / 2 × S8 each' } },
  { id: 'quad', group: 'quad', point: [43, -58, 106], distance: 3.1, anchor: 'PDC_Starboard_Gimbal', video: 'quad-turret',
    zh: { title: '四联装炮塔', body: '舰桥两侧各有一座有人四联炮塔，每座配置四门 S8 武器。', spec: '2 座炮塔 / 每座 4 × S8' },
    en: { title: 'Quad-gun turrets', body: 'A crewed quad turret flanks each side of the bridge, with four S8 weapons per mount.', spec: '2 turrets / 4 × S8 each' } },
] as const satisfies readonly { id: string; group: WeaponGroup | null; point: readonly [number, number, number]; distance: number; anchor: string | null; anchors?: readonly string[]; video: string | null; zh: { title: string; body: string; spec: string }; en: { title: string; body: string; spec: string } }[]

export const WEAPON_DEPLOY_SECONDS = 4.8
export type WeaponLevels = Record<WeaponGroup, number>
export function uniformWeaponLevels(value: number): WeaponLevels {
  return { main: value, single: value, defense: value, quad: value }
}
export function focusedWeaponLevels(step: number): WeaponLevels {
  const levels = uniformWeaponLevels(0), group = WEAPON_TOUR[clampWeaponStep(step)]!.group
  if (group) levels[group] = 1
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

// Monotone cubic interpolation prevents the camera focus from overshooting a
// station and briefly reversing along the hull between closely spaced guns.
function sampleTrack(values: readonly number[], progress: number) {
  const t = clampWeaponProgress(progress) * (values.length - 1)
  const index = Math.min(values.length - 2, Math.floor(t)), u = t - index
  const slope = (i: number) => {
    if (i === 0) return values[1]! - values[0]!
    if (i === values.length - 1) return values[i]! - values[i - 1]!
    const a = values[i]! - values[i - 1]!, b = values[i + 1]! - values[i]!
    return a * b <= 0 ? 0 : 2 * a * b / (a + b)
  }
  return (2*u*u*u - 3*u*u + 1)*values[index]! + (u*u*u - 2*u*u + u)*slope(index)
    + (-2*u*u*u + 3*u*u)*values[index + 1]! + (u*u*u - u*u)*slope(index + 1)
}
const trackX = WEAPON_TOUR.map(shot => shot.point[0] * .01)
const trackY = WEAPON_TOUR.map(shot => shot.point[2] * .01)
const trackZ = WEAPON_TOUR.map(shot => -shot.point[1] * .01)
const trackDistance = WEAPON_TOUR.map(shot => shot.distance)

export function sampleContinuousWeaponCamera(progress: number, aspect: number) {
  const p = clampWeaponProgress(progress)
  const target = new THREE.Vector3(sampleTrack(trackX, p), sampleTrack(trackY, p), sampleTrack(trackZ, p))
  const framing = Math.max(.8, Math.pow(1.6 / Math.max(1.6, aspect), .35)) * Math.max(1, 1 / aspect)
  const angle = THREE.MathUtils.lerp(.12, Math.PI - .12, p)
  // A small longitudinal offset gives depth while never passing below the
  // hull. Unlike a world-up orbit this stays stable directly over the spine.
  const position = new THREE.Vector3(-Math.cos(angle), Math.sin(angle), .16).normalize()
    .multiplyScalar(sampleTrack(trackDistance, p) * framing).add(target)
  return { position, target, up: new THREE.Vector3(0, 0, -1) }
}

export function sampleWeaponCamera(step: number, aspect: number) {
  return sampleContinuousWeaponCamera(weaponStepProgress(step), aspect)
}

export function advanceWeaponCameraProgress(current: number, destination: number, dt: number) {
  const target = clampWeaponProgress(destination)
  const next = THREE.MathUtils.lerp(clampWeaponProgress(current), target, 1 - Math.exp(-Math.max(0, dt) / .14))
  return Math.abs(next - target) < .00001 ? target : next
}
