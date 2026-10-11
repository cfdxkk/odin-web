# Orbit pace and engine light — v0.11.45-rc.1

The previous one-way orbit had an 83.7:1 speed range: the opening barely turned while the last quarter rushed around the ship. The camera now makes one full turn at six degrees per second. Radius, elevation and target still pass through the authored inspection values; their time-based Hermite interpolation has matching periodic tangents for a smooth loop. The phase places the stern pass at 40 seconds, during NAV ignition.

The transparent nozzle glow sprites and exhaust cones were entering GTAO's opaque depth/normal override. This made their underlying rectangles show up as solid occluders around the nozzles. The AO pass now excludes only these engine-light objects and restores their visibility for normal rendering, including on render failure. Physical hull and nozzle surfaces retain AO.

Validation:

- `npm test`: 83 passed. Checks include uniform speed, framing velocity across shot joins and the loop, and AO exclusion/visibility restoration.
- `npm run verify:asset`: both GLBs valid, zero animation clips.
- `npm run generate`: static build passed.
- Dense sampling of the full 60-second orbit at three viewport configurations: one full turn, uniform speed, no reversed orbit or view direction.
- Browser evidence is recorded in `browser-check.json` with screenshots of the main site and engine close-up.

The native Blender file, both GLBs, weapon rig and mechanical motion remain unchanged from v0.11.44. No source geometry was modified.
