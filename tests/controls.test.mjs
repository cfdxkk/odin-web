import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PerspectiveCamera, Vector3 } from 'three'
import { createExplorationControls } from '../app/lib/odin-controls.ts'

test('holding the right button pans camera and target together; left drag orbits', () => {
  const document = new EventTarget(), canvas = new EventTarget()
  Object.assign(canvas, { ownerDocument: document, style: {}, clientWidth: 1440, clientHeight: 1000, getRootNode: () => document, setPointerCapture() {}, releasePointerCapture() {} })
  const camera = new PerspectiveCamera(33, 1.44, .035, 500)
  camera.position.set(8, 4, -8); camera.lookAt(0, 0, 0)
  const controls = createExplorationControls(camera, canvas)
  controls.enabled = true; controls.enableDamping = false; controls.update()
  const dispatch = (target, type, button, x, y) => {
    const event = new Event(type, { cancelable: true })
    Object.assign(event, { button, pointerId: 1, pointerType: 'mouse', clientX: x, clientY: y, pageX: x, pageY: y })
    target.dispatchEvent(event)
  }
  const drag = button => {
    dispatch(canvas, 'pointerdown', button, 600, 500)
    dispatch(document, 'pointermove', button, 720, 560)
    dispatch(document, 'pointerup', button, 720, 560)
  }
  const originalPosition = camera.position.clone(), originalDirection = camera.getWorldDirection(new Vector3())
  drag(2)
  assert.ok(controls.target.length() > .2, 'Right drag must visibly translate the focal point')
  assert.ok(camera.position.clone().sub(originalPosition).distanceTo(controls.target) < 1e-6)
  assert.ok(camera.getWorldDirection(new Vector3()).distanceTo(originalDirection) < 1e-6)
  const target = controls.target.clone()
  drag(0)
  assert.ok(controls.target.distanceTo(target) < 1e-6, 'Left drag must preserve focal point')
  assert.ok(camera.getWorldDirection(new Vector3()).distanceTo(originalDirection) > .05)
  const menu = new Event('contextmenu', { cancelable: true }); canvas.dispatchEvent(menu)
  assert.equal(menu.defaultPrevented, true)
  controls.dispose()
})
