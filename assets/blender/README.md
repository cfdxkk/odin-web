# Editable Odin asset

`odin_articulated_v0.4.0.blend` is the current editable exterior model. The original `odin.blend` and earlier versioned copies remain unchanged. It contains geometry, PBR textures and named static joints, with no animation actions.

Version 0.4 restores original single-gun armor skins, the front bridge shield, and the hidden aft door/frame. It separates the outer main-barrel tubes, fits paired main-bay covers ahead of the original shrouds, corrects twin-mount orientation and prepares parallel quad-gun slides. The 13 engine origins remain at the nozzle centers established in v0.2.1. All mechanical motion is authored in `app/lib/odin-rig.ts`, with mode/exhaust timing in `app/lib/odin-motion.ts`.

Re-export with Blender 5.1:

```powershell
blender -b assets/blender/odin_articulated_v0.4.0.blend --python tools/export_articulated_asset.py
```

To reconstruct this revision from v0.3.0, first run `tools/inspect_articulation.py` against the original model to create `work/source-articulation.json`, then run `tools/revise_mechanisms_v04.py` against the v0.3.0 copy. The original is only read as a library to recover its hidden door objects. The script saves a separate v0.4.0 file.

See [reference observations and pose review](../../docs/review/README.md). This is a fan-art reconstruction from public exterior references, not the official production rig.
