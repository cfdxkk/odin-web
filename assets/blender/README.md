# Editable Odin asset

`odin_articulated_v0.6.0.blend` is the current editable exterior model. The original `odin.blend` and earlier versioned copies remain unchanged. It contains geometry, PBR textures and named static joints, with no animation actions.

Each main battery has five independently translated armor pieces. The continuous side skins have polygonal shroud notches and chamfered foredeck edges; their two-stage guide runs outside the gun corridor before descending below the hull lip. The fifth piece is the short wedge at the very front of these covers, identified in the user's annotated close-up. It first lifts and then slides toward the bow; the farther foredeck remains intact. Two additional narrow aft skirts are separated from the original hull surfaces below the shrouds, retaining their UVs and contour; they translate down independently of the rising turret. The gun assembly waits until all five pieces are clear. All movement is authored in `app/lib/odin-rig.ts`; `app/lib/odin-motion.ts` controls the 6.5-second transitions and exhaust interlock.

Re-export with Blender 5.1:

```powershell
blender -b assets/blender/odin_articulated_v0.6.0.blend --python tools/export_articulated_asset.py
```

To reconstruct v0.6, run `tools/revise_main_battery_v06.py` against the v0.5.0 copy; it saves a separate v0.6.0 file. The original model is never saved or modified. Earlier versions and their reconstruction scripts remain available.

See [reference observations, geometric clearance check and pose review](../../docs/review/README.md). This is a fan-art reconstruction from public exterior references, not the official production rig.
