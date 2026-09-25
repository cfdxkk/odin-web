# v0.8.11 — corrected armor partition and hull-aligned hinges

The latest user drawing defines three independent boundaries at each dorsal junction: the rotating turret shroud (blue), forward sliding main leaf (green), and aft hinged leaf (red). The diagonal triangular region now belongs to the aft leaf. The previous main-leaf rear return is removed.

Both aft leaves remain single inclined planes. Their straight material-edge pivots run parallel to the original hull crease, rather than the earlier trimmed, diverging edge. Local receiving slots follow the exact hinge lines, and a fixed underlap closes the main leaf's lower fore-corner window. Small mechanical seams remain; the plates are independently movable solids.

The five dorsal leaves have full perimeter walls and deep-red inner surfaces. Main/nose skins use a 0.25-unit vertical thickness, with fitted scarf bevels at the shroud; aft leaves use 0.18-unit normal thickness. Constrained triangulation preserves the original side/roof planes and serrations without folded triangles. The aft shroud underside has a local receiving rebate for the opening sweep.

The dorsal nose first clears its seal, then slides forward. Main leaves make room before the aft leaves turn 130 degrees. The accepted v0.8.9 bore motion, shorter side-bore descent, deployed endpoints, other weapons and bridge armor remain unchanged. All motion is authored by Nuxt/Three.js; the revised Blend and both GLBs contain no animation clips. Original `odin.blend` is unchanged.

- [Side before](before-side.png) / [side after](after-side.png)
- [Top before](before-top.png) / [top after](after-top.png)
- [Rear oblique before](before-rear-oblique.png) / [rear oblique after](after-rear-oblique.png)
- [Unfold/fold preview](main-battery-preview.mp4) and [twelve-frame sequence](main-battery-sequence.png)
- [Physical geometry checks](physical-fit.json), [101-pose armor clearance](main-clearance.json), [101-pose hull sweep](hull-sweep.json), [other systems](unchanged-systems.json), [animation provenance](animation-preview.json)

Validation: `npm test`, `npm run verify:asset`, `npm run generate`; actual high-quality GLB reviewed in the browser from side, top, rear-oblique and open/midstroke views. Static comparison cameras are identical between revisions.
