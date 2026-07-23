import math
import sys
from collections import deque
import heapq
import copy
import itertools
from itertools import permutations
def mi() : return map(int,sys.stdin.readline().split())
def ii() : return int(sys.stdin.readline().rstrip())
def i() : return sys.stdin.readline().rstrip()
a=ii()
l=list(mi())
s=0
t=0
for i in l:
  s+=i
  t+=i**2
print(int((s**2-t)/2))