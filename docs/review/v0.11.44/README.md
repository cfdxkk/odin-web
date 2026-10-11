# Cinematic orbit direction — v0.11.44-rc.1

The opening orbit keys previously went from −0.79 to −1.08 radians, then reversed toward −0.95 and −0.62. The original spline continued backwards until about 7.67 seconds. The opening keys now increase towards the existing 18-second shot.

Orbit angle uses a monotone Hermite track with weighted harmonic tangents. Angles remain unwrapped through one full turn; interpolation cannot overshoot into a reverse orbit. The first and last angular tangents match, keeping rotation direction and angular speed continuous across the 60-second loop. The original zoom, elevation and target tracks are retained.

Validation:

- 6,001 samples per configuration for desktop, narrow desktop and mobile: zero reversed orbit samples and zero reversed view-direction samples; exactly one full turn.
- Angular speed checked on both sides of every shot boundary and the loop wrap. All original inspection-shot radii, elevations and targets retained.
- `npm test` (79 passed), `npm run verify:asset`, `npm run generate` passed.
- Actual rendered camera coordinates checked while playing across 60 → 0 and the first 16 seconds. Explicit pause checked while switching exploration mode and chapters. Main, secondary, defense, bridge arms and fixed bridge structures checked in the rendered review.

This is a camera-only revision. The editable native file and both GLBs remain v0.11.43 with identical SHA-256 hashes. No weapon geometry or articulation changes; both exports retain zero animation clips.

Evidence: `camera-verification.json`, `browser-check.json`, and `website-preview.png`. `tools/check_camera_orbit_v01144.mjs` reproduces the analytical comparison against immutable tag v0.11.43-rc.1. The main canvas exposes its rendered camera position for browser verification.
