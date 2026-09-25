# v0.8.9 — continuous main-bore lift

The outer bores previously finished their seating lift at 44% deployment, then waited for the shared cradle lift to start at 46%. Separate easing made the pause longer perceptually. Seating now blends into the accelerating cradle, keeping the outer bores moving throughout the handoff. Reversing uses exactly the same path.

The outer bores' additional stow depth is halved. Their inward nesting and fully deployed reach are preserved; the centre bore remains rigidly attached to its own cover. On closing, a short final sink still finishes after the covers stop.

This release reuses the approved v0.8.8 geometry, materials, armor motion and editable Blender source unchanged. Motion remains in Nuxt/Three.js. `reviewVersion` identifies this motion revision separately from `assetVersion` in the preview provenance.

- [1280 × 720 unfolding/folding video](main-battery-preview.mp4)
- [12-frame sequence](main-battery-sequence.png)
- [Closed view](closed.png) / [open view](open.png)
- [Animation provenance](animation-preview.json)
- [Armor/gun clearance](main-clearance.json): 101 actual JS poses, 30 pairs per pose, zero collision samples.
- [Armor/hull sweep](hull-sweep.json): all 10 leaves across 101 poses, zero collision samples.

Validation: `npm test` (25 tests), `npm run verify:asset` (high/lite GLBs; zero animation clips), and `npm run generate`. Tests sample real world-space bore travel at 1,001 deployment values, check continuous outward travel, the handoff speed, short terminal seating, centre-cover alignment, and unchanged fully deployed transforms. Secondary batteries, PDC/defense mounts, bridge quad arms and bridge armor retain their prior joint motion. The 14.57-second preview was fully decoded (437 frames).

This remains a fan-art reconstruction. The approved shell is not remodelled for this timing revision.
