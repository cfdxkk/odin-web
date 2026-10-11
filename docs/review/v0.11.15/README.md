# v0.11.15 axial seven-piece armor review

The bow and stern single-gun bays each have six hull-edge hinged leaves (three per side) and one translating nose assembly. The editable skins and their red inner backing are copied from the approved SideBattery 1 flank armor, then fitted to the two axial slot frames. The previous axial cover meshes are not reused. The breech-end leaves have a shorter, tapered inboard edge; the three pairs meet along continuous seams and a narrow flat crown.

On closing, the existing gun rotation finishes first. The pair nearest the muzzle closes first, followed by the middle and breech pairs; the nose assembly then slides and settles into its seat. The bow retains the original `odin.blend` gun keyframes, the stern retains its prior gun motion, and both turret mounts stay fixed throughout. The exported GLBs contain static joints and no animation clips.

| Station | Closed | Folding | Deployed | Top view |
| --- | --- | --- | --- | --- |
| Bow | [oblique](bow-closed-oblique.png) | [oblique](bow-folding-oblique.png) | [oblique](bow-deployed-oblique.png) | [closed](bow-closed-top.png) |
| Stern | [oblique](stern-closed-oblique.png) | [oblique](stern-folding-oblique.png) | [oblique](stern-deployed-oblique.png) | [closed](stern-closed-top.png) |

The Blender builder checks both corners of every neighboring closed seam before saving. Browser review covered closed, folding and deployed poses from side, oblique and top angles for both guns. `npm test` (38 passing), `npm run verify:asset`, and `npm run generate` passed.
