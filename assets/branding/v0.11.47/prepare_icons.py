"""Resize the unmodified official badge for browser icons."""
from pathlib import Path
from hashlib import sha256
from PIL import Image

root = Path(__file__).resolve().parents[3]
folder = root / 'public' / 'images'
source = folder / 'odin-founders-badge-v0.11.47.png'
assert sha256(source.read_bytes()).hexdigest() == '60987981b7d41739304ad8cece78df2bdbd148f370a4dacc347e47941a2d7cfc'
image = Image.open(source).convert('RGBA')
for name, size in [('icon', 32), ('touch', 180)]:
    image.resize((size, size), Image.Resampling.LANCZOS).save(folder / f'odin-founders-{name}-v0.11.47.png', optimize=True)
