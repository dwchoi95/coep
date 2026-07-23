value = input().split()
rows = int(value[0])
colmuns = int(value[1])
OddColNum = colmuns 
EvenColNum = OddColNum
if (colmuns % 2) != 0:
  OddColNum = OddColNum + 1

OddRowCount = rows 
EvenRowCount = rows 
if (OddRowCount % 2) != 0:
  OddRowCount = OddRowCount + 1

counts = OddRowCount * OddColNum + EvenColNum + EvenRowCount
  
print(counts)
    