n, m = map(int, input().split())
t = {}
for i in range(n):
    a,b = map(int, input().split())
    t[a] = b
t = sorted(t.items())
print(t)
r = 0
for i in t:
    if i[1] < m:
        r += i[0]*i[1]
        m -= i[1]
    else:
        r += i[0]*(m)
        break
print(r)
