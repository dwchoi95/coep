N=int(input())
s=list(input().split())
r=s.count('R')
b=s.count('B')
if r>b:
  print('Yes')
else:
  print('No')