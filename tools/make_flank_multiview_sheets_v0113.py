from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

R=Path(__file__).resolve().parents[1]
src=R/'work/v0113-review/multiview'
dst=R/'work/v0113-review/sheets';dst.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
for mount in ['SideBattery_1_Starboard','SideBattery_1_Port','SideBattery_3_Starboard','SideBattery_3_Port']:
    canvas=Image.new('RGB',(2200,1125),'#151c22');draw=ImageDraw.Draw(canvas)
    for row,pose in enumerate(['0.00','0.48','1.00']):
        for col,view in enumerate(['side','upper','lower','rear']):
            im=Image.open(src/f'{mount}-{pose}-{view}.png').convert('RGB').resize((550,350),Image.Resampling.LANCZOS)
            x=col*550;y=row*375
            canvas.paste(im,(x,y+25))
            draw.rectangle((x,y,x+550,y+25),fill='#182129')
            draw.text((x+9,y+2),f'{mount} | {pose} | {view}',fill='#f5f5f5',font=font)
    canvas.save(dst/f'{mount}-matrix.png',optimize=True)
