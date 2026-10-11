# Turret motion tempo — v0.11.43-rc.1

The bridge quads previously squeezed their release into 15% of the timeline, followed by a long idle interval before aiming. Aft twin covers 5–8 crossed their entire stroke in 5%, while the complete turret needed 47%. The new family clocks distribute time across the accepted pose paths and shorten stationary handoffs.

| Assembly | Phase | Timeline | Time in a 6.5-second stroke |
| --- | --- | --- | --- |
| Bridge quads | Original tube, cradle and hull-petal release | 0–33% | 2.145 s |
| Bridge quads | Original frame-30 to frame-45 carriage travel | 35–67% | 2.080 s |
| Bridge quads | Original three-channel aim | 69–100% | 2.015 s |
| Aft twins 5–8 | Hull cover release | 0–26% | 1.690 s |
| Aft twins 5–8 | Complete turret and rail travel | 26–64% | 2.470 s |
| Aft twins 5–8 | Aiming | 66–98% | 2.080 s |

Mechanical handoffs are 0.13 seconds. Aft scanning starts only after the turret reaches its aiming endpoint. Opening and closing retrace the same path. The affected review shots now use the same 6.5-second stroke as manual deployment; other review shots retain their existing duration. Switching shots preserves phase, direction and explicit pause.

All 550 editable meshes, UVs, material assignments, 215 joint rest frames and joint properties match v0.11.42. Original `odin.blend` remains unchanged. Reduced quad center packing, existing tube reach, fitted translation-only petals and all cover thicknesses are retained. Native tempo metadata and Nuxt use the same JSON profile; both GLBs contain zero animation clips.

Validation:

- 1,203 sampled runtime poses match the accepted v0.11.42 path exactly for all 54 affected joints; the remaining 161 joints have identical world transforms at the same global progress.
- Actual runtime meshes checked at 442 forward/reverse poses per mount: no tube/armor, tube/tube, cradle/cradle, aft gun/cover or rail/cover contacts. Removing aft turret descent triggers the collision control.
- Six affected mounts played through a complete opening and closing cycle in the browser, with paused views at three angles. Main batteries, singles, defense mounts, bridge arms and fixed bridge details also reviewed.
- `npm test` (76 passed), `npm run verify:asset`, `npm run generate` passed. Finished temporary browsers are closed; one paused user preview and one static service remain.

Evidence: `source-geometry.json`, `tempo-verification.json`, `mesh-clearance.json`, `aft-twin-mesh-clearance.json`, `asset-hashes.json`, `browser-check.json`, and the rendered preview images.

The original comparison runtime is recovered from immutable tag `v0.11.42-rc.1` by `tools/sample_turret_tempo_v01143.mjs`. Mesh sweeps consume its captured runtime poses using `tools/audit_turret_tempo_v01143.py` in the versioned editable native file.
