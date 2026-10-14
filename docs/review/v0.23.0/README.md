# v0.23.0 — continuous flight and scroll articulation

The weapon tour now starts rotating immediately and gradually steers the same angular velocity toward the stern. It reaches the overhead region late in the torpedo segment, overlaps the aft tilt, and progressively pulls back. A fixed longitudinal orbit axis avoids the lateral slide caused by moving the center vertically between weapons.

Weapon poses and camera position use the same damped scroll progress. Main, single, twin and quad batteries deploy cumulatively as the user advances; reverse scrolling retraces their deployment ramps. Station changes no longer launch timed deployment clips. A finite blend is retained only for entering or leaving the tour. All mounts stow together on entering the bridge.

## Evidence

Local validation passed: 159 tests, both asset checks (zero GLB animation clips), static generation, and 62 browser assertions across the two entry directions.

- `camera-flight.json`: dense path sampling, both entry sides and four viewport ratios; continuity, monotone distance and angular-speed checks.
- `scene-qa.json`: real browser poses, partial deployment, both route sides, reverse scroll, pause persistence and bridge/aft handoffs.
- `layout-qa.json`: desktop, ultrawide, short desktop and mobile layouts, gallery controls and transparent photography.
- `footer-refinement.md`: image provenance, fixed-size 4×4 print treatment and isolated-speck cleanup.
- `footer-backup/`: the exact v0.22 component, screen helper, styles, screenshot and hashes. Its source image remains unchanged.

The new footer can be compared with the frozen backup at `/review/footer-v0.23.0.html`. All model and original Blender files are unchanged in this revision.

## Deployment

`vercel.json` builds with `npm ci` and `npm run generate`, then publishes `.output/public` as a static site. `.vercelignore` excludes editable source artwork, Blender files, local captures, tests and review documents from the deployment upload. The source repository retains those assets. The dedicated Vercel project is `cfdxkks-projects/odin-web`; deployment is performed after merging the release PR to main.
