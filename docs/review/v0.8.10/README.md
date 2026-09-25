# v0.8.10 — fitted armor returns and physical hinges

The annotated side gap now has two separate owners: a rear return on each moving main leaf, and an underlapping receiver attached to the fixed hull. The receiver remains inboard of the moving return's path. The four planar aft leaves turn 130 degrees about their actual straight material edges; the fixed receiving shoulders include clearance for the finite-thickness sweep.

The accepted outer planes, ribs and serrations are retained. Armor gains inward thickness, with thin mating rims and beveled transitions at closely fitted edges. Dorsal side leaves lift 0.30 source units for clearance, then use their previous outboard/downward endpoints. The fore cavity's rear-facing and inward side faces are now deep red; exterior gray paint remains gray.

The continuous v0.8.9 bore motion is unchanged. All articulation is still authored by Nuxt/Three.js. The original `odin.blend` is unchanged; editable geometry is saved separately as `assets/blender/odin_articulated_v0.8.10.blend`.

- [Complete unfolding/folding preview](main-battery-preview.mp4), H.264, 1280 × 720, 437 decoded frames.
- [Twelve-frame sequence](main-battery-sequence.png).
- [Closed side view](side-closed.png), [junction detail](junction-closeup.png), [red fore interior](interior-open.png), [hinge midstroke](hinge-midstroke.png).
- [Armor/gun and armor/armor clearance](main-clearance.json): 101 actual JS poses, 30 pairs per pose, zero collisions.
- [Fixed hull sweep](hull-sweep.json): all ten leaves and the new fixed receivers, 101 poses, zero collisions.
- [Physical fit](physical-fit.json): planar aft faces, hinge endpoints on actual mesh vertices, finite thickness, correct parentage, and original-source checksum.
- [Animation provenance](animation-preview.json) and [geometry construction report](geometry-build.json).

Validation: `npm test` (25 tests), `npm run verify:asset` (both GLBs contain zero animation clips), and `npm run generate`. Tests cover main batteries, secondary mounts, PDC/quad arms, defense mounts, bridge armor, reverse scrubbing, explicit pause persistence, and engine interlocks. Browser verification uses the PC high-quality asset.

This is a fan-art reconstruction; the supplied user annotations guide the local junction corrections.
