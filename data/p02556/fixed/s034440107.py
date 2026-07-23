from sys import *
N = int(stdin.readline())
a,b = [],[]
for i in range(N):
    tmp = list(map(int, stdin.readline().split()))
    a.append(tmp[0] + tmp[1])
    b.append(tmp[0] - tmp[1])

a.sort()
b.sort()
print(max(a[-1]-a[0], b[-1]-b[0]))
