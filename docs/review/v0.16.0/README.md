# Minimal dark showcase — v0.16.0-rc.1

The opening introduction keeps the ship name, class and two specifications. Every ship stage uses an accessible straight down-arrow with a restrained opacity pulse; reduced motion disables the pulse. The homepage orbit and explicit pause behavior are preserved.

The header moves above the viewport from the second ship stage, and the playback and free-exploration controls disappear. The bow camera now includes the laser array. Four locally hosted official videos form a compact 2×2 grid: main battery, bow lasers, PDC and bridge quad turret. Videos start paused and grayscale, play muted only on hover or focus, and stop when hidden. Only one card plays at a time. Main and quad videos are mirrored in presentation; the official file bytes are unchanged.

The fourth ship stage makes one wheel gesture transition to the wallpaper gallery. The header returns at the gallery. Ordinary scrolling resumes inside the gallery and footer, with a reverse step back to the last ship stage at the gallery's top boundary. The gallery contains only four official landscape exterior wallpapers and fills its image window.

The footer retains the four-color stripe, credits and thanks, and only the official-links column. Its illustration and text occupy one viewport composition so the introduction and links remain visible at the document's bottom on narrow, short and ultrawide displays. A smooth Imagegen source plate feeds a deterministic four-unit dot lattice. All circles are aligned, use tone-dependent radii and two inks, and contain no random speckling or embedded bitmap.

Validation:

- `npm test`: 100 passing tests.
- `npm run verify:asset`: both GLBs valid; 214 meshes, 20 materials, 12 textures and zero animation clips.
- `npm run generate`: successful static generation.
- 34 browser assertions, including all four videos, mirroring, hidden controls, pause persistence, forward/reverse gallery handoffs, localization and footer visibility from 320 to 3440 pixels.
- 39 rendered poses across 13 main, secondary, twin, bridge quad and defensive stations; 215 runtime joints, no page errors and no idle redraws.
- All four MP4s decode completely. The local videos total 2.93 MB and load only on interaction; poster images total 90.5 KB.
- The footer contains 57,983 circles on a four-unit lattice. Unit tests validate every center and radius, uniqueness, and exactly two inks.
- Model geometry, runtime mechanics, original orbit and scene renderer are unchanged, with blob hashes in `unchanged-assets.json`.

Screenshots: [opening](./home-zh.png), [weapons and videos](./batteries-zh.png), [bridge](./bridge-zh.png), [engines](./engines-zh.png), [wallpapers](./wallpapers-zh.png), [footer](./footer-zh.png), [narrow footer](./footer-390-en.png), [ultrawide footer](./footer-3440-en.png).

Sources: [official media manifest](./official-media-sources.json), [Imagegen prompt and source plate](../../../assets/illustrations/v0.16.0/prompt.md), [print-grid record](./halftone-grid.json).
