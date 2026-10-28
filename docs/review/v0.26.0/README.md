# v0.26.0 — ODIN MONOGRAPH

A live, illustrated 3D cover leads into four independently composed spreads: silhouette, mechanical anatomy, life aboard, and a visual archive. The presentation uses paper, graphite and cobalt, broad Latin typography and Chinese serif headlines. Official artwork is confined to the interior and archive chapters; the cover contains no image element.

## Interaction and visual design

- Three real-time treatments: etched print with light surfaces left mostly blank, contour drawing from visible depth/normal discontinuities, and a neutral maquette. Treatment changes dissolve without resetting the view or pause preference.
- The diagonal cover uses bounded movement (approximately ±4.3°), pointer parallax, direct orbit/zoom/pan, view reset and PNG export. Chapter changes use masked image reveals and separate text timing.
- Entering the anatomy spread deploys the original mechanisms. Returning to the cover stows them. Five focus views identify main batteries, single secondary mounts, twin mounts, bridge quad arms and propulsion. Cobalt coloring follows genuine static-joint ancestry, not incidental mesh datablock names.
- Pause intent persists through chapters, materials, focus, overlays, visibility and pointer/keyboard slider edits. Reduced motion starts stationary and supports an explicit opt-in. Engines light only after full stowage; bridge armor remains fixed.
- Four interior views and eleven attributed images have native modal viewing, keyboard switching, focus return and source links. A colophon records concept-stage facts and their sources.

## Validation

The final build passed **175 automated tests**, `npm run verify:asset`, and `npm run generate`. Full and lite assets retain 214 meshes, 20 materials, 12 embedded textures, 215 static joints, and zero animation clips. Existing nonfatal Nitro external-import warnings remain in the successful generation log.

`browser-qa.json` records **96 production-build functional assertions plus 5 focused post-fix checks**, all passing. The full suite covers pause, six views, three treatments, pointer/keyboard/blur/cancel slider paths, deployment and thrust interlock, download, eleven archive images, four interiors, modal focus, real WebGL context loss and retry, reduced-motion opt-in, and layouts at 1920×1080, 1366×768, 3440×1440 and 390×844. Visibility tests use controlled `document.hidden` values/events; they are not a claim about native browser background throttling.

A visual review discovered that the merged hull's old mesh datablock name resembled a secondary-weapon joint. The highlight lookup now requires actual static-joint metadata. Asset-backed regression tests exercise both GLBs and all eleven secondary mounts. See `renderer-qa.md` for the earlier renderer study, followed by the final production browser report for the completed acceptance checks.

## Asset and release scope

Original `odin.blend`, versioned Blender geometry, both GLBs, textures and established mechanical helpers are unchanged. No exported animation clips or newly generated artwork are used. Older renderer implementations remain available for historical inspection.

Review branch: `codex/odin-folio-v0.26.0`. Review tag: `v0.26.0-rc.1`. A new pull request targets `cfdxkk/odin-web:main`. This is a preview revision, not a merge or production release. Vercel publication uses the existing project and keeps its login protection, under the user's existing preview authorization.

Screenshots: `cover.png`, `anatomy.png`, `within.png`, `archive.png`, `mobile-cover.png`, plus the selected mechanical QA images. They are captured from the local production build.
