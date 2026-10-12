# Odin dark full-screen showcase — v0.15.0-rc.1

The original black/navy palette, Barlow typography, founder badge colors and directional display lighting are restored. A single shared WebGL canvas covers the full viewport behind four scrolling introductions. The canvas stays pinned throughout the tour; text scrolls over it while finite camera and mechanism transitions connect each stage.

Only the four ship introductions intercept the wheel. The complete 27-image official archive and footer retain ordinary continuous scrolling. Artwork uses its original colors. English and Chinese UI remain complete.

The mountain footer is retained as a dark illustration. Odin's hull, bridge and mountain layers share visible halftone dots. The generated PNG master, exact prompts and optimized delivery asset are committed in [assets/illustrations/v0.15.0](../../../assets/illustrations/v0.15.0/prompt.md). The built-in Imagegen tool produced the illustration; the WebP is an encoded delivery copy.

Rendering stops when the canvas leaves the visible tour area, including the strip hidden behind the fixed header. The user's explicit pause preference survives guide changes, language switching and slider gestures.

Validation:

- `npm test`: 94 passing tests.
- `npm run verify:asset`: both GLBs have 214 meshes, 20 materials, 12 textures and zero animation clips.
- `npm run generate`: successful static generation.
- 28 browser checks cover transitions, wheel navigation, pause, scrubbing, locale, archive, renderer idling and reduced motion.
- 22 presentation checks cover full-viewport rendering, text overlays, dark colors, native image/model colors, wheel boundaries, manual zoom, footer and nine viewport widths from 320 to 3440 pixels.
- 39 poses across 13 main, secondary, twin, bridge quad and defensive stations; 215 runtime joints, no browser errors and no idle redraws.
- Original model, editable Blender asset and mechanical motion paths are unchanged; blob hashes are recorded in `browser-check.json`.

Screenshots:

- [Desktop / Chinese](./desktop-zh.png)
- [Desktop / English](./desktop-en.png)
- [Four guided views](./guided-views.jpg)
- [Dark halftone footer](./footer-zh.png)
- [Official artwork](./gallery-zh.png)
- [Mobile](./mobile-zh.png)
- [Ultrawide](./ultrawide-en.png)
