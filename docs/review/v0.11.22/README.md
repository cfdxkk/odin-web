# v0.11.22-rc.1 — stern and keel cover edge fit

The stern moving nose cover was approximately 13% wider than its adjacent folding leaves, with a 0.242-unit center slit. It now follows their 4.92-unit width and 0.030-unit center seam. The keel equivalent follows its 4.596-unit leaf width and 0.028-unit seam. Both retain the original 56-vertex, 66-face source shell topology and rolled edge detail.

The complete leading diagonal, including the crown, crease and outside corner, is fitted to the original stationary receiver with a 0.020-unit longitudinal seam. Six missing fixed keel support faces are recovered directly from the untouched `odin.blend` `holo.022` object. This closes the former triangular opening under the keel nose cover. The existing stern fixed support and both hull meshes remain unchanged.

All six folding leaves in each bay share a straight outer line, flat crown strip and continuous neighboring edges. Their rear crown edges meet the unchanged gun-root housings instead of retaining the artificial 0.8-unit retreat. Original flank grate detail and red inner materials remain. The cap still lifts before sliding; the leaves retain their existing 95-degree travel and timing.

The keel remains at the accepted former **14% whole-assembly position**. All 187 joint transforms, the entire web animation rig, original bow/stern barrel actions and 812 unrelated mesh geometries/materials are unchanged. The two original source Blender files are unchanged. Editable geometry is saved as `assets/blender/odin_articulated_v0.11.22.blend`; both exported GLBs contain zero animation clips.

## Validation

- `npm test`: 45 passing, including original barrel action fixtures, the fixed keel seat, cover sequencing and reverse scrubbing. The fitted cap checks cover all three receiver corners and the adjacent leaf width.
- `npm run verify:asset`: high/lite assets valid, 176 meshes, 20 materials, 12 embedded textures, zero clips.
- `npm run generate`: static build successful.
- `tools/check_axial_fit_v01122.py`: measures actual saved mesh vertices, rather than only joint metadata. Neighboring roof edges agree within 0.000017 model units; cap profile corners within 0.000004. Restored keel support agrees with the original file within 0.000005. Unchanged mesh hashes, transforms and source-file fingerprints are recorded in [geometry-audit.json](geometry-audit.json).
- Desktop browser: 61 scripted poses and two enlarged closed details. Closed, lifting, advancing, opening, deployed and reverse poses reviewed in the rendered high asset. Both main batteries, eight flank singles, eight defense twins, both bridge quad/PDC mounts and fixed bridge armor rechecked. Zero browser console errors. See [browser-checks.json](browser-checks.json).

## Rendered inspection

| Area | Closed fit | Open fit |
| --- | --- | --- |
| Stern nose and shutters | [Width and center seam](stern-closed-detail.png) · [Complete receiver diagonal](stern-fit-closed.png) | [Covers open at 64%](stern-fit-open64.png) · [Original barrel deployed](stern-fit-deployed.png) |
| Keel nose and shutters | [Center seam and restored nose support](keel-closed-detail.png) · [Side receiver fit](keel-fit-closed.png) | [Covers open at 64%](keel-fit-open64.png) · [Original barrel deployed](keel-fit-deployed.png) |

[Cover travel and reverse poses](qa-axial.png) · [Main batteries](qa-main.png) · [Flank singles](qa-flank.png) · [Defense twins](qa-defense.png) · [Bridge quad/PDC and fixed armor](qa-bridge.png)

Review tag: `v0.11.22-rc.1`. This revision targets `main` and builds on PR #42.
