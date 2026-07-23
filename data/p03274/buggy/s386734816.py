N, K = map(int,input().split())
listMap = [int(i) for i in input().split()]
minMin = float("inf")

for j in range(N - K):
    L = j
    R = j + K - 1
    sumL = abs(listMap[L]) + abs(listMap[L] - listMap[R])
    sumR = abs(listMap[R]) + abs(listMap[R] - listMap[L])
    sum = min(sumL, sumR)
    if sum < minMin:
        minMin = sum

if minMin == float("inf"):
    minMin = listMap[0]

print(minMin)