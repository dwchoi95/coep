N = int(input())
A = list(map(int, input().split()))
kisuu = 0
for i in range(N):
  if A[i] % 2 == 0:
    kisuu += 2
print(2**N-kisuu)