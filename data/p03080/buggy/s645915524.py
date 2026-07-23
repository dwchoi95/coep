

import sys

input = sys.stdin.readline
N = int(input())
s = input().split()
r = 0
b = 0

for i in range(0, len(s)):
    if s[i] == 'R':
        r += 1
    else:
        b += 1

if r > b:
    print("Yes")
else:
    print("No")
