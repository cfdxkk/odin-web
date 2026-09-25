# Editable Odin asset

`odin_articulated_v0.7.0.blend` is the current editable exterior model. The original `odin.blend` and earlier versioned copies remain unchanged. It contains geometry, PBR textures and named static joints, with no animation actions.

Each main battery has five independently translated armor pieces: two forward leaves, two narrow fillers below the rotating gun shrouds, and the short fore-end cap. Version 0.7 restores the complete `holo.001` and `holo.013` hull meshes from v0.5. The aft fillers are new thin shells spanning the gap between the shroud toes and fixed hull lips; no fixed-hull faces are cut out. Their reconstruction data and the main-leaf seams use measured closed-pose boundaries in `tools/main_armor_v07_boundaries.json`. The dorsal leaves follow the existing serrated lip; the ventral source lip has its own faceted profile rather than a mirrored copy of those teeth.

The main-leaf guides now travel 10.5 outboard / 17.6 inward for the dorsal bank and 10 / 16.1 for the ventral bank, in asset source-coordinate units. The corresponding v0.6 totals were 16.4 / 23.2 and 16.4 / 23. The fore-end cap lifts before sliding toward the bow. The outer two tubes of each triple gun telescope through a full 16-unit stroke along their measured bore axes, nesting farther into their sleeves while preserving the previous fully deployed SCM endpoint. The gun assembly waits until all five pieces clear; stowing follows the same sequence in reverse.

All movement is authored in `app/lib/odin-rig.ts`; `app/lib/odin-motion.ts` controls the 6.5-second transitions and exhaust interlock. The static model stores guide and tube-axis metadata only. The hull preservation report compares exact vertex coordinates, polygon/edge topology and object transforms against v0.5, allowing the recessed-floor material assignment to change.

Re-export with Blender 5.1:

```powershell
blender -b assets/blender/odin_articulated_v0.7.0.blend --python tools/export_articulated_asset.py
```

To reconstruct v0.7, run `tools/revise_main_battery_v07.py` against the v0.5.0 copy; it saves a separate v0.7.0 file. The v0.6 script remains as a historical reconstruction of the earlier five-piece design, including its now-superseded hull-cut aft skirts. The original model is never saved or modified. Earlier versions and their reconstruction scripts remain available.

See [reference observations, geometric clearance check and pose review](../../docs/review/README.md). This is a fan-art reconstruction from public exterior references, not the official production rig.
