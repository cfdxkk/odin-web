# Articulation review

`articulation-stages.jpg` shows v0.3.0 deployment at 0%, 50% and 100% from eight views. The poses come from `createOdinRig()` in the actual Nuxt source, evaluated against the GLB node hierarchy and applied to the separate Blender model for static inspection. Workbench lighting is used to expose geometry; these are not screenshots of the final PBR web renderer and no Blender animation is exported.

Rows: dorsal main battery, bridge, tower quad close-up, rear bridge armor, ventral battery, deck defense mounts, side profile, restored aft door. The 25% and 75% inspection frames remain temporary local files.

Run `node tools/review_rig_poses.mjs`, then `blender -b assets/blender/odin_articulated_v0.3.0.blend --python tools/render_rig_review.py` to regenerate local inspection frames.

The official [RSI page](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin) main-battery clip (`ns6umeu6gb7w5`) shows covers opening outward along two longitudinal hinge lines. The tower clip (`meqm0flrf1683`) shows the carriage extending before its four arms unfold. The fixed forks now remain with the turret gimbal while the barrels and arms fold through 180 degrees. The [SCL aft view at 51:48](https://www.youtube.com/watch?v=CFoQp6wRjPo&t=3108s) informs the replacement tapered lower hangar closure. These reproduce observable exterior motion, not unpublished internal engineering.

The original file is unchanged. Both high/lite exports contain zero animation clips. Runtime checks cover hinge positions, cover/barrel clearance order, complete carriage travel before arm unfolding, neutral return before stow, fixed main/single-barrel aim, and reversible free-exploration engine interlocks.

![Static mechanism review](articulation-stages.jpg)
