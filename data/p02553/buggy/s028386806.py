def resolve():
    a, b, c, d = list(map(int, input().split()))
    ans = -10 ** 9

    for x in (a, b):
        for y in (c, d):
            ans = max(ans, x * y)
    if (b == 0 and d > 0) or (b > 0 and d == 0):
        ans = 0

    print(ans)

resolve()