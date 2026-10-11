# v0.11.2 — vertical flank armor fitted to the original slot

This revision corrects all four vertical flank batteries, port and starboard **1 and 3**. It starts from the editable v0.11.1 asset; the original `odin.blend` and the upper sloping batteries 2/4 are unchanged.

The v0.11.1 smooth armor skins stood roughly 0.8–1.2 model units proud of the original inner-slot facet. Their first-plate leading edges also stopped above and outside the lower rim; an added folded return hid some of that mismatch. The actual visible skins now follow the broad original inner-slot facet. Their flat crowns and outer boundaries are measured from the source hull, with the first plate's long edge passing through the original rail stations and its front edge meeting the original lower rim. The folded return is gone. This closes the forward two mounts' long wedge gap without covering the surrounding bay cheek.

The existing detailed grates and stiffeners remain on the inner face and retain their red primer. They were reshaped with the new roof so none protrudes through the smooth gray exterior. All four centered barrels remain parallel to their slots in NAV; while stowed, each settles farther inboard to clear the lower roof, then returns to its accepted SCM firing location. The first sliders lift farther before the forward stroke so they clear the surrounding hull after releasing their closed seal. The rear pedestal and groups 3/4 still translate as a single assembly.

| Mount | Closed, viewed from behind | Open, side view |
| --- | --- | --- |
| Starboard 1 | [Front contour](front-rear-closed.png) | [Red inner grates](front-side-open.png) |
| Starboard 3 | [Aft contour](aft-rear-closed.png) | [Red inner grates](aft-side-open.png) |

The port geometry is measured independently from its own source facets and was inspected in the browser in NAV. The geometry and scope audit reports 508 unchanged objects outside the four mounts, maximum visible roof-to-source-plane deviation below 0.002 units, and maximum first-plate front-rim mismatch of 0.000011 units. All 24 red interior grate meshes sit at least 0.40 units behind the new exterior. The original `odin.blend` SHA-256 remains `9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e`.

`npm test` passed 34 tests. `npm run verify:asset` passed both high and lite GLBs with zero animation clips, and `npm run generate` passed. The [101-pose contact sweep](side-contact-summary.json) found no gun/armor, adjacent leaf, or local fairing intersections. It records 10 first-plate/source-rim contacts at the fully seated pose and the first 1% of its lift; no first-plate/hull contacts remain later in the motion. The intentionally allowed aft-slider parking penetration is outside the forward-slider hull check. The [geometry audit](geometry-audit.json) gives the measured fits for all eight armor halves.

To rebuild, run `tools/refit_flank_armor_v0112.py` once with `odin_articulated_v0.11.1.blend` open in Blender 5.1. It writes `assets/blender/odin_articulated_v0.11.2.blend`. Export that file with `tools/export_articulated_asset.py`, sample the Three.js poses with `node tools/review_secondary_poses.mjs 0.11.2 --exported`, then run `tools/audit_flank_armor_v0112.py` (baseline first against v0.11.1) and `tools/check_side_batteries_v0112.py` against v0.11.2. Animation remains authored in Nuxt/Three.js; the GLBs contain only geometry, materials, textures and static joints.
