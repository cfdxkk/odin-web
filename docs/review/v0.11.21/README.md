# v0.11.21-rc.1 — axial armor seams and fixed keel bay

The stern foremost plate's center opening is reduced from 0.345 to 0.242 source model units. Its outer contour, topology and travel remain unchanged. The stationary slot walls extend along their measured original six-point lower profile to the hinged covers, including the low section next to the breech.

Six disconnected bow outboard skirts are removed. The receiver floor, fifteen bore supports, raised muzzle lip and existing seven-cover mechanism are retained.

The complete keel bay is fixed at the **v0.11.20 deployment 14%** carriage position. The exact pre-change world transform is recorded in `tests/fixtures/keel-locked-mount-v01121.json`; no whole-bay translation remains in the web rig. Six accepted flank-derived stern leaves and the original-source stern nose shell are fitted to the keel. The nose lifts during 0–8%, then slides during 10–25%. The six leaves open in the stern order with a 95° sweep and finish by 64%, before the existing barrel lift. Inward armor, ribs and channel faces are red. The foremost crown meets the original keel receiver with a 0.02 source-unit seam.

The original bow and stern barrel motion is unchanged. The source `odin.blend` and `odin_with_anime.blend` files are unchanged; the revised editable model is `assets/blender/odin_articulated_v0.11.21.blend`. Both GLBs contain zero animation clips.

## Verification

- `npm test`: 45 passing. Includes the saved old 14% keel transform across forward/reverse progress, matched stern/keel leaf timing and angles, lift-before-slide, and the original bow/stern action fixtures.
- `npm run verify:asset`: high and lite GLBs, static joints, zero clips, six fitted keel leaves, gray exteriors and red inner materials.
- `npm run generate`: successful static build.
- `tools/check_axial_fit_v01121.py`: saved closed leaves match the stern template within 0.0001 source units; the keel hull vertices are unchanged; 812 unrelated mesh geometries/materials and 179 other joint transforms are preserved. Original file fingerprints and seam measurements are in [geometry-audit.json](geometry-audit.json).
- Desktop browser: 55 saved cases covering closed, intermediate, deployed and reverse poses for all three axial bays; both main batteries, all flank singles, all defense twins, both bridge quad/PDC mounts, and fixed bridge armor. Zero console errors. See [browser-checks.json](browser-checks.json).

## Rendered views

| Inspection | View |
| --- | --- |
| Stern stationary walls and shutter seam | [Closed oblique](stern-closed-oblique.png) · [Side](stern-closed-side.png) |
| Stern foremost plate center seam | [Nose detail](stern-nose-seam-detail.png) |
| Bow floating skirts removed | [Closed oblique](bow-clean-oblique.png) · [Open](bow-clean-open.png) |
| Keel old assembly reference | [v0.11.20 at 14%](keel-before-14.png) |
| Keel fixed seat, closed armor | [Closed](keel-closed-first.png) · [Bottom view](keel-closed-top.png) |
| Keel nose release sequence | [Lift 8%](keel-nose-lift-08.png) · [Advance 25%](keel-nose-forward-25.png) |
| Keel six folding covers | [40%](keel-opening-40.png) · [64%](keel-open-64.png) |
| Keel exposed red channel and deployed barrel | [Deployed](keel-deployed.png) |
| Additional intermediate clearance checks | [Stern 40%](stern-folding-40.png) · [Stern 52%](stern-folding-52.png) · [Keel 53%](keel-folding-53.png) |

Review tag: `v0.11.21-rc.1`. This revision targets `main` and builds on PR #41.
