import sys

a, b, k = map(int, sys.stdin.readline().split())
m = min(a, b) + 1
anslist = []
cnt = 0
for i in range(1, m):
    if a % i == 0 and b % i == 0:
        anslist.append(i)
anslist.reverse()
print(anslist[k-1])
