import profile from './turret-tempo-profile.json' with { type: 'json' }
import { DEPLOY_SECONDS } from './odin-motion.ts'

export type TurretFamily = 'quad' | 'aftTwin'

// These clocks retime the complete accepted pose path, including each gun's
// supports and covers. Keeping one clock per family preserves every clearance
// and relative movement instead of speeding individual joints independently.
// Linear stage clocks retain the existing easing once; their joins lie at
// stopped poses, so no extra easing or velocity jump is introduced.
export function turretPoseProgress(progress: number, family: TurretFamily) {
  const knots = profile[family].knots as [number, number][]
  const d = Math.max(0, Math.min(1, progress))
  for (let i = 1; i < knots.length; i++) {
    const [end, to] = knots[i]!
    const [start, from] = knots[i - 1]!
    if (d <= end) return from + (to - from) * (d - start) / (end - start)
  }
  return knots.at(-1)![1]!
}

export function reviewStrokeSeconds(station: number) {
  return station === 12 || station === 13 || (station >= 18 && station <= 21) ? DEPLOY_SECONDS : 3
}

// Preserve the direction and deployment when changing review stations; the
// one-second endpoint holds retain their elapsed time as well.
export function retimeReviewCycle(cycle: number, previous: number, next: number) {
  if (cycle < previous) return cycle / previous * next
  if (cycle < previous + 1) return next + cycle - previous
  if (cycle < 2 * previous + 1) return next + 1 + (cycle - previous - 1) / previous * next
  return 2 * next + 1 + cycle - 2 * previous - 1
}
