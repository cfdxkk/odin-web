# Footer refinement and backup

Before editing, v0.22's renderer, screen helper, layout CSS, footer component, review screenshot and hashes were saved in [`footer-backup`](./footer-backup/README.md). The source v0.19 WebP is unchanged and remains available. The preview at `/review/footer-v0.23.0.html?mode=backup` executes the frozen v0.22 renderer and helper, compiled independently of the current version, so its appearance remains a usable comparison.

## Illustration

The built-in Imagegen tool edited the existing v0.19 composition in place conceptually, saved non-destructively as a new asset. It raised the existing ship above the mountain ridge and filled its former position with the surrounding valley. The accepted output preserves the ship's main silhouette, perspective, mast, hull and engine layout, with no new ship design requested.

- Exact prompt: [`footer-image-prompt.txt`](./footer-image-prompt.txt).
- Generated master: `assets/illustrations/v0.23.0/odin-raised-master.png`.
- Delivery asset: `public/images/odin-mountain-footer-v0.23.0.webp` (format conversion only; the generated composition is unaltered).
- Earlier source: `public/images/odin-mountain-footer-v0.19.0.webp`, unchanged.

## Native print treatment

- Fixed square-mark pitch increased from 3.2 to 3.8 CSS pixels; the mark itself is now 3.192 pixels wide. The 4×4 gray-level ordering remains unchanged.
- Disconnected, faint source flecks are filtered on the continuous tone field **before** screening. A second support pass removes very faint tips that are connected to the horizon in continuous tones but would become isolated first-level ink squares after screening. It retains either broad local support or a ridge continuing through the sample, so thin distant mountain lines and bright ship details survive.
- The far-field fade spans a longer vertical interval, using `smooth((heightFraction + .12) / .6)`. This keeps the raised bridge silhouette legible while the surrounding distant ridges dissolve gradually. Only ink intensity fades; mark size remains fixed.
- There is still one shared low-pass and ordered screen across the whole composition, not separate textures for ship and landscape.

Seven focused screen tests pass, including removal of isolated weak specks and threshold-created horizon tips, retention of thin faint ridges and preservation of a small bright ship feature. Browser comparison screenshots are captured from the real old/new renderer code.
