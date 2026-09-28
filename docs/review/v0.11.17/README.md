# v0.11.17 axial turret review

The bow and stern single-gun mounts keep their existing gun, housing, receiver,
and hull meshes. The seven covers at each bay were rebuilt from the accepted
`SideBattery_1_Starboard` meshes. The breech pair remains shorter and
trapezoidal but reaches closer to the gun-root armor; the bow crown follows the
lower marked hull line, and the stern crown meets its housing. Both front caps lift
off the closed seal before moving toward the muzzle. The bow receiver's
accepted rigid position is retained.

The front caps continue their third leaves' side-view crown slope. The bow's
six hinged covers and nose cap were lowered together without changing any
contact hinge; side, oblique and head-on review images show the final fit.
The bow's first breech-side leaf has a slightly shorter inboard rear corner
to clear the turret housing; its forward edge still meets the second leaf.
The enlarged `bow-seam-*` images show the closed fit and early folding pose.

The bow gun still follows `odin.002` frames 30–56 from the untouched
`odin.blend`. The stern gun now follows its own `odin.026` frames 11–37,
including the original location and Euler-channel motion. Both actions are
reproduced in Nuxt/Three.js; exported GLBs have no animation clips.

The review page has a new **正视** camera option. The included screenshots show
the closed side, oblique, and head-on silhouettes, an intermediate bow fold,
the deployed stern gun, and spot checks of the keel, flank, bridge quad, and
main battery. The other defense/PDC systems are also covered by the rig tests.

Validation: `npm test` (43 passing), `npm run verify:asset`, and
`npm run generate`. Blender signatures for `odin.002`, `odin.003`, `odin.026`,
`odin.027`, both axial mounts, the bow receiver, and both main-battery mounts
match v0.11.16 exactly.
