a, b = map(int, input().split())

ans = 0
for i in range(a, b+1):
    if str(i)[:2] == str(i)[-1:-3:-1]:
        ans += 1
print(ans)