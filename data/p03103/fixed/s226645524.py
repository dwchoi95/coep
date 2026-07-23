n, m = map(int, input().split())
l = []
for i in range(n):
    a, b = map(int, input().split())
    l.append((a, b))

l = sorted(l)


r = 0
for i in l:
    if i[1] < m:
        r += i[0]*i[1]
        m -= i[1]
    else:
        r += i[0]*(m)
        break
print(r)
