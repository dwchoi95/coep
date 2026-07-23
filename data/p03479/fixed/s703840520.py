from math import floor
from decimal import Decimal

A, B = list(map(int, input().split()))

num = A
c = 0
while num <= B:
    num *= 2
    c+=1

print(c)
