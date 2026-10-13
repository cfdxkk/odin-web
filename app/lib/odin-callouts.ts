import * as THREE from 'three'

export type CalloutOrigin = { x: number; y: number; visible: boolean }
export type CalloutPoint = CalloutOrigin & { ghost?: boolean }
export type CalloutSegment = { x1: number; y1: number; x2: number; y2: number; ghost: boolean }

const ease = (value: number) => { const u = THREE.MathUtils.clamp(value, 0, 1); return u * u * (3 - 2 * u) }

// One shared trunk and one vertical span avoid overlapping translucent lines.
// The reveal always starts at the label before reaching the projected mount.
export function calloutSegments(origin: CalloutOrigin, points: readonly CalloutPoint[], reveal: number): CalloutSegment[] {
  const targets = points.filter(point => point.visible)
  if (!origin.visible || !targets.length || reveal <= 0) return []
  const kneeX = origin.x + 42
  const trunk = ease(reveal / .26), stem = ease((reveal - .26) / .20), branch = ease((reveal - .46) / .54)
  const segments: CalloutSegment[] = [{ x1: origin.x, y1: origin.y, x2: THREE.MathUtils.lerp(origin.x, kneeX, trunk), y2: origin.y, ghost: false }]
  if (stem > 0) {
    const min = Math.min(origin.y, ...targets.map(point => point.y)), max = Math.max(origin.y, ...targets.map(point => point.y))
    segments.push({ x1: kneeX, y1: THREE.MathUtils.lerp(origin.y, min, stem), x2: kneeX, y2: THREE.MathUtils.lerp(origin.y, max, stem), ghost: false })
  }
  if (branch > 0) for (const point of targets) segments.push({ x1: kneeX, y1: point.y, x2: THREE.MathUtils.lerp(kneeX, point.x, branch), y2: point.y, ghost: !!point.ghost })
  return segments
}

export function createOdinCallouts(host: HTMLElement) {
  const canvas = document.createElement('canvas')
  canvas.className = 'odin-callout-canvas'
  canvas.setAttribute('aria-hidden', 'true')
  Object.assign(canvas.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', zIndex: '4', pointerEvents: 'none' })
  host.appendChild(canvas)
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  const scene = new THREE.Scene(), camera = new THREE.OrthographicCamera(0, 1, 0, 1, -1, 1)
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(6 * 3 * 12), colors = new Float32Array(6 * 3 * 12)
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3).setUsage(THREE.DynamicDrawUsage))
  const material = new THREE.MeshBasicMaterial({ color: 0xc4cbcc, vertexColors: true, transparent: true, opacity: .80, depthTest: false, depthWrite: false, side: THREE.DoubleSide, toneMapped: false })
  const line = new THREE.Mesh(geometry, material)
  line.frustumCulled = false; scene.add(line)
  const dotGeometry = new THREE.CircleGeometry(2.4, 20)
  const dots = Array.from({ length: 4 }, () => {
    const dot = new THREE.Mesh(dotGeometry, new THREE.MeshBasicMaterial({ color: 0xc4cbcc, transparent: true, opacity: .80, depthTest: false, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }))
    scene.add(dot); return dot
  })
  let elapsed = 0, width = 1, height = 1, dirty = true, wasVisible = false
  let lastOrigin = '', lastPoints = ''
  function reset() { elapsed = 0; dirty = true; wasVisible = false; canvas.style.opacity = '0'; clear() }
  function clear() { renderer.clear(); canvas.dataset.visible = 'false'; canvas.dataset.points = '[]' }
  function resize(w: number, h: number, ratio: number) {
    width = w; height = h; renderer.setPixelRatio(Math.min(2, ratio)); renderer.setSize(width, height, false)
    camera.right = width; camera.bottom = height; camera.updateProjectionMatrix(); dirty = true
  }
  function moving(origin?: CalloutOrigin) { return dirty || (!!origin?.visible && wasVisible && elapsed < .95) }
  function render(origin: CalloutOrigin | undefined, points: readonly CalloutPoint[], dt: number, reducedMotion: boolean) {
    const visible = !!origin?.visible && points.some(point => point.visible)
    const originKey = origin ? `${origin.x}/${origin.y}/${origin.visible}` : ''
    const pointKey = points.map(point => `${point.x}/${point.y}/${point.visible}/${point.ghost}`).join(';')
    if (!visible) {
      if (wasVisible || dirty) clear()
      wasVisible = false; dirty = false; lastOrigin = originKey; lastPoints = pointKey
      return
    }
    elapsed = reducedMotion ? .95 : Math.min(.95, elapsed + dt)
    if (!dirty && elapsed >= .95 && originKey === lastOrigin && pointKey === lastPoints && wasVisible) return
    dirty = false; wasVisible = true; lastOrigin = originKey; lastPoints = pointKey
    canvas.style.opacity = String(ease(elapsed / .16))
    const segments = calloutSegments(origin!, points, elapsed / .95)
    let vertex = 0
    for (const segment of segments) {
      const dx = segment.x2 - segment.x1, dy = segment.y2 - segment.y1, length = Math.hypot(dx, dy)
      if (length < .001) continue
      const nx = -dy / length * .5, ny = dx / length * .5
      const corners = [[segment.x1 + nx, segment.y1 + ny], [segment.x1 - nx, segment.y1 - ny], [segment.x2 + nx, segment.y2 + ny], [segment.x2 - nx, segment.y2 - ny]]
      for (const index of [0, 1, 2, 2, 1, 3]) {
        const corner = corners[index]!
        positions[vertex * 3] = corner[0]!; positions[vertex * 3 + 1] = corner[1]!; positions[vertex * 3 + 2] = 0
        // Both mounted batteries need the same readable annotation weight.
        // Their exact projected anchors already distinguish the two branches.
        const shade = 1
        colors[vertex * 3] = shade; colors[vertex * 3 + 1] = shade; colors[vertex * 3 + 2] = shade
        vertex++
      }
    }
    geometry.setDrawRange(0, vertex)
    geometry.attributes.position!.needsUpdate = true; geometry.attributes.color!.needsUpdate = true
    dots.forEach((dot, index) => {
      const point = points[index]
      dot.visible = !!point?.visible && elapsed >= .94
      if (point) { dot.position.set(point.x, point.y, 0); dot.material.opacity = .80 }
    })
    renderer.render(scene, camera)
    canvas.dataset.visible = 'true'; canvas.dataset.reveal = (elapsed / .95).toFixed(3)
    canvas.dataset.origin = JSON.stringify(origin)
    canvas.dataset.points = JSON.stringify(points)
  }
  return { canvas, reset, resize, moving, render, dispose() {
    geometry.dispose(); dotGeometry.dispose(); material.dispose(); dots.forEach(dot => dot.material.dispose()); renderer.dispose(); canvas.remove()
  } }
}
