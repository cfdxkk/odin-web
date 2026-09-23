# Articulation review — v0.6.0

`main-armor-parts.png` identifies the five pieces: red and pink are the two long side skins, black and yellow are the aft skirts below the gun shrouds, and green is the short wedge at their forward end, in the position marked in the user's close-up. The farther foredeck is fixed and intact. Review colors are not saved to the asset.

`main-battery-sequence.jpg` shows 0%, 20%, 34%, 50%, 75% and 100% deployment. `main-armor-guide.jpg` isolates the first clearance stages. `articulation-stages.jpg` shows nine views at 0%, 50% and 100%. These are actual `createOdinRig()` poses evaluated against the exported GLB hierarchy and applied to the separate Blender copy. Workbench lighting exposes geometry; these are not final PBR web screenshots. No Blender animation is exported.

Rows: dorsal main battery, front bridge armor, bridge quad close-up, rear bridge armor, ventral battery, deck defense, side profile, original aft door and bow single battery.

```bash
node tools/review_rig_poses.mjs
blender -b assets/blender/odin_articulated_v0.6.0.blend --python tools/check_main_clearance.py
blender -b assets/blender/odin_articulated_v0.6.0.blend --python tools/render_rig_review.py
blender -b assets/blender/odin_articulated_v0.6.0.blend --python tools/render_armor_parts.py
python tools/make_rig_review_sheet.py
```

## Reference and reconstruction

- The [RSI Odin page](https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin) main-battery clip (`ns6umeu6gb7w5`, 0–3.0 seconds) shows the long ribbed armor translating without pivoting. The v0.6 side skins follow the source roof slope with polygonal edges around the shroud and front cap. They move outboard along the sloping exterior, then descend below the hull lip, avoiding the stowed barrels. The original serrated deck lip stays fixed. The short cap lifts over its seal, then slides toward the bow. Its location was corrected from the farther foredeck to the small wedge in the user's second annotation.
- All five covers are parked by 34% deployment. Gun leveling starts at 36%, followed by barrel and cradle rise and the two small outer-tube telescope movements. Stowing evaluates exactly the same paths in reverse, so the guns settle before armor closes. The full transition lasts 6.5 seconds. Original recessed hull faces replace the old rectangular bay floor and rails that projected through the narrowing exterior.
- The black/yellow aft skirts from the user's final annotation are separate original hull surfaces under the gun shrouds. Their cut boundaries retain the source surface and UVs; the moving skins replace those faces rather than stacking new plates over fixed armor. These two joints translate down/out before the gun rises and remain parented to the hull. Each dorsal/ventral battery now has five covers, ten total.
- The same page's quad clip (`meqm0flrf1683`) shows parallel gun axes during deployment. The previous 180-degree barrel flip is removed. The gunner pod travels only eight source units; the individual gun assemblies slide out after it. Slow aiming starts only after deployment.
- Original single-battery vented armor skins are separated from the hull for three paired shutters. Their bearing/link geometry remains in the bay. The cover leaves clear before gun elevation, and close after retraction.
- [SCL at 48:33](https://www.youtube.com/watch?v=CFoQp6wRjPo&t=2913s) shows the bridge blast shields. The front skirt was still fused into the hull in earlier exports, so animating the roof parts did not expose the bridge. That original skirt is now separated and folds/slides over the roof; rear louvers retain their own hinges.
- [SCL at 51:48](https://www.youtube.com/watch?v=CFoQp6wRjPo&t=3108s) helps identify the aft closure. The misplaced replacement is removed. Hidden original objects `holo.025` and `holo.026` are recovered with their original world transforms; their door/frame edges match without a guessed placement.
- Twin mounts use the inverse of their source orientation before applying a small upward aim and varied headings. Main and single-barrel guns do not idle-scan.

The [SCL video at 5:48](https://www.youtube.com/watch?v=CFoQp6wRjPo&t=348s) discusses the Odin's armament, but the linked timestamp does not provide the close-up deployment cycle. The RSI page's main-battery clip provides that fixed-camera view, including the closing sequence at roughly 5.3–7.4 seconds. Exact internal guides remain unavailable, so the sliding distance and hidden deck cassette are fan-art estimates measured against the visible plate motion.

`main-clearance.json` records triangle-surface intersection checks at 101 actual JS deployment poses. It tests all ten armor pieces against their bank's barrels, shrouds and mounts, plus every pair of armor pieces in each bank: 30 assembly pairs per pose. No intersections were detected. The report includes asset and rig-code hashes. This is sampled exterior mesh clearance, not a continuous collision proof or validation of unavailable internal ship structure. Closing retraces the same poses.

The original file is unchanged. The versioned Blender copy has no animation actions; both GLBs have zero clips. All 19 tests pass, including cover clearance before gun rise, lift-before-slide cap travel, rigid reversible side plates, constant quad barrel orientation, short pod travel, independent outer tubes, bridge movement, pause intent, camera continuity and exhaust interlocks. Both asset verification and Nuxt static generation pass. Browser QA checks the PC high-quality renderer, free exploration and the deployment sequence.

![Five-piece location key](main-armor-parts.png)

![Five-piece plan view](main-armor-parts-top.png)

![Early armor clearance](main-armor-guide.jpg)

![Static mechanism review](articulation-stages.jpg)

![Main battery deployment sequence](main-battery-sequence.jpg)
