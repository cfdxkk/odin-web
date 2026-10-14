import test from 'node:test'
import assert from 'node:assert/strict'
import { createSeekTransition, sampleSeekTransition } from '../app/lib/odin-seek.ts'
import { sampleOdinMotion } from '../app/lib/odin-motion.ts'

test('timeline clicks animate the displayed mechanics while keeping the selected clock fixed', () => {
  for (const [from, time] of [
    [{ deployment: 0, thrust: 0 }, 24],
    [{ deployment: 1, thrust: 0 }, 46],
    [{ deployment: .43, thrust: .2 }, 4],
    [{ deployment: 0, thrust: 1 }, 24],
    [{ deployment: .25, thrust: 0 }, 16],
  ]) {
    const transition = createSeekTransition(from, time)
    const first = sampleSeekTransition(transition, 0)
    assert.equal(first.deployment, from.deployment)
    assert.equal(first.thrust, from.thrust)
    assert.ok(transition.duration >= .8 && transition.duration <= 3.2)
    let previous = first
    for (let frame = 1; frame <= 240; frame++) {
      const next = sampleSeekTransition(transition, transition.duration * frame / 240)
      assert.equal(next.time, time, 'The playhead stays at the click while its visible pose catches up')
      assert.ok(Math.abs(next.deployment - previous.deployment) < .02)
      assert.ok(Math.abs(next.thrust - previous.thrust) < .05)
      previous = next
    }
    const end = sampleOdinMotion(time)
    assert.equal(previous.deployment, end.deployment)
    assert.equal(previous.thrust, end.thrust)
  }
})

test('repeated timeline clicks retarget the exact in-between rig and exhaust state', () => {
  let visible = { deployment: 0, thrust: 1 }
  for (const time of [24, 46, 3, 24, 15, 50, 34]) {
    const next = createSeekTransition(visible, time)
    const first = sampleSeekTransition(next, 0)
    assert.equal(first.deployment, visible.deployment)
    assert.equal(first.thrust, visible.thrust)
    visible = sampleSeekTransition(next, next.duration * .43)
  }
})

test('seeking from NAV to combat fades the visible flame before opening the guns', () => {
  const transition = createSeekTransition({ deployment: 0, thrust: 1 }, 24)
  assert.ok(transition.fadeSeconds > 0)
  for (let i = 0; i <= 20; i++) {
    const sample = sampleSeekTransition(transition, transition.fadeSeconds * i / 20)
    assert.equal(sample.deployment, 0)
  }
  assert.equal(sampleSeekTransition(transition, transition.fadeSeconds).thrust, 0)
})
