# Editable Odin asset

`odin_articulated_v0.5.0.blend` is the current editable exterior model. The original `odin.blend` and earlier versioned copies remain unchanged. It contains geometry, PBR textures and named static joints, with no animation actions.

Version 0.5 replaces the rectangular main-bay substitutes with four complete armor plates based on the source `立方体` / `立方体.002` contours. Their static guide metadata describes an outboard and inward-deck translation; the plates do not rotate. The three gun bores, outer telescopic tubes, armored housing and circular cradle use a coordinated deployment sequence in `app/lib/odin-rig.ts`. Other articulated systems and the 13 engine origins remain from v0.4. All movement is authored in Nuxt; `app/lib/odin-motion.ts` controls modes and exhaust timing.

Re-export with Blender 5.1:

```powershell
blender -b assets/blender/odin_articulated_v0.5.0.blend --python tools/export_articulated_asset.py
```

To reconstruct v0.5, run `tools/revise_main_battery_v05.py` against the v0.4.0 copy; it saves a separate v0.5.0 file. The measured source plate vertices are recorded in the script. The original model is never saved or modified.

See [reference observations and pose review](../../docs/review/README.md). This is a fan-art reconstruction from public exterior references, not the official production rig.
