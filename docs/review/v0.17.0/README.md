# Odin guided armament tour / v0.17.0

This revision adds a five-stop weapon inspection inside chapter 02. The other three ship chapters and the wallpaper/footer document flow remain separate.

- A wheel gesture selects the next weapon. The text stays in the same column while the camera translates from the bow toward the bridge. Number buttons and the down arrow provide click/keyboard alternatives.
- The inspected class deploys using the existing mechanical function. Other classes use their measured NAV transforms. Reversing or changing the selection starts from the currently displayed pose.
- The SVG leader projects an actual moving model joint every rendered frame. The static bow array uses its measured model-space point. Its text end is measured from the live DOM, including language and viewport changes.
- Four downloaded official demonstration clips appear individually beside their corresponding weapon. They remain muted, grayscale and paused until interaction, and stop when their chapter is hidden.
- The original Blender files, GLBs, geometry and accepted mechanical trajectories are unchanged. Selective rendering adds a wrapper around the existing rig; matrix-equivalence tests cover both GLB variants.
- The opening film, timeline, persistent pause preference and manual view retain their existing behavior. Manual entry is unavailable during a finite chapter handoff so it cannot replace a partly stowed group with an all-weapon pose.

## Sources

Weapon size grades and counts use the [official Odin page](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin) and its [weapon-statistics graphic](https://media.robertsspaceindustries.com/uhjpyw81y6eqe/source.jpg). S8/S10/S12 are size grades, not millimetre calibres. The [official SCL episode](https://www.youtube.com/watch?v=CFoQp6wRjPo) is linked as further reference. Its automatic weaponry chapter was confirmed, but a full transcript was not available; this revision does not invent developer quotes or individual weapon timestamps. The adjacent JSON records the verified facts and media provenance.

The production filename `pdc.mp4` and model prefix `PDC_` are not used as official classifications. The clip depicts the large twin-mount mechanism; `PDC_` in this model identifies the bridge quads. The official 42 S2 point-defense mounts are a separate category.

## Footer and visual finish

The [original footer Figma file](https://www.figma.com/design/4ukEOT8r7jlKIWdU3hh14X/Footers?node-id=1-146) was inspected after user sign-in. Its reference frame is 1440 × 880; `image 16` is a 1260 × 1012 screened landscape at x=90, y=-132, with a separate #008E47 Color-blend layer. It provides reference for aligned printing dots and tonal hierarchy, rather than the identity or geometry of Odin.

Our footer uses the actual project GLB in a reproducible WebGL landscape render and one regular, amplitude-modulated Canvas screen. Dot centers share a grid across ship and mountains. No generated imitation of the ship is used. The community mark and official links remain live DOM elements, legible at the bottom of the page.

The overall presentation also uses local Inter/Inter Tight typography, one text-column width, quieter navigation and adjusted model key/fill lighting.

## Validation

Run `npm test`, `npm run verify:asset`, and `npm run generate`. Browser evidence covers selection/reversal, projection, independent rig levels, video lifecycle, film/manual controls, responsive footer redraw, and articulation review stations. See the adjacent validation record for final results.
