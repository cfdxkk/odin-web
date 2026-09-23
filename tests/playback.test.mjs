import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isPlaying, nextPlayback, sampleOdinMotion, MODES } from '../app/lib/odin-motion.ts'

test('dragging temporarily pauses and releasing resumes when the user was playing', () => {
  let state = { userPaused: false, scrubbing: false }
  state = nextPlayback(state, 'scrub-start'); assert.equal(isPlaying(state), false)
  state = nextPlayback(state, 'scrub-end'); assert.equal(isPlaying(state), true)
})
test('an explicit pause survives scrubbing, mode changes and browser tab changes', () => {
  let state = nextPlayback({ userPaused: false, scrubbing: false }, 'toggle')
  for (const event of ['scrub-start', 'scrub-end', 'mode-change', 'visibility-change']) {
    state = nextPlayback(state, event); assert.equal(isPlaying(state), false, event)
  }
  state = nextPlayback(state, 'toggle'); assert.equal(isPlaying(state), true)
})
test('the three modes have stable timeline entry points', () => {
  assert.deepEqual(MODES.map(m => m.name), ['飞船外观', 'SMC/战斗', 'NAV/航行'])
  assert.equal(sampleOdinMotion(MODES[0].time).mode, 'exterior')
  assert.equal(sampleOdinMotion(MODES[1].time).mode, 'scm')
  assert.equal(sampleOdinMotion(MODES[2].time).mode, 'nav')
})
test('exterior presentation has no deployed weapons or engine exhaust', () => {
  for (let t = 0; t < 12; t += .1) assert.deepEqual([sampleOdinMotion(t).deployment, sampleOdinMotion(t).thrust], [0, 0])
})
test('SCM deploys all weapons; NAV begins by stowing them', () => {
  assert.equal(sampleOdinMotion(20).deployment, 1)
  assert.equal(sampleOdinMotion(26).deployment, 1)
  assert.ok(sampleOdinMotion(30).deployment < 1)
  assert.equal(sampleOdinMotion(33).deployment, 0)
})
test('thrusters cannot ignite while any weapon is in the deployment sequence', () => {
  for (let t = 0; t <= 40; t += .025) {
    const state = sampleOdinMotion(t)
    if (state.deployment > 0) assert.equal(state.thrust, 0, `time ${t}`)
    if (state.thrust > 0) { assert.equal(state.deployment, 0); assert.equal(state.mode, 'nav') }
  }
  assert.equal(sampleOdinMotion(30.8).thrust, 0)
  assert.ok(sampleOdinMotion(32).thrust < sampleOdinMotion(33.5).thrust)
  for (let t = 33.8; t <= 39; t += .1) assert.equal(sampleOdinMotion(t).thrust, 1)
})
