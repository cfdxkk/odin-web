import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isPlaying, nextPlayback, sampleOdinMotion, advanceManualMotion, FILM_DURATION, DEPLOY_SECONDS, MODES } from '../app/lib/odin-motion.ts'

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
  assert.deepEqual(MODES.map(m => m.name), ['飞船外观', 'SCM/战斗', 'NAV/航行'])
  assert.equal(sampleOdinMotion(MODES[0].time).mode, 'exterior')
  assert.equal(sampleOdinMotion(MODES[1].time).mode, 'scm')
  assert.equal(sampleOdinMotion(MODES[2].time).mode, 'nav')
})
test('exterior presentation has no deployed weapons or engine exhaust', () => {
  for (let t = 0; t < 12; t += .1) assert.deepEqual([sampleOdinMotion(t).deployment, sampleOdinMotion(t).thrust], [0, 0])
})
test('SCM deploys all weapons; NAV begins by stowing them', () => {
  assert.equal(sampleOdinMotion(24).deployment, 1)
  assert.equal(sampleOdinMotion(32).deployment, 1)
  assert.ok(sampleOdinMotion(38).deployment < 1)
  assert.equal(sampleOdinMotion(44).deployment, 0)
  assert.equal(sampleOdinMotion(12 + DEPLOY_SECONDS / 2).deployment, .5)
  assert.equal(sampleOdinMotion(12 + DEPLOY_SECONDS).deployment, 1)
  assert.equal(sampleOdinMotion(32 + DEPLOY_SECONDS).deployment, 0)
  assert.ok(DEPLOY_SECONDS < 7, 'The complete transition is faster than the previous nine seconds')
})
test('thrusters cannot ignite while any weapon is in the deployment sequence', () => {
  for (let t = 0; t <= FILM_DURATION; t += .025) {
    const state = sampleOdinMotion(t)
    if (state.deployment > 0) assert.equal(state.thrust, 0, `time ${t}`)
    if (state.thrust > 0) { assert.equal(state.deployment, 0); assert.equal(state.mode, 'nav') }
  }
  const stowed = 32 + DEPLOY_SECONDS
  assert.equal(sampleOdinMotion(stowed).thrust, 0)
  assert.ok(sampleOdinMotion(stowed + .5).thrust < sampleOdinMotion(stowed + 2).thrust)
  for (let t = stowed + 2.5; t <= 58; t += .1) assert.equal(sampleOdinMotion(t).thrust, 1)
})

test('free exploration NAV visibly ignites after full stow, and reversals stay interlocked', () => {
  let state = { deployment: 1, thrust: 0 }
  for (let n = 0; n < 1800; n++) {
    state = advanceManualMotion(state, false, 1 / 60)
    if (state.deployment > 0) assert.equal(state.thrust, 0)
    if (n < DEPLOY_SECONDS * 60 - 2) assert.ok(state.deployment > 0, 'The complete stow sequence finishes before thrust')
    if (n > DEPLOY_SECONDS * 60 + 2) assert.ok(state.thrust > 0, 'Exhaust begins as soon as stow finishes')
  }
  assert.deepEqual(state, { deployment: 0, thrust: 1 })
  for (let n = 0; n < 850; n++) {
    state = advanceManualMotion(state, true, 1 / 60)
    if (state.thrust > 0) assert.equal(state.deployment, 0)
  }
  assert.deepEqual(state, { deployment: 1, thrust: 0 })
  for (let n = 0; n < 100; n++) state = advanceManualMotion(state, false, 1 / 60)
  assert.ok(state.deployment > 0 && state.deployment < 1)
  for (let n = 0; n < 150; n++) state = advanceManualMotion(state, true, 1 / 60)
  assert.deepEqual(state, { deployment: 1, thrust: 0 })
})
