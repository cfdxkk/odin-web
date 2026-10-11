# Aft twin receiver seam and shell-section correction

At NAV, the v0.11.35 covers left an inclined wedge at the fore seam and an
exposed serrated lower edge. The four-corner approximation used the forward
edge of the fore rim strip and an intermediate floor point for station 6/8.
Its uniform normal extrusion also placed the inner lower edge below the
source hull return, so an average roof thickness did not reproduce the
visible side-wall section.

The four covers now follow the full outer and inner fore/aft cut profiles of
the untouched `odin.blend` receiver, including all 56 paired lower edge
sections per aperture. The lower return remains wider and differently angled
than the roof rim, matching the adjoining hull instead of averaging both into
one slab. The fore/aft joints retain only 0.008 source units of clearance.
The small lower serrations affect only the narrow rim; the broad faces have
continuous shading.

`source-geometry.json` verifies 482 source receiver vertices against the
original Blender file. All six outer/inner receiver contours on each gate
remain within 0.00803 source units; the complete lower section vectors agree
within 0.00003. Its old-cover controls reject both the old end profiles and
the uniform extrusion. Each gate is a closed shell. The fixed hull, the
other 528 meshes, and all 207 joint transforms and motion properties are
unchanged. The original file remains unchanged; editable geometry is saved
in `assets/blender/odin_articulated_v0.11.36.blend`.

Validation: `npm test`, `npm run verify:asset`, and `npm run generate`, plus
401 actual-mesh poses per cover, gun scan endpoints, rendered closed seams
from oblique/side/top views, and complete gate deployment and reverse seeks.
Main, secondary, defense/PDC, bridge quad arms and bridge armor are also
reviewed at both endpoints. Both exported GLBs contain zero animation clips.
`browser-check.json` and the adjacent screenshots record the final render.
The temporary checking browser is closed after review, leaving one static
preview service and the user's review tab.
