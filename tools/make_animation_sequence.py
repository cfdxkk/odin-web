"""Make a 4 x 3 sequence sheet from twelve frames of a rendered JS preview.

python tools/make_animation_sequence.py --version 0.8.1
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', required=True)
parser.add_argument('--work-dir')
parser.add_argument('--output-dir')
args = parser.parse_args()
work = ROOT / (args.work_dir or f'work/preview-v{args.version}')
output = ROOT / (args.output_dir or f'docs/review/v{args.version}')
manifest = json.loads((work / 'render-manifest.json').read_text(encoding='utf8'))
if manifest['assetVersion'] != args.version or manifest['frameCount'] != 101:
    raise RuntimeError('Render manifest does not match the requested version and 101 samples')
stages = [(0, '完全收拢'), (5, '护甲脱开接缝'), (10, '前盖准备前移'),
          (16, '主护甲向外让位'), (22, '后片沿斜轴下翻'), (30, '护甲接近展开终点'),
          (34, '护甲让位完成'), (45, '炮管调平'), (60, '炮塔升起'),
          (75, '三根炮管同步伸出'), (90, '炮管接近伸出终点'), (100, 'SCM／战斗模式')]
version_numbers = tuple(int(part) for part in args.version.split('-', 1)[0].split('.'))
if version_numbers >= (0, 8, 3):
    stages = [(0, '完全收拢'), (5, '护甲脱开接缝'), (10, '前盖准备前移'),
              (16, '主护甲向外让位'), (22, '后片沿斜轴下翻'), (30, '外装甲接近展开终点'),
              (34, '外装甲让位完成'), (45, '侧炮就位，等待共同抬升'),
              (60, '炮管与护罩同步抬升'), (75, '同步抬升与三管伸长'),
              (90, '抬升与伸长接近终点'), (100, 'SCM／战斗模式')]
card_w, caption_h, header_h = 800, 75, 104
image_h = round(card_w * manifest['height'] / manifest['width'])
card_h = image_h + caption_h
canvas = Image.new('RGB', (4 * card_w, header_h + 3 * card_h), '#0a111b')
draw = ImageDraw.Draw(canvas)


def font(size, bold=False):
    candidates = (['C:/Windows/Fonts/msyhbd.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
                  if bold else ['C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


draw.text((34, 17), 'ANVIL ODIN  /  主炮展开动画预览', font=font(48, True), fill='#e7edf2')
draw.text((34, 72), f'v{args.version} 候选版 · 12 个采样姿态 · 固定机位 · 实际 JS 动作 · 完整展开与收拢请播放 MP4',
          font=font(19), fill='#9aaebe')
for slot, (index, label) in enumerate(stages):
    entry = manifest['frames'][index]
    source = work / 'frames' / entry['file']
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
        raise RuntimeError(f'Rendered frame changed after its manifest was written: {source}')
    with Image.open(source) as image:
        still = image.convert('RGB').resize((card_w, image_h), Image.Resampling.LANCZOS)
    x, y = (slot % 4) * card_w, header_h + (slot // 4) * card_h
    canvas.paste(still, (x, y))
    draw.rectangle((x, y + image_h, x + card_w - 1, y + card_h - 1), fill='#121e2a')
    draw.rectangle((x, y, x + card_w - 1, y + card_h - 1), outline='#284354', width=2)
    draw.text((x + 21, y + image_h + 15), f'{slot + 1:02d}   {index:03d}%', font=font(29, True), fill='#e7edf2')
    draw.text((x + 225, y + image_h + 19), label, font=font(25), fill='#9fc4d1')
output.mkdir(parents=True, exist_ok=True)
path = output / 'main-battery-sequence.png'
canvas.save(path, optimize=True)
print(json.dumps({'file': str(path), 'dimensions': canvas.size, 'bytes': path.stat().st_size}))
