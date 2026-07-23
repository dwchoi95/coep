A, B = map(int, input().split())
ans = 0
for i in range(A, B + 1):
    i = str(i)
    if i[:2] == i[-2:]:
        ans += 1
print(ans)