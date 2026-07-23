
N = int(input())
A = list(map(int, input().split()))
B = list(map(int, input().split()))
count = 0
ad = 0

for i in range(N):
  if A[i] <= B[i] + ad:
    count += A[i]
    ad = max(0, B[i] - max(A[i] - ad, 0))
    
  else:
    count += B[i] + ad
    ad = 0
    

count += min(A[N], ad)     

print(count)