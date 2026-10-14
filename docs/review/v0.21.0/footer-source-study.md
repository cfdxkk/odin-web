# Footer print study

## Evidence from the author's Figma file

Read-only inspection of the [original Footers file](https://www.figma.com/design/4ukEOT8r7jlKIWdU3hh14X/Footers?node-id=1-146) on 2026-10-14 confirmed:

- The selected footer frame `1:146` is 1440 × 880 with background `#F7FDFA`.
- The mountain artwork is the image layer `image 16`, node `1:147`, at x=90, y=−132, sized 1260 × 1012.
- Its Properties panel exposes an **Image** fill and original-image download link (image hash `e350b90e86a45a709bfa5d2e59a238785d1dd2c3`). There is no separate noise/shader/effect control on the selected image.
- The visible artwork already contains the aligned print screen. The existing v0.17 inspection recorded a separate `#008E47` Color-blend overlay. Thus the grain visible in Figma is a pre-screened raster, not a live Figma noise effect we can transfer by copying a filter parameter.

The Figma connector could not return design context because it requires edit access. The signed-in browser allowed the read-only layer and property inspection above. Attempting the image download stalled and was abandoned; the original source image was not acquired, so its upstream authoring tool and exact screening algorithm are **not known**. No such provenance is claimed.

## Adaptation

The existing v0.19 ship-and-mountains composition is retained, without another AI redraw of Odin. A low-pass pass removes its incompatible etched mountain texture, then one amplitude-modulated circle screen renders the whole composition at the actual browser pixel resolution. Ship and mountains use the same samples, pitch, ink and falloff.

- Continuous-tone reduction: grayscale and 2.2 CSS-pixel blur, before sampling.
- Aligned dot spacing: 3.2 CSS pixels; no random positions or sizes.
- Ink: muted neutral gray, approximately `#C4C8C5`, on `#070B10`.
- The upper ridges fade gradually into the page; lower artwork remains above the footer links.
- Device-pixel rasterization avoids resizing a previously screened bitmap; rendering occurs only when the footer becomes visible or changes size.

The alternative v0.16.2 model-derived valley was compared and rejected: the smaller ship and smooth procedural hills repeat the composition problems the user already disliked. The preview at `/review/footer-screen-v0.21.0.html` keeps this alternative available for direct comparison, alongside the previous artwork.
