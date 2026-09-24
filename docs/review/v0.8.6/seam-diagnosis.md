# v0.8.6 closed seam audit (read-only)

## Actual through-gap: aft armor lower rim

Seven red pixels in `baseline-v085-closed-edge.png`, from (510,292) to (630,382), cast through the upper seam and hit original fixed bay floor `holo.001`, polygon **19352**, material **Odin_Bay_Primer**, at Z=32.045–32.443. The closure therefore really is open here; it is not a shading-only line.

At the aft armor plane the opening lies approximately X=11.758→11.203, Y=108.341→115.651, Z=39.411→38.841 (asset source coordinates, near/starboard side). Adjacent aft-edge to hull height offsets are:

| Seam Y | Aft edge above fixed hull |
|---|---:|
|108.341|0.1973|
|109.559|0.1997|
|110.757|0.1988|
|111.975|0.1914|
|113.197|0.1591|
|114.436|0.1048|
|115.653|0.0517|

Relevant fixed lip faces are 48354, 89890, 185368; corresponding aft faces around 1319→1246. See `aft-through-gap-sections.json` for exact paired points. The v0.8.5 tool reprojects old outer-edge XY coordinates onto a changed planar aft surface. That makes the old outer boundary float above the fixed hull. It needs a newly intersected plane/hull boundary, not a smaller constant XY clearance, a different paint color, or bending the main flat armor face.

Suggested minimal structural solution: retain the aft armor plane and fit its free outer perimeter to that plane's actual intersection with the unchanged fixed hull, with a narrow consistent clearance and an appropriate thickness bevel. Re-evaluate the shared main/aft end point and the 130-degree sweep after fitting. If no intersection exists within the permitted boundary, the chosen plane/end anchors need adjustment; projecting the existing boundary upward is insufficient.

## Forward serrated edge: real external step, not an open sightline

Across Y=118–166, reference-lip screen rays and rays 1–8 pixels outboard hit the fixed **grey** hull lips/serrated sloping faces, not red inner walls or distant hull surfaces. `near-seam-sections.json` contains vertical cross sections of moving armor and fixed hull independently, plus per-pixel scene ray hits. It avoids relying solely on nearest-surface distance.

The fixed exterior lip falls away from the moving leaf edge more sharply toward the bow. At 0.5 source units outboard of the reference lip, fixed hull height minus lip height is: Y135 +0.161; Y140 -0.308; Y143 -0.106; Y145.5 -0.163; Y148 -0.209; Y150.5 -0.231; Y153 -0.230; Y156 -0.355; Y158 -0.444; Y160 -0.456; Y162 -0.456; Y164 -0.458. This explains increasingly large apparent triangular gaps even though the immediate mating-point clearance is only 0.035.

The visible gray triangular step faces are existing hull polygons 187804, 187803, 187802, 163309, 170381, 187800, 167841, 43184, 178681, 100414, 155208. Their world-facing normals and exact vertex IDs are in `fixed-serrated-step-faces.json`. Toward the bow their outward slope gets steeper (e.g. normals transition from (0.499,-0.372,0.782) to (0.803,-0.103,0.587)). Correcting the appearance must account for this original step profile instead of globally offsetting the moving leaf or merely reducing a .035 gap.

No Blend, exported asset, or production tool was modified by this audit.

## Reproducing the diagnostic rays

All baseline rays use `assets/blender/odin_articulated_v0.8.5.blend` and the actual runtime deployment=0 joint pose from `work/preview-v0.8.5/poses.json`. Image coordinates are pixel centers with a top-left origin.

Aft through-gap camera: entry `baseline-v085-closed-edge.png` in `work/v086-review/baseline-v085-seam-renders.json`; 1920×1280 orthographic render, camera location (4.114999771,6.380000114,5.389999866), Euler rotation (0.907830179,0.000000056,2.466851711), ortho scale 0.800000012. Reproduce with `work/v086-review/raycast-aft-red.py`; pixel locations are stored in `aft-red-pixels.json`. Exact scene ray hits and the derived armor-plane aperture coordinates are in `aft-red-ray-hits.json` and `aft-through-gap-sections.json`.

Forward/entire lower-edge section camera: `docs/review/v0.8.5/seam-detail-renders.json`; image `closed-seam-detail.png`, 1920×1280. Reproduce with `work/v086-review/section-near-seam.py`. This samples source Y=118,124,130,135,138,140,143,145.5,148,150.5,153,154.5,156,158,160,162,164,166, at each measured original lip point and eight pixels either side in screen Y. Full points and face results are in `near-seam-sections.json`. Sampled moving/fixed vertical intersections use source X offsets -.1,-.04,-.02,0,.02,.04,.1,.2,.5 from the measured lip, ray direction (0,0,-1).

This does not claim every possible gap is sampled, or that the remaining issues are color problems. The positive diagnosis of the aft opening uses observed rays that hit the bay floor. The forward gray-step diagnosis applies to the sampled locations and is supported independently by the fixed polygon geometry and cross sections.

Final candidate verification is pending the geometry agent's frozen asset. It must repeat the baseline pixels and add offset rays along the candidate's actual changed seam, since filling the old pixel alone does not prove the new perimeter is closed.
