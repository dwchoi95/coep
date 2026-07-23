

N,M,C=map(int, input().split())

B=list(map(int, input().split()))
count=total=0

for j in range(N):
  A=list(map(int, input().split()))
  for k in range(M):
    total=total+(A[k]*B[k])
  else:
    if total+C>0:
      count+=1
      total=0

print(count)