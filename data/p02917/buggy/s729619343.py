n = int(input())
a = [0] * n
b = [int(i) for i in input().split()]
ans = 0
a[0] = b[0]
a[1] = b[0]

for i in range(2, n-1):
    a[i] = min(b[i], b[i-1])
a += [b[-1]]
print(sum(a))

