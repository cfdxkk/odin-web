# Odin chapter tour — v0.13.0-rc.1

The light NASA-punk interface now works as a 12-chapter field guide. The information column scrolls in snapped sections while a single 3D viewport stays pinned. A chapter change selects a fixed camera shot and a useful inspection configuration; scroll position does not scrub weapon animation or camera motion. Main upper/lower batteries, single batteries, forward/aft twins, bridge quad guns, defense mounts, bow, bridge and engines are covered before the official image archive and footer.

The guide starts paused. Playback is an explicit persistent choice. Chapter navigation, language, quality and manual-view changes preserve that choice; slider drags temporarily suspend a playing sequence. In a paused view, rendering stops after the camera settles. The canvas stops rendering when the reader reaches the archive or footer. Only one preview server and the existing user-facing browser tab are retained.

## Visual changes

- Inter Tight replaces the large Helvetica headings, using locally served font files. [Google Fonts](https://fonts.google.com/specimen/Inter+Tight); [OFL license](../../../public/fonts/inter-tight-OFL.txt).
- The handwritten note is removed. Printed labels, thin panel seams, fasteners and restrained four-color registration strips retain the equipment character.
- Warm-neutral hemisphere and directional fills make the hull's lower surfaces more readable against the light panel. Original geometry, UVs and paint assets are preserved.
- A broad, multi-column footer ends in an original halftone mountain landscape containing the actual Odin silhouette. Generated with built-in Imagegen; [exact prompt and references](../../../assets/illustrations/v0.13.0/prompt.md), [PNG master](../../../assets/illustrations/v0.13.0/odin-mountain-footer-master.png). The optimized page asset is a 505 KB WebP.

## Languages and official artwork

Chinese and English cover navigation, chapter text, controls, gallery captions, alternatives, project notes, review stations and document metadata. The header switch preserves the current scene and URL query; the selected language persists locally. Ship names, source names and acronyms remain proper names.

The archive contains 27 distinct artwork images from the [official RSI Odin concept page](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin): exterior, interior, armament stills, livery variants and the original compositing layers. Brand marks, specification charts, duplicate mobile charts and videos are not artwork slides. [Full primary-source manifest](artwork-sources.json). Full-size display images total 3.42 MB and load one at a time; small lazy-loaded thumbnails provide direct selection. Both arrows wrap around the archive. Images retain their original aspect ratio and © Cloud Imperium Games credit.

## Validation

- `npm test`: 90 passing tests, including chapter boundaries, camera axes, locale completeness and every local gallery image.
- `npm run verify:asset`: both GLBs have 214 meshes, 20 materials, 12 embedded textures and **zero animation clips**.
- `npm run generate`: passed.
- Browser checks: real mouse-wheel snap, pinned viewport, pause persistence, temporary slider pause/resume, manual pan, quality, CN/EN, document metadata, modal, all 27 slides, gallery wrap, and zero off-screen/idle redraws.
- No horizontal overflow at 320, 390, 700, 800, 801, 1024, 1440, 2560 or 3440 px widths.
- Twelve guided views inspected; mechanical review covers 39 poses across main batteries, mirrored side batteries, quads, twins and bridge. All retain 215 static runtime joints.
- Editable Blender geometry, both GLBs and all weapon trajectory modules are unchanged.

See [browser evidence](browser-check.json), [desktop guide](desktop-zh.png), [English quad close-up](quad-en.png), [art archive](gallery-zh.png), [mountain footer](footer-zh.png), [ultrawide overview](ultrawide-en.png), [phone view](mobile-zh.png) and [all guided shots](guided-views.jpg).
