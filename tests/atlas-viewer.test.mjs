import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ATLAS_MODES, atlasMotionActive, createAtlasDeploymentTransition, advanceAtlasDeployment, atlasEngineTarget } from '../app/lib/atlas-viewer-state.ts'
import { DEPLOY_SECONDS, isPlaying, nextPlayback } from '../app/lib/odin-motion.ts'

const baseState = { playing: true, mode: 'overview', deployment: 0, active: true, reducedMotion: false, technical: false, scrubbing: false }

test('engine inspection waits for the complete closing stroke before ignition', () => {
  let transition = createAtlasDeploymentTransition(1, 0)
  let deployment = 1
  for (let step = 1; step < 650; step++) {
    const pose = advanceAtlasDeployment(transition, 0, .01)
    transition = pose.transition; deployment = pose.deployment
    assert.ok(deployment > 0)
    assert.equal(atlasEngineTarget(deployment, 'engines'), 0)
  }
  const closed = advanceAtlasDeployment(transition, 0, .1)
  assert.equal(closed.deployment, 0)
  assert.equal(closed.transition, undefined)
  assert.equal(atlasEngineTarget(closed.deployment, 'engines'), .85)
  assert.equal(atlasEngineTarget(Number.EPSILON, 'engines'), 0)
})

test('reversing a chapter transition starts at the rendered mechanical pose', () => {
  const opening = advanceAtlasDeployment(createAtlasDeploymentTransition(0, 1), 1, DEPLOY_SECONDS / 3)
  const closing = createAtlasDeploymentTransition(opening.deployment, 0)
  const first = advanceAtlasDeployment(closing, 0, 0)
  assert.equal(first.deployment, opening.deployment)
  const next = advanceAtlasDeployment(first.transition, 0, .05)
  assert.ok(next.deployment < first.deployment && next.deployment > 0)
  assert.equal(atlasEngineTarget(next.deployment, 'overview'), 0)
})

test('range drag or keyboard edit takes over a finite chapter transition immediately', () => {
  const transition = createAtlasDeploymentTransition(0, 1)
  const dragged = advanceAtlasDeployment(transition, 1, .2, true)
  assert.deepEqual(dragged, { deployment: 1, transition: undefined })
  const keyboard = advanceAtlasDeployment(transition, .37, .2)
  assert.deepEqual(keyboard, { deployment: .37, transition: undefined })
})

test('an explicit pause remains paused across every mode, visibility and slider cycle', () => {
  let intent = { userPaused: true, scrubbing: false }
  for (const mode of ATLAS_MODES) {
    for (const visible of [false, true]) {
      intent = nextPlayback(intent, 'scrub-start')
      assert.equal(atlasMotionActive({ ...baseState, mode, playing: isPlaying(intent), scrubbing: intent.scrubbing }, visible), false)
      intent = nextPlayback(intent, 'scrub-end')
      assert.equal(atlasMotionActive({ ...baseState, mode, playing: isPlaying(intent) }, visible), false)
      assert.equal(intent.userPaused, true)
    }
  }
})

test('playing resumes after a drag but cannot advance while hidden or inactive', () => {
  let intent = { userPaused: false, scrubbing: false }
  intent = nextPlayback(intent, 'scrub-start')
  assert.equal(atlasMotionActive({ ...baseState, playing: isPlaying(intent), scrubbing: true }, true), false)
  intent = nextPlayback(intent, 'scrub-end')
  const resumed = { ...baseState, playing: isPlaying(intent) }
  assert.equal(atlasMotionActive(resumed, true), true)
  assert.equal(atlasMotionActive(resumed, false), false)
  assert.equal(atlasMotionActive({ ...resumed, active: false }, true), false)
})

test('reduced motion finishes requested poses without enabling automatic motion', () => {
  const pose = advanceAtlasDeployment(createAtlasDeploymentTransition(0, 1), 1, .01, false, true)
  assert.deepEqual(pose, { deployment: 1, transition: undefined })
  assert.equal(atlasMotionActive({ ...baseState, reducedMotion: true }, true), false)
})
