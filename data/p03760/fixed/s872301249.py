

import sys




read = sys.stdin.buffer.read
readline = sys.stdin.buffer.readline
readlines = sys.stdin.buffer.readlines
sys.setrecursionlimit(10 ** 7)

O, E = read().decode('utf8').split()

ans = ''
for i, j in zip(O, E):
    ans += i + j

if len(O) > len(E):
    ans += O[-1]

print(ans)
