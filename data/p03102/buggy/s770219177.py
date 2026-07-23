N,M,C=map(int, input().split())
B=list(map(int, input().split()))

count=0
for i in range(N):
  A = list(map(int, input().split()))
  sum=0
  for j in range(M):
    sum+=B[j]*A[j]
    if sum+C>0:
      count+=1

print(count)