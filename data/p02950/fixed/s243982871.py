import sys
input = sys.stdin.readline
p=int(input())
A=[int(i) for i in input().split()]
B=[0]*p

P=[[0]*p for _ in range(p)]
for i in range(1,p): 
  for j in range(1,p):
    if j==1:
      P[i][j]=i
    else:
      P[i][j]=(P[i][j-1]*i)%p

for i in range(p):
  a=A[i]
  B[0]-=a
  for j in range(1,p):
    B[j]-=a*P[i][j]
    if j==p-1:
      B[j]+=a
B=B[::-1]
for i in range(p):
  B[i]%=p
print(*B)