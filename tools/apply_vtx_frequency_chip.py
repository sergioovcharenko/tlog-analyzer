from pathlib import Path

path = Path("index.html")
s = path.read_text(encoding="utf-8")

marker = "function tx16NormalizedState(item){\n"
if "function tx16VtxFrequency" not in s:
    helper = """function tx16VtxFrequency(saPos,sbPos){
  const matrix={
    1:{1:5180,2:5240,3:5300},
    2:{1:5520,2:5580,3:5640},
    3:{1:5700,2:5765,3:5825}
  };
  return matrix[saPos]?.[sbPos]??null;
}

"""
    if marker not in s:
        raise SystemExit("missing tx16NormalizedState marker")
    s = s.replace(marker, helper + marker, 1)

old = "    sb:sbPos?`K${sbPos}`:'—',"
new = "    sb:sbPos?`K${sbPos} • ${tx16VtxFrequency(saPos,sbPos)} MHz`:'—',"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("missing SB normalized state marker")

path.write_text(s, encoding="utf-8")
