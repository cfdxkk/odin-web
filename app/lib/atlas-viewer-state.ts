export const ATLAS_MODES = ['overview', 'main', 'secondary', 'defense', 'bridge', 'engines'] as const
export type AtlasMode = typeof ATLAS_MODES[number]

export type AtlasViewerState = {
  playing: boolean
  mode: AtlasMode
  deployment: number
  active: boolean
  reducedMotion: boolean
  technical: boolean
  scrubbing?: boolean
}

export function atlasDeployment(value: number) {
  return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0))
}

// Playback is owned by the page. Neither chapter changes nor visibility can
// alter this preference, and dragging only temporarily suspends the orbit.
export function atlasMotionActive(state: AtlasViewerState, visible: boolean, dragging = false) {
  return state.playing && state.active && visible && !state.reducedMotion && !state.scrubbing && !dragging
}

export type AtlasDeploymentTransition = { from: number; to: number; elapsed: number; duration: number }

export function createAtlasDeploymentTransition(from: number, target: number): AtlasDeploymentTransition | undefined {
  const start = atlasDeployment(from), to = atlasDeployment(target)
  return start === to ? undefined : { from: start, to, elapsed: 0, duration: Math.abs(to - start) * DEPLOY_SECONDS }
}

export function advanceAtlasDeployment(transition: AtlasDeploymentTransition | undefined, target: number, dt: number, scrubbing = false, reducedMotion = false) {
  const requested = atlasDeployment(target)
  if (!transition || transition.to !== requested || scrubbing || reducedMotion) return { deployment: requested, transition: undefined }
  const elapsed = transition.elapsed + Math.max(0, Number.isFinite(dt) ? dt : 0)
  const fraction = Math.min(1, elapsed / transition.duration)
  if (fraction === 1) return { deployment: requested, transition: undefined }
  const eased = fraction * fraction * (3 - 2 * fraction)
  return { deployment: transition.from + (transition.to - transition.from) * eased, transition: { ...transition, elapsed } }
}

export function atlasEngineTarget(deployment: number, mode: AtlasMode) {
  // Never infer closure from a rounded percentage or an almost-zero value.
  return deployment === 0 ? mode === 'engines' ? .85 : .16 : 0
}

export const ATLAS_VIEWS: Record<AtlasMode, {
  target: readonly [number, number, number]
  direction: readonly [number, number, number]
  distance: number
}> = {
  overview: { target: [0, .24, -.15], direction: [1.35, .8, 1], distance: 9.5 },
  main: { target: [0, .16, -.72], direction: [-1.25, .85, -.6], distance: 5.6 },
  secondary: { target: [-.45, .22, .12], direction: [-1.4, .58, -.7], distance: 5.5 },
  defense: { target: [-.45, .05, .8], direction: [-1.2, -.48, .9], distance: 5.1 },
  bridge: { target: [0, .76, .85], direction: [-1.05, .58, 1.2], distance: 5.6 },
  engines: { target: [0, .1, 2.05], direction: [-.7, .38, 1.4], distance: 6.1 },
}
import { DEPLOY_SECONDS } from './odin-motion.ts'

