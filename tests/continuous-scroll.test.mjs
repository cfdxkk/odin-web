import test from 'node:test'
import assert from 'node:assert/strict'
import { weaponScrollProgress, weaponScrollOffset, weaponStepAt, weaponStageTop, isWithinWeaponScroll } from '../app/lib/odin-scroll.ts'

test('each inspection choice maps to its real scroll position at any viewport height', () => {
  for (const viewport of [600,844,1080,1440]) {
    const height = viewport * 6.5
    for (let step=0;step<6;step++) {
      const offset=weaponScrollOffset(step,6,height,viewport)
      assert.equal(weaponStepAt(weaponScrollProgress(-offset,height,viewport),6),step)
      assert.equal(weaponStageTop(-offset,height,viewport),0,'weapon chapter stays selected throughout the pinned range')
    }
    const positions=Array.from({length:51},(_,i)=>weaponScrollProgress(-i/50*(height-viewport),height,viewport))
    assert.equal(new Set(positions).size,51,'wheel position is continuous, not six quantized camera stops')
    assert.equal(weaponScrollProgress(200,height,viewport),0)
    assert.equal(weaponScrollProgress(-height,height,viewport),1)
  }
})

test('weapon interior releases native wheel scrolling, while its ends can hand off to adjacent stages', () => {
  const height=6500,viewport=1000
  assert.equal(isWithinWeaponScroll(0,height,viewport,1),true)
  assert.equal(isWithinWeaponScroll(0,height,viewport,-1),false)
  assert.equal(isWithinWeaponScroll(-2750,height,viewport,1),true)
  assert.equal(isWithinWeaponScroll(-2750,height,viewport,-1),true)
  assert.equal(isWithinWeaponScroll(-5500,height,viewport,1),false)
  assert.equal(isWithinWeaponScroll(-5500,height,viewport,-1),true)
  assert.equal(weaponStageTop(350,height,viewport),350)
  assert.equal(weaponStageTop(-5800,height,viewport),-300)
})
