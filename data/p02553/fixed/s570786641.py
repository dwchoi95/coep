a, b, c, d = map(int, input().split())

ans = a * c
for x in [a, b]:
    for y in [c,d]:
        if x * y > ans:
            ans = x * y
print(ans)
