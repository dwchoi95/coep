N = int(input())
A = list(map(int, input().split()))
kisuu = 1
for i in range(N):
  if A[i] % 2 == 0:
    kisuu *= 2
print(3**N-kisuu)
