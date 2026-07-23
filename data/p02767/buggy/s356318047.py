import math
N = int(input())
X = list(map(int,input().split()))
a = sum(X)
mean = a/N
b = 0
for i in range(N):
    b +=(X[i]-mean)**2
print(math.ceil(b))