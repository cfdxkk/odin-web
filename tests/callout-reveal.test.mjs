import { test } from 'node:test'
import assert from 'node:assert/strict'
import { advanceCalloutReveal, createCalloutRevealState, CALLOUT_NEAR_END_SECONDS } from '../app/lib/odin-callout-reveal.ts'
import { calloutSegments } from '../app/lib/odin-callouts.ts'

const ready = { key: 'beam', animate: true, visible: true, cameraRemaining: 0, scrolling: false }
const origin = { x: 300, y: 200, visible: true }
const points = [{ x: 900, y: 150, visible: true }, { x: 850, y: 500, visible: true }]
function run(state, input, seconds, fps = 60) {
  for (let frame = 0; frame < seconds * fps; frame++) state = advanceCalloutReveal(state, input, 1 / fps)
  return state
}

test('the entrance leader starts on the first near-settled camera frame without a quiet-time delay', () => {
  let state = createCalloutRevealState()
  for (const blocked of [{ cameraRemaining: 1 }, { scrolling: true }]) {
    state = run(state, { ...ready, ...blocked }, 2)
    assert.equal(state.reveal, 0)
    assert.ok(state.pending, 'A paused loop must keep checking the pending entrance')
    assert.deepEqual(calloutSegments(origin, points, state.reveal), [], 'Never leave a label-side stub')
  }
  state = advanceCalloutReveal(state, { ...ready, cameraRemaining: CALLOUT_NEAR_END_SECONDS }, 1 / 60)
  assert.ok(state.reveal > 0 && state.reveal < .05, 'The first ready frame begins drawing immediately')
  assert.equal(calloutSegments(origin, points, state.reveal).length, 1, 'Reveal begins at the left label')
  state = run(state, ready, 1)
  assert.equal(state.reveal, 1)
  assert.equal(state.pending, false, 'A completed paused shot may stop requesting GPU frames')
})

test('later weapons appear in full and follow their anchors while the camera and mounts move', () => {
  const entrance = run(createCalloutRevealState(), ready, .3)
  for (const key of ['main', 'torpedoes', 'single', 'bridge-batteries', 'beam']) {
    const state = advanceCalloutReveal(entrance, { key, animate: false, visible: true, cameraRemaining: 2.8, scrolling: true }, 1 / 60)
    assert.equal(state.reveal, 1, `${key} must not redraw or wait at each stop`)
    assert.equal(state.pending, false)
    const moved = points.map(point => ({ ...point, x: point.x + 20, y: point.y - 15 }))
    assert.deepEqual(calloutSegments(origin, moved, state.reveal).slice(2).map(line => [line.x2, line.y2]), [[920, 135], [870, 485]])
  }
})

test('small scrolls during and after the entrance do not restart its drawing', () => {
  const partial = run(createCalloutRevealState(), ready, .3)
  const moved = advanceCalloutReveal(partial, { ...ready, scrolling: true, cameraRemaining: .5 }, 1 / 60)
  assert.ok(moved.reveal > partial.reveal, 'A started entrance continues from its visible stroke')
  const complete = run(moved, ready, 1)
  const scrolledAgain = advanceCalloutReveal(complete, { ...ready, scrolling: true }, 1 / 60)
  assert.equal(scrolledAgain.reveal, 1)
  const reentered = advanceCalloutReveal(createCalloutRevealState(), { ...ready, cameraRemaining: 2.8 }, 1 / 60)
  assert.equal(reentered.reveal, 0, 'A fresh chapter entry can play its own entrance')
})

test('a hidden origin clears the entire line without replaying an already completed entrance', () => {
  const complete = run(createCalloutRevealState(), ready, 2)
  const hidden = advanceCalloutReveal(complete, { ...ready, visible: false }, .02)
  assert.equal(hidden.reveal, 0)
  assert.equal(hidden.pending, false)
  assert.deepEqual(calloutSegments(origin, points, hidden.reveal), [])
  const reappeared = advanceCalloutReveal(hidden, ready, .02)
  assert.equal(reappeared.reveal, 1)
})

test('reduced motion is immediate and normal draw duration is frame-rate independent', () => {
  const reduced = advanceCalloutReveal(createCalloutRevealState(), { ...ready, reducedMotion: true, scrolling: true }, .001)
  assert.equal(reduced.reveal, 1)
  const initial = createCalloutRevealState()
  const thirty = run(initial, ready, .6, 30)
  const sixty = run(initial, ready, .6, 60)
  assert.ok(Math.abs(thirty.reveal - sixty.reveal) < 1e-12)
  const invalidTime = advanceCalloutReveal(sixty, ready, NaN)
  assert.equal(invalidTime.reveal, sixty.reveal)
})
