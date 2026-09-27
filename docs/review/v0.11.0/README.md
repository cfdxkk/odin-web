# v0.11.0 — four vertical flank batteries

Only port/starboard batteries **1 and 3** receive the new mechanism. Sloping flank 2/4, axial singles, mains, defense/PDC and bridge retain the preceding candidate. The original `odin.blend` is unchanged.

## Result

- Four mirrored armor groups per mount. The new first pair is an unequal-ended trapezoid and lifts before sliding forward. The two old legacy tip wings are removed.
- The three source grate pairs fold about their measured inner attachment rails. Their outer backing is continuous hull paint; the grate detail stays inside. Groups 2/3/4 each expose 8.70 source units in the closed pose.
- All adjacent sloping seams use the same rake. The seams across each flat crown are straight across both halves, without a center V.
- The complete original outer pedestal, trough, bearings, barrel, rear trunnion and groups 3/4 belong to the same carriage. Closing folds the leaves, raises the carriage, then advances it 2.08 source units to the mating diagonal edge. The gun pitches only after the covers clear.
- Infill is limited to the marked triangular bay break and its mirrored counterpart. The small aft-pedestal triangular recesses are capped on their existing rim. There is no full-bay overlay.
- The aft first pair may park inside the hull as explicitly requested. Its motion matches the forward mechanism.

## Verification

`npm test`: **33 passed**. `npm run verify:asset` and `npm run generate`: passed. Both GLBs contain zero animation clips. The editable asset and exports are recorded in [validation.json](validation.json).

101 actual JavaScript poses sampled from the exported rig have zero reported contacts for barrels versus covers, groups 2/3, groups 1/2, covers versus local infill, and forward sliders versus fixed hull. This is a scoped triangle-surface check, not a claim that every part of the ship is collision-free. Aft slider/hull contact is deliberately excluded because its parking overlap is authorized. See [contact summary](side-contact-summary.json).

[Surface audit](surface-audit.json) checks that all 24 original detailed leaves stay beneath the continuous outer skin. [Scope audit](scope-audit.json) verifies 506 unaffected objects and preserves all source faces transferred from the two shared hull/pedestal meshes, with maximum rest-position vertex error below 0.000011 source units. The source `odin.blend` SHA-256 remains `9ec8b6ee36e6315c7c0cae8576472879518cc5bf48b79382c2affbcbd71af15e`.

The browser review covers all four affected mounts in NAV and SCM, intermediate carriage/folding poses, plus upper/lower mains, the bridge quad gun, aft defense gun and bridge. No browser console errors were observed. Local preview: `http://127.0.0.1:4173/?review=secondary`.

## Browser captures

| Mount | Closed | Open |
| --- | --- | --- |
| Forward starboard | [NAV](starboard-forward-closed.png) | [SCM](starboard-forward-open.png) |
| Forward port | [NAV](port-forward-closed.png) | [SCM](port-forward-open.png) |
| Aft starboard | [NAV](starboard-aft-closed.png) | [SCM](starboard-aft-open.png) |
| Aft port | [NAV](port-aft-closed.png) | [SCM](port-aft-open.png) |

[Carriage stage](port-forward-carriage.png) · [Folding stage](port-forward-folding.png)

## Reproduction

Run `revise_side_batteries_v0110.py` on the v0.10.0 blend, then `refine_side_edges_v0110.py` once on the newly generated v0.11.0 blend. Export using `export_articulated_asset.py`. Animation remains entirely in `app/lib/odin-rig.ts`; Blender stores only geometry, materials and static joints.

For the pose sweep, run `node tools/review_secondary_poses.mjs 0.11.0 --exported`, then run `check_side_batteries_v0110.py` against the v0.11.0 blend. Run the surface and scope audit scripts against the same blend; the scope audit first needs a v0.10.0 run with `-- --snapshot`.
