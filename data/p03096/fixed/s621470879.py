import sys, math, itertools, collections, bisect
input = lambda: sys.stdin.buffer.readline().rstrip().decode('utf-8')
inf = float('inf') ;mod = 10**9+7
mans = inf ;ans = 0 ;count = 0 ;pro = 1

n = int(input())
C = [int(input()) for i in range(n)]
pairs = [-1]*(n+1)
data = [-1]*(2*10**5+1)
for i,ci in enumerate(C):
  if data[ci] != -1 and abs(i-data[ci]) != 1:
    pairs[data[ci]] = i
  data[ci] = i
imos = [0] * (n+1)
for i in range(n-1,-1,-1):
  
  if pairs[i] == -1:
    imos[i] = imos[i+1]
    
  else:
    j = pairs[i]
    imos[i] = imos[i+1] + imos[j] + 1
    imos[i] %= mod
  
  
  
print((imos[0]+1)%mod)

