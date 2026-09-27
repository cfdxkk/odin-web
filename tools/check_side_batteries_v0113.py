"""Sweep the four re-anchored flank battery mechanisms through actual JS poses."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
code=(R/'tools/check_side_batteries_v0112.py').read_text()
code=code.replace('work/v0112-review','work/v0113-review')
exec(compile(code,str(__file__),'exec'))
