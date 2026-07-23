import sys
input = sys.stdin.readline
p=int(input())
A=[int(i) for i in input().split()]
B=[0]*p

P=[[0]*p for _ in range(p)]
for i in range(1,p): 
  for j in range(p):
    if j==0:
      P[i][j]=i
    else:
      P[i][j]=(P[i][j-1]*i)%p
PP=[0]*p
for i in range(1,p):
  for j in range(1,p):
    PP[j]=(PP[j]+P[i][j])%p
for i in range(p):
  a=A[i]
  B[0]-=a
  for j in range(1,p):
    B[j]-=a*PP[j]
    if j==p-1:
      B[j]+=a
B=B[::-1]
for i in range(p):
  B[i]%=p
print(*B)