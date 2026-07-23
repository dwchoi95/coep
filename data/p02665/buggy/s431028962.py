N = int(input())
A = list(map(int, input().split()))
last = A[-1]
count = last
root = 1
for i in range(N):
  if root > last + A[i]:
    root = last + A[i]
  count+=root
  root = (root-A[i])*2
  if root < A[i+1]:
    print(-1)
    break
else:
  print(count)