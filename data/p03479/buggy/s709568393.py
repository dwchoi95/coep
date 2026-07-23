X, Y = map(int, input().split())
ans = 0
while X <= Y:
    Y /= 2
    print(Y)
    ans += 1
print(ans)