# Four-stage Odin tour — v0.13.1-rc.1

The 12 introductions are condensed into four snapped stages: vehicle overview, main batteries and bow, secondary guns and bridge, then propulsion. Each stage has a short introduction, one detail sentence and two specification rows in both languages. Footer links point to the new stages; the official artwork archive and mountain footer follow the tour.

Changing stages moves the camera along a 2.8-second eased arc. Configuration changes animate from the current visible weapon pose instead of seeking straight to an endpoint. Deployment retains the 6.5-second mechanical stroke. Thrust fades before deployment and starts only after complete stowage. Reversing or skipping stages starts from the current pose. Two consecutive SCM views retain the deployed rig while the camera moves.

These are finite guide transitions, separate from continuous film playback. The user's pause preference is preserved. Playback buttons and slider actions take control of the transition; reduced-motion mode selects the destination immediately. Paused rendering stops when the transition settles, and the canvas does not render off screen. The existing approved weapon paths, Blender file and GLB assets remain unchanged.

## Validation

- `npm test`: 93 passed. New tests cover intermediate guide poses, native deployment duration, thrust interlocks, matching film-clock poses and interrupted reversals.
- `npm run verify:asset`: both GLBs valid, 214 meshes / 20 materials / 12 textures, zero animation clips.
- `npm run generate`: passed.
- [Browser evidence](browser-check.json): 28 successful checks, zero page errors. Real wheel snap; all three camera arcs sampled; animated deployment/stow; retained SCM pose; reversible transitions; persistent pause; slider pause/resume; language; gallery; mobile and reduced-motion behavior; idle/off-screen rendering stops.
- No horizontal overflow at 390, 800, 801, 1440, 2560 or 3440 px.
- [Mechanical review](articulation-check.json): 39 rendered poses covering upper/lower main batteries, mirrored side singles, bridge quads, forward/aft twins and bridge. 215 runtime joints; zero page errors.
- [Four guided views](guided-views.jpg), [mobile view](mobile-zh.png).

Source and artwork attribution are unchanged; see the [v0.13.0 source archive](../v0.13.0/README.md).
