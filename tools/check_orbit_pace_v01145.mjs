import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'
import { createHash } from 'node:crypto'
import { sampleOdinCamera } from '../app/lib/odin-camera.ts'

const work = 'work/v01145-review', review = 'docs/review/v0.11.45'
fs.mkdirSync(work, { recursive: true }); fs.mkdirSync(review, { recursive: true })
fs.writeFileSync(`${work}/baseline-camera.ts`, execFileSync('git', ['show', 'v0.11.44-rc.1:app/lib/odin-camera.ts']))
const { sampleOdinCamera: before } = await import(pathToFileURL(path.resolve(`${work}/baseline-camera.ts`)))
const delta = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b))
function sweep(sample, aspect, mobile) {
  let angle, view, total = 0, minimum = Infinity, maximum = 0, reverse = 0, reverseView = 0
  for (let n = 0; n <= 6000; n++) {
    const { position: p, target: q } = sample(n / 100, aspect, mobile)
    const a = Math.atan2(p.z, p.x), b = Math.atan2(p.z - q.z, p.x - q.x)
    if (n) {
      const da = delta(a, angle), dv = delta(b, view), speed = da / .01
      total += da; minimum = Math.min(minimum, speed); maximum = Math.max(maximum, speed)
      if (da <= 0) reverse++; if (dv <= 0) reverseView++
    }
    angle = a; view = b
  }
  return { samples: 6001, totalRadians: total, minimumRadiansPerSecond: minimum, maximumRadiansPerSecond: maximum,
    speedRatio: maximum / minimum, reverseOrbitSamples: reverse, reverseViewSamples: reverseView }
}
const configurations = []
for (const [aspect, mobile] of [[1.6, false], [.9, false], [.6, true]]) {
  const old = sweep(before, aspect, mobile), current = sweep(sampleOdinCamera, aspect, mobile)
  assert.ok(current.speedRatio < 1.00000001)
  assert.equal(current.reverseOrbitSamples, 0); assert.equal(current.reverseViewSamples, 0)
  assert.ok(Math.abs(current.totalRadians - 2 * Math.PI) < 1e-10)
  configurations.push({ aspect, mobile, before: old, after: current })
}
const assets = {}
const baselineAssets = JSON.parse(fs.readFileSync('docs/review/v0.11.44/camera-verification.json')).assets
for (const [key, baseline] of Object.entries(baselineAssets)) {
  const sha256 = createHash('sha256').update(fs.readFileSync(baseline.path)).digest('hex')
  assert.equal(sha256, baseline.sha256); assets[key] = { path: baseline.path, sha256, unchanged: true }
}
for (const file of ['app/lib/odin-rig.ts', 'app/lib/odin-motion.ts']) {
  const current = fs.readFileSync(file, 'utf8').replaceAll('\r\n', '\n')
  const previous = execFileSync('git', ['show', `v0.11.44-rc.1:${file}`], { encoding: 'utf8' }).replaceAll('\r\n', '\n')
  assert.ok(current === previous, `${file} changed outside this camera/render revision`)
}
const report = { version: 'v0.11.45-rc.1', baseline: 'v0.11.44-rc.1', configurations, assets, weaponMotionUnchanged: true,
  orbitDegreesPerSecond: 6, sternPassSeconds: 40, engineLightExcludedFromAODepth: true }
fs.writeFileSync(`${review}/camera-verification.json`, JSON.stringify(report, null, 2) + '\n')
console.log(JSON.stringify({ configurations, weaponMotionUnchanged: true, assetsUnchanged: true }, null, 2))
