import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { ODIN_TOUR, sampleTourCamera, selectTourChapter, clampTourIndex } from '../app/lib/odin-tour.ts'
import { SITE_COPY, CHAPTER_COPY, resolveOdinLocale } from '../app/lib/odin-copy.ts'
import { ODIN_ARTWORK } from '../app/lib/odin-artwork.ts'

test('scrolling selects whole chapters in both directions, with no continuous motion fraction', () => {
  const selected = []
  for (let scroll = 0; scroll <= 4000; scroll += 13) {
    const result = selectTourChapter([0, 1000, 2000, 3000, 4000].map(y => y - scroll), 0)
    assert.ok(Number.isInteger(result))
    selected.push(result)
  }
  assert.deepEqual([...new Set(selected)], [0, 1, 2, 3, 4])
  assert.equal(selectTourChapter([0, 1000, 2000], 499), 0)
  assert.equal(selectTourChapter([0, 1000, 2000], 501), 1)
  assert.equal(selectTourChapter([0, 1000, 2000], 1499), 1)
  assert.equal(selectTourChapter([0, 1000, 2000], 1501), 2)
  assert.equal(clampTourIndex(-100), 0)
  assert.equal(clampTourIndex(100), ODIN_TOUR.length - 1)
  assert.equal(clampTourIndex(NaN), 0)
})

test('guided cameras frame upper, lower and bridge weapons in the correct source axes', () => {
  for (let index = 0; index < ODIN_TOUR.length; index++) {
    const shot = ODIN_TOUR[index]
    for (const aspect of [.6, 1.4, 2.4, 3.5]) {
      const pose = sampleTourCamera(index, aspect)
      assert.deepEqual(pose.target.toArray(), [shot.point[0] * .01, shot.point[2] * .01, -shot.point[1] * .01])
      assert.ok(pose.position.toArray().every(Number.isFinite))
      assert.ok(pose.position.distanceTo(pose.target) > .5)
    }
  }
  const upper = sampleTourCamera(2), lower = sampleTourCamera(3)
  assert.ok(upper.position.y > upper.target.y)
  assert.ok(lower.position.y < lower.target.y)
  assert.ok(sampleTourCamera(7).target.y > upper.target.y)
  assert.ok(sampleTourCamera(0, .6).position.distanceTo(sampleTourCamera(0, .6).target) > sampleTourCamera(0, 2).position.distanceTo(sampleTourCamera(0, 2).target))
})

function strings(value) { return typeof value === 'string' ? [value] : Object.values(value).flatMap(strings) }
test('both languages cover every page, review and chapter key; English contains no Chinese UI', () => {
  assert.deepEqual(Object.keys(SITE_COPY.zh).sort(), Object.keys(SITE_COPY.en).sort())
  assert.deepEqual(Object.keys(CHAPTER_COPY.zh).sort(), ODIN_TOUR.map(shot => shot.id).sort())
  assert.deepEqual(Object.keys(CHAPTER_COPY.en).sort(), ODIN_TOUR.map(shot => shot.id).sort())
  for (const text of strings({ site: SITE_COPY.en, tour: CHAPTER_COPY.en, art: ODIN_ARTWORK.map(art => art.en) })) {
    assert.ok(!/[\u3400-\u9fff]/.test(text), `Untranslated English string: ${text}`)
    assert.ok(text.length)
  }
  assert.equal(resolveOdinLocale('en'), 'en')
  assert.equal(resolveOdinLocale('zh'), 'zh')
  assert.equal(resolveOdinLocale('invalid'), 'zh')
})

test('the complete official artwork archive has local images, aspect ratios and primary sources', () => {
  const manifest = JSON.parse(readFileSync(new URL('../docs/review/v0.13.0/artwork-sources.json', import.meta.url)))
  assert.equal(ODIN_ARTWORK.length, manifest.count)
  assert.equal(ODIN_ARTWORK.length, 27)
  assert.equal(new Set(ODIN_ARTWORK.map(art => art.src)).size, 27)
  for (const art of ODIN_ARTWORK) {
    assert.ok(existsSync(new URL(`../public${art.src}`, import.meta.url)))
    assert.ok(existsSync(new URL(`../public${art.thumb}`, import.meta.url)))
    assert.ok(art.width > 0 && art.height > 0)
    assert.ok(art.source.startsWith('https://robertsspaceindustries.com/i/'))
    assert.ok(art.zh.alt && art.en.alt && art.zh.title && art.en.title)
  }
  for (const category of ['Exterior', 'Interiors', 'Armament & structure', 'Liveries']) assert.ok(ODIN_ARTWORK.some(art => art.en.category === category))
})
