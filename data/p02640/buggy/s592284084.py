x, y = map(int, input().split())
ans = 'no'
for a in range(x + 1):
    b = x - a
    if 2*a + 4*b == y:
        ans = 'yes'
print(ans)