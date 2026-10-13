export type WeaponGroup = 'main' | 'single' | 'defense' | 'quad'

export const WEAPON_GROUPS = ['main', 'single', 'defense', 'quad'] as const

// Include the complete mechanism: its covers, carriers, bores and shared
// rails must use one clock. The legacy PDC_ prefix names the bridge quads;
// Defense_ names the eight twin mounts, not those four-barrel assemblies.
export function classifyWeaponJoint(name: string): WeaponGroup | undefined {
  if (name.startsWith('Main_') || name.startsWith('Hatch_')) return 'main'
  if (name.startsWith('Axial_') || name.startsWith('SideBattery_')) return 'single'
  if (name.startsWith('Defense_') || name.startsWith('DefenseRail_')) return 'defense'
  if (name.startsWith('PDC_')) return 'quad'
  return undefined
}
