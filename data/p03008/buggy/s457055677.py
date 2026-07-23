import sys
input = sys.stdin.readline

N = int(input())
ga, sa, ba = map(int, input().split())
gb, sb, bb = map(int, input().split())
A = [10**18] * 3
B = [10**18] * 3
dg = abs(ga - gb)
ds = abs(sa - sb)
db = abs(ba - bb)
if ga < gb:
    A[0] = ga
elif ga > gb:
    B[0] = gb
if sa < sb:
    A[1] = sa
elif sa > sb:
    B[1] = sb
if ba < bb:
    A[2] = ba
elif ba > bb:
    B[2] = bb

def calc(X):
    res = -1
    for i in range(N+1):
        if X[0] * i > N:
            break
        M = N - X[0] * i
        j = M 
        k = (M - X[1] * j) 
        res = max(res, dg * i + ds * j + db * k)
        k = M 
        j = (M - X[2] * k) 
        res = max(res, dg * i + ds * j + db * k)
    return res

N += calc(A)
N += calc(B)
print(N)

