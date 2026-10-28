# v0.24.0 — ODIN ATLAS

A new art direction and interaction model for the Odin showcase: warm ivory editorial pages, oversized typography and acid-green accents, with a separate charcoal 3D observatory. Reuses the established ship assets without reusing the previous website layout.

## Experience

- A tightly framed transparent hero image rendered from the full-detail existing GLB (2600 × 1199 RGBA), subtle pointer parallax, native anchor navigation and a chapter index.
- Six selectable 3D inspection views: complete ship, main batteries, single secondary batteries, twin batteries, bridge quad arms and fixed armor, and propulsion. Camera and configuration changes are continuous; a direct slider takes over the complete original rig.
- Explicit pause persists across mode, slider and visibility changes. Pointer/keyboard scrubbing temporarily pauses a playing orbit. Engines remain extinguished until weapons are fully stowed.
- Wireframe inspection, view reset and transparent PNG capture. Offscreen suspension, reduced-motion support, resource disposal, context-loss fallback and retry.
- Three interior views with official sources, an asymmetric four-image archive, accessible native lightbox with arrow-key navigation and focus return.

## Validation

- `npm test`: 165 passed (159 existing + 6 focused Atlas state/interlock tests).
- `npm run verify:asset`: both GLBs valid, with zero animation clips.
- `npm run generate`: passed; generated static output was tested in Chromium on a hardware RTX 4070 SUPER renderer using the full model.
- 60 browser assertions passed across content, playback, mechanical transitions, controlled visibility and context-loss recovery. A 175-frame deployment/stow sample confirmed zero thrust during every nonzero weapon deployment frame.
- Layout checks covered 1920×1080, 3440×1440, 1366×768 and 390×844 without horizontal overflow. All main/secondary/twin/quad families were checked in rendered views; the original fixed bridge armor is retained.
- Native background-tab throttling could not be conclusively measured because the automation browser kept `document.hidden=false`. Controlled visibility events and real offscreen suspension passed. This limit is recorded in `browser-qa.json`.
- Production build emitted existing nonfatal Nitro external-import warnings. No runtime page errors were reported during final static-build content/recovery checks.

## Assets and release scope

The original `odin.blend`, all versioned Blender geometry, both GLBs, textures and rig are unchanged. The new hero PNG is a WebGL render of that geometry, not an edited concept illustration. The official images and their source links are retained.

This is a new feature branch and release candidate for a PR against `cfdxkk/odin-web:main`. Production is not replaced by the review preview. The existing Sites identity and access configuration are unchanged.

Screenshots: `desktop-hero.png`, `mobile-hero.png`, `observatory.png`. Machine-readable evidence: `browser-qa.json`.
