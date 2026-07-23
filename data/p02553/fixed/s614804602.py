import sys
import collections as cc
import math as mt
I=lambda:list(map(int,input().split()))
a,b,c,d=I()
print(max(a*c,a*d,b*c,b*d))