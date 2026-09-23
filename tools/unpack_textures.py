import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'work'/'textures'
root.mkdir(exist_ok=True)
for im in bpy.data.images:
    if any(x in im.name for x in ['panel_a_base_diff','0e955e_ship_painted_tileable']):
        im.filepath_raw=str(root/im.name);im.file_format='PNG';im.save()
        print(im.name, list(im.size),flush=True)
