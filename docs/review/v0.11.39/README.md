# Forward twin turrets: shorter inclined stow

Turrets 1–4 now retract inward and downward together along their measured
original lower cradle ramps. Horizontal travel is 3.3 source units; descent
is 2.464–2.467 units, at approximately 36.75 degrees. The former movements
travelled almost ten units inward and descended 4.6 units in a separate
phase. The deployed height remains the accepted original rest height.

Closing neutralizes aim, aligns the complete cradle with the fixed receiver,
then moves the upper housing, lower supports and guides together during
progress 64%–24%. After the cradle seats, only the original tube surfaces
withdraw five more units horizontally during 22%–4%. Their original rear
elevation brackets remain on the turret. Opening reverses those steps.
The source guide heading is preserved while the cradle centers; there is no
additional descent during the barrel-only stroke.

Original guide and tube faces, materials and UVs are partitioned exactly
once. Each tube contains 9,882 source vertices; its retained rear brackets
contain 3,698. All 530 other native meshes and all 207 existing joint rest
frames remain unchanged. The four fixed white receiver lips receive local
surface cuts around separate original-component sweeps with a 0.04-unit
margin. Their central canopy surfaces match the original at 49 samples per
turret within 0.000006 units, and their original height is unchanged. The
untouched original `odin.blend` SHA-256 remains
`9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e`.
Editable geometry is saved in `assets/blender/odin_articulated_v0.11.39.blend`.

`mesh-clearance.json` checks 416 actual runtime poses for each turret,
including reverse travel and scan endpoints. There are zero receiver or
upper-gun/guide contacts. Removing the descent produces receiver contacts
on all four turrets, so the check rejects a horizontal-only carriage path.
`source-geometry.json` verifies source preservation, roof geometry and
measured ramp tangency. `other-motion.json` compares all 193 unaffected
joints at 303 deployment/time samples, with zero world-matrix difference.

Validation: 67 tests, asset verification and Nuxt static generation pass.
Both GLBs contain zero animation clips. Browser checks cover the four
forward twins in oblique, side and overhead views through both directions,
plus main, secondary, aft defense, bridge quad/PDC and bridge armor
endpoints. Basic 390-pixel layout, explicit pause and idle rendering pass.
`asset-hashes.json` binds the evidence to the saved native/high/lite files;
`browser-check.json` records the review. The temporary checking browser is
closed, with no background Blender jobs. One paused user preview and one
static preview service remain.

To reproduce, run `tools/sample_forward_twins_v01139.mjs` with Node's type
stripping enabled, then run `tools/verify_forward_twins_v01139.py` and
`tools/audit_forward_twins_v01139.py` in background Blender on the saved
v0.11.39 file. To rebuild, sample the committed GLB joint poses first, open
v0.11.38 and run `tools/rebuild_forward_twins_v01139.py`, then open its
saved v0.11.39 file and run `tools/fit_forward_twin_receivers_v01139.py`.
Export that file with `tools/export_articulated_asset.py`. Use two Blender
threads and run the native jobs sequentially.
