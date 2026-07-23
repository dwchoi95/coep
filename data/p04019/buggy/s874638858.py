import sys
from collections import Counter

inint = lambda: int(sys.stdin.readline())
inintm = lambda: map(int, sys.stdin.readline().split())
inintl = lambda: list(inintm())
instrm = lambda: map(str, sys.stdin.readline().split())
instrl = lambda: list(instrm())

s = input()

if not ("N" in s and "S" in s):
    print("No")
    exit()
    if not ("E" in s and "W" in s):
        print("No")
        exit()

print("Yes")