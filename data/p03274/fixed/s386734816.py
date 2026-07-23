N, K = map(int,input().split())
listMap = [int(i) for i in input().split()]
minMin = float("inf")

if N == 1:
    minMin = listMap[0]

for j in range(N - (K - 1)):
    L = j
    R = j + (K - 1)
    sumL = abs(listMap[L]) + abs(listMap[L] - listMap[R])
    sumR = abs(listMap[R]) + abs(listMap[R] - listMap[L])
    sum = min(sumL, sumR)
    if sum < minMin:
        minMin = sum

print(minMin)