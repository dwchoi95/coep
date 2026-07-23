

import sys




read = sys.stdin.buffer.read
readline = sys.stdin.buffer.readline
readlines = sys.stdin.buffer.readlines
sys.setrecursionlimit(10 ** 7)

O, E = read().decode('utf8').split()
ans = [i+j for i, j in zip(O, E)]

print(''.join(ans))
