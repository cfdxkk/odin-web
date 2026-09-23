"""Assemble web-authored static rig poses into review images (no source footage)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
source = root/'work/rig-review'
target = root/'docs/review'
target.mkdir(parents=True, exist_ok=True)
try:
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
except OSError:
    font = ImageFont.load_default()

def sheet(name, rows, stages, width):
    tile_height = round(width * 2/3)
    header = 35
    canvas = Image.new('RGB', (width*len(stages), (tile_height+header)*len(rows)), '#17212a')
    draw = ImageDraw.Draw(canvas)
    for row, (view, label) in enumerate(rows):
        for col, (stage, stage_label) in enumerate(stages):
            src = Image.open(source/f'{view}-{stage:.2f}.png').convert('RGB')
            src = src.resize((width, tile_height), Image.Resampling.LANCZOS)
            x = col*width; y = row*(tile_height+header)
            canvas.paste(src, (x, y+header))
            draw.text((x+12, y+6), f'{label}   {stage_label}', fill='#e5ecf2', font=font)
    canvas.save(target/name, quality=90, optimize=True, subsampling=0)
    print(target/name)

stages=[(0,'CLOSED'),(.20,'ARMOR CLEARING'),(.34,'BAY CLEAR'),
        (.5,'GUN LIFT'),(.75,'CRADLE RISE'),(1,'SCM READY')]
width=800;tile_height=round(width*2/3);header=35
canvas=Image.new('RGB',(width*3,(tile_height+header)*2),'#17212a');draw=ImageDraw.Draw(canvas)
for i,(stage,label) in enumerate(stages):
    src=Image.open(source/f'main-rear-{stage:.2f}.png').convert('RGB').resize((width,tile_height),Image.Resampling.LANCZOS)
    x=(i%3)*width;y=(i//3)*(tile_height+header)
    canvas.paste(src,(x,y+header));draw.text((x+12,y+6),f'{stage:.0%}   {label}',fill='#e5ecf2',font=font)
canvas.save(target/'main-battery-sequence.jpg',quality=92,optimize=True,subsampling=0)
sheet('main-armor-guide.jpg',[('main-top','FIVE-PIECE ARMOR')],[(0,'CLOSED'),(.10,'LIFT / CLEAR'),(.20,'SLIDING')],800)
sheet('articulation-stages.jpg',
      [('main','DORSAL MAIN'),('bridge','BRIDGE'),('quad','QUAD GUN'),
       ('bridge-rear','REAR ARMOR'),('ventral','VENTRAL MAIN'),
       ('defense','PDC'),('side','SIDE PROFILE'),('stern','AFT DOOR'),
       ('single','SINGLE GUN')], [(0,'0%'),(.5,'50%'),(1,'100%')], 550)
