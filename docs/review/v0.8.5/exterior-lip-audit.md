# v0.8.5 exterior lip / closed red line audit

The closed-preview red line is an incorrectly painted existing exterior lip, not a long physical gap into the cavity. Five sampled red pixels at (378,355), (418,385), (459,415), (500,445), (521,460) all hit `holo.001` polygon **185047** directly. Its outward source-space normal is (-0.314699, 0.030679, 0.948695). The opposite lip is polygon 155029. Both were light grey in v0.8.3 and were accidentally included in v0.8.4 because its normal filter only checked the inward X component.

The main sliding panels already follow the actual original opening. Dorsal lateral margin: 0.03494–0.03500 source units; height offset: 0.00492–0.00500. Dorsal distance to actual hull: 0.02712–0.03531. Ventral lateral margin: 0.03499–0.03500; height offset: 0.00500; distance to hull: 0.03408–0.03533. These edges should not be widened or supplemented with fabricated seals to hide a material-selection bug.

The original planar aft-leaf outer rim is 0.03200–0.05648 from the dorsal hull and 0.01843–0.05359 from the ventral hull. The aft leaf's angle/meeting edge is being revised separately; this material audit makes no geometry changes there.

`tools/finish_armor_lips_v085.py` restores the exact v0.8.3 finish on 18 dorsal and 23 ventral outward-facing rim/bevel faces (outward Z normal >0.8). It preserves every actual red cavity wall, every other face assignment and all mesh vertices. It creates no new geometry. The long red line disappears in `lip-corrected-00.png`; the requested inner wall remains deep red in `lip-corrected-45.png` and `lip-corrected-62.png`.

Evidence: `red-seam-ray-hits.json`, `original-lip-materials.json`, `outer-seam-audit.json`, `exterior-lip-finish.json`.
