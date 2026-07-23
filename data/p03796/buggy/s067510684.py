import sys

M = 10**9 + 7
N = int(sys.stdin.readline().strip())

x = 1

for i in range(N):
    x = (x * i) % M

print(x)
