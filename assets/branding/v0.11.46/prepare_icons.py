"""Resize the generated transparent master into the shipped web assets."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[3]
image = Image.open(Path(__file__).with_name('odin-club-mark.png')).convert('RGBA')
assert image.getchannel('A').getextrema() == (0, 255)
# Ignore near-invisible alpha specks when choosing a crop; preserve all pixels
# inside that crop, with room for antialiased badge edges.
left, top, right, bottom = image.getchannel('A').point(lambda p: 255 if p >= 8 else 0).getbbox()
image = image.crop((max(0, left - 4), max(0, top - 4), min(image.width, right + 4), min(image.height, bottom + 4)))
folder = root / 'public' / 'images'
folder.mkdir(exist_ok=True)
header = image.copy()
header.thumbnail((160, 192), Image.Resampling.LANCZOS)
header.save(folder / 'odin-club-mark-v0.11.46.webp', lossless=True, method=6)
for name, size in [('icon', 32), ('touch', 180)]:
    glyph = image.copy()
    glyph.thumbnail((size - 4, size - 4), Image.Resampling.LANCZOS)
    icon = Image.new('RGBA', (size, size))
    icon.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    icon.save(folder / f'odin-club-{name}-v0.11.46.png', optimize=True)
