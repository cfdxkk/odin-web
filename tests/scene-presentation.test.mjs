import test from 'node:test'
import assert from 'node:assert/strict'
import { createManualReturn, sampleManualReturn, advanceManualResume, advanceFilmClock } from '../app/lib/odin-manual-return.ts'
import { sampleOdinMotion } from '../app/lib/odin-motion.ts'
import { calloutSegments } from '../app/lib/odin-callouts.ts'
import { photoDimensions } from '../app/lib/odin-photo.ts'

test('leaving manual NAV/SCM starts from the actual visible pose and returns to the preserved guide clock', () => {
  for (const [from, time] of [
    [{ deployment: 0, thrust: 1 }, 24],
    [{ deployment: 1, thrust: 0 }, 46],
    [{ deployment: .43, thrust: 0 }, 4],
    [{ deployment: .63, thrust: 0 }, 15],
    [{ deployment: 0, thrust: .36 }, 40],
  ]) {
    const transition = createManualReturn(from, time)
    const first = sampleManualReturn(transition, 0)
    assert.equal(first.deployment, from.deployment)
    assert.equal(first.thrust, from.thrust)
    for (let i = 0; i <= 100; i++) {
      const sample = sampleManualReturn(transition, transition.duration * i / 100)
      assert.equal(sample.time, time, 'the guide timeline must not seek to a synthetic deployment time')
      assert.ok(sample.deployment >= 0 && sample.deployment <= 1)
      assert.ok(sample.thrust >= 0 && sample.thrust <= 1)
    }
    const last = sampleManualReturn(transition, transition.duration)
    const expected = sampleOdinMotion(time)
    assert.equal(last.deployment, expected.deployment)
    assert.equal(last.thrust, expected.thrust)
  }
})

test('reversing a manual return captures its current in-between pose without a jump', () => {
  const transition = createManualReturn({ deployment: 1, thrust: 0 }, 46)
  const current = sampleManualReturn(transition, transition.duration * .37)
  const reversed = createManualReturn(current, 24)
  const first = sampleManualReturn(reversed, 0)
  assert.equal(first.deployment, current.deployment)
  assert.equal(first.thrust, current.thrust)
  assert.equal(first.time, 24)
  assert.ok(createManualReturn({ deployment: 1, thrust: 0 }, 24).duration >= .65, 'matching mechanical positions still need time to blend the aim clock')
})

test('film loop signal belongs only to the frame crossing the end', () => {
  assert.deepEqual(advanceFilmClock(59.97, .02, 60), { time: 59.99, looped: false })
  const loop = advanceFilmClock(59.99, .02, 60)
  assert.equal(loop.looped, true)
  assert.ok(Math.abs(loop.time - .01) < 1e-8)
  assert.equal(advanceFilmClock(loop.time, .02, 60).looped, false)
})

test('interrupting a guide return extinguishes residual thrust continuously before the manual interlock resumes', () => {
  for (const deployed of [false, true]) {
    let state = { deployment: .91, thrust: .24 }
    for (let i = 0; i < 30; i++) {
      const next = advanceManualResume(state, deployed, 1 / 60)
      assert.ok(Math.abs(next.thrust - state.thrust) <= 1 / 60 / 1.2 + 1e-10)
      assert.ok(Math.abs(next.deployment - state.deployment) <= 1 / 60 / 6.5 + 1e-10)
      state = next
    }
    assert.equal(state.thrust, 0)
  }
  assert.equal(advanceManualResume({ deployment: 0, thrust: 0 }, false, .02, .1).thrust, 0, 'pending selective groups must still block ignition')
  assert.ok(advanceManualResume({ deployment: 0, thrust: .4 }, false, .02).thrust > .4, 'fully stowed NAV resumes ignition normally')
})

test('two projected batteries share one trunk and retain both real endpoints', () => {
  const origin = { x: 360, y: 300, visible: true }
  const points = [{ x: 890, y: 240, visible: true }, { x: 820, y: 410, visible: true, ghost: true }]
  const segments = calloutSegments(origin, points, 1)
  assert.equal(segments.length, 4)
  assert.deepEqual(segments[0], { x1: 360, y1: 300, x2: 402, y2: 300, ghost: false })
  assert.deepEqual(segments[1], { x1: 402, y1: 240, x2: 402, y2: 410, ghost: false })
  assert.deepEqual(segments.slice(2).map(({ x2, y2, ghost }) => [x2, y2, ghost]), [[890, 240, false], [820, 410, true]])
  const first = calloutSegments(origin, points, .1)
  assert.equal(first.length, 1)
  assert.ok(first[0].x2 > origin.x && first[0].x2 < 402)
  assert.deepEqual(calloutSegments(origin, points, 0), [])
  assert.deepEqual(calloutSegments({ ...origin, visible: false }, points, 1), [])
  assert.deepEqual(calloutSegments(origin, points.map(p => ({ ...p, visible: false })), 1), [])
})

test('capture resolution preserves the visible aspect ratio while bounding large GPU allocations', () => {
  for (const [w,h] of [[1440,1000],[1920,1080],[3440,1440],[7680,2160],[390,844]]) {
    const output = photoDimensions(w,h)
    assert.ok(output.width <= 5760 && output.height <= 4320)
    assert.ok(output.width * output.height <= 20_005_000)
    assert.ok(Math.abs(output.width / output.height - w / h) < .003)
  }
  assert.deepEqual(photoDimensions(1440,1000), { width:2880,height:2000 })
  assert.deepEqual(photoDimensions(4000,2000,4096), { width:4096,height:2048 })
})
