

import sys
input = sys.stdin.readline
sys.setrecursionlimit(10**6)


A, B = map(int, input().split())

if A == B:
    print(1)
    exit()

count = 1
B -= A
while True:
    count += 1
    if A > B:
        print(count)
        exit()

    B -= A