import sys
import math
def get_array(): return list(map(int, sys.stdin.readline().strip().split()))
def get_ints(): return map(int, sys.stdin.readline().strip().split())
def input(): return sys.stdin.readline().strip()
a,b,c,d=get_ints()
x=max(a,b)
y=max(c,d)
print(x*y)