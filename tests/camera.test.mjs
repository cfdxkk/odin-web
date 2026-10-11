import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ODIN_CAMERA_ORBIT_SECONDS, sampleOdinCamera } from '../app/lib/odin-camera.ts'

const cameraTime = authoredTime => authoredTime * ODIN_CAMERA_ORBIT_SECONDS / 60
test('authored flight changes elevation, distance and aim without positional cuts', () => {
  const shots = [0, 12, 24, 43, 60].map(t => sampleOdinCamera(cameraTime(t)))
  assert.ok(Math.abs(shots[0].position.length() - shots[2].position.length()) > 3)
  assert.ok(shots[0].target.distanceTo(shots[2].target) > .5)
  assert.ok(shots[0].position.distanceTo(shots[4].position) < 1e-6)
  for (let t = .02; t <= ODIN_CAMERA_ORBIT_SECONDS; t += .02) {
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
      const { position: p, target: q } = sampleOdinCamera(cameraTime(n / 100), aspect, mobile)
      const a = Math.atan2(p.z, p.x), b = Math.atan2(p.z - q.z, p.x - q.x)
      if (n) {
        const movement = delta(a, orbit), facing = delta(b, view)
        assert.ok(movement > 0, `Orbit reverses or stops at ${n / 100}s`)
        assert.ok(facing > 0, `Target tracking reverses the apparent turn at ${n / 100}s`)
        total += movement
      }
      orbit = a; view = b
    }
    assert.ok(Math.abs(total - 2 * Math.PI) < 1e-10, 'Each camera loop makes exactly one turn')
  }
})

test('orbit advances at a uniform eight degrees per second throughout the loop', () => {
  const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
  const angle = t => { const p = sampleOdinCamera(t).position; return Math.atan2(p.z, p.x) }
  const step = .01, expected = 8 * Math.PI / 180
  for (let n = 1; n <= ODIN_CAMERA_ORBIT_SECONDS / step; n++) {
    const speed = delta(angle(n * step), angle((n - 1) * step)) / step
    assert.ok(Math.abs(speed - expected) < 1e-10, `Orbit speeds up or slows down at ${n * step}s`)
  }
})

test('orbit angular speed remains continuous across shot boundaries and the 45-second wrap', () => {
  const angle = t => { const p = sampleOdinCamera(t).position; return Math.atan2(p.z, p.x) }
  const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
  const dt = .00001
  for (const t of [7, 12, 18, 24, 30, 36, 43, 50, 56].map(cameraTime)) {
    const left = delta(angle(t), angle(t - dt)) / dt
    const right = delta(angle(t + dt), angle(t)) / dt
    assert.ok(left > 0 && right > 0)
    assert.ok(Math.abs(left - right) < .00001, `Angular speed jumps at ${t}s`)
  }
  const leaving = delta(angle(dt), angle(0)) / dt
  const arriving = delta(angle(ODIN_CAMERA_ORBIT_SECONDS), angle(ODIN_CAMERA_ORBIT_SECONDS - dt)) / dt
  assert.ok(Math.abs(leaving - arriving) < .00001, 'Loop wrap preserves angular speed')
})

test('framing velocity stays smooth across shot joins and the loop wrap', () => {
  const dt = .00001
  const velocity = (a, b) => {
    const before = sampleOdinCamera(a), after = sampleOdinCamera(b)
    return [...after.position.clone().sub(before.position).divideScalar(dt).toArray(),
      ...after.target.clone().sub(before.target).divideScalar(dt).toArray()]
  }
  for (const t of [7, 12, 18, 24, 30, 36, 43, 50, 56, 60].map(cameraTime)) {
    const left = velocity(t - dt, t), right = t === ODIN_CAMERA_ORBIT_SECONDS ? velocity(0, dt) : velocity(t, t + dt)
    left.forEach((value, axis) => assert.ok(Math.abs(value - right[axis]) < .0001, `Framing velocity jumps at ${t}s on axis ${axis}`))
  }
})

test('evenly paced orbit retains the authored zoom, elevation and framing at every inspection shot', () => {
  for (const [time, radius, height, aimY, aimZ] of [
    [0, 11.6, 3.7, .24, 0], [7, 10.7, 2.9, .28, -.20],
    [12, 8.9, 4.4, .38, -.70], [18, 7.7, 3.7, .45, -.50],
    [24, 7.0, 2.8, .76, .40], [30, 8.6, 2.1, .56, .45],
    [36, 10.1, 3.5, .32, .20], [43, 11.0, 2.5, .20, 0],
    [50, 11.6, 4.2, .25, -.20], [56, 12.0, 4.5, .24, 0], [60, 11.6, 3.7, .24, 0],
  ]) {
    const { position: p, target: q } = sampleOdinCamera(cameraTime(time))
    assert.ok(Math.abs(Math.hypot(p.x, p.z) - radius) < 1e-9)
    assert.ok(Math.abs(p.y - height) < 1e-9)
    assert.ok(Math.abs(q.y - aimY) < 1e-9 && Math.abs(q.z - aimZ) < 1e-9)
  }
})

test('the faster orbit remains continuous over multiple camera and weapon film loops', () => {
  const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
  const angle = t => { const p = sampleOdinCamera(t).position; return Math.atan2(p.z, p.x) }
  for (let t = .01; t <= 180; t += .01) {
    assert.ok(Math.abs(delta(angle(t), angle(t - .01)) / .01 - 8 * Math.PI / 180) < 1e-9,
      `Orbit jumps at ${t}s, including 60-second weapon film wraps`)
  }
  assert.ok(sampleOdinCamera(60).position.distanceTo(sampleOdinCamera(0).position) > 10,
    'The camera keeps its own phase when the weapon film returns to zero')
})
