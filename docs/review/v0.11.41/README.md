# Bridge quads: synchronized armor release and shorter center packing

The four quad tubes previously used the cradle packing curve while their
nearby armor used its square. At intermediate deployment the tubes were
therefore packed much farther inward than the armor. Each complete source
tube, bearing and fork now reads its own armor joint's packing clock.
The four-way tube stroke is shortened from 2.00 Y / 0.30 Z to 1.95 Y /
0.33 Z in Blender coordinates; the small vertical adjustment clears the
original fitted skins throughout release. The long gray guides retain
their accepted net 0.60 Y travel.

Armor and transverse tube release run together over 3%–18%. Axial tube
extension then runs over 20%–56%. Reverse travel withdraws the tubes before
the armor and bearings compact. The accepted axial travel of
14.40237037037037 source units, source frame-30 carriage seat, original
aiming curves, armor-only translation and ship-X lock are retained.

`tube-spacing.json` compares 181 intermediate poses per side with
v0.11.40. Fore/aft tube pair separation is wider or unchanged throughout
release, and both transverse spacings are wider from 8% to full release.
At 10% the fore/aft separation increases from 5.16934 to 5.80653 units.

All 550 editable meshes, materials, UVs and 215 static rest frames remain
identical to v0.11.40. Only 24 quad joint properties change. All 191 other
joint trajectories match the previous runtime at 303 sampled poses.
The original `odin.blend` remains unchanged. The new editable version is
`assets/blender/odin_articulated_v0.11.41.blend`; both GLBs contain zero
animation clips.

`mesh-clearance.json` audits 442 actual Nuxt poses per side, including
reverse seeks. It checks tube/armor, tube/tube and adjacent complete
bearing/fork surfaces, shared transverse progress, delayed axial travel,
unchanged closed armor edges, hull roof fit and hidden tube tips.
All checked pairs are clear. Armor vertex X and armor rotation remain
constant. `source-geometry.json` and `asset-hashes.json` bind the evidence
to the saved native and final exports.

Rebuild from the saved v0.11.40 native with
`tools/synchronize_bridge_quads_v01141.py`, then export with
`tools/export_articulated_asset.py`. Capture runtime poses with
`tools/sample_bridge_quads_v01141.mjs` and run
`tools/verify_bridge_quads_v01141.py` and
`tools/audit_bridge_quads_v01141.py` in two-thread background Blender.

Validation: all 70 tests, `npm run verify:asset` and `npm run generate`
pass. Browser review covers both quad turrets in four views with forward
and reverse seeks, plus main, secondary, twin/defense, PDC and bridge armor
endpoints. Explicit pause and idle rendering are checked. The temporary
checking browser is closed after review; the user preview remains paused.
