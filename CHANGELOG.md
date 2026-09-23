# Changelog

## v0.2.0-rc.1

- Rebuild the static asset with 119 independent mechanical joints. Main guns now clear rigid bay covers before lifting their cradles and aligning their barrels; secondary batteries, eight defense mounts, quad-gun carriages and individual folding arms have their own motions.
- Recover 45 bridge armor slats, complete the front shield panels and fit glazing to the actual bridge surface. Add fixed guides for the sliding quad-gun mounts.
- Use the official RSI deployment clips and the SCL bridge-shield demonstration as exterior references. Internal mechanism dimensions and timing remain a fan-art reconstruction, not the official production rig.
- Save the editable, animation-free Blender source separately at `assets/blender/odin_articulated_v0.2.0.blend`; preserve the original `odin.blend`.
- Prioritize desktop quality with about 2.42 million triangles, real bevels, 2K PBR maps, reconstructed tangent normals, ambient occlusion, 4K shadows and multisample antialiasing. Embed high-quality WebP textures to keep the desktop GLB below 25 MiB.
- Replace the four chapters with Exterior / SCM / NAV. Exterior has no exhaust; NAV stows all systems before gradually igniting the engines.
- Distinguish an explicit pause from a temporary slider hold. Releasing a drag resumes only if the user had not paused.
- Add the official Made by the Community mark and retain the independent fan-art attribution.
- Add GitHub PR validation and immutable review-version tags.

Validation: eight playback/mechanical tests; structural checks for both static GLBs; production Nuxt generation; browser interaction checks; static render review of five deployment stages from six angles using transforms evaluated by the actual JS rig.

## v0.1.1

Baseline of the previously published Nuxt site, imported into `cfdxkk/odin-web` before the articulation revision.
