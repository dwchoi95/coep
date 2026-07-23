def resolve():
    n = int(input())
    a = list(map(int, input().split()))
    b = list(map(int, input().split()))

    ans = 0

    for i in range(n):
        beat_now = min(a[i], b[i])
        ans += beat_now
        beat_next = min(a[i + 1], b[i] - min(a[i], b[i]))
        ans += beat_next
        a[i + 1] -= beat_next

    print(ans)


resolve()