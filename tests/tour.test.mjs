import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { ODIN_TOUR, sampleTourCamera, sampleTourDisplayCamera, selectTourChapter, clampTourIndex, createTourTransition, sampleTourTransition, tourWheelTarget } from '../app/lib/odin-tour.ts'
import { sampleOdinCamera, ODIN_CAMERA_ORBIT_SECONDS } from '../app/lib/odin-camera.ts'
import { sampleOdinMotion, DEPLOY_SECONDS } from '../app/lib/odin-motion.ts'
import { SITE_COPY, CHAPTER_COPY, resolveOdinLocale } from '../app/lib/odin-copy.ts'
import { ODIN_ARTWORK, ODIN_WALLPAPERS } from '../app/lib/odin-artwork.ts'

test('the homepage uses the original orbit while every detail chapter holds its inspection shot', () => {
  for (const [aspect, mobile] of [[.6, true], [16 / 9, false], [32 / 9, false]]) {
    for (const time of [0, 1, 22.5, 44.99, 45, 59.99, 60, 135]) {
      const opening = sampleTourDisplayCamera(0, time, aspect, mobile)
      const original = sampleOdinCamera(time, aspect, mobile)
      assert.deepEqual(opening.position.toArray(), original.position.toArray())
      assert.deepEqual(opening.target.toArray(), original.target.toArray())
      for (let index = 1; index < ODIN_TOUR.length; index++) {
        const detail = sampleTourDisplayCamera(index, time, aspect, mobile)
        const held = sampleTourCamera(index, aspect)
        assert.deepEqual(detail.position.toArray(), held.position.toArray())
        assert.deepEqual(detail.target.toArray(), held.target.toArray())
      }
    }
    assert.ok(sampleTourDisplayCamera(0, 0, aspect, mobile).position.distanceTo(sampleTourDisplayCamera(0, 1, aspect, mobile).position) > .1)
    assert.ok(sampleTourDisplayCamera(0, 0, aspect, mobile).position.distanceTo(sampleTourDisplayCamera(0, ODIN_CAMERA_ORBIT_SECONDS, aspect, mobile).position) < 1e-9)
  }
})

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

test('four guided chapters frame the hull, batteries, bridge and engines in source axes', () => {
  assert.deepEqual(ODIN_TOUR.map(shot => shot.id), ['overview', 'batteries', 'bridge', 'engines'])
  for (let index = 0; index < ODIN_TOUR.length; index++) {
    const shot = ODIN_TOUR[index]
    for (const aspect of [.6, 1.4, 2.4, 3.5]) {
      const pose = sampleTourCamera(index, aspect)
      assert.deepEqual(pose.target.toArray(), [shot.point[0] * .01, shot.point[2] * .01, -shot.point[1] * .01])
      assert.ok(pose.position.toArray().every(Number.isFinite))
      assert.ok(pose.position.distanceTo(pose.target) > .5)
    }
  }
  const batteries = sampleTourCamera(1), bridge = sampleTourCamera(2), engines = sampleTourCamera(3)
  assert.ok(batteries.target.z < 0, 'Main batteries are forward of the center')
  assert.ok(bridge.target.y > batteries.target.y, 'Bridge view is above the main deck')
  assert.ok(engines.position.z > engines.target.z, 'Stern view looks forward from behind the nozzles')
  assert.ok(sampleTourCamera(0, .6).position.distanceTo(sampleTourCamera(0, .6).target) > sampleTourCamera(0, 2).position.distanceTo(sampleTourCamera(0, 2).target))
})

test('staged wheel navigation releases both tour boundaries to ordinary document scrolling', () => {
  assert.equal(tourWheelTarget(0, 1, 112, 112), 1)
  assert.equal(tourWheelTarget(1, 1, 112, 112), 2)
  assert.equal(tourWheelTarget(2, -1, 112, 112), 1)
  assert.equal(tourWheelTarget(3, 1, 112, 112), undefined, 'The artwork and footer must scroll freely after stage four')
  assert.equal(tourWheelTarget(0, -1, 112, 112), undefined)
  assert.equal(tourWheelTarget(3, -1, -200, 112), 3, 'Returning from the archive first aligns the last stage')
  assert.equal(tourWheelTarget(1, 1, 250, 112), 1, 'A partly visible stage is aligned before advancing')
})

test('the final ship stage can hand one wheel gesture to the wallpaper stage', () => {
  assert.equal(tourWheelTarget(3, 1, 0, 0, true), 4)
  assert.equal(tourWheelTarget(3, 1, 250, 0, true), 3, 'Align the current stage before leaving it')
  assert.equal(tourWheelTarget(0, -1, 0, 0, true), undefined)
  assert.equal(tourWheelTarget(2, 1, 0, 0, true), 3)
})

