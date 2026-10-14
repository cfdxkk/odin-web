export type CalloutReadiness = {
  key: string | number
  animate?: boolean
  cameraRemaining?: number
  scrolling?: boolean
}

export type CalloutRevealState = {
  key: string | number | undefined
  drawTime: number
  reveal: number
  pending: boolean
}

export const CALLOUT_NEAR_END_SECONDS = .15
export const CALLOUT_DRAW_SECONDS = .8

export function createCalloutRevealState(): CalloutRevealState {
  return { key: undefined, drawTime: 0, reveal: 0, pending: false }
}

/** Only the weapon-tour entrance draws its leader. It starts with the camera's
 * arrival, without waiting for unrelated mechanical animations or a quiet hold.
 * Once started, scrolling follows the model instead of replaying the entrance.
 * Other chapters display the complete leader on their first visible frame.
 */
export function advanceCalloutReveal(
  previous: CalloutRevealState,
  input: CalloutReadiness & { visible: boolean; reducedMotion?: boolean },
  dt: number,
): CalloutRevealState {
  const remaining = input.cameraRemaining ?? 0
  const ready = !input.scrolling && Number.isFinite(remaining) && remaining <= CALLOUT_NEAR_END_SECONDS
  const elapsed = previous.key === input.key ? previous.drawTime : 0
  if (!input.visible) return { key: input.key, drawTime: elapsed, reveal: 0, pending: false }
  if (!input.animate || input.reducedMotion) return { key: input.key, drawTime: CALLOUT_DRAW_SECONDS, reveal: 1, pending: false }
  if (!ready && elapsed === 0) return { key: input.key, drawTime: 0, reveal: 0, pending: true }
  const delta = Number.isFinite(dt) ? Math.max(0, dt) : 0
  const drawTime = Math.min(CALLOUT_DRAW_SECONDS, elapsed + delta)
  const reveal = drawTime / CALLOUT_DRAW_SECONDS
  return { key: input.key, drawTime, reveal, pending: reveal < 1 }
}
