N = int(input())
X = list(map(int, input().split()))
min = 1000000

for i in range(1, X[N-1]+1):
    T = 0
    for j in range(N):
      T += (X[j]-i) ** 2
    if T < min:
        min = T

print(min)