# Bridge quads: restore original motion and reduce tube center packing

The requested revision returns both bridge quad turrets to the v0.11.40
effect. Armor paths and fitted endpoints, original frame-30 carriage seat,
aiming, tube axial travel and its 3%–18% interval are unchanged from that
baseline. The rejected shared-path prototype is not included.

Only transverse tube packing changes. Its fore/aft endpoint is slightly
shorter (1.98 instead of 2.00 source units). Once the existing armor clears
the tube corridor, 12%–15% deployment smoothly reduces the remaining
packing amount by up to 60%. This is a reduction along the existing path;
it never increases original packing or introduces another direction or
rotation. Source gray bearings remain rigidly attached to the tubes. Long
guides compensate to retain their original net 0.60 fore/aft endpoint.

`tube-spacing.json` compares actual tube mesh bounds at 181 poses per side,
including every intermediate pose in the release interval. It uses the
mesh centers, not the shared joint origins. Neither transverse spacing
becomes narrower. At 14%, fore/aft separation grows from 6.58869 to 7.44113
source units (about 13%); upper/lower separation grows from 2.92896 to
3.05525. Fully deployed tube positions remain identical to the baseline.

All 550 source meshes, materials, UVs, hierarchy and 215 static rest frames
are identical to v0.11.40. Only 16 cradle/guide motion metadata records
change; all 199 other joint metadata records, including all eight tube
axial records and all armor records, remain unchanged. The other 191 joint
world trajectories match the old runtime exactly at 303 sampled poses.
The original `odin.blend` remains unchanged. Editable native source is
`assets/blender/odin_articulated_v0.11.42.blend`; GLBs have zero animation
clips, and Nuxt/Three.js authors all movement.

`mesh-clearance.json` checks 442 actual runtime poses per side, including
reverse seeks. Tube/armor, tube/tube and adjacent complete bearing/fork
surfaces are clear. It also verifies unchanged axial timing and reach,
fixed ship-X armor coordinates, zero armor rotation, fitted closed edges
and the adjoining hull roof plane. `source-geometry.json` and
`asset-hashes.json` bind this evidence to the saved native and exports.

Rebuild from v0.11.40 with `tools/limit_bridge_quad_packing_v01142.py` and
export with `tools/export_articulated_asset.py`. Capture Nuxt poses with
`tools/sample_bridge_quads_v01142.mjs`, then run
`tools/verify_bridge_quads_v01142.py` and
`tools/audit_bridge_quads_v01142.py` in two-thread background Blender.

Validation: all 71 tests, `npm run verify:asset` and `npm run generate`
pass. Browser review covers both quads in four views with forward/reverse
seeks and playback, plus main, secondary, twin/defense, PDC and bridge
armor endpoints. Explicit pause and idle rendering are verified. The
temporary checking browser is closed; only the user preview is kept.
