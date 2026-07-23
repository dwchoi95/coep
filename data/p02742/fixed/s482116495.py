value = input().split()
rows = int(value[0])
colmuns = int(value[1])


if colmuns == 1:
  rows = 1
elif rows == 1:
  colmuns = 1

OddColNum = colmuns 
EvenColNum = OddColNum
if (colmuns % 2) != 0:
  OddColNum = OddColNum + 1
if (colmuns == 1):
  OddColNum = 1

OddRowCount = 0
EvenRowCount = rows 
if (rows % 2) == 0:
  OddRowCount = rows 
else:
  OddRowCount = (rows 
if (rows == 1):
  OddRowCount = 1

counts = OddRowCount * OddColNum + EvenColNum * EvenRowCount
print(counts)