from sys import *
N = int(stdin.readline())
a = []

for i in range(N):
    tmp = list(map(int, stdin.readline().split()))
    a.append(tmp)
a.sort(key = lambda k: k[0]+k[1])
best = 0
for i in range(N-1):
    best = max(best, abs(a[i][0] - a[-1][0]) + abs(a[i][1] - a[-1][1]))

print(best)
