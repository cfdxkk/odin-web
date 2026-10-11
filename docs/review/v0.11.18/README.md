# v0.11.18 source stern plate review

The stern cover marked with a red X was an incorrect rear substitute. It has
been removed. The moving front cover now uses the eight existing faces of the
farther-forward roof plate marked with a green check, extracted from the
untouched `odin.blend/holo.001`. Its closed endpoint is the original source
position. The same eight faces were removed from the fixed hull so the cover
does not leave a stationary duplicate as it opens.

The original stern trough shoulder and forward fixed hull faces are restored
without reshaping them. The stern barrel mesh is rigidly returned to its
original closed position; the stern and bow source keyframe motion remains in
Nuxt/Three.js. The bow cap parks farther down its existing channel slope to
clear the original bore during the lift. Both exported GLBs contain zero
animation clips. The editable revision is
`assets/blender/odin_articulated_v0.11.18.blend`.

`stern-closed-oblique.png`, `stern-closed-side.png`,
`stern-folding-side.png`, `stern-deployed-side.png`, and
`stern-closed-front.png` show the stern cover from multiple poses. The former
red-X location is left uncovered as requested; the barrel channel is visible
there from some angles. `bow-transition-038-side.png` shows the bow clearance
at 38%. The other screenshots check the keel single, flank single, bridge
quad, aft twin, and main armor in the refreshed browser preview.

Validation: `npm test` (45 passing), `npm run verify:asset`, `npm run generate`,
and browser review of the recorded poses. The original `odin.blend` was read
but not edited.
