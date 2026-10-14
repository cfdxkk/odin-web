# Fixed-mark footer screen

The v0.21 circular, variable-radius AM screen has been removed. The new treatment follows the user's description of coarse, woven, ordered print; it does not claim to reproduce the original Figma asset's unknown authoring algorithm.

## Rendering

- Existing v0.19 composition is retained, with no further redraw of Odin.
- Ship and landscape pass through the same 2.2 CSS-pixel low-pass/grayscale treatment.
- Every visible mark has the same square footprint: 2.688 × 2.688 CSS pixels, on a 3.2-pixel pitch.
- A repeating 4 × 4 Bayer matrix chooses between four gray ink levels. Intermediate tones form sparse squares, checkerboard and interlocking cross-like arrangements. Neither the mark size nor its position is random or luminance-dependent.
- The 12.8-pixel pattern unit produces a coarser woven texture. Both 2.8 and 3.2-pixel pitches were compared before selecting the latter.
- The upper atmosphere changes ink intensity, not mark dimensions. A raised dark threshold removes near-black source noise so it does not become a field of bright floating marks above the mountains.
- The screen is rasterized into native device pixels and recalculated only on visibility/size changes. It is not a bitmap pattern stretched by CSS.

## Checks

Three focused tests verify the complete periodic 4 × 4 ordering, monotonic gray levels, and the exact checkerboard arrangement at the midpoint between two inks. Browser previews at 1920 × 1080, 3440 × 1440, 1366 × 768 and 390 × 844 showed no horizontal overflow. Screenshots include a 100% detail of the ship and mountain texture.

Comparison preview: `/review/footer-weave-v0.22.0.html`. The previous circular screen is available through its second button solely for comparison.
