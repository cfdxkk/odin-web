# Faster orbit and Odin club emblem — v0.11.46-rc.1

The orbit now completes a uniform turn in 45 seconds at eight degrees per second, a 33⅓% increase from v0.11.45. The camera uses its own periodic clock so the existing 60-second weapon film cannot reset its angle. Camera position, framing velocity and angular speed remain continuous at each orbit wrap. Seeking deliberately selects the corresponding camera phase; explicit pause and free exploration hold both cinematic clocks.

The missing header mark is replaced with a newly rendered transparent emblem inspired by the [official RSI Odin Founders Club badge](https://media.robertsspaceindustries.com/84qwqukbwkgsk/source.png). It keeps the gold pointed ring and silver top-down ship silhouette. The generated master, exact prompt, source record and deterministic resize script are in `assets/branding/v0.11.46/`. The header uses a compact lossless WebP; PNG favicon and touch icons use new versioned URLs. The badge reference is linked in the site's creation credits.

Validation:

- `npm test`: 84 passed. The orbit tests check uniform speed, continuous framing, direction and repeated camera/weapon film boundaries.
- `npm run verify:asset`: both GLBs valid, with zero animation clips.
- `npm run generate`: static site build passed.
- Dense sampling over three minutes and three viewport configurations: zero reversed samples, four complete 45-second orbits, uniform eight-degree speed.
- Browser checks crossed both natural 45-second camera and 60-second weapon-film wraps. Measured speed stayed within 0.00004°/s of 8°/s. Explicit pause held through seeking, chapter changes and free exploration.
- Header logo loaded; both favicon and touch icon returned HTTP 200 and decoded to their expected dimensions.
- Inspected 34 stowed/deployed views covering main guns, single and twin secondaries, bridge quad/PDC mounts and bridge armor. Review rendering held its frame count while paused.
- Browser console: zero errors. The temporary checking browser was closed; the single user-facing preview remains paused at the opening view.

The original Blender file, current editable model, both GLBs, weapon rig, mechanical timing and prior engine-light AO fix are unchanged. See `camera-verification.json` and `browser-check.json` for measurements and hashes; `website-preview.png` shows the integrated logo.
