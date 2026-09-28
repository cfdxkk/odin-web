# v0.11.4 — vertical flank armor closed line and lower nose fit

This candidate changes only the four **vertical** flank singles, port and starboard 1 and 3. In v0.11.3, the second through fourth armor groups were higher than the first plate's hull receiver. The first plate therefore climbed from the receiver to those groups, making a visible diagonal transition when closed. This revision lowers groups 2–4 to the measured front receiver crown (2.8667 model units on the forward mounts; 2.6055 on the aft mounts) and flattens each first slider crown to the same height. The exterior contact edges now share one straight plan-view rail per side. The resulting closed four-plate line is continuous in the upper views below.

The lower-nose triangular slit is filled on the original **lower inner-slot panel** with a separate fixed triangle sampled from that panel's source vertices. It is not attached to the upper fairing. The existing first-plate front seat remains unchanged. All 24 folding leaves were rebaked around their actual outer contact edges after the contour edit; their red inner grates remain below the smooth exterior skins. The rear pedestal and gun still travel with groups 3 and 4.

Each matrix shows NAV closed, 48% opening, and SCM deployed as rows; side, upper, lower, and rear views as columns. These are actual Three.js rig poses applied to the editable Blender geometry. Workbench lighting is for checking surfaces and seams; no animation clips are exported.

| Mount | Multi-angle review |
| --- | --- |
| Starboard 1 | [Forward starboard](SideBattery_1_Starboard-matrix.png) |
| Port 1 | [Forward port](SideBattery_1_Port-matrix.png) |
| Starboard 3 | [Aft starboard](SideBattery_3_Starboard-matrix.png) |
| Port 3 | [Aft port](SideBattery_3_Port-matrix.png) |

The [mesh audit](geometry-audit.json) found a maximum first-plate crown-height error of **0.0000037**, a maximum plan-view outer-rail error of **0.0000078**, and a maximum actual armor-edge-to-hinge-axis error of **0.0000137** model units. The new lower triangles use original lower-panel vertices exactly. The first-plate front rims remain within **0.000011** units of their previous hull seats, and all red inner grates stay at least **0.4027** units beneath the roof. The other **508 objects** are unchanged from v0.11.3. The original `odin.blend` SHA-256 is unchanged (`9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e`).

The [101-pose collision sweep](side-contact-summary.json) found no gun/armor, adjacent group, or armor/fairing intersections. The ten recorded first-plate/source-rim contacts are the expected seat contact at 0–1% of opening. `npm test` passed 34 tests, both GLBs passed `npm run verify:asset` with **zero animation clips**, and `npm run generate` succeeded. The updated high-detail model was also checked in the browser at NAV and 50% for the changed mounts, including upper, side, and angled views.

To reproduce, open the committed v0.11.3 editable file in Blender 5.1 and run `tools/refine_flank_contour_v0114.py`. Export the resulting `assets/blender/odin_articulated_v0.11.4.blend` with `tools/export_articulated_asset.py`. Generate the actual Three.js poses with `node tools/review_secondary_poses.mjs 0.11.4 --exported`, then run `tools/check_side_batteries_v0114.py`, `tools/audit_flank_armor_v0114.py`, `tools/render_flank_multiview_v0114.py`, and `tools/make_flank_multiview_sheets_v0114.py`. The last script needs Pillow. Animation remains in Nuxt/Three.js; the GLBs carry only geometry, materials, textures, and static joints.
