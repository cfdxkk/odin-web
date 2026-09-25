import { MOUSE, type Camera } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

export function createExplorationControls(camera: Camera, canvas: HTMLCanvasElement) {
  const controls = new OrbitControls(camera, canvas)
  controls.enabled = false
  controls.enableDamping = true; controls.dampingFactor = .06
  controls.minDistance = 3; controls.maxDistance = 22
  controls.enablePan = true; controls.screenSpacePanning = true; controls.panSpeed = .55
  controls.mouseButtons = { LEFT: MOUSE.ROTATE, MIDDLE: MOUSE.DOLLY, RIGHT: MOUSE.PAN }
  controls.rotateSpeed = .5; controls.zoomSpeed = .6
  return controls
}
