n, m = map(int, input().split())
l = []
for i in range(n):
    x, y, z = map(int, input().split())
    l.append([x, y, z])
ans = 0
for i in range(8):
    a = bin(i)[2:].zfill(3)
    xi = 1 if a[0] == '1' else - 1
    yi = 1 if a[1] == '1' else - 1
    zi = 1 if a[2] == '1' else - 1
    l = sorted(l, key=lambda value: value[0] * xi + value[1] * yi + value[2] * zi, reverse=True)
    ans = max(ans, abs(sum(j[0] * xi for j in l[:m])) + abs(sum(j[1]*yi for j in l[:m])) +abs(sum(j[2]*zi for j in l[:m])))
print(ans)

