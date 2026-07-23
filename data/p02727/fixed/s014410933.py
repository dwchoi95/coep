X,Y,A,B,C = list(map(int,input().split()))
p = sorted(list(map(int,input().split())),reverse=True)
q = sorted(list(map(int,input().split())),reverse=True)
r = sorted(list(map(int,input().split())),reverse=True)

taberu = p[0:X] + q[0:Y] + r
taberu.sort(reverse=True)

print(sum(taberu[0:X+Y]))