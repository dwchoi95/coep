import sys

S = input()
w = int(input())

for index, s in enumerate(S):
    if index % w == 0:
        sys.stdout.write(s)

