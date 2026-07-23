import collections

N = int(input())
A = list(map(int,input().split()))
B = collections.Counter(A).most_common()

a = B[0][0]
b = a + 1
c = a - 1

L = [a,b,c]
C = [0,0,0]

for i in range(N):
  for j in range(3):
    d = abs(A[i] - L[j])
    if d <= 1:
      C[j] += 1
    
print(max(C))