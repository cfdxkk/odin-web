import { createTourTransition, sampleTourTransition } from './odin-tour.ts'
import type { TourTransition } from './odin-tour.ts'
import { advanceManualMotion } from './odin-motion.ts'
import type { ManualMotion } from './odin-motion.ts'

// The guide clock stays where exploration started. Only the visible pose
// catches up; this also blends the aim clock when NAV/SCM already agrees.
export function createManualReturn(from: { deployment: number; thrust: number }, targetTime: number): TourTransition {
  const transition = createTourTransition(from, targetTime)
  return { ...transition, duration: Math.max(.65, transition.duration) }
}

export function sampleManualReturn(transition: TourTransition, elapsed: number) {
  return { ...sampleTourTransition(transition, elapsed), time: transition.targetTime }
}

// A guide handoff may contain both partial deployment and residual thrust.
// When the user interrupts it, preserve that visible flame and fade it out at
// the normal manual rate instead of snapping it to the interlock's zero state.
export function advanceManualResume(state: ManualMotion, deployed: boolean, dt: number, pendingDeployment = 0): ManualMotion {
  const next = advanceManualMotion(state, deployed, dt)
  if (!deployed && Math.max(next.deployment, pendingDeployment) > .00001) next.thrust = Math.max(0, state.thrust - dt / 1.2)
  return next
}

export function advanceFilmClock(time: number, dt: number, duration: number) {
  const next = time + dt
  return { time: next % duration, looped: next >= duration }
}
