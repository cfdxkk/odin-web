# v0.11.1 — flank cradle and surface corrections

Scope remains the four vertical port/starboard batteries **1 and 3**. This candidate builds on v0.11.0; the original `odin.blend` stays unchanged.

- The source rear pedestal, bearings, gun and armor groups 3/4 move together. The separately extracted deep bay floor and transition returns now stay on the hull, outside the user's marked moving outline.
- All four complete bores are centered on their measured channel plane, with their rear pitch pivots on the same axis. The two aft guns no longer rest approximately 13.2 degrees inward: all four stow parallel to the channel.
- The small triangular transition gaps receive local closure. The front nose openings use the original boundary vertices and the lower inner-slot nose plane, removing the triangular depression and fold. The old raised wing lip is not restored.
- All 24 original inner grate meshes use the red primer material, including their stiffeners and frame returns. The existing exterior backing stays hull gray.
- The aft first sliders have a short folded end returning inward/down onto the original lower slot rim identified by the user's marked line. Their leading-edge rake is approximately 1.481; they no longer extend toward the larger outer hull surround. Each roof and return face is planar, and the rear seam and lift/slide motion are retained.
- Equal armor lengths, matching inclined seams, straight crown seams, lift/slide sequencing and the authorized aft-slider parking overlap are retained.

## Validation

`npm test`: **34 passed**. `npm run verify:asset` and `npm run generate`: passed. High/lite exports have zero animation clips.

The [geometry audit](geometry-audit.json) verifies 508 objects outside the revised assemblies are unchanged, 12 fixed bay structures have zero motion across 101 actual JavaScript poses, the actual four bores are centered and parallel to their slots, and each nose infill is coplanar with its lower inner-slot facet. Each aft return's actual bottom edge coincides with the original lower-rim vertices; the roof and return faces are planar. The [contact sweep](side-contact-summary.json) checks barrels against armor, adjacent groups, local fairings and forward sliders against hull. Aft slider/hull parking overlap remains intentionally allowed; this is not a global collision-free claim.

Browser review covers all four revised mounts in NAV/SCM and intermediate poses, plus main batteries, defense/PDC, bridge quad arms and bridge structures. Local preview: `http://127.0.0.1:4173/?review=secondary`.

| Mount | Closed | Open |
| --- | --- | --- |
| Forward starboard | [NAV](starboard-forward-closed.png) | [SCM](starboard-forward-open.png) |
| Forward port | [NAV](port-forward-closed.png) | [SCM](port-forward-open.png) |
| Aft starboard | [NAV](starboard-aft-closed.png) | [SCM](starboard-aft-open.png) |
| Aft port | [NAV](port-aft-closed.png) | [SCM](port-aft-open.png) |

[Aft bore parallel to slot](starboard-aft-parallel.png) · [Forward bore parallel to slot](port-forward-parallel.png) · [Carriage stage](starboard-aft-carriage.png)

[Close-up of the folded end seated on the lower inner rim](aft-inner-rim-closeup.png) is a native Blender geometry render of the same closed pose. [Validation and file hashes](validation.json) record the final candidate.

## Reproduction

Run `revise_side_batteries_v0111.py` once against v0.11.0, then export the saved v0.11.1 blend using `export_articulated_asset.py`. The reconstruction reads the earlier v0.10.0 cap as a library to recover its boundary vertices without changing it. Animation remains in `app/lib/odin-rig.ts`.

Run `node tools/review_secondary_poses.mjs 0.11.1 --exported`, then `check_side_batteries_v0111.py` against v0.11.1. Run `audit_side_batteries_v0111.py` first against v0.11.0 for its baseline, then against v0.11.1 for the comparison.
