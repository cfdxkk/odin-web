# Homepage orbit — v0.15.1-rc.1

The first tour chapter now autoplays the original uniform 45-second orbit and weapon sequence. Previously, passing chapter index zero selected a fixed camera shot, and the page loaded paused. Detail chapters still hold their inspection shots and retain finite camera and articulation transitions.

Returning to the overview from a closeup or free exploration resumes the orbit at the visible heading. The camera and weapon timeline use separate clocks: a slider seek or a 60-second film wrap no longer resets the homepage view. Explicit pause survives chapter, language and exploration changes. A drag temporarily pauses a playing sequence, then resumes it; dragging a paused sequence leaves it paused. Reduced motion disables autoplay, and off-screen rendering still stops.

Validation:

- `npm test`: 96 passing tests, including orbit rejoining and overview-versus-detail camera regression checks.
- `npm run verify:asset`: both GLBs valid, 214 meshes, 20 materials, 12 textures and zero animation clips.
- `npm run generate`: successful static generation.
- 48 browser assertions cover autoplay, eight-degree-per-second motion, film wraps, scrubbing, explicit pause, chapter transitions, locale, exploration, reduced motion, full-screen layout, wheel boundaries and nine viewport widths.
- 39 rendered poses across 13 main, secondary, twin, bridge quad and defensive stations; 215 runtime joints, no page errors and no idle redraws.
- Blob hashes confirm geometry, mechanical motion, CSS and the dark halftone footer are unchanged.

Evidence:

- [Homepage / Chinese](./homepage-zh.png)
- [Successive orbit frames](./orbit-sequence.jpg)
- [Return to homepage / English](./homepage-return-en.png)
- [Rendered articulation checks](./articulation-contact.jpg)
- [Orbit playback checks](./orbit-qa.json), [pause and guide checks](./pause-guide-qa.json), [layout checks](./style-qa.json), [articulation data](./review-qa.json), [unchanged asset hashes](./unchanged-assets.json).
