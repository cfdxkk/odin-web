# Folio renderer QA — v0.26.0

Recorded 2026-10-29, Asia/Shanghai. Browser testing used Chromium through Playwright CLI on the local RTX 4070 SUPER. Desktop viewport: 1920 × 1080 for the integrated page; initial isolated renderer study: 1600 × 1000. Mobile layout check: 390 × 844.

## Mechanical and playback observations

- The full `/models/odin.glb` loaded on the hardware GPU. Runtime reported 215 static joints and weapon groups `{ "main": 34, "single": 104, "defense": 40, "quad": 36 }`.
- All six focus modes were exercised in the isolated renderer. Main, secondary, defense, and bridge had deployment 1 and thrust 0; engine mode had deployment 0 and thrust 0.85. Overview had deployment 0 and thrust 0.
- A continuous main-to-engines closing transition was sampled with `requestAnimationFrame` for 8.8 seconds: **661 samples; zero samples with both deployment > 0 and thrust > 0**. First sample: deployment 0.99998, thrust 0. Last sample: deployment 0, thrust 0.85.
- Explicit pause remained set throughout that transition: every sample reported `playing=false` and `animationTime=24.00000`. An additional stationary pause check also left animation time unchanged.
- That continuous test preceded the final camera/ink/highlight refinements. The rig, deployment transition helpers, and engine interlock were unchanged by those refinements. A separate production-build browser review is still the responsibility of the release check.
- Existing geometry and original mechanical helpers were not edited. Bridge armor remains fixed. GLB animation clips are checked and rejected by this viewer if present.

## Final presentation checks

- The integrated cover now uses a bow-near, stern-far diagonal composition. Automatic movement is a bounded ±0.075-radian arc (approximately ±4.3°), rebased after a user drag. It no longer accumulates a full orbit. `orbitAngle` and `orbitTime` are exposed in canvas diagnostics for subsequent QA.
- The cover has no artificial blue cross-section stripe. Mechanical selection colors meshes by their real weapon-joint ancestry; main hatch skins and fixed bridge armor stay neutral. The integrated main-battery screenshot visibly shows both selected main assemblies in cobalt.
- Print shading now leaves lit surfaces mostly paper-white and reserves dots for darker regions. Contour mode derives visible edges from depth/normal discontinuities; it does not draw hidden edges or triangle wireframes. Treatment changes use a short blend and settle without changing play intent.
- The desktop mechanical canvas uses the whole page and a 13% projection offset. Narrow displays use a 5% offset and a wider aspect fit. The 390 × 844 cover check showed the complete ship without clipped bow or stern.
- A final attempt to recapture the mobile mechanical page timed out waiting for `mode=main` and `cameraTransition=false` during concurrent integration work. The browser was closed; the final narrow-screen mechanical framing must be rechecked against the stable production build. The earlier mobile screenshot shows both main weapon assemblies, with surrounding hull cropped at the right viewport edge.
- The final focused TypeScript command completed with exit code 0. The isolated renderer's last clean console check reported zero errors and zero warnings. Integrated Nuxt development logs include the framework's informational Suspense notice; no renderer exception was observed.
- The wrapper cancels its owned loading manager and disposes the WebGL context on unmount. The context-loss handler disposes the render loop before reporting failure. A full fault-injection/network-cancellation test was not performed in this visual pass.

## Local visual evidence

The following QA screenshots are local ignored output, not published assets:

- `output/playwright/v026-cover-etching2.png` — integrated diagonal cover, clean title area, reduced ink.
- `output/playwright/v026-anatomy-highlight1.png` — integrated main batteries, cobalt selection and full-width framing.
- `output/playwright/v026-mobile-cover-fit.png` — complete ship in the mobile cover.
- `output/playwright/v026-mobile-anatomy-fit.png` — earlier narrow-screen mechanical framing, before the last aspect-fit widening.
- `output/playwright/folio-qa-{main,secondary,defense,bridge,engines,overview}.png` — earlier isolated focus and articulation checks, before final visual refinements.

No extra geometry, Blender files, or exported GLB assets were created or modified for this renderer.

## Secondary highlight correction after production review

The production reviewer found the secondary-battery mode coloring most of the hull. Inspection of both actual GLB JSON chunks identified a naming collision: node `Odin_Asset_Geometry` contains the merged hull, but its mesh datablock is named `Axial_Stern_FixedSlotLips`. GLTFLoader uses that datablock name for the mesh's 18 material primitives. The initial prefix-based traversal mistook these primitive names for secondary-weapon ownership.

The correction accepts ownership only from ancestors carrying `staticJoint: true`; primitive/datablock names do not establish ownership. Main hatch skins remain neutral. The source-material UUID plus weapon-group cache separation is retained. The secondary view alone was moved 20% farther away to leave the navigation column clear.

Four regression tests passed against both `odin.glb` and `odin-lite.glb`: merged-hull primitives stay neutral, all eleven secondary mounts retain their group, and representative main/defense/quad/hatch boundaries remain correct. The focused TypeScript check passed. No server was started for this correction; the release reviewer will check the regenerated build visually.
