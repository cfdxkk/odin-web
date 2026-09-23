"""Local reference contact sheets for motion analysis; not shipped in the site."""
import sys, urllib.request, concurrent.futures
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'work/review-python'))
import imageio.v2 as iio
from PIL import Image,ImageDraw
out=root/'work/reference-assets';out.mkdir(exist_ok=True)
clips=['907z65lvckcie','meqm0flrf1683','ns6umeu6gb7w5','3p246qbd4kwlp']
def make_clip(key):
 path=out/f'{key}.mp4'
 if not path.exists():
  urllib.request.urlretrieve(f'https://media.robertsspaceindustries.com/{key}/mp4_1280.mp4',path)
 reader=iio.get_reader(path)
 meta=reader.get_meta_data();duration=meta['duration'];fps=meta['fps']
 sheet=Image.new('RGB',(1280,760),(20,20,20));draw=ImageDraw.Draw(sheet)
 for i in range(8):
  t=(duration-.15)*i/7
  im=Image.fromarray(reader.get_data(round(t*fps)));im.thumbnail((640,170))
  x=(i%2)*640;y=(i//2)*190
  sheet.paste(im,(x,y+20));draw.text((x+10,y+3),f'{key}  {t:.2f}s',fill='white')
 reader.close();sheet.save(out/f'{key}-sequence.jpg',quality=92)
 print(key,duration,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(make_clip,clips))
