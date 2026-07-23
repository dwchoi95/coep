N = int(input())
A = list(map(int, input().split()))
last = A[-1]
count = last
root = 1
for i in range(N):
  if i+1 == N and root > A[i+1]:
    root = last + A[i]
  elif root > (last + A[i+1])*2:
    root = (last + A[i+1])*2
  count+=root
  root = (root-A[i])*2
  if root < A[i+1]:
    print(-1)
    break
else:
  print(count)
