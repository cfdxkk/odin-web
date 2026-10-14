# Odin tour and print footer — v0.16.1-rc.1

The opening view keeps one ship-class/manufacturer description. All four introductions share the same column width. The weapons camera looks farther back along the hull and uses a wider frame; the third introduction concerns the bridge only. The last stage shows the aft hull and lower bridge from the rear quarter, with engine ignition happening during weapon stowage.

Entering free exploration preserves the camera position, target, lens and normalized framing offset. Residual OrbitControls damping is cleared on reentry. The homepage timeline again selects the orbit phase as well as the weapon pose. Explicit pause remains in force through seeks, manual mode and chapter changes; dragging a playing timeline pauses only for the drag.

The four local official clips share one preview window with four numbered choices. Hover or focus selects and plays one clip in color; leaving or hiding the player pauses it and restores grayscale. Main-battery and bridge-quad mirroring is retained. The wallpaper gallery is a full-width image with previous/next controls, without invented captions or thumbnails. The header returns on arrival, and the forward/reverse wheel handoff remains finite.

Each of the thirteen nozzles now uses an open flowing plume, a brighter inner core, restrained pressure bands and a radial nozzle glow. Every layer is excluded from the AO depth/normal pass. Plume growth stays attached to the nozzle; no cap or rectangular light face enters the hull. Effects animate in the held aft view while playback is enabled and freeze on explicit pause or when the viewport is off screen.

The footer illustration was redrawn with the actual shipped model as the identity reference. A deterministic newspaper screen then gives the ship and mountains the same aligned lattice, with connected ink and small negative holes in highlights. The footer keeps thanks, creator credit, the four-color stripe, official links and the restored community-made badge. Its text, links and lower marks remain visible at the document's bottom from 320 to 3440 pixels.

Validation:

- `npm test`: 104 passing tests.
- `npm run verify:asset`: both GLBs valid, 214 meshes, 20 materials, 12 embedded textures and zero animation clips.
- `npm run generate`: successful static generation.
- 44 browser assertions covering camera continuity, scrub/playback behavior, equal text widths, all four videos, concurrent ignition/stowage, gallery cycling and wheel boundaries, localization and responsive footer visibility.
- 39 rendered poses across main, single, twin, bridge quad and defensive stations; 215 runtime joints, no page errors, idle rendering stops.
- Original editable geometry, both GLBs, mechanical rig, film motion, turret timing and orbit math unchanged; [blob hashes](./unchanged-assets.json).

Screenshots: [opening](./home-zh.png), [weapons](./batteries-zh.png), [video preview](./video-preview.png), [bridge](./bridge-zh.png), [aft hull](./engines-zh.png), [wallpapers](./wallpapers-zh.png), [footer](./footer-zh.png), [narrow footer](./footer-390-en.png), [ultrawide footer](./footer-3440-en.png).

Illustration: [identity reference and Imagegen prompt](../../../assets/illustrations/v0.16.1/prompt.md), [editable print master](../../../assets/illustrations/v0.16.1/odin-mountain-print.svg), [grid record](./halftone-grid.json), [asset hashes](./illustration-hashes.json).
