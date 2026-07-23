import sys

A, B, C = input().split()
a = int(A)
b = int(B)
c = int(C)

if a == b:
    if a == c:
        print('Yes')
        sys.exit()

print('No')
