import { test } from 'node:test'
import assert from 'node:assert/strict'
import { sampleOdinCamera } from '../app/lib/odin-camera.ts'
test('authored flight changes elevation, distance and aim without positional cuts', () => {
  const shots = [0, 12, 24, 43, 60].map(t => sampleOdinCamera(t))
  assert.ok(Math.abs(shots[0].position.length() - shots[2].position.length()) > 3)
  assert.ok(shots[0].target.distanceTo(shots[2].target) > .5)
  assert.ok(shots[0].position.distanceTo(shots[4].position) < 1e-6)
  for (let t = .02; t <= 60; t += .02) {
    const a = sampleOdinCamera(t), b = sampleOdinCamera(t - .02)
    assert.ok(a.position.distanceTo(b.position) < .09, `camera continuity at ${t}`)
    assert.ok(a.target.distanceTo(b.target) < .02)
  }
})
