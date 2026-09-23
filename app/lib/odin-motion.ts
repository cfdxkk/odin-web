export const FILM_DURATION = 40
export const MODES = [
  { name: '外观', english: 'EXTERIOR', time: 0, caption: '于静默中，显露锋芒。' },
  { name: 'SCM', english: 'COMBAT CONFIGURATION', time: 12, caption: '装甲就位。全舰武备展开。' },
  { name: 'NAV', english: 'NAVIGATION CONFIGURATION', time: 26, caption: '收拢武备，驶向深空。' },
] as const
export function ease(a: number, b: number, value: number) {
  const u = Math.max(0, Math.min(1, (value - a) / (b - a)))
  return u * u * (3 - 2 * u)
}
export function sampleOdinMotion(time: number) {
  const t = Math.max(0, Math.min(FILM_DURATION, time))
  const deployment = ease(12, 19, t) * (1 - ease(26, 33, t))
  // Thrust is interlocked with the mechanical stow sequence, including armor.
  const thrust = deployment === 0 ? ease(33.4, 37.6, t) * (1 - ease(39, 40, t)) : 0
  return { deployment, thrust, mode: t < 12 ? 'exterior' : t < 26 ? 'scm' : 'nav' }
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
