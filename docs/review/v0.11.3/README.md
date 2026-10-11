# v0.11.3 — four vertical flank armor contact hinges

This revision is confined to the port and starboard vertical flank batteries **1 and 3**. The v0.11.2 lower edges and first-plate forward rims correctly met the original inner slot, but its roof projection pulled the flat crowns about 0.8 model units too far into the hull. All eight armor halves now span from those measured lower rails to the accepted flat crown height. The first pair tapers into the original front lip. The outside stays smooth and hull-painted; the grates are recessed and red on the inside.

The 24 hinged second, third and fourth plates were also rotating around an axis displaced from their attachment edges. Each joint is now positioned on the two actual outer-edge vertices of its fitted backing in the closed pose. The open geometry was re-authored from that fixed closed shape, so the plate's attachment edge remains stationary through the fold. Each leaf travels 150 degrees; this fully exposes the bay without hitting the fixed triangular fairings. The rear cradle, barrel, and groups 3/4 still move together after the leaves fold. The first pair still lifts and slides toward the bow.

Each sheet below shows **NAV, 48% transition, and SCM** in rows, from **side, upper, lower, and rear** in columns:

| Mount | Twelve-view sheet |
| --- | --- |
| Starboard 1 | [Front starboard](front-starboard-matrix.png) |
| Port 1 | [Front port](front-port-matrix.png) |
| Starboard 3 | [Aft starboard](aft-starboard-matrix.png) |
| Port 3 | [Aft port](aft-port-matrix.png) |

The [independent mesh audit](geometry-audit.json) measures the actual exterior edge against each hinge axis, rather than comparing joint metadata alone: maximum deviation is **0.000018 model units** across all 24 hinges. Flat-crown height error is at most **0.000024** units, and each first-plate front rim remains within **0.000011** units of its original seat. All 24 red interior grates remain at least **0.4027** units below their exterior roofs. The other **508 objects** are unchanged from v0.11.2, and the original `odin.blend` SHA-256 remains `9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e`.

`npm test` passes 34 tests; `npm run verify:asset` validates both exported GLBs with **zero animation clips**; `npm run generate` succeeds. The [101-pose sweep](side-contact-summary.json) reports no gun/armor, adjacent leaf, or armor/fairing intersections. Its ten first-plate/source-rim contacts occur only at the fully seated pose or the first 1% of lift. In the browser, all four mounts were inspected halfway through folding; front and aft mounts were checked in NAV, and the main battery, bridge quad, defense/PDC and bridge structure were also checked.

To reproduce the model and audit, open the committed v0.11.2 editable file in Blender 5.1 and run `tools/refit_flank_armor_v0113.py`. Export the resulting `assets/blender/odin_articulated_v0.11.3.blend` with `tools/export_articulated_asset.py`. Generate actual Three.js poses using `node tools/review_secondary_poses.mjs 0.11.3 --exported`, then run `tools/check_side_batteries_v0113.py` and `tools/audit_flank_armor_v0113.py` against v0.11.3. For the unchanged-object baseline, run the audit once against v0.11.2 first. The matrix images come from `tools/render_flank_multiview_v0113.py` and `tools/make_flank_multiview_sheets_v0113.py` after pose sampling. Animation remains in Nuxt/Three.js; the GLBs store static joints, geometry, materials and textures only.
