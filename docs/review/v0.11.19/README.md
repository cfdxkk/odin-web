# v0.11.19 axial armor and bore-channel review

The stern foremost **moving** plate is the complete, detached 66-face armor
shell already present in the untouched `odin.blend/holo.001`. It remains in its
source position when the gun is deployed and slides into the nose opening when
stowed. The eight triangular fixed-hull faces incorrectly animated as the
plate in v0.11.18 no longer ride the front-cap joint. The duplicate static
vented leaves are removed; the original stationary roof is restored.

The stern six shutter leaves keep their fitted closed seams and now stop after
a 95-degree opening sweep, short of the rear hull. The original bow and stern
barrel geometry and source keyframe positions are unchanged. Both barrel
actions remain authored in Nuxt/Three.js.

The bow receiver bore opening extends two model units toward the muzzle. Its
foremost plate has a sloping end seam, and its crown is seated against the
fixed receiver roof. The fixed inward faces of the bow and eight side-gun
channels use the existing deep-red interior paint. Gun mounts and other
equipment inside those channels keep their separate materials.

The versioned editable file is
`assets/blender/odin_articulated_v0.11.19.blend`; the source `odin.blend` was
read only. Both exported GLBs contain zero animation clips.

Browser images:

- [Stern plate in its original deployed position](stern-deployed-oblique.png)
- [Stern plate fitted when closed, oblique](stern-closed-oblique.png)
- [Stern plate fitted when closed, side](stern-closed-side.png)
- [Stern shutter motion](stern-folding-side.png)
- [Bow inclined nose seam](bow-closed-side.png)
- [Bow bore clearance at 38%](bow-transition-038-oblique.png)
- [Side-gun red channel](flank-deployed-oblique.png)
- [Bridge quad](bridge-quad-deployed-oblique.png),
  [aft twin](aft-twin-closed-oblique.png),
  [keel single](keel-closed-oblique.png), and
  [main battery](main-closed-oblique.png) regression views

Validation: `npm test` (45 passing), `npm run verify:asset`,
`npm run generate`, and the linked browser views.
