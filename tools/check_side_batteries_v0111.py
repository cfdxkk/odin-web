"""v0.11.1 actual-pose contact sweep, retaining the original scoped checks."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
code=(R/'tools/check_side_batteries_v0110.py').read_text()
exec(compile(code.replace("work/v0110-review","work/v0111-review"),str(__file__),'exec'))
