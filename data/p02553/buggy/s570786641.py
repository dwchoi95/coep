a, b, c, d = map(int, input().split())

ans = -2e20
for x in [a, b, 0]:
    for y in [c,d, 0]:
        if x * y > ans:
            ans = x * y
print(ans)