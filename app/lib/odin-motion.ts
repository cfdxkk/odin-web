export const FILM_DURATION = 60
export const MODES = [
  { name: '飞船外观', english: 'EXTERIOR', time: 0, caption: '于静默中，显露锋芒。' },
  { name: 'SCM/战斗', english: 'COMBAT CONFIGURATION', time: 12, caption: '装甲就位。全舰武备展开。' },
  { name: 'NAV/航行', english: 'NAVIGATION CONFIGURATION', time: 32, caption: '收拢武备，驶向深空。' },
] as const
export function ease(a: number, b: number, value: number) {
  const u = Math.max(0, Math.min(1, (value - a) / (b - a)))
  return u * u * (3 - 2 * u)
}
export function sampleOdinMotion(time: number) {
  const t = Math.max(0, Math.min(FILM_DURATION, time))
  const deployment = ease(12, 24, t) * (1 - ease(32, 44, t))
  // Thrust is interlocked with the mechanical stow sequence, including armor.
  const thrust = deployment === 0 ? ease(44.5, 48, t) * (1 - ease(58, 60, t)) : 0
  return { deployment, thrust, mode: t < 12 ? 'exterior' : t < 32 ? 'scm' : 'nav' }
}
export type ManualMotion = { deployment: number; thrust: number }
// Reversible manual transitions have the same mechanical interlock as the film.
// Turning back to combat first extinguishes the engines; NAV lights after stow.
export function advanceManualMotion(state: ManualMotion, deployed: boolean, dt: number): ManualMotion {
  let { deployment, thrust } = state
  if (deployed) {
    thrust = Math.max(0, thrust - dt / 1.2)
    if (thrust === 0) deployment = Math.min(1, deployment + dt / 12)
  } else {
    deployment = Math.max(0, deployment - dt / 12)
    thrust = deployment === 0 ? Math.min(1, thrust + dt / 3.5) : 0
  }
  return { deployment, thrust }
}
export type PlaybackState = { userPaused: boolean; scrubbing: boolean }
export type PlaybackEvent = 'toggle' | 'scrub-start' | 'scrub-end' | 'mode-change' | 'visibility-change'
export function nextPlayback(state: PlaybackState, event: PlaybackEvent): PlaybackState {
  switch (event) {
    case 'toggle': return { ...state, userPaused: !state.userPaused }
    case 'scrub-start': return { ...state, scrubbing: true }
    case 'scrub-end': return { ...state, scrubbing: false }
    default: return state
  }
}
export function isPlaying(state: PlaybackState) { return !state.userPaused && !state.scrubbing }