test('the wallpaper gallery keeps the four official wide exterior scenes', () => {
  assert.equal(ODIN_WALLPAPERS.length, 4)
  assert.deepEqual(ODIN_WALLPAPERS.map(art => art.sourceName), ['sc-anvil-odin-exterior-3.jpg', 'sc-anvil-odin-exterior-4.jpg', 'sc-anvil-odin-exterior-5.jpg', 'sc-anvil-odin-exterior-7.jpg'])
  for (const art of ODIN_WALLPAPERS) {
    assert.ok(art.width / art.height > 2)
    assert.equal(art.en.category, 'Exterior')
  }
})

test('chapter transitions retain the native deployment duration and show intermediate poses', () => {
  const opening = createTourTransition(sampleOdinMotion(0), 24)
  assert.equal(opening.duration, DEPLOY_SECONDS)
  assert.equal(sampleTourTransition(opening, 0).deployment, 0)
  assert.equal(sampleTourTransition(opening, opening.duration / 2).deployment, .5)
  assert.deepEqual(sampleTourTransition(opening, opening.duration), { deployment: 1, thrust: 0, time: 24 })
  const samePose = createTourTransition(sampleOdinMotion(24), 24)
  assert.equal(samePose.duration, 0, 'Moving to the next weapon view must not restart deployment')
})

test('propulsion ignites during stowage while the return to weapons fades exhaust first', () => {
  for (const fromTime of [0, 24, 46]) for (const toTime of [0, 24, 46]) {
    const transition = createTourTransition(sampleOdinMotion(fromTime), toTime)
    const initial = sampleOdinMotion(fromTime), target = sampleOdinMotion(toTime)
    for (let i = 0; i <= 100; i++) {
      const pose = sampleTourTransition(transition, transition.duration * i / 100)
      assert.ok(pose.deployment >= 0 && pose.deployment <= 1)
      assert.ok(pose.thrust >= 0 && pose.thrust <= 1)
      if (toTime === 24) assert.ok(pose.thrust === 0 || pose.deployment === initial.deployment, 'Fade exhaust before deploying weapons')
      const film = sampleOdinMotion(pose.time)
      assert.ok(Math.abs(film.deployment - pose.deployment) < 1e-9, 'Scrubbing starts from the currently rendered deployment')
      if (pose.deployment === 0) assert.ok(Math.abs(film.thrust - pose.thrust) < 1e-9)
      if (transition.duration && i === 0) { assert.equal(pose.deployment, initial.deployment); assert.equal(pose.thrust, initial.thrust) }
      if (i === 100) { assert.equal(pose.deployment, target.deployment); assert.equal(pose.thrust, target.thrust) }
    }
  }
})

test('the engine chapter starts stowage and ignition together without adding their durations', () => {
  const transition = createTourTransition(sampleOdinMotion(24), 46)
  assert.equal(transition.duration, DEPLOY_SECONDS)
  const early = sampleTourTransition(transition, .5)
  assert.ok(early.deployment < 1 && early.deployment > 0)
  assert.ok(early.thrust > 0 && early.thrust < 1)
  const lit = sampleTourTransition(transition, 2.5)
  assert.equal(lit.thrust, 1)
  assert.ok(lit.deployment > 0, 'The engines are fully lit before the weapons finish stowing')
})

test('rapid chapter reversals start at the visible pose instead of an endpoint', () => {
  const opening = createTourTransition(sampleOdinMotion(0), 24)
  const partial = sampleTourTransition(opening, 2.3)
  const reverse = createTourTransition(partial, 46)
  const start = sampleTourTransition(reverse, 0)
  assert.equal(start.deployment, partial.deployment)
  assert.equal(start.thrust, partial.thrust)
  for (let elapsed = .01; elapsed < reverse.duration; elapsed += .07) {
    const pose = sampleTourTransition(reverse, elapsed)
    assert.ok(pose.deployment <= partial.deployment)
    assert.ok(pose.thrust >= start.thrust && pose.thrust <= 1)
  }
  const extinguishing = createTourTransition(sampleOdinMotion(46), 24)
  const power = sampleTourTransition(extinguishing, .5)
  assert.ok(power.thrust > 0 && power.thrust < 1 && power.deployment === 0)
  const switchAgain = createTourTransition(power, 0)
  assert.equal(sampleTourTransition(switchAgain, 0).thrust, power.thrust)
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
