# Odin Web working agreements

- Every user-requested revision must use a new feature or fix branch and a GitHub pull request against `cfdxkk/odin-web`'s `main`. Do not push feature changes directly to GitHub `main`.
- Tag each reviewable revision (`vX.Y.Z-rc.N` while a PR is open, stable semver after release). Never move an existing tag. Link the tag and PR in the handoff.
- PC fidelity and correct mechanical articulation take priority over mobile optimization.
- Check main batteries, secondary batteries, defense/PDC mounts, bridge quad gun arms and bridge armor, not only the main guns.
- Keep the original `odin.blend` unchanged. Save revised editable geometry to `assets/blender/` with a versioned filename; commit it to GitHub.
- Export geometry, materials, textures and static joints only. Author animation in Nuxt/Three.js; GLBs must contain zero animation clips.
- Explicit user pause must survive mode changes, browser visibility changes and slider interactions. A playing film pauses only for the duration of a slider drag.
- Run `npm test`, `npm run verify:asset` and `npm run generate`, then verify the changed behavior in the browser. Recheck rendered articulation when joints or geometry change.
