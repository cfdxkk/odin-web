import { createTourTransition, sampleTourTransition } from './odin-tour.ts'
import type { TourTransition } from './odin-tour.ts'

export type SeekOptions = { immediate?: boolean }

// A timeline click chooses its destination immediately, but the visible rig
// travels there. Keep the exhaust interlock and start from the rendered pose,
// including when a second click interrupts an unfinished seek.
export function createSeekTransition(from: { deployment: number; thrust: number }, targetTime: number): TourTransition {
  const transition = createTourTransition(from, targetTime)
  const duration = Math.max(.8, Math.min(3.2, transition.duration))
  const scale = transition.duration > 0 ? duration / transition.duration : 1
  return {
    ...transition,
    fadeSeconds: transition.fadeSeconds * scale,
    moveSeconds: transition.moveSeconds * scale,
    igniteSeconds: transition.igniteSeconds * scale,
    duration,
  }
}

export function sampleSeekTransition(transition: TourTransition, elapsed: number) {
  return { ...sampleTourTransition(transition, elapsed), time: transition.targetTime }
}
