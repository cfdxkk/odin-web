# Odin valley / model-derived print

The ship in this revision is the actual project model, not a generated likeness.

- Editable scene: `tools/render-footer-plate.ts`.
- Model: `public/models/odin.glb`, with `createOdinRig(...).apply(0, 0)`.
- The GLB, joint hierarchy and original Blender files are unchanged.
- Continuous-tone plate: `public/images/odin-valley-continuous-v0.16.2.png`, 3840 × 1600.
- Terrain is a deterministic mesh with near ridges, low valley mist and distance fog. It has no random screen dots.
- The website applies one amplitude-modulated screen using `FooterPrint.client.vue`. Dot centers are aligned to the actual canvas size and device-pixel ratio, instead of scaling a pre-screened bitmap.
- The print is drawn only on first visibility or a size change. There is no additional live 3D scene and no continuous footer animation.

## Rebuild the plate

1. Bundle `tools/render-footer-plate.ts` with the project's esbuild, in ESM format, into `work/v0162-review/render-footer.js`.
2. Serve the repository root on loopback only. Open `tools/render-footer-plate.html` in a hardware-accelerated browser.
3. Wait for `html[data-ready=true]`, set the viewport to 3840 × 1600 at device scale 1, and capture the canvas as the continuous plate.
4. The site creates the final responsive print from that plate. Do not add a second raster screen or blur the ship.

This revision uses code-native WebGL and Canvas rendering. No image-generation prompt or AI-redrawn ship is involved.
