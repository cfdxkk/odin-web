type AnchorShot = { id: string; anchor: string | null; anchors?: readonly string[] }
type HullSide = -1 | 1

// Port is negative world X. Retain the last visible flank at the centered
// dorsal view: floating-point noise must not send a leader across the hull.
export function facingWeaponSide(cameraX: number, previous: HullSide): HullSide {
  return Math.abs(cameraX) < .01 ? previous : cameraX < 0 ? -1 : 1
}

export function weaponAnchorNames(shot: AnchorShot, side: HullSide): readonly string[] {
  if (shot.id === 'single') return [side < 0 ? 'SideBattery_2_Port' : 'SideBattery_2_Starboard']
  if (shot.id === 'bridge-batteries') return side < 0
    ? ['Defense_01_Elevation', 'PDC_Port_Gimbal']
    : ['Defense_03_Elevation', 'PDC_Starboard_Gimbal']
  return shot.anchors ?? (shot.anchor ? [shot.anchor] : [])
}
