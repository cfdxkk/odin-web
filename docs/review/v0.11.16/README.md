# v0.11.16 bow armor pivot alignment

The bow receiver restored from `odin.blend` was translated 3.45 model units forward and 0.55 upward in v0.11.12. The new flank-derived bow armor in v0.11.15 was accidentally anchored to its earlier v0.10 slot frame. This revision translates only the six bow shutter joints and the bow front-cap joint by that same rigid receiver offset. Their hinge-edge and closed-seam metadata follows the joints. No armor mesh vertices, hinge angles, front-cap travel, gun motion, hull, stern or other weapon joints change.

| Bow pose | Browser capture |
| --- | --- |
| Closed before | [side](bow-before-closed-side.png) |
| Closed after | [side](bow-after-closed-side.png), [oblique](bow-after-closed-oblique.png), [top](bow-after-closed-top.png), [seam side](bow-seam-closed-side.png), [seam oblique](bow-seam-closed-oblique.png) |
| Folding after | [side](bow-after-folding-side.png), [seam oblique](bow-seam-folding-oblique.png) |
| Deployed after | [side](bow-after-deployed-side.png) |

The unchanged stern remains visible in [side](stern-closed-side.png) and [oblique](stern-closed-oblique.png) views. Browser review also covered the bow's folding and deployed oblique/top poses, the keel, flank batteries, bridge quad and armor, both main batteries and an aft twin. An exported-asset diff confirmed that every non-bow mesh buffer and joint, including PDC and defense mounts, is unchanged. The dedicated test compares all seven bow joint positions against the source slot frame plus the receiver's stored displacement. `npm test`, `npm run verify:asset`, and `npm run generate` passed.
