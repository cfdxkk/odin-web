import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'

test('the footer uses two inks and a regular non-overlapping amplitude-modulated dot grid', () => {
  const record = JSON.parse(readFileSync(new URL('../docs/review/v0.16.0/halftone-grid.json', import.meta.url)))
  const svg = readFileSync(new URL('../public/images/odin-mountain-footer-v0.16.0.svg', import.meta.url), 'utf8')
  const circles = [...svg.matchAll(/<circle cx="(\d+)" cy="(\d+)" r="([\d.]+)"\/>/g)]
  assert.equal(circles.length, record.dots)
  assert.ok(circles.length > 20000)
  assert.deepEqual([...new Set([...svg.matchAll(/fill="(#[\da-f]+)"/g)].map(match => match[1]))], record.inks)
  assert.ok(!svg.includes('<image'), 'No continuous-tone picture may sit underneath the print dots')
  const occupied = new Set()
  for (const [, x, y, radius] of circles) {
    assert.equal((Number(x) - record.gridOrigin[0]) % record.pitch, 0)
    assert.equal((Number(y) - record.gridOrigin[1]) % record.pitch, 0)
    assert.ok(Number(radius) > 0 && Number(radius) < record.pitch / 2)
    assert.ok(!occupied.has(`${x},${y}`))
    occupied.add(`${x},${y}`)
  }
})

test('all four official motion clips and posters are local, with only main and quad mirrored', () => {
  const record = JSON.parse(readFileSync(new URL('../docs/review/v0.16.0/official-media-sources.json', import.meta.url)))
  assert.equal(record.videos.length, 4)
  assert.deepEqual(record.presentationRequirements.additionalMirrors, ['main-battery', 'quad-turret'])
  for (const clip of record.videos) {
    assert.ok(clip.src.startsWith('/videos/odin/'))
    assert.ok(clip.poster.startsWith('/videos/odin/'))
    assert.ok(existsSync(new URL(`../public${clip.src}`, import.meta.url)))
    assert.ok(existsSync(new URL(`../public${clip.poster}`, import.meta.url)))
  }
})

test('the fine newspaper screen keeps aligned dots and permits connected ink in highlights', () => {
  const record = JSON.parse(readFileSync(new URL('../docs/review/v0.16.1/halftone-grid.json', import.meta.url)))
  const svg = readFileSync(new URL(`../${record.master}`, import.meta.url), 'utf8')
  const circles = [...svg.matchAll(/<circle cx="(\d+)" cy="(\d+)" r="([\d.]+)"\/>/g)]
  assert.equal(circles.length, record.dots)
  assert.ok(record.joinedDots > 1000, 'Highlights need joined ink and small negative holes, rather than only isolated bright dots')
  assert.ok(record.pitch / record.width < .002)
  assert.ok(existsSync(new URL(`../${record.target}`, import.meta.url)))
  assert.deepEqual([...new Set([...svg.matchAll(/fill="(#[\da-f]+)"/g)].map(match => match[1]))], record.inks)
  assert.ok(!svg.includes('<image'))
  const occupied = new Set()
  let joined = 0
  for (const [, x, y, radius] of circles) {
    assert.equal((Number(x) - record.gridOrigin[0]) % record.pitch, 0)
    assert.equal((Number(y) - record.gridOrigin[1]) % record.pitch, 0)
    assert.ok(Number(radius) > 0 && Number(radius) <= record.pitch / Math.SQRT2 + .001)
    if (Number(radius) > record.pitch / 2) joined++
    assert.ok(!occupied.has(`${x},${y}`))
    occupied.add(`${x},${y}`)
  }
  assert.equal(joined, record.joinedDots)
})
