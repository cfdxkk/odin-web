"""Encode and fully decode-check an unfold/hold/fold/hold main-battery preview.

python tools/encode_animation_preview.py --version 0.8.1 --ffmpeg /path/to/ffmpeg
FFMPEG_BINARY or ffmpeg on PATH may replace --ffmpeg. MP4 defaults to
docs/review/vVERSION; optional --gif writes a large GIF only in ignored work/.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', required=True)
parser.add_argument('--work-dir')
parser.add_argument('--output-dir')
parser.add_argument('--ffmpeg', default=os.environ.get('FFMPEG_BINARY'))
parser.add_argument('--duration', type=float, default=6.5, help='Seconds per unfolding/folding motion')
parser.add_argument('--hold', type=float, default=.8, help='Seconds held at each endpoint')
parser.add_argument('--fps', type=int, default=30)
parser.add_argument('--gif', action='store_true')
args = parser.parse_args()
if args.duration <= 0 or args.hold < 0 or args.fps < 1:
    parser.error('Duration/fps must be positive and hold must be nonnegative')
ffmpeg = args.ffmpeg or shutil.which('ffmpeg')
if not ffmpeg:
    parser.error('ffmpeg was not found: pass --ffmpeg or set FFMPEG_BINARY / PATH')
ffmpeg = str(Path(ffmpeg).resolve()) if Path(ffmpeg).is_file() else shutil.which(ffmpeg)
if not ffmpeg:
    parser.error('The requested ffmpeg executable does not exist')
work = (ROOT / (args.work_dir or f'work/preview-v{args.version}')).resolve()
output = (ROOT / (args.output_dir or f'docs/review/v{args.version}')).resolve()
manifest = json.loads((work / 'render-manifest.json').read_text(encoding='utf8'))
if manifest['assetVersion'] != args.version or manifest['frameCount'] != 101:
    raise RuntimeError('Render manifest does not match the requested version and 101 samples')
paths = [work / 'frames' / frame['file'] for frame in manifest['frames']]
for frame, path in zip(manifest['frames'], paths):
    if hashlib.sha256(path.read_bytes()).hexdigest() != frame['sha256']:
        raise RuntimeError(f'Rendered frame changed after its manifest was written: {path}')
# One complete loop has 200 intervals: 100 unfolding and 100 folding.
indices = list(range(101)) + list(range(99, 0, -1))
durations = [args.duration / 100 for _ in indices]
durations[0] += args.hold
durations[100] += args.hold
lines = []
for index, duration in zip(indices, durations):
    # The manifest filenames are generated numeric names, avoiding ffconcat
    # quoting issues with arbitrary absolute paths or non-ASCII workspace names.
    if not re.fullmatch(r'frame-\d{4}\.png', paths[index].name):
        raise RuntimeError('Unexpected frame filename')
    lines.extend([f'file frames/{paths[index].name}', f'duration {duration:.9f}'])
lines.append(f'file frames/{paths[0].name}')
concat = work / 'preview-concat.txt'
concat.write_text('\n'.join(lines) + '\n', encoding='utf8')
output.mkdir(parents=True, exist_ok=True)
mp4 = output / 'main-battery-preview.mp4'
total_duration = 2 * (args.duration + args.hold)
subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0',
                '-i', concat.name, '-r', str(args.fps), '-vf', 'format=yuv420p', '-c:v', 'libx264',
                '-crf', '18', '-preset', 'fast', '-movflags', '+faststart', '-t', str(total_duration), mp4.as_posix()],
               cwd=work, check=True)
# Fully decode the MP4; do not report a successful preview based only on an
# encoder exit code or the existence of its output file.
decoded = subprocess.run([str(ffmpeg), '-hide_banner', '-i', str(mp4), '-f', 'null', '-'],
                         capture_output=True, text=True, errors='replace', check=True)
counts = re.findall(r'frame=\s*(\d+)', decoded.stderr)
if not counts or abs(int(counts[-1]) - round(total_duration * args.fps)) > 1:
    raise RuntimeError('Decoded MP4 frame count does not match its intended duration')
report = {key: value for key, value in manifest.items() if key != 'frames'}
report.update({'file': mp4.name, 'bytes': mp4.stat().st_size,
               'sha256': hashlib.sha256(mp4.read_bytes()).hexdigest(), 'codec': 'H.264/yuv420p',
               'fps': args.fps, 'unfoldSeconds': args.duration, 'foldSeconds': args.duration,
               'endpointHoldSeconds': args.hold, 'targetDurationSeconds': total_duration,
               'durationSeconds': int(counts[-1]) / args.fps,
               'decodedFrames': int(counts[-1])})
(output / 'animation-preview.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({'mp4': str(mp4), 'bytes': mp4.stat().st_size, 'decodedFrames': int(counts[-1])}))

if args.gif:
    from PIL import Image
    with Image.open(paths[0]) as first:
        width, height = first.size
    tile = (max(1, width // 4), max(1, height // 4))
    sample = Image.new('RGB', (tile[0] * 4, tile[1] * 4))
    for k, index in enumerate(range(0, 101, 7)):
        with Image.open(paths[index]) as src:
            sample.paste(src.convert('RGB').resize(tile), ((k % 4) * tile[0], (k // 4) * tile[1]))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    frames = []
    for path in paths:
        with Image.open(path) as src:
            frames.append(src.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE))
    # GIF stores time in centiseconds. Round cumulative times to avoid drift.
    gif_durations, elapsed, previous = [], 0, 0
    for duration in durations:
        elapsed += duration * 100
        current = round(elapsed)
        gif_durations.append((current - previous) * 10)
        previous = current
    gif = work / 'main-battery-preview.gif'
    sequence = [frames[index] for index in indices]
    sequence[0].save(gif, save_all=True, append_images=sequence[1:], duration=gif_durations,
                     loop=0, disposal=1, optimize=False)
    with Image.open(gif) as encoded:
        for index in range(encoded.n_frames):
            encoded.seek(index)
            encoded.load()
        print(json.dumps({'gif': str(gif), 'bytes': gif.stat().st_size, 'decodedFrames': encoded.n_frames}))
