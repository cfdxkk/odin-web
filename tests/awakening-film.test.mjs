import test from 'node:test'
import assert from 'node:assert/strict'
import { PerspectiveCamera, Vector3 } from 'three'
import { AWAKENING_CHAPTERS, AWAKENING_DURATION, clampFilmTime, sampleAwakeningFilm, shouldAdvanceFilm } from '../app/lib/awakening-film.ts'

const distance = (a, b) => Math.hypot(...a.map((value, i) => value - b[i]))

test('the awakening is a bounded 72-second film with four contiguous chapters', () => {
  assert.equal(AWAKENING_DURATION, 72)
  assert.deepEqual(AWAKENING_CHAPTERS.map(({ start, end }) => [start, end]), [[0, 16], [16, 32], [32, 54], [54, 72]])
  assert.equal(new Set(AWAKENING_CHAPTERS.map(chapter => chapter.id)).size, 4)
  for (const chapter of AWAKENING_CHAPTERS) {
    assert.ok(chapter.title && chapter.en && chapter.line && chapter.description)
  }
  for (const [time, expected] of [[-5, 0], [0, 0], [72, 72], [1000, 72], [NaN, 0], [Infinity, 0], [-Infinity, 0]]) {
    assert.equal(clampFilmTime(time), expected)
    assert.equal(sampleAwakeningFilm(time).time, expected)
  }
  for (const [time, expected] of [[0, 0], [15.999, 0], [16, 1], [31.999, 1], [32, 2], [53.999, 2], [54, 3], [72, 3]]) {
    assert.equal(sampleAwakeningFilm(time).chapter, expected)
  }
})

test('deployment uses the complete opening and closing strokes before engine ignition', () => {
  for (const time of [0, 16, 31.999, 32, 54, 60, 72]) assert.equal(sampleAwakeningFilm(time).deployment, 0)
  assert.equal(sampleAwakeningFilm(35.25).deployment, .5)
  for (const time of [38.5, 42, 47.5]) assert.equal(sampleAwakeningFilm(time).deployment, 1)
  assert.equal(sampleAwakeningFilm(50.75).deployment, .5)
  assert.equal(sampleAwakeningFilm(54).thrust, 0)
  assert.ok(sampleAwakeningFilm(54.001).thrust > 0)
  assert.equal(sampleAwakeningFilm(60).thrust, 1)
  for (let frame = 0; frame <= AWAKENING_DURATION * 120; frame++) {
    const sample = sampleAwakeningFilm(frame / 120)
    for (const key of ['deployment', 'thrust', 'scan', 'energy', 'warp']) {
      assert.ok(sample[key] >= 0 && sample[key] <= 1, `${key} is out of range at ${sample.time}`)
    }
    if (sample.time <= 54 || sample.deployment > 0) assert.equal(sample.thrust, 0, `Premature ignition at ${sample.time}`)
    if (sample.thrust > 0) assert.equal(sample.deployment, 0)
    if (sample.time <= 64) assert.equal(sample.warp, 0)
  }
  assert.equal(sampleAwakeningFilm(72).warp, 1)
})

test('seeking is deterministic, reversible and independent of previous samples', () => {
  const original = sampleAwakeningFilm(44.25)
  for (const time of [71, 0, 54, 33, 72, 16]) sampleAwakeningFilm(time)
  assert.deepEqual(sampleAwakeningFilm(44.25), original)
  const mutated = sampleAwakeningFilm(44.25)
  mutated.camera.position[0] = 1000
  assert.deepEqual(sampleAwakeningFilm(44.25), original, 'Callers must not mutate the camera track through a sample')
})

test('the camera stays outside the hull and moves continuously through every chapter', () => {
  let previous = sampleAwakeningFilm(0).camera
  for (let frame = 0; frame <= AWAKENING_DURATION * 120; frame++) {
    const time = frame / 120, camera = sampleAwakeningFilm(time).camera
    for (const value of [...camera.position, ...camera.target]) assert.ok(Number.isFinite(value))
    assert.ok(camera.position[0] <= -2.65, `Camera enters the hull's lateral clearance at ${time}`)
    assert.ok(distance(camera.position, camera.target) > 3.8, `Camera approaches its target too closely at ${time}`)
    assert.ok(distance(camera.position, previous.position) < .035, `Camera teleports at ${time}`)
    assert.ok(distance(camera.target, previous.target) < .006, `Camera target teleports at ${time}`)
    previous = camera
  }
  // Test velocity around all joins, including mechanical and chapter boundaries.
  const epsilon = .00001
  for (const time of [8, 16, 24, 32, 38.5, 42.5, 46, 47.5, 49.5, 54, 60, 64, 68]) {
    for (const field of ['position', 'target']) {
      const before = sampleAwakeningFilm(time - epsilon).camera[field]
      const at = sampleAwakeningFilm(time).camera[field]
      const after = sampleAwakeningFilm(time + epsilon).camera[field]
      const left = at.map((value, axis) => (value - before[axis]) / epsilon)
      const right = after.map((value, axis) => (value - at[axis]) / epsilon)
      assert.ok(distance(left, right) < .0001, `${field} velocity jumps at ${time}`)
    }
  }
})

test('opening composition holds the silhouette and the ending accelerates away from the engines', () => {
  const pose = sampleAwakeningFilm(0).camera
  const camera = new PerspectiveCamera(33, 16 / 9, .025, 150)
  camera.position.set(...pose.position); camera.lookAt(...pose.target); camera.updateMatrixWorld(true)
  const silhouette = [[0, -.13, -3.8], [0, .2, 3.5], [-1, -.2, 0], [1, -.2, 0], [0, 1.39, .8]]
    .map(point => new Vector3(...point).project(camera))
  const width = (Math.max(...silhouette.map(point => point.x)) - Math.min(...silhouette.map(point => point.x))) / 2
  assert.ok(width > .60, `Opening silhouette is too small: ${width}`)
  for (const point of silhouette) assert.ok(Math.abs(point.x) < 1 && Math.abs(point.y) < .95, 'Opening silhouette is cropped')
  const from = sampleAwakeningFilm(64).camera, middle = sampleAwakeningFilm(68).camera, to = sampleAwakeningFilm(72).camera
  assert.ok(distance(middle.position, from.position) < distance(to.position, middle.position), 'Final pullback should accelerate')
  assert.ok(to.position[2] > 20 && distance(to.position, to.target) > 25)
})

test('temporary blockers preserve explicit pause and resume only the unpaused film', () => {
  const playing = Object.freeze({ userPaused: false, scrubbing: false, visible: true, overlayOpen: false, inspect: false, reducedMotion: false, started: true })
  assert.equal(shouldAdvanceFilm(playing), true)
  for (const blocker of [{ scrubbing: true }, { visible: false }, { overlayOpen: true }, { inspect: true }, { reducedMotion: true }, { started: false }]) {
    assert.equal(shouldAdvanceFilm({ ...playing, ...blocker }), false)
    assert.equal(shouldAdvanceFilm(playing), true, 'Removing a temporary blocker resumes playback')
    const paused = Object.freeze({ ...playing, userPaused: true })
    assert.equal(shouldAdvanceFilm({ ...paused, ...blocker }), false)
    assert.equal(shouldAdvanceFilm(paused), false, 'Removing a temporary blocker must not clear explicit pause')
    assert.equal(paused.userPaused, true)
  }
})
