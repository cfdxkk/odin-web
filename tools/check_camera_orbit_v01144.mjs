import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'
import { createHash } from 'node:crypto'
import { sampleOdinCamera } from '../app/lib/odin-camera.ts'

const work='work/v01144-review',review='docs/review/v0.11.44'
fs.mkdirSync(work,{recursive:true});fs.mkdirSync(review,{recursive:true})
fs.writeFileSync(`${work}/baseline-camera.ts`,execFileSync('git',['show','v0.11.43-rc.1:app/lib/odin-camera.ts']))
const {sampleOdinCamera:before}=await import(pathToFileURL(path.resolve(`${work}/baseline-camera.ts`)))
const delta=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b))
function sweep(sample,aspect,mobile) {
  let angle,view,total=0,minSpeed=Infinity,reverse=0,reverseView=0
  const reverseTimes=[]
  for(let n=0;n<=6000;n++) {
    const {position:p,target:q}=sample(n/100,aspect,mobile)
    const a=Math.atan2(p.z,p.x),b=Math.atan2(p.z-q.z,p.x-q.x)
    if(n){const da=delta(a,angle),dv=delta(b,view);total+=da;minSpeed=Math.min(minSpeed,da/.01);if(da<0){reverse++;reverseTimes.push(n/100)}if(dv<0)reverseView++}
    angle=a;view=b
  }
  return {samples:6001,reverseSamples:reverse,reverseViewSamples:reverseView,reverseInterval:reverseTimes.length?[reverseTimes[0],reverseTimes.at(-1)]:null,totalRadians:total,minAngularSpeed:minSpeed}
}
const configurations=[]
let maxRadiusError=0,maxHeightError=0,maxTargetError=0
for(const [aspect,mobile]of [[1.6,false],[.9,false],[.6,true]]) {
  const previous=sweep(before,aspect,mobile),current=sweep(sampleOdinCamera,aspect,mobile)
  assert.ok(previous.reverseSamples>0&&current.reverseSamples===0&&current.reverseViewSamples===0)
  assert.ok(Math.abs(current.totalRadians-2*Math.PI)<1e-10)
  configurations.push({aspect,mobile,before:previous,after:current})
  for(let n=0;n<=6000;n++) {
    const a=before(n/100,aspect,mobile),b=sampleOdinCamera(n/100,aspect,mobile)
    maxRadiusError=Math.max(maxRadiusError,Math.abs(Math.hypot(a.position.x,a.position.z)-Math.hypot(b.position.x,b.position.z)))
    maxHeightError=Math.max(maxHeightError,Math.abs(a.position.y-b.position.y))
    maxTargetError=Math.max(maxTargetError,a.target.distanceTo(b.target))
  }
}
const previousHashes=JSON.parse(fs.readFileSync('docs/review/v0.11.43/asset-hashes.json'))
const assets={}
for(const key of ['native','high','lite']) {
  const {path:file,sha256}=previousHashes[key],current=createHash('sha256').update(fs.readFileSync(file)).digest('hex')
  assert.equal(current,sha256);assets[key]={path:file,sha256:current,unchanged:true}
}
const report={version:'v0.11.44-rc.1',baseline:'v0.11.43-rc.1',configurations,maxRadiusError,maxHeightError,maxTargetError,assets}
fs.writeFileSync(`${review}/camera-verification.json`,JSON.stringify(report,null,2)+'\n')
console.log(report)
