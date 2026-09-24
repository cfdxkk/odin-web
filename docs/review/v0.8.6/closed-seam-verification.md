# v0.8.6 closed-seam verification

**Result: the visible continuous red openings are removed in the final close view.** Normal narrow mechanical assembly seams remain; this report does not claim welded or mathematically opaque joints.

Verified editable asset SHA256: `25e46353b858967e064b6af5c0ba406a127eae186cfad058f960ef02377133aa`.

The inspected 1920×1280 image is `final-closed-edge.png`, rendered from that exact asset and the final runtime pose. Image SHA256: `28bf6e5b9692281b215a8e23f4c86fc8351fad2148943817f049f1b1c276c283`. Its image hash, orthographic camera, all 17 targeted ray results and pixel evidence are included in `closed-seam-verification.json`.

| Check | Final result |
|---|---|
| Seven original aft red-line pixels | All seven rays hit the grey aft armor, at the expected exterior height. |
| Ten earlier visible Nose defect pixels | Eight rays hit the grey Nose surface; two enter the remaining microscopic mechanical seam. |
| Rendered Nose tip region and surrounding seam band | **0 clearly red pixels**; the previous 45-pixel continuous red line and neighboring marks are gone. |
| Rendered aft/main joint region | One isolated red pixel at (648,396), shared by both region records; no continuous red opening. |

Pixel assessment checks a three-pixel band around the earlier dense boundary sweep's recorded entry positions, plus the entire Nose target region X1500–1605/Y710–756 so a shifted line cannot pass as a repair. A clearly red pixel is defined as R≥G+6, R≥B+4 and R≥1.25G. The earlier candidate showed 50 such Nose pixels, including a 45-pixel connected line; the final shows none.

The two remaining Nose ray entries are at (1557,733) and (1566,738), and are transparently recorded. They do not produce clearly red rendered pixels in the final view. Fine mathematical point rays can pass through an intentional fit clearance even when antialiasing and surrounding fitted grey edges produce an ordinary narrow assembly seam. No additional geometry change is requested for these isolated samples.

The check uses the final v0.8.6 closed runtime pose from `work/preview-v0.8.6/poses.json`, captured from the final exported GLB. Image and camera provenance are committed in `final-seam-renders.json`. The camera, editable geometry, exported model and pose metadata all refer to the final v0.8.6 revision. This is a close-camera closure verification, not a proof covering every possible viewing angle or every mathematical point along all ship joints.

