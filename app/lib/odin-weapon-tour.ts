import * as THREE from 'three'
import { WEAPON_GROUPS, type WeaponGroup } from './odin-weapon-groups.ts'

export const WEAPON_SOURCE = 'https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin'
// Source coordinates: +Y points toward the bow, +Z is above the hull.
// A fixed oblique heading makes each step a translation along the ship.
export const WEAPON_TOUR = [
  { id: 'beam', group: null, point: [0, 369.5, 6.8], distance: 3.2, anchor: null, video: 'bow-laser',
    zh: { title: '舰艏光束武器', body: '舰艏的 12 个发射器构成一套 S12 光束武器，由驾驶员控制。', spec: '1 × S12 / 驾驶员控制' },
    en: { title: 'Bow beam weapon', body: 'Twelve bow emitters form one pilot-controlled S12 beam weapon.', spec: '1 × S12 / Pilot controlled' } },
  { id: 'main', group: 'main', point: [0, 102, 43], distance: 3.6, anchor: 'Main_Dorsal_Shroud_Center', video: 'main-battery',
    zh: { title: '三联装主炮', body: '舰体上层与舰腹各布置一座有人炮塔，每座搭载三门 S12 主炮。', spec: '2 座炮塔 / 每座 3 × S12' },
    en: { title: 'Triple main batteries', body: 'One crewed turret sits above the hull and another below it. Each carries three S12 guns.', spec: '2 turrets / 3 × S12 each' } },
  { id: 'single', group: 'single', point: [55, 16, 30], distance: 2.5, anchor: 'SideBattery_2_Starboard', video: null,
    zh: { title: '单联装副炮', body: 'S10 单联炮塔分为有人与遥控两种配置，分布在舰体不同位置。', spec: '3 座有人 + 8 座遥控 / S10' },
    en: { title: 'Single-gun batteries', body: 'S10 single-gun turrets are distributed around the hull in crewed and remote configurations.', spec: '3 crewed + 8 remote / S10' } },
  { id: 'twin', group: 'defense', point: [22, -36, 53], distance: 2.3, anchor: 'Defense_03_Elevation', video: 'pdc',
    zh: { title: '双联装炮塔', body: '八座有人双联炮塔，每座配备两门 S8 武器。', spec: '8 座炮塔 / 每座 2 × S8' },
    en: { title: 'Twin-gun turrets', body: 'Eight crewed twin turrets each carry two S8 weapons.', spec: '8 turrets / 2 × S8 each' } },
  { id: 'quad', group: 'quad', point: [43, -58, 106], distance: 2.2, anchor: 'PDC_Starboard_Gimbal', video: 'quad-turret',
    zh: { title: '四联装炮塔', body: '舰桥两侧各有一座有人四联炮塔，每座配置四门 S8 武器。', spec: '2 座炮塔 / 每座 4 × S8' },
    en: { title: 'Quad-gun turrets', body: 'A crewed quad turret flanks each side of the bridge, with four S8 weapons per mount.', spec: '2 turrets / 4 × S8 each' } },
] as const satisfies readonly { id: string; group: WeaponGroup | null; point: readonly [number, number, number]; distance: number; anchor: string | null; video: string | null; zh: { title: string; body: string; spec: string }; en: { title: string; body: string; spec: string } }[]

export const WEAPON_TRANSITION_SECONDS = 2.4
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
export function sampleWeaponCamera(step: number, aspect: number) {
  const shot = WEAPON_TOUR[clampWeaponStep(step)]!
  const [x, y, z] = shot.point
  const target = new THREE.Vector3(x * .01, z * .01, -y * .01)
  const framing = Math.max(.8, Math.pow(1.6 / Math.max(1.6, aspect), .35)) * Math.max(1, 1 / aspect)
  const position = new THREE.Vector3(1.45, 2.3, -1).normalize().multiplyScalar(shot.distance * framing).add(target)
  return { position, target, up: new THREE.Vector3(0, 0, -1) }
}
