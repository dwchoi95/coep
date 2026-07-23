import sys

A, B, C = input().split()

if A == B:
    if A == C:
        print('YES')
        sys.exit()

print('NO')
