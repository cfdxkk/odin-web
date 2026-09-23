# Articulation review

`articulation-stages.jpg` shows deployment at 0%, 50% and 100% from six views. The poses come from `createOdinRig()` in the actual Nuxt source, evaluated against the GLB node hierarchy and applied to the separate Blender model for static inspection. Workbench lighting is used to expose geometry; these are not screenshots of the final PBR web renderer and no Blender animation is exported.

Rows: dorsal main battery, bridge/quad guns, rear bridge armor, deck defense mounts, ventral main battery, whole-ship side profile. The original 25% and 75% inspection frames remain temporary local files.

Run `node tools/review_rig_poses.mjs`, then `blender -b assets/blender/odin_articulated_v0.2.0.blend --python tools/render_rig_review.py` to regenerate local inspection frames.

![Static mechanism review](articulation-stages.jpg)
