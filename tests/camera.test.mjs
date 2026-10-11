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

test('cinematic orbit and viewing direction advance one way through the complete loop', () => {
  const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
  for (const [aspect, mobile] of [[1.6, false], [.9, false], [.6, true]]) {
    let orbit, view, total = 0
    for (let n = 0; n <= 6000; n++) {
      const { position: p, target: q } = sampleOdinCamera(n / 100, aspect, mobile)
      const a = Math.atan2(p.z, p.x), b = Math.atan2(p.z - q.z, p.x - q.x)
      if (n) {
        const movement = delta(a, orbit), facing = delta(b, view)
        assert.ok(movement > 0, `Orbit reverses or stops at ${n / 100}s`)
        assert.ok(facing > 0, `Target tracking reverses the apparent turn at ${n / 100}s`)
        total += movement
      }
      orbit = a; view = b
    }
    assert.ok(Math.abs(total - 2 * Math.PI) < 1e-10, 'The film makes exactly one turn')
  }
})

test('orbit angular speed remains continuous across shot boundaries and the 60-second wrap', () => {
  const angle = t => { const p = sampleOdinCamera(t).position; return Math.atan2(p.z, p.x) }
  const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
  const dt = .00001
  for (const t of [7, 12, 18, 24, 30, 36, 43, 50, 56]) {
    const left = delta(angle(t), angle(t - dt)) / dt
    const right = delta(angle(t + dt), angle(t)) / dt
    assert.ok(left > 0 && right > 0)
    assert.ok(Math.abs(left - right) < .00001, `Angular speed jumps at ${t}s`)
  }
  const leaving = delta(angle(dt), angle(0)) / dt
  const arriving = delta(angle(60), angle(60 - dt)) / dt
  assert.ok(Math.abs(leaving - arriving) < .00001, 'Loop wrap preserves angular speed')
})

test('camera direction fix retains the authored zoom, elevation and framing at every inspection shot', () => {
  for (const [time, radius, height, aimY, aimZ] of [
    [0, 11.6, 3.7, .24, 0], [7, 10.7, 2.9, .28, -.20],
    [12, 8.9, 4.4, .38, -.70], [18, 7.7, 3.7, .45, -.50],
    [24, 7.0, 2.8, .76, .40], [30, 8.6, 2.1, .56, .45],
    [36, 10.1, 3.5, .32, .20], [43, 11.0, 2.5, .20, 0],
    [50, 11.6, 4.2, .25, -.20], [56, 12.0, 4.5, .24, 0], [60, 11.6, 3.7, .24, 0],
  ]) {
    const { position: p, target: q } = sampleOdinCamera(time)
    assert.ok(Math.abs(Math.hypot(p.x, p.z) - radius) < 1e-9)
    assert.ok(Math.abs(p.y - height) < 1e-9)
    assert.ok(Math.abs(q.y - aimY) < 1e-9 && Math.abs(q.z - aimZ) < 1e-9)
  }
})
