import math
from statistics import mean, median,variance,stdev
N = int(input())
X = list(map(int,input().split()))
a = sum(X)
ave = round(a/N)
b = 0
for i in range(N):
    b +=(X[i]-ave)**2
print(b)