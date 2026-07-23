N = int(input())
A = list(map(int, input().split()))
sa = sum(A)
last = A[-1]
count = last
root = 1
for i in range(N):
  sa -= A[i]
  if root <= A[i]:
    print(-1)
    break
  elif root-A[i] > sa:
    root = sa + A[i]
  count+=root
  root = (root-A[i])*2
else:
  if count == 0 or root < last:
    count = -1
  print(count)
