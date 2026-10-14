export type CalloutReadiness = {
  key: string | number
  cameraRemaining?: number
  mechanismRemaining?: number
  scrolling?: boolean
}

export type CalloutRevealState = {
  key: string | number | undefined
  quietTime: number
  reveal: number
  pending: boolean
}

export const CALLOUT_NEAR_END_SECONDS = .15
export const CALLOUT_QUIET_SECONDS = .12
export const CALLOUT_DRAW_SECONDS = .8

export function createCalloutRevealState(): CalloutRevealState {
  return { key: undefined, quietTime: 0, reveal: 0, pending: false }
}

/** A callout belongs to a settled shot, rather than to the moving camera.
 * Reset the whole stroke on interruption so neither an old branch nor a short
 * label-side stub survives a scroll, a reversal, or a weapon-group change.
 */
export function advanceCalloutReveal(
  previous: CalloutRevealState,
  input: CalloutReadiness & { visible: boolean; reducedMotion?: boolean },
  dt: number,
): CalloutRevealState {
  const remaining = Math.max(input.cameraRemaining ?? 0, input.mechanismRemaining ?? 0)
  const ready = !input.scrolling && Number.isFinite(remaining) && remaining <= CALLOUT_NEAR_END_SECONDS
  if (!input.visible || !ready) return { key: input.key, quietTime: 0, reveal: 0, pending: input.visible }
  if (input.reducedMotion) return { key: input.key, quietTime: CALLOUT_QUIET_SECONDS + CALLOUT_DRAW_SECONDS, reveal: 1, pending: false }
  // A new subject starts with a clean frame even after a long suspended frame.
  if (previous.key !== input.key) return { key: input.key, quietTime: 0, reveal: 0, pending: true }
  const delta = Number.isFinite(dt) ? Math.max(0, dt) : 0
  const quietTime = Math.min(CALLOUT_QUIET_SECONDS + CALLOUT_DRAW_SECONDS, previous.quietTime + delta)
  const reveal = Math.min(1, Math.max(0, (quietTime - CALLOUT_QUIET_SECONDS) / CALLOUT_DRAW_SECONDS))
  return { key: input.key, quietTime, reveal, pending: reveal < 1 }
}
