import test from 'node:test'
import assert from 'node:assert/strict'
import { footerInkLevel, FOOTER_SCREEN_MATRIX, FOOTER_SCREEN_INKS } from '../app/lib/odin-footer-screen.ts'

test('footer screen is a complete repeating 4×4 order with no random marks', () => {
  assert.deepEqual([...FOOTER_SCREEN_MATRIX].sort((a,b)=>a-b), Array.from({length:16},(_,i)=>i))
  for(let y=0;y<4;y++) for(let x=0;x<4;x++) {
    assert.equal(footerInkLevel(.42,x,y), footerInkLevel(.42,x+4,y+4))
  }
})

test('footer ink darkens and lightens by fixed gray levels, monotonically', () => {
  for(let y=0;y<4;y++) for(let x=0;x<4;x++) {
    assert.equal(footerInkLevel(-1,x,y), 0)
    assert.equal(footerInkLevel(2,x,y), FOOTER_SCREEN_INKS.length-1)
    let previous=0
    for(let n=0;n<=100;n++) { const level=footerInkLevel(n/100,x,y); assert.ok(level>=previous);previous=level }
  }
})

test('halfway between gray levels produces a checkerboard instead of larger dots', () => {
  for(let y=0;y<4;y++) for(let x=0;x<4;x++) {
    assert.equal(footerInkLevel(.5,x,y), (x+y)%2===0?2:1)
  }
})
