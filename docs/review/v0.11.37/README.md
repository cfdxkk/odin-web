# Complete aft twin gate thickness

The v0.11.36 gates stopped at the first inner shell layer. In an elevated
view, their upper edges were visibly thinner than the adjoining fixed hull.
The four 5–8 gates now reach the innermost original hull edge, with both
intermediate layers retained around their borders. The upper section spans
1.042–1.077 source units, approximately twice the former first-layer section.
The exterior fit and the 0.008-unit end clearances are retained.

The station 6/8 aft roof boundary follows the actual original edge between
120851 and 120854. Internal end-cut vertex 120853 is below that edge and is
not used as the roof crown, preventing a shallow valley in the complete lip.

`source-geometry.json` verifies 950 receiver vertices and 22 actual roof edges
against untouched `odin.blend`, including both mirrored sides. Bidirectional
roof-boundary checks and complete upper/lower section vectors agree within
0.00003 source units. The former first-layer gate fails the complete thickness
check by more than 0.50 units. All four shells are watertight. All other 528
meshes and all 207 joint transforms and motion properties are unchanged.
Editable geometry is saved in `assets/blender/odin_articulated_v0.11.37.blend`.

Validation: 63 tests, asset verification, static generation, 401 actual-mesh
motion samples per gate, and both gun scan endpoints. The browser review
covers closed upper rims, side/top views, deployment and reverse seeks, plus
main, secondary, defense/PDC, bridge quad arms and bridge armor at both ends.
Both GLBs have zero animation clips. `asset-hashes.json` binds the reports to
the native and exported models; `browser-check.json` records rendered checks.
The temporary checking browser is closed, leaving one paused user preview
and one static preview service.
