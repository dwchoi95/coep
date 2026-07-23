n = int(input())
a = list(input().split())

b = []
for i in range(n):
    if i % 2 == 0:
        b.append(a[i])
    else:
        b.insert(0, a[i])

print(' '.join(b))
