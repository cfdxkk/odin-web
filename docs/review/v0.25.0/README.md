# v0.25.0 — ODIN AWAKENING

A full-viewport interactive art experience replaces the conventional long-page showcase. The ship becomes the subject of a 72-second cinematic awakening, with a continuous camera flight, original procedural atmosphere and direct access to its mechanical articulation.

## Experience

The four acts share one deterministic timeline:

| Act | Time | Presentation |
| --- | --- | --- |
| 01 — 显影 / REVELATION | 00:00–00:16 | An eclipse composition reveals the solid ship through warm copper and orange light. |
| 02 — 重构 / RECONSTRUCTION | 00:16–00:32 | The hull automatically shifts into a cool blue holographic reconstruction with a moving scan. |
| 03 — 武备 / ARMAMENT | 00:32–00:54 | The camera moves from the main batteries through secondary and twin mounts to the bridge quad arms, following deployment and stowage. |
| 04 — 跃迁 / TRANSCENDENCE | 00:54–01:12 | Fully stowed weapons permit engine ignition; the camera accelerates away through a particle warp sequence. |

- Direct chapter selection and timeline seeking, persistent explicit pause, and temporary pause while dragging a slider. Visibility changes, overlays and free inspection suspend the film without clearing the user's pause preference.
- Six free-inspection views: complete ship, main batteries, single secondary batteries, twin batteries, bridge quad arms with the original fixed bridge armor, and propulsion. Drag to orbit, zoom, pan, reset the camera or adjust the complete deployment stroke.
- A selectable spectral view, PNG capture and a fullscreen control. Reduced-motion preferences are respected, with an explicit user opt-in to play the full experience.
- Original procedural Web Audio ambience is enabled only through the sound control. No background music starts automatically.
- Eight existing official images appear in a native full-screen dialog: four interior views and four exterior concepts. The viewer provides previous/next controls, keyboard navigation, source links and an About view identifying the fan-made interpretation and concept-stage material.

The eclipse, holographic reconstruction, lighting and particle warp are artistic presentation effects, not new claims about the ship's official systems or performance.

## Mechanical contract

All weapons remain stowed through 00:32, deploy over the complete 6.5-second stroke, hold from 00:38.5 to 00:47.5, and fully stow by 00:54. Thrust remains exactly zero whenever deployment is nonzero and begins only after 00:54. Warp intensity rises during 01:04–01:12.

The camera track uses continuous, shape-preserving interpolation. Its authored positions stay outside the ship, including the low pass by the twin mounts. Timeline samples are deterministic and independent of seek direction.

## Validation

- `npm test`: **171 passed**, including six new film tests covering chapter boundaries, 120 fps mechanical interlock sampling, deterministic seeking, finite and continuous camera motion, opening silhouette framing, the accelerating final pullback and pause blockers.
- `npm run verify:asset`: **passed**; both shipped GLBs retain zero animation clips.
- `npm run generate`: **passed**. The generated static output is the target of final browser verification. Existing nonfatal Nitro external-import warnings remain in the build log; the initial static browser run reported no console warnings or errors.
- Browser validation: **68 assertions passed**, with zero application errors. The complete 72-second film visited all four acts, rendered 5,420 frames at approximately 75 fps on the test RTX 4070 SUPER, and never combined nonzero deployment with thrust. All six inspection views, main/secondary/twin/quad articulation, fixed bridge armor, pause and pointer/keyboard scrubbing, reduced-motion opt-in, eight images, PNG capture, fullscreen and real WebGL context-loss recovery were verified.
- Layouts passed at 1920×1080, 1366×768, 3440×1440 and 390×844. The ending removes the previous chapter caption on desktop and mobile. Visibility was checked with controlled `document.hidden` and visibility events; native background-tab throttling could not be reliably simulated by the browser tool. See `browser-qa.json` for scope and evidence.
- Software renderers use the smaller GLB and disable AO/bloom. The full cinematic lighting and postprocessing were verified on the hardware renderer.

## Assets and release scope

The original `odin.blend`, versioned Blender geometry, both GLBs, textures and the established articulation rig are unchanged. Mechanical animation remains authored in Nuxt/Three.js; no animation clips are exported into the GLBs. Existing official images retain their source attribution.

This revision is a **review preview** on `codex/odin-awakening-v0.25.0`, for a new GitHub pull request against `cfdxkk/odin-web:main`. It has **not been merged into `main`** and is not a production release. The immutable review tag is [v0.25.0-rc.1](https://github.com/cfdxkk/odin-web/tree/v0.25.0-rc.1).

[Vercel preview](https://odin-hm51k7vez-cfdxkks-projects.vercel.app) is Ready and retains the project's existing Vercel authentication. The user explicitly authorized this preview publication. The production site and existing Sites identity are unchanged.

Screenshots: `desktop-prologue.png`, `desktop-inspection.png`, `reconstruction.png`, `transcendence.png`, `ending.png`, `mobile-inspection.png`.
