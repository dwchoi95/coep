

import sys
input = sys.stdin.readline
sys.setrecursionlimit(10**6)


A, B = map(int, input().split())

if B == 1:
    print(0)
    exit()

if A >= B:
    print(1)
    exit()

count = 2
B -= (A-1)
while True:
    if A >= B:
        print(count)
        exit()

    count += 1
    B -= (A-1)
