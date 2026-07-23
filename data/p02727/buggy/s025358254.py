X, Y, a, b, c = list(map(int,input().split()))
p = list(map(int,input().split()))
q = list(map(int,input().split()))
r = list(map(int,input().split()))
s = sorted(p)[::-1][:X] + sorted(q)[::-1][:X] + r
ans = sum(s[:X + Y])
print(ans)                   