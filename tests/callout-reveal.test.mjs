import { test } from 'node:test'
import assert from 'node:assert/strict'
import { advanceCalloutReveal, createCalloutRevealState, CALLOUT_NEAR_END_SECONDS } from '../app/lib/odin-callout-reveal.ts'
import { calloutSegments } from '../app/lib/odin-callouts.ts'

const ready = { key: 'main', visible: true, cameraRemaining: 0, mechanismRemaining: 0, scrolling: false }
const origin = { x: 300, y: 200, visible: true }
const points = [{ x: 900, y: 150, visible: true }, { x: 850, y: 500, visible: true }]
function run(state, input, seconds, fps = 60) {
  for (let frame = 0; frame < seconds * fps; frame++) state = advanceCalloutReveal(state, input, 1 / fps)
  return state
}

test('callouts wait for both camera and mechanics, then draw even when film playback is paused', () => {
  let state = createCalloutRevealState()
  for (const blocked of [{ cameraRemaining: 1 }, { mechanismRemaining: 1 }, { scrolling: true }]) {
    state = run(state, { ...ready, ...blocked }, 2)
    assert.equal(state.reveal, 0)
    assert.ok(state.pending, 'A paused render loop must keep checking an unfinished handoff')
    assert.deepEqual(calloutSegments(origin, points, state.reveal), [], 'No label-side stub while camera or mechanism moves')
  }
  state = run(state, ready, .1)
  assert.equal(state.reveal, 0, 'Brief scroll lulls do not flash a line')
  state = run(state, ready, .1)
  assert.ok(state.reveal > 0 && state.reveal < .2)
  assert.equal(calloutSegments(origin, points, state.reveal).length, 1, 'Reveal begins at the left label')
  state = run(state, ready, 1)
  assert.equal(state.reveal, 1)
  assert.equal(state.pending, false, 'A completed paused shot may stop requesting GPU frames')
  assert.deepEqual(calloutSegments(origin, points, state.reveal).slice(2).map(line => [line.x2, line.y2]), [[900, 150], [850, 500]])
})

test('near-end threshold allows drawing at the end of the shot, never during its main movement', () => {
  let state = run(createCalloutRevealState(), { ...ready, cameraRemaining: CALLOUT_NEAR_END_SECONDS + .001 }, 1)
  assert.equal(state.reveal, 0)
  state = run(state, { ...ready, cameraRemaining: CALLOUT_NEAR_END_SECONDS, mechanismRemaining: CALLOUT_NEAR_END_SECONDS }, .2)
  assert.ok(state.reveal > 0)
  const obstructed = run(state, { ...ready, mechanismRemaining: Infinity }, 1)
  assert.equal(obstructed.reveal, 0, 'An unknown animation endpoint must not reveal prematurely')
})

test('scroll reversal clears every segment and restarts the reveal from the label', () => {
  let state = run(createCalloutRevealState(), ready, .65)
  assert.ok(calloutSegments(origin, points, state.reveal).length > 1)
  state = advanceCalloutReveal(state, { ...ready, scrolling: true }, 1 / 60)
  assert.equal(state.reveal, 0)
  assert.deepEqual(calloutSegments(origin, points, state.reveal), [])
  state = run(state, ready, .15)
  const restarted = calloutSegments(origin, points, state.reveal)
  assert.equal(restarted.length, 1)
  assert.equal(restarted[0].x1, origin.x)
  assert.ok(restarted[0].x2 < origin.x + 42)
})

test('a new weapon or a hidden origin cannot inherit a partial or completed line', () => {
  const complete = run(createCalloutRevealState(), ready, 2)
  const next = advanceCalloutReveal(complete, { ...ready, key: 'torpedoes' }, 5)
  assert.equal(next.reveal, 0, 'Even a delayed first frame belongs to the new shot')
  const hidden = advanceCalloutReveal(complete, { ...ready, visible: false }, .02)
  assert.equal(hidden.reveal, 0)
  assert.equal(hidden.pending, false)
  const reappeared = advanceCalloutReveal(hidden, ready, .02)
  assert.equal(reappeared.reveal, 0)
  assert.equal(reappeared.pending, true)
})

test('reduced motion still waits for readiness, while normal draw duration is frame-rate independent', () => {
  let reduced = advanceCalloutReveal(createCalloutRevealState(), { ...ready, reducedMotion: true, scrolling: true }, 1)
  assert.equal(reduced.reveal, 0)
  reduced = advanceCalloutReveal(reduced, { ...ready, reducedMotion: true }, .001)
  assert.equal(reduced.reveal, 1)
  const initial = advanceCalloutReveal(createCalloutRevealState(), ready, 0)
  const thirty = run(initial, ready, .6, 30)
  const sixty = run(initial, ready, .6, 60)
  assert.ok(Math.abs(thirty.reveal - sixty.reveal) < 1e-12)
  assert.deepEqual(advanceCalloutReveal(initial, ready, NaN), initial)
})
