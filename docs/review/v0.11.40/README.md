# Forward twins: stationary lower foundations and constant cradle heading

The independent lower foundation under each forward twin is now fixed to
the hull. These are original `holo.011` islands 71 (turrets 1/3) and 70
(turrets 2/4), each with 140 vertices and 145 faces. Only their attachment
changes. Partitioned source faces, materials and UVs are retained exactly
once; the remaining upper housing, lower shoe, supports and guides keep
their accepted movement.

The former 65%–85% cradle alignment turn is removed. Centering now uses one
constant installation direction throughout deployment and reverse travel.
The whole moving cradle follows the same short inclined translation as
v0.11.39, along the actual stationary foundation plane. After seating,
the tubes still retract an additional five source units horizontally;
their rear brackets remain on the turret.

`source-geometry.json` verifies the exact source partition, stationary
foundation placement and ramp tangency. All 542 other native meshes and
215 existing static joint rest transforms are unchanged. The original
`odin.blend` remains untouched. Editable geometry is committed in
`assets/blender/odin_articulated_v0.11.40.blend`; both GLBs have zero clips.

`mesh-clearance.json` samples 416 actual runtime poses for each turret,
including reverse seeks and scan endpoints. It checks constant foundation
world transforms and cradle heading, fixed hood clearance, and absence of
upper gun/guide/foundation contacts. Lower shoe/foundation contacts, also
present at the source endpoint, are recorded separately as support
engagement rather than deleting the original connecting surfaces.
`other-motion.json` compares all 193 unaffected joints at 303 samples.

Browser review includes all four forward twins in front, oblique, side and
overhead views, both directions, plus main, secondary, aft defense,
bridge quad/PDC and bridge armor endpoints. It also verifies explicit
pause and idle rendering. The temporary checking browser is closed after
review; only one paused user preview and one preview service remain.

Rebuild from the saved v0.11.39 native file with
`tools/fix_forward_twin_foundations_v01140.py`, then export with
`tools/export_articulated_asset.py`. Sample actual runtime poses with
`tools/sample_forward_twins_v01140.mjs`, and run
`tools/verify_forward_twins_v01140.py` and
`tools/audit_forward_twins_v01140.py` in two-thread background Blender.

Validation: all 69 tests, `npm run verify:asset` and `npm run generate` pass.
Browser observations and current native/high/lite hashes are recorded in
`browser-check.json` and `asset-hashes.json`.
