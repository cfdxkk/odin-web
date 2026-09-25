"""Assemble the twelve Blender review stills into one 4 x 3 contact sheet."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
POSES_PATH = ROOT / 'work/v08-review/poses.json'
FRAMES_DIR = ROOT / 'docs/review/v0.8/frames'
OUTPUT = ROOT / 'docs/review/v0.8/main-battery-sequence.png'
POSES = json.loads(POSES_PATH.read_text(encoding='utf8')).get('poses', [])
if len(POSES) != 12:
    raise RuntimeError(f'Expected 12 poses, found {len(POSES)}')
COLS, ROWS = 4, 3
CARD_W, IMAGE_H, CAPTION_H, HEADER_H = 800, 533, 75, 104
CARD_H = IMAGE_H + CAPTION_H
canvas = Image.new('RGB', (COLS * CARD_W, HEADER_H + ROWS * CARD_H), '#0a111b')
draw = ImageDraw.Draw(canvas)


def font(size, bold=False):
    candidates = (
        ['C:/Windows/Fonts/msyhbd.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
        if bold else
        ['C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


title_font, frame_font, stage_font = font(48, True), font(29, True), font(25)
draw.text((34, 17), 'ANVIL ODIN  /  主炮展开动画审核', font=title_font, fill='#e7edf2')
draw.text((34, 72), 'v0.8 候选版 · 12 个展开阶段 · 固定机位 · 实际 JS 动作静帧 · 收拢沿相反顺序执行 · 尚未发布网站', font=font(19), fill='#9aaebe')
for slot, pose in enumerate(POSES):
    source = FRAMES_DIR / pose['file']
    if not source.is_file():
        raise FileNotFoundError(f'Missing rendered stage {slot + 1}: {source}')
    with Image.open(source) as opened:
        if opened.size != (1440, 960):
            raise RuntimeError(f'{source} is {opened.size}; expected 1440 x 960')
        still = opened.convert('RGB').resize((CARD_W, IMAGE_H), Image.Resampling.LANCZOS)
    x = (slot % COLS) * CARD_W
    y = HEADER_H + (slot // COLS) * CARD_H
    canvas.paste(still, (x, y))
    draw.rectangle((x, y + IMAGE_H, x + CARD_W - 1, y + CARD_H - 1), fill='#121e2a')
    draw.rectangle((x, y, x + CARD_W - 1, y + CARD_H - 1), outline='#284354', width=2)
    draw.text((x + 21, y + IMAGE_H + 15), f"{pose['index']:02d}   {round(pose['deployment'] * 100):03d}%", font=frame_font, fill='#e7edf2')
    draw.text((x + 225, y + IMAGE_H + 19), pose['label'], font=stage_font, fill='#9fc4d1')
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUTPUT, optimize=True)
print(f'Saved 4 x 3 sequence, {canvas.width} x {canvas.height}: {OUTPUT}')
