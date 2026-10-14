# Swiss Odin page — v0.14.0-rc.1

The equipment-panel presentation is replaced with a Swiss typographic layout. Header, tour, archive and footer content align to a twelve-column grid. Self-hosted Inter uses only regular and bold weights, large left-aligned headings, small body text, black ink, warm off-white paper and the single accent `#DA291C`. Hardware fasteners, warning stripes, viewport corner marks and multicolor registration strips are removed from the header, model and archive. UI surfaces have no shadows, gradients or textures.

The ship and official artwork receive a monochrome presentation through CSS; original model paint, textures and art files remain intact. The gallery's source links open the original color artwork. The existing mountain footer, Odin illustration, official badge and footer colors are retained as the requested exception to the main page's restrained palette.

## Scrolling

The document has no CSS scroll snapping. Wheel navigation handles only events originating inside the four-stage ship tour, and advances once per gesture. The model stays pinned and existing camera/weapon transitions continue. At the first and last boundaries the wheel is returned to normal document scrolling. Returning from the archive first aligns the final tour stage. Manual exploration retains wheel zoom.

The artwork archive and footer use ordinary continuous scrolling. Language switching, explicit pause, slider drag behavior and reduced-motion support remain available. The preview stops drawing GPU frames when paused or off screen.

## Validation

- `npm test`: 94 passed, including tour boundary release and return alignment.
- `npm run verify:asset`: both GLBs valid; 214 meshes, 20 materials, 12 embedded textures and zero animation clips.
- `npm run generate`: passed.
- [Tour and interaction evidence](browser-check.json): 28 successful checks, zero page errors.
- [Style and wheel evidence](style-check.json): 20 successful checks. Twelve-column alignment, Inter regular/bold, left alignment, title/body size contrast, exact RGB palette, monochrome imagery, retained footer, no equipment decoration, shadows or gradients. Real wheel deltas remain 230 px in the archive and 180 px in the footer, with no snap or stage interception.
- Nine widths from 320 to 3440 px have no horizontal overflow.
- [Mechanical review](articulation-check.json): 39 poses across main batteries, mirrored singles, bridge quads, forward/aft twins and bridge. All 215 runtime joints remain present; no page errors.
- Native Blender/GLBs, approved weapon motion modules and the mountain footer asset are unchanged.

Screenshots: [Chinese overview](desktop-zh.png), [English overview](desktop-en.png), [art archive](gallery-zh.png), [retained footer](footer-zh.png), [ultrawide](ultrawide-en.png), [mobile](mobile-zh.png), [four tour views](guided-views.jpg).

Fonts: [Inter OFL](../../../public/fonts/inter-OFL.txt), [footer Inter Tight OFL](../../../public/fonts/inter-tight-OFL.txt). Official artwork and footer provenance remain documented in the [v0.13.0 source archive](../v0.13.0/README.md).
