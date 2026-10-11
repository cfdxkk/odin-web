import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PerspectiveCamera, Vector3 } from 'three'
import { ODIN_CAMERA_ORBIT_SECONDS, sampleOdinCamera, odinCameraFraming, interpolateOdinCamera } from '../app/lib/odin-camera.ts'

const cameraTime = authoredTime => authoredTime * ODIN_CAMERA_ORBIT_SECONDS / 60
test('the complete orbit keeps its distance, elevation and aim steady without cuts', () => {
  const initial = sampleOdinCamera(0)
  assert.ok(initial.position.distanceTo(sampleOdinCamera(ODIN_CAMERA_ORBIT_SECONDS).position) < 1e-6)
  for (let t = .02; t <= ODIN_CAMERA_ORBIT_SECONDS; t += .02) {
    const a = sampleOdinCamera(t), b = sampleOdinCamera(t - .02)
    assert.ok(a.position.distanceTo(b.position) < .09, `camera continuity at ${t}`)
    assert.ok(a.target.distanceTo(initial.target) < 1e-9, 'The view should not track different points of the hull')
    assert.ok(Math.abs(a.position.y - initial.position.y) < 1e-9, 'The view should not climb and descend')
    assert.ok(Math.abs(a.position.distanceTo(a.target) - initial.position.distanceTo(initial.target)) < 1e-9,
      'The view should not zoom in and out during the orbit')
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

test('ultrawide framing gives the hull a useful screen width and keeps its silhouette visible', () => {
  const silhouette = [[0, -.13, -3.8], [0, .2, 3.5], [-1, -.2, 0], [1, -.2, 0], [0, 1.39, .8]].map(p => new Vector3(...p))
  for (const [aspect, minimumWidth] of [[16 / 9, .5], [21 / 9, .45], [32 / 9, .35]]) {
    const pose = sampleOdinCamera(0, aspect)
    const camera = new PerspectiveCamera(33, aspect, .035, 500)
    camera.setViewOffset(aspect * 900, 900, 0, 900 * odinCameraFraming(aspect).viewOffsetY, aspect * 900, 900)
    camera.position.copy(pose.position); camera.lookAt(pose.target); camera.updateMatrixWorld(true)
    const points = silhouette.map(p => p.clone().project(camera))
    const width = (Math.max(...points.map(p => p.x)) - Math.min(...points.map(p => p.x))) / 2
    assert.ok(width > minimumWidth, `The ship is too small at aspect ${aspect}: ${width}`)
    for (const p of points) assert.ok(Math.abs(p.x) < .95 && Math.abs(p.y) < .8, 'The opening silhouette must remain in view')
    const offset = pose.position.clone().sub(pose.target).normalize()
    assert.ok(offset.distanceTo(sampleOdinCamera(0, 16 / 9).position.sub(sampleOdinCamera(0, 16 / 9).target).normalize()) < 1e-9,
      'Adapting to a wider screen must not change the viewing angle')
  }
})

test('opposite-side seeks stay outside the ship and preserve their endpoint views', () => {
  for (const toTime of [12, ODIN_CAMERA_ORBIT_SECONDS / 2, 32, 44]) {
    const from = sampleOdinCamera(0, 32 / 9), to = sampleOdinCamera(toTime, 32 / 9)
    const minimumDistance = Math.min(from.position.distanceTo(from.target), to.position.distanceTo(to.target))
    for (let n = 0; n <= 100; n++) {
      const pose = interpolateOdinCamera(from, to, n / 100)
      assert.ok(pose.position.distanceTo(pose.target) >= minimumDistance - 1e-9, 'A chapter change must not cut through the hull')
      if (n === 0) assert.ok(pose.position.distanceTo(from.position) < 1e-9)
      if (n === 100) assert.ok(pose.position.distanceTo(to.position) < 1e-9)
    }
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
