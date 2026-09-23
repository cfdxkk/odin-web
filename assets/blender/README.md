# Editable Odin asset

`odin_articulated_v0.2.1.blend` is the current separate, editable exterior model derived from the user's `odin.blend`. The original and the v0.2.0 copy remain unchanged. Version 0.2.1 restores the 13 engine origins to their actual nozzle centers without moving any mesh vertices in world space.

The model has independent main barrel cradles, sliding shrouds, rigid telescopic covers, mirrored secondary batteries, defense carriages, tower quad-gun arms, and 45 recovered bridge armor slats. It includes 2K original wear/normal/roughness textures and additional machined edge geometry. It intentionally has no animation actions.

Re-export from this file with Blender 5.1:

```powershell
blender -b assets/blender/odin_articulated_v0.2.1.blend --python tools/export_articulated_asset.py
```

Motion remains authored in `app/lib/odin-rig.ts`, with mode and exhaust timing in `app/lib/odin-motion.ts`.

Reference observations: RSI Odin page's main gun deployment clip (`ns6umeu6gb7w5`, 0–3 seconds), tower quad gun clip (`meqm0flrf1683`, 0–3 seconds), and [official SCL at 48:30–48:44](https://www.youtube.com/watch?v=CFoQp6wRjPo&t=2910s) for bridge blast shields. Invisible internal actuators are reconstructed for this fan artwork; this is not the official production rig.
