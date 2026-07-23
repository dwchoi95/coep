import sys
from collections import Counter

inint = lambda: int(sys.stdin.readline())
inintm = lambda: map(int, sys.stdin.readline().split())
inintl = lambda: list(inintm())
instrm = lambda: map(str, sys.stdin.readline().split())
instrl = lambda: list(instrm())

s = input()

if "N" in s and "S" in s and "E" in s and "W" in s:
    print("Yes")
    exit()

if ("N" in s and "S" in s) and ("E" not in s and "W" not in s):
    print("Yes")
    exit()

if ("E" in s and "W" in s) and ("N" not in s and "S" not in s):
    print("Yes")
    exit()

print("No")