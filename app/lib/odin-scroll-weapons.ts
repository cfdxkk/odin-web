import { clampWeaponProgress, interpolateWeaponLevels, type WeaponLevels } from './odin-weapon-tour.ts'

// These are positions on the same continuous track that drives the camera.
// Each completed ramp remains at one; scrolling backward retraces the ramp.
export const SCROLL_WEAPON_RANGES = {
  main: [.10, .30],
  single: [.60, .80],
  defense: [.84, 1],
  quad: [.84, 1],
} as const

// The rig's aiming motions also depend on time. A fixed clock prevents a
// stopped scroll position from continuing to turn the defense mounts.
export const SCROLL_WEAPON_AIM_TIME = 24
export type ScrollWeaponPose = { levels: WeaponLevels; animationTime: number }

export function sampleScrollWeaponLevels(progress: number): WeaponLevels {
  const p = clampWeaponProgress(progress)
  const ramp = ([start, end]: readonly [number, number]) => {
    const u = clampWeaponProgress((p - start) / (end - start))
    return u * u * (3 - 2 * u)
  }
  return {
    main: ramp(SCROLL_WEAPON_RANGES.main),
    single: ramp(SCROLL_WEAPON_RANGES.single),
    defense: ramp(SCROLL_WEAPON_RANGES.defense),
    quad: ramp(SCROLL_WEAPON_RANGES.quad),
  }
}

// Only chapter entry uses a finite handoff from the actually visible pose.
// Its destination remains live, so scrolling during entry never queues an old
// weapon pose behind the new camera position.
export function sampleScrollWeaponPose(progress: number, from?: ScrollWeaponPose, handoffProgress = 1): ScrollWeaponPose {
  const levels = sampleScrollWeaponLevels(progress)
  if (!from) return { levels, animationTime: SCROLL_WEAPON_AIM_TIME }
  const u = clampWeaponProgress(handoffProgress), eased = u * u * (3 - 2 * u)
  return {
    levels: interpolateWeaponLevels(from.levels, levels, u),
    animationTime: from.animationTime + (SCROLL_WEAPON_AIM_TIME - from.animationTime) * eased,
  }
}
