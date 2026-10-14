import test from 'node:test'
import assert from 'node:assert/strict'
import { cleanFooterTones, footerInkLevel, FOOTER_SCREEN_MATRIX, FOOTER_SCREEN_INKS } from '../app/lib/odin-footer-screen.ts'

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

test('footer plate removes disconnected faint flecks, not long faint mountain ridges', () => {
  const width=40,height=12,tones=new Float32Array(width*height)
  tones[2*width+3]=.08
  for(let x=3;x<34;x++) tones[8*width+x]=.045
  const clean=cleanFooterTones(tones,width,height)
  assert.equal(clean[2*width+3],0)
  for(let x=3;x<34;x++) assert.equal(clean[8*width+x],tones[8*width+x])
  assert.equal(tones[2*width+3]>.07,true)
})

test('footer plate preserves small bright ship details', () => {
  const tones=new Float32Array(100); tones[44]=.65;tones[45]=.1
  const clean=cleanFooterTones(tones,10,10)
  assert.equal(clean[44],tones[44]);assert.equal(clean[45],tones[45])
})

test('faint threshold tips connected to a mountain do not become floating printed squares', () => {
  const width=40,height=14,tones=new Float32Array(width*height)
  for(let y=6;y<height;y++) for(let x=1;x<width-1;x++) tones[y*width+x]=.025
  // A weak upward tip remains connected in the continuous-tone plate, but
  // only its top sample coincides with the screen's first visible threshold.
  tones[4*width+8]=.0181;tones[5*width+8]=.0181;tones[4*width+9]=.0116
  const clean=cleanFooterTones(tones,width,height)
  assert.equal(clean[4*width+8],0)
  for(let x=3;x<width-3;x++) assert.equal(clean[7*width+x],tones[7*width+x])
})

test('the faint support pass keeps a narrow continuous distant ridge', () => {
  const width=40,height=10,tones=new Float32Array(width*height)
  for(let x=2;x<38;x++) tones[5*width+x]=.018
  const clean=cleanFooterTones(tones,width,height)
  for(let x=3;x<37;x++) assert.equal(clean[5*width+x],tones[5*width+x])
})
