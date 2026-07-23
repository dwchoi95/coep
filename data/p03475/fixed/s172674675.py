n = int(input())
CSF = []
for i in range(n-1):
  CSF.append(list(map(int, input().split())))
for i in range(n-1):
  s = CSF[i][1]
  for j in range(i,n-1):
    s += CSF[j][0]
    if j < n-2:
      if s < CSF[j+1][1]:
        s = CSF[j+1][1]
      if s%CSF[j+1][2] != 0:
        s = (s
  print(s)
print(0)
