import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'
import { createHash } from 'node:crypto'
import { ODIN_CAMERA_ORBIT_SECONDS, sampleOdinCamera } from '../app/lib/odin-camera.ts'

const work = 'work/v01146-review', review = 'docs/review/v0.11.46'
fs.mkdirSync(work, { recursive: true }); fs.mkdirSync(review, { recursive: true })
fs.writeFileSync(`${work}/baseline-camera.ts`, execFileSync('git', ['show', 'v0.11.45-rc.1:app/lib/odin-camera.ts']))
const { sampleOdinCamera: before } = await import(pathToFileURL(path.resolve(`${work}/baseline-camera.ts`)))
const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
function sweep(sample, duration, aspect, mobile) {
  let angle, view, total = 0, minimum = Infinity, maximum = 0, reverse = 0, reverseView = 0
  for (let n = 0; n <= duration * 100; n++) {
    const { position: p, target: q } = sample(n / 100, aspect, mobile)
    const a = Math.atan2(p.z, p.x), b = Math.atan2(p.z - q.z, p.x - q.x)
    if (n) {
      const da = delta(a, angle), dv = delta(b, view), speed = da / .01
      total += da; minimum = Math.min(minimum, speed); maximum = Math.max(maximum, speed)
      if (da <= 0) reverse++; if (dv <= 0) reverseView++
    }
    angle = a; view = b
  }
  return { duration, samples: duration * 100 + 1, totalRadians: total, minimumRadiansPerSecond: minimum,
    maximumRadiansPerSecond: maximum, speedRatio: maximum / minimum, reverseOrbitSamples: reverse, reverseViewSamples: reverseView }
}
const configurations = []
for (const [aspect, mobile] of [[1.6, false], [.9, false], [.6, true]]) {
  const old = sweep(before, 60, aspect, mobile), current = sweep(sampleOdinCamera, ODIN_CAMERA_ORBIT_SECONDS, aspect, mobile)
  const continuous = sweep(sampleOdinCamera, 180, aspect, mobile)
  assert.ok(current.speedRatio < 1.00000001)
  assert.equal(continuous.reverseOrbitSamples, 0); assert.equal(continuous.reverseViewSamples, 0)
  assert.ok(Math.abs(current.totalRadians - 2 * Math.PI) < 1e-10)
  assert.ok(Math.abs(current.minimumRadiansPerSecond / old.minimumRadiansPerSecond - 4 / 3) < 1e-9)
  assert.ok(Math.abs(continuous.totalRadians - 8 * Math.PI) < 1e-10)
  configurations.push({ aspect, mobile, before: old, after: current, continuous })
}
const assets = {}
const baselineAssets = JSON.parse(fs.readFileSync('docs/review/v0.11.45/camera-verification.json')).assets
for (const [key, baseline] of Object.entries(baselineAssets)) {
  const sha256 = createHash('sha256').update(fs.readFileSync(baseline.path)).digest('hex')
  assert.equal(sha256, baseline.sha256); assets[key] = { path: baseline.path, sha256, unchanged: true }
}
for (const file of ['app/lib/odin-rig.ts', 'app/lib/odin-motion.ts', 'app/lib/odin-ao.ts']) {
  const current = fs.readFileSync(file, 'utf8').replaceAll('\r\n', '\n')
  const previous = execFileSync('git', ['show', `v0.11.45-rc.1:${file}`], { encoding: 'utf8' }).replaceAll('\r\n', '\n')
  assert.equal(current, previous, `${file} changed outside this camera/logo revision`)
}
const report = { version: 'v0.11.46-rc.1', baseline: 'v0.11.45-rc.1', configurations, assets,
  weaponMotionUnchanged: true, engineAOFixUnchanged: true, orbitSeconds: ODIN_CAMERA_ORBIT_SECONDS,
  orbitDegreesPerSecond: 8, speedIncreasePercent: 100 / 3, weaponFilmSeconds: 60 }
fs.writeFileSync(`${review}/camera-verification.json`, JSON.stringify(report, null, 2) + '\n')
console.log(JSON.stringify({ orbitSeconds: ODIN_CAMERA_ORBIT_SECONDS, orbitDegreesPerSecond: 8,
  configurations: configurations.length, weaponMotionUnchanged: true, assetsUnchanged: true }))
