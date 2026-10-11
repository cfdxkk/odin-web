# Complete forward twin turret lift

Forward twin turrets 1–4 previously translated the white hull hoods and
lifted only the upper gun by two extra source units. The lower armored
cradle, support brackets and guides stayed at the former height. The
hoods are now fixed at their original frame-30 outboard positions, matching
the marked review image. Each complete gun and lower cradle slides from a
4.6-unit lower stowed seat before rising to the old lift's starting height.
The original turret rest origin Z is 52.274616; no additional upper lift
remains. Closing neutralizes aim, lowers the assembly, then slides it inward
under the fixed hood. The shared guides have the same vertical stroke.

All original accepted rail faces, materials and UVs are partitioned exactly
once into the fixed hoods, lower cradles and remaining guides. The hood
surfaces match untouched `odin.blend` frame 30 within 0.00003 source units.
Raised turret origins match source frame 15. A few inherited evaluated
bearing seam vertices differ from the raw original by up to 0.1503 units;
their accepted coordinates and faces are preserved without deformation.
All 530 other native meshes and all 207 static joint transforms are
unchanged. Only four carriage and two rail motion metadata records change.
Editable geometry is saved in `assets/blender/odin_articulated_v0.11.38.blend`.

`mesh-clearance.json` checks 416 actual runtime poses per turret, including
reverse travel and scan endpoints. There are no turret-to-fixed-hood or
upper-gun-to-guide contacts. The original lower bracket/guide mating
surfaces retain their contact relationship. Removing the lowered seat
produces hood intersections on all four turrets, confirming that the
clearance check rejects the old height. A separate comparison verifies
that all 193 unaffected joints have identical world matrices across 303
deployment/time samples.

Validation: 65 tests, asset verification and static generation pass. Both
GLBs contain zero animation clips. Browser checks cover all four forward
twins in oblique, side and overhead views, forward and reverse seeks, plus
main, secondary, aft defense, bridge quad/PDC and bridge armor endpoints.
Explicit pause and idle rendering are checked. `asset-hashes.json` binds
the evidence to the native and exported models; `browser-check.json`
records the rendered review. The temporary checking browser is closed,
leaving one paused user preview and one static preview service.

To reproduce the source proof, open the v0.11.38 native file in background
Blender and run `tools/verify_forward_twins_v01138.py`. To reproduce the
clearance sweep, first run
`node --experimental-strip-types tools/sample_forward_twins_v01138.mjs`,
then open the same native file in background Blender and run
`tools/audit_forward_twins_v01138.py`. Use two Blender threads. To rebuild,
open v0.11.37 and run `tools/rebuild_forward_twins_v01138.py`, then export
the saved v0.11.38 native file with `tools/export_articulated_asset.py`.
