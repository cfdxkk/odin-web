import type { Object3D, WebGLRenderer, WebGLRenderTarget } from 'three'
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js'

// Exhaust is additive light, not an opaque occluder. The normal/depth override
// otherwise turns glow sprites into solid rectangular faces at the nozzles.
export class OdinGTAOPass extends GTAOPass {
  readonly excludedObjects = new Set<Object3D>()

  override render(renderer: WebGLRenderer, writeBuffer: WebGLRenderTarget, readBuffer: WebGLRenderTarget, deltaTime: number, maskActive: boolean) {
    const visible = [...this.excludedObjects].filter(object => object.visible)
    visible.forEach(object => { object.visible = false })
    try {
      super.render(renderer, writeBuffer, readBuffer, deltaTime, maskActive)
    } finally {
      visible.forEach(object => { object.visible = true })
    }
  }
}
